# services/git_service.py
import gc
import json
from typing import Optional, Tuple
from pathlib import Path
from datetime import datetime


class GitService:
    """Git 同步服务"""

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
            self.git.Repo.init(self.repo_path, initial_branch="main")
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
        """提交更改"""
        try:
            repo = self._get_repo()
            repo.git.add(A=True)
            if repo.is_dirty():
                repo.index.commit(message)
                return True, "提交成功"
            return True, "没有需要提交的更改"
        except Exception as e:
            return False, f"提交失败: {e}"

    def pull(self) -> Tuple[bool, str]:
        """拉取远程更改；冲突时中止合并，保留两端原始数据。"""
        try:
            repo = self._get_repo()
            if not self.has_remote():
                return True, "没有配置远程仓库"

            origin = repo.remotes.origin
            target_branch = "main"

            # 尝试获取远程分支信息
            try:
                origin.fetch()
            except Exception as e:
                error_msg = str(e)
                if "Could not connect" in error_msg or "Connection" in error_msg or "timed out" in error_msg.lower():
                    return False, f"网络连接失败，请检查网络后重试"
                return False, f"获取远程信息失败: {error_msg}"

            # 检查远程是否有 main 分支
            remote_branch = f"origin/{target_branch}"
            if remote_branch not in [ref.name for ref in origin.refs]:
                return True, "远程没有对应分支，跳过拉取"

            # 不自动提交用户尚未处理的合并。
            merge_head_path = Path(repo.git_dir) / "MERGE_HEAD"
            if merge_head_path.exists():
                return False, "存在未完成的合并，请先处理后再同步"

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
                        return False, "同步存在合并冲突，已中止合并并保留本地和远程数据，请处理冲突后重试"
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
                return True, "远程仓库为空，跳过拉取"
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
                return True, "没有配置远程仓库"

            target_branch = "main"

            # 推送当前已合并的数据，不切换到可能过期的本地 main 分支。
            repo.git.push("--set-upstream", "origin", f"HEAD:{target_branch}")

            return True, "推送成功"
        except Exception as e:
            error_msg = str(e)
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

    def sync(self, data_service=None) -> Tuple[bool, str]:
        """同步：保存并备份 -> 提交 -> 拉取 -> 重载 -> 推送。"""
        if not self.has_remote():
            return False, "未配置远程仓库"
        repo = self._get_repo()
        if (Path(repo.git_dir) / "MERGE_HEAD").exists():
            return False, "存在未完成的合并，请先处理后再同步"
        # 同步前先创建备份
        if data_service:
            try:
                data_service.save()
                data_service.flush()
                data_service.backup()
            except Exception as e:
                return False, f"同步前保存或备份失败: {e}"

        # 提交本地更改
        success, msg = self.commit(f"同步数据 {datetime.now().isoformat()}")
        if not success:
            return False, msg

        # 拉取远程更改
        success, msg = self.pull()
        if not success:
            return False, msg

        # 拉取后立即更新内存；即使推送失败，后续编辑也基于已拉取的数据。
        if data_service:
            try:
                data_service.load()
            except Exception as e:
                return False, f"同步后加载数据失败: {e}"

        # 推送
        success, msg = self.push()
        if not success:
            return False, msg

        return True, "同步完成"
