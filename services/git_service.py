# services/git_service.py
import gc
import json
import os
from typing import Optional, Tuple
from pathlib import Path
from datetime import datetime


class GitService:
    """Git 同步服务"""
    NETWORK_TIMEOUT = 45

    def __init__(self, repo_path: str):
        self.repo_path = Path(repo_path)
        self._git = None
        self._repo = None

    @property
    def git(self):
        """延迟加载 gitpython"""
        if self._git is None:
            import git
            self._git = git
        return self._git

    def _get_repo(self):
        """获取 Repo 对象"""
        if self._repo is None:
            self._repo = self.git.Repo(self.repo_path)
        return self._repo

    def cleanup(self):
        """清理资源，关闭 Repo 对象"""
        if self._repo is not None:
            try:
                self._repo.close()
            except Exception:
                pass
            self._repo = None
        # 强制垃圾回收，确保清理 git 子进程
        gc.collect()

    def is_repo(self) -> bool:
        """检查是否是 Git 仓库"""
        return (self.repo_path / ".git").exists()

    def init_repo(self) -> bool:
        """初始化 Git 仓库"""
        try:
            self.repo_path.mkdir(parents=True, exist_ok=True)
            with self.git.Repo.init(self.repo_path, initial_branch="main"):
                pass
            return True
        except Exception as e:
            print(f"Init repo error: {e}")
            return False

    def has_remote(self) -> bool:
        """检查是否配置了远程仓库"""
        if not self.is_repo():
            return False
        try:
            repo = self._get_repo()
            return "origin" in [remote.name for remote in repo.remotes]
        except Exception:
            return False

    def get_status(self) -> Tuple[bool, str]:
        """获取仓库状态，返回 (有更改, 状态信息)"""
        try:
            repo = self._get_repo()
            if repo.is_dirty():
                return True, "有未提交的更改"
            return False, "工作目录干净"
        except Exception as e:
            return False, f"获取状态失败: {e}"

    def commit(self, message: str = "更新数据") -> Tuple[bool, str]:
        """只提交应用数据，不包含备份或仓库中的其他文件。"""
        try:
            repo = self._get_repo()
            repo.git.add("--", "data.json")
            if not repo.head.is_valid() or repo.git.diff("HEAD", "--", "data.json"):
                repo.git.commit("--only", "-m", message, "--", "data.json")
                return True, "提交成功"
            return True, "没有需要提交的更改"
        except Exception as e:
            return False, f"提交失败: {e}"

    def _network_environment(self):
        environment = {
            'GIT_TERMINAL_PROMPT': '0', 'GCM_INTERACTIVE': 'Never',
        }
        # 保留用户选择的 SSH 客户端、密钥及 core.sshCommand。
        if not os.environ.get('GIT_SSH_COMMAND') and not os.environ.get('GIT_SSH'):
            try:
                configured = self._get_repo().git.config('--get', 'core.sshCommand')
            except self.git.GitCommandError:
                configured = None
            if not configured:
                environment['GIT_SSH_COMMAND'] = 'ssh -oBatchMode=yes -oConnectTimeout=15'
        return environment

    def _target_branch(self, repo):
        """优先使用 origin 的跟踪分支，其次远程 HEAD，兼容 main/master。"""
        if not repo.head.is_detached:
            tracking = repo.active_branch.tracking_branch()
            if tracking is not None and tracking.remote_name == 'origin':
                return tracking.remote_head
        try:
            return repo.remotes.origin.refs.HEAD.reference.remote_head
        except (AttributeError, ValueError):
            pass
        branches = [ref.remote_head for ref in repo.remotes.origin.refs if ref.remote_head != 'HEAD']
        if len(branches) == 1:
            return branches[0]
        # 没有跟踪信息时读取远程默认分支；这不会拉取或改变本地数据。
        with repo.git.custom_environment(**self._network_environment()):
            info = repo.git.ls_remote('--symref', 'origin', 'HEAD', kill_after_timeout=self.NETWORK_TIMEOUT)
        for line in info.splitlines():
            if line.startswith('ref: refs/heads/') and line.endswith('\tHEAD'):
                return line.split('\t')[0].removeprefix('ref: refs/heads/')
        if not branches:
            return 'main'
        raise ValueError('无法确定远程数据分支，请配置当前分支的 origin 跟踪关系')

    def pull(self) -> Tuple[bool, str]:
        """拉取远程更改；冲突时中止合并，保留两端原始数据。"""
        try:
            repo = self._get_repo()
            if not self.has_remote():
                return False, "未配置远程仓库"

            origin = repo.remotes.origin

            # 尝试获取远程分支信息
            try:
                with repo.git.custom_environment(**self._network_environment()):
                    origin.fetch(prune=True, kill_after_timeout=self.NETWORK_TIMEOUT)
            except Exception as e:
                error_msg = str(e)
                if any(word in error_msg.lower() for word in ('connect', 'timed out', 'timeout')):
                    return False, "网络连接失败或超时，请检查网络后重试"
                return False, f"获取远程信息失败: {error_msg}"

            target_branch = self._target_branch(repo)
            remote_branch = f"origin/{target_branch}"
            if remote_branch not in [ref.name for ref in origin.refs]:
                if not [ref for ref in origin.refs if ref.remote_head != 'HEAD']:
                    return True, "远程仓库为空，无可拉取的数据"
                return False, f'远程分支 {target_branch} 不存在，请检查分支配置'

            # 不自动提交用户尚未处理的合并。
            merge_head_path = Path(repo.git_dir) / "MERGE_HEAD"
            if merge_head_path.exists():
                return False, "存在未完成的合并，请先处理后再拉取"

            # fetch 已获取远程数据，直接合并，避免重复网络请求。
            data_file = self.repo_path / 'data.json'
            had_data_file = data_file.exists()
            try:
                repo.git.merge(remote_branch, "--allow-unrelated-histories", "--no-edit",
                               "--no-commit", "--no-ff")
            except Exception as e:
                if merge_head_path.exists():
                    if not self._merge_initial_data(repo, remote_branch):
                        repo.git.merge("--abort")
                        return False, "拉取存在合并冲突，已中止合并并保留本地和远程数据，请处理冲突后重试"
                else:
                    raise e

            if merge_head_path.exists():
                # 文本合并成功也可能产生无效 JSON 或重复记录；提交前校验。
                try:
                    if had_data_file or data_file.exists():
                        from services.data_service import DataService
                        DataService.parse_data(json.loads(data_file.read_text(encoding='utf-8')))
                    repo.git.commit('-m', '合并远程数据')
                except Exception as error:
                    repo.git.merge('--abort')
                    return False, f'合并数据校验或提交失败，已恢复本地数据: {error}'

            return True, "拉取成功"
        except Exception as e:
            error_msg = str(e)
            if "no reference" in error_msg.lower() or "couldn't find remote ref" in error_msg.lower():
                return True, "远程仓库为空，无可拉取的数据"
            return False, f"拉取失败: {error_msg}"

    def _merge_initial_data(self, repo, remote_branch) -> bool:
        """独立初始化的仓库首次同步时，按 ID 合并互不冲突的记录。"""
        if repo.merge_base('HEAD', remote_branch) or set(repo.index.unmerged_blobs()) != {'data.json'}:
            return False
        try:
            from services.data_service import DataService
            local = json.loads(repo.git.show(':2:data.json'))
            remote = json.loads(repo.git.show(':3:data.json'))
            DataService.parse_data(local)
            DataService.parse_data(remote)
            # 全新安装生成的空默认板块不需要带入已有的远程数据。
            default_boards = [('Commands', '💻'), ('Prompts', '🤖')]
            if (all(not local.get(name) for name in ('commands', 'tasks', 'questions'))
                    and [(b['name'], b.get('icon', '📁')) for b in local.get('boards', [])] == default_boards
                    and all(not b.get('description') for b in local.get('boards', []))):
                merged = remote
            else:
                merged = dict(remote)
                for name in ('boards', 'commands', 'tasks', 'questions'):
                    records = {row['id']: row for row in remote.get(name, [])}
                    for row in local.get(name, []):
                        if row['id'] in records and records[row['id']] != row:
                            return False
                        records[row['id']] = row
                    merged[name] = list(records.values())
            (self.repo_path / 'data.json').write_text(
                json.dumps(merged, ensure_ascii=False, indent=2), encoding='utf-8')
            repo.git.add('data.json')
            return True
        except Exception:
            return False

    def push(self) -> Tuple[bool, str]:
        """推送到远程"""
        try:
            repo = self._get_repo()
            if not self.has_remote():
                return False, "未配置远程仓库"

            target_branch = self._target_branch(repo)

            # 普通推送会拒绝覆盖远程的新提交；上传不隐式拉取或强制覆盖。
            with repo.git.custom_environment(**self._network_environment()):
                repo.git.push("--set-upstream", "origin", f"HEAD:{target_branch}",
                              kill_after_timeout=self.NETWORK_TIMEOUT)

            return True, "推送成功"
        except Exception as e:
            error_msg = str(e)
            if any(word in error_msg.lower() for word in ('timed out', 'timeout')):
                return False, '上传连接超时，本地数据已保留；请检查网络后重试'
            if any(reason in error_msg.lower() for reason in ("non-fast-forward", "fetch first", "[rejected]")):
                return False, "远程有尚未拉取的改动，请先点击“拉取数据”，成功后再上传"
            return False, f"推送失败: {error_msg}"

    def get_remote_url(self) -> Optional[str]:
        """获取远程仓库地址"""
        if not self.is_repo():
            return None
        try:
            repo = self._get_repo()
            if "origin" in [remote.name for remote in repo.remotes]:
                return repo.remotes.origin.url
            return None
        except Exception:
            return None

    def set_remote_url(self, url: str) -> Tuple[bool, str]:
        """设置 origin 地址；空地址移除 origin，保留其他远程仓库。"""
        try:
            repo = self._get_repo()
            url = (url or "").strip()
            has_origin = "origin" in [r.name for r in repo.remotes]
            if not url:
                if has_origin:
                    repo.delete_remote(repo.remotes.origin)
                return True, "远程地址已清除"
            if has_origin:
                repo.remotes.origin.set_url(url)
            else:
                repo.create_remote("origin", url)
            return True, "设置成功"
        except Exception as e:
            return False, f"设置失败: {e}"

    def _prepare_transfer(self, data_service) -> Tuple[bool, str]:
        """等待本地保存并备份，再提交数据，为上传或拉取做准备。"""
        if not self.has_remote():
            return False, "未配置远程仓库"
        repo = self._get_repo()
        if (Path(repo.git_dir) / "MERGE_HEAD").exists():
            return False, "存在未完成的合并，请先处理后再上传或拉取"
        if data_service:
            try:
                # 编辑操作已排队保存；不要用可能过期的内存再次覆盖磁盘。
                data_service.flush()
                data_service.assert_current()
                data_service.backup()
            except Exception as e:
                return False, f"操作前保存或备份失败: {e}"

        return self.commit(f"保存本地数据 {datetime.now().isoformat()}")

    def upload_data(self, data_service=None) -> Tuple[bool, str]:
        """提交并上传本地数据，不拉取远程改动。"""
        success, msg = self._prepare_transfer(data_service)
        if not success:
            return False, msg
        success, msg = self.push()
        return (True, "上传成功") if success else (False, msg)

    def pull_data(self, data_service=None) -> Tuple[bool, str]:
        """备份并保留本地更改，拉取后重载；不推送任何提交。"""
        success, msg = self._prepare_transfer(data_service)
        if not success:
            return False, msg
        success, msg = self.pull()
        if not success:
            return False, msg

        if data_service:
            try:
                data_service.load()
            except Exception as e:
                return False, f"拉取后加载数据失败: {e}"

        return True, msg
