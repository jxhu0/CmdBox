# services/git_service.py
import gc
import json
import os
import sys
import subprocess
import tempfile
from typing import Optional, Tuple
from pathlib import Path
from datetime import datetime

from services.data_schema import parse_data
from services.file_lock import data_file_lock


class SyncConflict(str):
    """失败提示及用户可以确认覆盖的两个提交。"""

    def __new__(cls, message, branch, local_commit, remote_commit, remote_url):
        conflict = super().__new__(cls, message)
        conflict.branch = branch
        conflict.local_commit = local_commit
        conflict.remote_commit = remote_commit
        conflict.remote_url = remote_url
        return conflict


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
            'GIT_TERMINAL_PROMPT': '0', 'GCM_INTERACTIVE': 'Never', 'LC_ALL': 'C',
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
            info = self._run_network_command(repo, 'ls_remote', '--symref', 'origin', 'HEAD')
        for line in info.splitlines():
            if line.startswith('ref: refs/heads/') and line.endswith('\tHEAD'):
                return line.split('\t')[0].removeprefix('ref: refs/heads/')
        if not branches:
            return 'main'
        raise ValueError('无法确定远程数据分支，请配置当前分支的 origin 跟踪关系')

    def _run_network_command(self, repo, command, *args):
        """Windows 的 GitPython 不支持 execute(kill_after_timeout)，改用进程等待。"""
        operation = getattr(repo.git, command)
        if sys.platform != 'win32':
            return operation(*args, kill_after_timeout=self.NETWORK_TIMEOUT)
        process = operation(*args, as_process=True)
        try:
            stdout, stderr = process.communicate(timeout=self.NETWORK_TIMEOUT)
        except subprocess.TimeoutExpired:
            # 同时终止 git 及其 SSH/认证子进程，避免子进程持有输出管道。
            try:
                subprocess.run(['taskkill', '/PID', str(process.pid), '/T', '/F'],
                               capture_output=True, timeout=5,
                               creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
            except (OSError, subprocess.TimeoutExpired):
                pass
            finally:
                if process.poll() is None:
                    process.kill()
                process.proc.wait(timeout=5)
            raise
        if process.returncode:
            raise self.git.GitCommandError(process.args, process.returncode, stderr, stdout)
        return stdout.decode('utf-8', errors='replace') if isinstance(stdout, bytes) else stdout

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

            with data_file_lock(self.repo_path):
                remote_commit = repo.commit(remote_branch).hexsha
                return self._merge_pull(repo, target_branch, remote_commit)
        except Exception as e:
            error_msg = str(e)
            if "no reference" in error_msg.lower() or "couldn't find remote ref" in error_msg.lower():
                return True, "远程仓库为空，无可拉取的数据"
            return False, f"拉取失败: {error_msg}"

    def _merge_pull(self, repo, branch, remote_commit):
        merge_head = Path(repo.git_dir) / 'MERGE_HEAD'
        if merge_head.exists():
            return False, '存在未完成的合并，请先处理后再拉取'

        data_file = self.repo_path / 'data.json'
        had_data_file = data_file.exists()
        try:
            self._start_merge(repo, remote_commit)
        except self.git.GitCommandError:
            if not merge_head.exists():
                raise
            conflicts = set(repo.index.unmerged_blobs())
            if not self._merge_initial_data(repo, remote_commit):
                repo.git.merge('--abort')
                message = '拉取存在合并冲突，已中止合并并保留两端数据'
                if conflicts == {'data.json'}:
                    message = self._pull_conflict(repo, message, branch, remote_commit)
                return False, message

        if merge_head.exists():
            # 文本合并成功也可能产生无效 JSON 或重复记录。
            try:
                if had_data_file or data_file.exists():
                    parse_data(json.loads(data_file.read_bytes()))
            except (ValueError, TypeError, KeyError) as error:
                repo.git.merge('--abort')
                message = f'合并数据校验失败，已恢复本地数据：{error}'
                return False, self._pull_conflict(repo, message, branch, remote_commit)
            except OSError:
                repo.git.merge('--abort')
                raise
            try:
                repo.git.commit('-m', '合并远程数据')
            except Exception as error:
                repo.git.merge('--abort')
                return False, f'合并数据提交失败，已恢复本地数据：{error}'

        return True, '拉取成功'

    def _start_merge(self, repo, remote_commit):
        repo.git.merge('--allow-unrelated-histories', '--no-edit', '--no-commit', '--no-ff', remote_commit)

    @staticmethod
    def _read_committed_data(repo, commit):
        blob = repo.commit(commit).tree['data.json']
        if blob.mode not in (0o100644, 0o100755):
            raise ValueError('data.json 必须是普通文件')
        return blob.data_stream.read()

    def _pull_conflict(self, repo, message, branch, remote_commit):
        try:
            parse_data(json.loads(self._read_committed_data(repo, remote_commit)))
        except (ValueError, TypeError, KeyError, OSError):
            return message
        return SyncConflict(message, branch, repo.head.commit.hexsha, remote_commit, self.get_remote_url())

    def _merge_initial_data(self, repo, remote_branch) -> bool:
        """独立初始化的仓库首次同步时，按 ID 合并互不冲突的记录。"""
        if repo.merge_base('HEAD', remote_branch) or set(repo.index.unmerged_blobs()) != {'data.json'}:
            return False
        try:
            local = json.loads(repo.git.show(':2:data.json'))
            remote = json.loads(repo.git.show(':3:data.json'))
            parse_data(local)
            parse_data(remote)
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
            local_commit = repo.head.commit.hexsha

            # 普通推送会拒绝覆盖远程的新提交；上传不隐式拉取或强制覆盖。
            with repo.git.custom_environment(**self._network_environment()):
                self._run_network_command(repo, 'push', "--set-upstream", "origin", f"HEAD:{target_branch}")

            return True, "推送成功"
        except Exception as e:
            error_msg = str(e)
            if any(word in error_msg.lower() for word in ('timed out', 'timeout')):
                return False, '上传连接超时，本地数据已保留；请检查网络后重试'
            if any(reason in error_msg.lower() for reason in ('non-fast-forward', 'fetch first')):
                message = '远程有尚未拉取的改动，请先点击“拉取数据”，成功后再上传'
                try:
                    remote_commit = self._remote_tip(repo, target_branch)
                except Exception as error:
                    return False, f'远程有尚未拉取的改动，但无法确认远程版本：{error}'
                if remote_commit:
                    message = SyncConflict(message, target_branch, local_commit, remote_commit, self.get_remote_url())
                return False, message
            return False, f"推送失败: {error_msg}"

    def _remote_tip(self, repo, branch):
        with repo.git.custom_environment(**self._network_environment()):
            info = self._run_network_command(repo, 'ls_remote', 'origin', f'refs/heads/{branch}')
        return info.split('\t', 1)[0] if info else None

    def overwrite_data(self, data_service, conflict: SyncConflict, *, upload: bool) -> Tuple[bool, str]:
        """备份被替换的一方，用选定的 data.json 完成合并。"""
        backup = None
        try:
            repo = self._get_repo()
            branch = conflict.branch
            ref = f'refs/heads/{branch}'
            if (self.get_remote_url() != conflict.remote_url or self._target_branch(repo) != branch
                    or self._remote_tip(repo, branch) != conflict.remote_commit):
                return False, '远程版本或配置已变化，请重新发起同步'

            if upload:
                # 备份和上传必须针对同一个远程仓库。
                if repo.git.remote('get-url', '--push', '--all', 'origin') != repo.git.remote('get-url', 'origin'):
                    return False, '远程读取与推送地址不同，无法确认覆盖备份，请检查 Git 配置'
                with repo.git.custom_environment(**self._network_environment()):
                    self._run_network_command(repo, 'fetch', '--no-tags', 'origin', ref)
                if repo.commit('FETCH_HEAD').hexsha != conflict.remote_commit:
                    return False, '远程版本已变化，请重新发起同步'

            data_service.flush()
            with data_file_lock(self.repo_path):
                data_service.assert_current()
                if not self._matches_local_data(repo, conflict.local_commit):
                    return False, '本地数据版本已变化，请重新发起同步'
                if self._has_pending_git_changes(repo):
                    return False, '存在已暂存的文件或未完成的 Git 操作，请先处理后再覆盖'

                if upload:
                    local_ref = repo.git.rev_parse('--symbolic-full-name', 'HEAD')
                    if self._has_other_outgoing_files(repo, conflict):
                        return False, '本地待推送的提交涉及 data.json 以外的文件，请先处理这些提交再上传'
                    try:
                        raw = self._read_committed_data(repo, conflict.remote_commit)
                    except KeyError:
                        raw = None  # 远程可能只有初始化提交，还没有应用数据。
                    source = 'remote'
                else:
                    parse_data(json.loads(self._read_committed_data(repo, conflict.remote_commit)))
                    raw = (self.repo_path / 'data.json').read_bytes()
                    source = 'local'
                if raw is not None:
                    try:
                        backup = data_service.backup_overwritten_data(raw, source)
                    except OSError as error:
                        return False, f'覆盖前备份失败：{error}'

                if upload:
                    resolved_commit = self._build_overwrite_commit(repo, conflict)
                else:
                    self._merge_remote_overwrite(repo, conflict.remote_commit)

            local_update = ''
            if upload:
                # 新提交以远程为父提交，预期值同时防止远程在备份后前进或回退。
                try:
                    with repo.git.custom_environment(**self._network_environment()):
                        self._run_network_command(repo, 'push', f'--force-with-lease={ref}:{conflict.remote_commit}',
                                                  '--no-follow-tags', 'origin', f'{resolved_commit}:{ref}')
                except self.git.GitCommandError as error:
                    if 'stale info' in str(error).lower():
                        saved = f'。备份：{backup.name}' if backup else ''
                        return False, f'远程版本在上传前已变化，请重新发起同步{saved}'
                    raise
                local_update = self._advance_after_overwrite(repo, local_ref, conflict.local_commit, resolved_commit)
            else:
                data_service.load()
            if backup is None:
                return True, f'已上传本地数据。此前远程尚无 data.json{local_update}'
            side = '远程' if upload else '本地'
            return True, f'已覆盖{side}数据。备份可在设置中恢复：{backup.name}{local_update}'
        except Exception as error:
            saved = f'。备份：{backup.name}' if backup else ''
            return False, f'覆盖失败：{error}{saved}'

    @staticmethod
    def _matches_local_data(repo, local_commit):
        return (repo.head.commit.hexsha == local_commit
                and not repo.git.diff('--name-only', 'HEAD', '--', 'data.json'))

    @staticmethod
    def _has_pending_git_changes(repo):
        return bool(repo.git.diff('--cached', '--name-only')) or any(
            (Path(repo.git_dir) / name).exists() for name in (
                'MERGE_HEAD', 'CHERRY_PICK_HEAD', 'REVERT_HEAD', 'rebase-merge', 'rebase-apply'
            )
        )

    @staticmethod
    def _has_other_outgoing_files(repo, conflict):
        # 检查所有远程未包含的提交，也拦截曾经加入、后来删除的文件。
        return bool(repo.git.log('--format=', '--name-only', '-z', '--full-history', '-m',
                                 f'{conflict.remote_commit}..{conflict.local_commit}',
                                 '--', '.', ':(top,exclude,literal)data.json'))

    @staticmethod
    def _build_overwrite_commit(repo, conflict):
        """在临时索引里只替换远程树中的 data.json。"""
        blob = repo.commit(conflict.local_commit).tree['data.json']
        if blob.mode not in (0o100644, 0o100755):
            raise ValueError('data.json 必须是普通文件')
        parse_data(json.loads(blob.data_stream.read()))
        with tempfile.TemporaryDirectory(prefix='cmdbox-overwrite-') as directory:
            with repo.git.custom_environment(GIT_INDEX_FILE=str(Path(directory) / 'index')):
                repo.git.read_tree(conflict.remote_commit)
                repo.git.update_index('--add', '--cacheinfo', f'{blob.mode:o},{blob.hexsha},data.json')
                tree = repo.git.write_tree()
        return repo.git.commit_tree(tree, '-p', conflict.remote_commit, '-p', conflict.local_commit,
                                    '-m', '以本地数据覆盖远程数据')

    def _advance_after_overwrite(self, repo, local_ref, local_commit, resolved_commit):
        """远程已接收提交，只有本地仍适合快进时才更新本地分支。"""
        hint = '。本地分支未更新，可在处理本地改动后重新拉取'
        try:
            with data_file_lock(self.repo_path):
                if (repo.git.rev_parse('--symbolic-full-name', 'HEAD') != local_ref
                        or not self._matches_local_data(repo, local_commit)
                        or self._has_pending_git_changes(repo)):
                    return hint
                repo.git.merge('--ff-only', '--no-edit', resolved_commit)
        except (self.git.GitCommandError, OSError, ValueError):
            return hint
        return ''

    def _merge_remote_overwrite(self, repo, remote_commit):
        merge_head = Path(repo.git_dir) / 'MERGE_HEAD'
        try:
            try:
                self._start_merge(repo, remote_commit)
            except self.git.GitCommandError:
                if not merge_head.exists() or set(repo.index.unmerged_blobs()) != {'data.json'}:
                    raise
            if not merge_head.exists():
                raise ValueError('分支已同步，请重新发起同步')
            repo.git.restore(f'--source={remote_commit}', '--staged', '--worktree', '--', 'data.json')
            parse_data(json.loads((self.repo_path / 'data.json').read_bytes()))
            repo.git.commit('-m', '以远程数据覆盖本地数据')
        except Exception:
            if merge_head.exists():
                repo.git.merge('--abort')
            raise

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
        try:
            if data_service:
                # 先等待后台保存，避免持锁等待另一个需要写锁的线程。
                data_service.flush()
            with data_file_lock(self.repo_path):
                if (Path(repo.git_dir) / 'MERGE_HEAD').exists():
                    return False, '存在未完成的合并，请先处理后再上传或拉取'
                if data_service:
                    data_service.assert_current()
                    data_service.backup()
                return self.commit(f'保存本地数据 {datetime.now().isoformat()}')
        except Exception as error:
            return False, f'操作前保存或备份失败：{error}'

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
