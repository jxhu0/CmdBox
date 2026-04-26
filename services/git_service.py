# services/git_service.py
import os
import gc
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
            repo = self.git.Repo(self.repo_path)
            return len(repo.remotes) > 0
        except Exception:
            return False

    def get_status(self) -> Tuple[bool, str]:
        """获取仓库状态，返回 (有更改, 状态信息)"""
        try:
            repo = self.git.Repo(self.repo_path)
            if repo.is_dirty():
                return True, "有未提交的更改"
            return False, "工作目录干净"
        except Exception as e:
            return False, f"获取状态失败: {e}"

    def commit(self, message: str = "Update data") -> Tuple[bool, str]:
        """提交更改"""
        try:
            repo = self.git.Repo(self.repo_path)
            repo.git.add(A=True)
            if repo.is_dirty():
                repo.index.commit(message)
                return True, "提交成功"
            return True, "没有需要提交的更改"
        except Exception as e:
            return False, f"提交失败: {e}"

    def pull(self) -> Tuple[bool, str]:
        """拉取远程更改，冲突时保留本地版本"""
        try:
            repo = self.git.Repo(self.repo_path)
            if not repo.remotes:
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

            # 检查是否有未完成的合并，如果有则先完成它（保留本地版本）
            merge_head_path = Path(repo.git_dir) / "MERGE_HEAD"
            if merge_head_path.exists():
                try:
                    self._resolve_conflicts(repo)
                    repo.git.add(".")
                    repo.git.commit("-m", "Merge: resolved by keeping local changes")
                except Exception:
                    # 如果无法完成合并，则中止
                    try:
                        repo.git.merge("--abort")
                    except Exception:
                        pass

            # 拉取远程更改，冲突时保留本地版本（ours）
            try:
                repo.git.pull("origin", target_branch, "--allow-unrelated-histories",
                              "--no-rebase", "-X", "ours")
            except Exception as e:
                error_msg = str(e)
                if "CONFLICT" in error_msg.upper() or "Merge conflict" in error_msg:
                    # 冲突时强制使用本地版本
                    self._resolve_conflicts(repo)
                    repo.git.add(".")
                    repo.git.commit("-m", "Merge: resolved by keeping local changes")
                    return True, "拉取完成（冲突已保留本地数据）"
                raise e

            return True, "拉取成功"
        except Exception as e:
            error_msg = str(e)
            if "no reference" in error_msg.lower() or "couldn't find remote ref" in error_msg.lower():
                return True, "远程仓库为空，跳过拉取"
            return False, f"拉取失败: {error_msg}"

    def push(self) -> Tuple[bool, str]:
        """推送到远程"""
        try:
            repo = self.git.Repo(self.repo_path)
            if not repo.remotes:
                return True, "没有配置远程仓库"

            origin = repo.remotes.origin
            target_branch = "main"

            # 如果本地是 master 分支，创建一个新的 main 分支并切换
            current_branch = repo.active_branch.name
            if current_branch != target_branch:
                try:
                    # 检查本地是否已有 main 分支
                    if target_branch not in [b.name for b in repo.branches]:
                        # 创建 main 分支
                        repo.create_head(target_branch)
                    # 切换到 main 分支
                    repo.git.checkout(target_branch)
                except Exception as e:
                    return False, f"切换分支失败: {e}"

            # 直接使用 git push 命令，确保设置上游分支
            repo.git.push("--set-upstream", "origin", target_branch)

            return True, "推送成功"
        except Exception as e:
            error_msg = str(e)
            return False, f"推送失败: {error_msg}"

    def get_remote_url(self) -> Optional[str]:
        """获取远程仓库地址"""
        if not self.is_repo():
            return None
        try:
            repo = self.git.Repo(self.repo_path)
            if repo.remotes:
                return repo.remotes.origin.url
            return None
        except Exception:
            return None

    def set_remote_url(self, url: str) -> Tuple[bool, str]:
        """设置远程仓库地址"""
        try:
            repo = self.git.Repo(self.repo_path)

            # 移除现有的 origin 远程（如果存在）
            if "origin" in [r.name for r in repo.remotes]:
                repo.delete_remote(repo.remotes.origin)

            # 添加新的远程仓库
            repo.create_remote("origin", url)

            return True, "设置成功"
        except Exception as e:
            return False, f"设置失败: {e}"

    def _resolve_conflicts(self, repo):
        """解决合并冲突：保留本地版本，远端独有的文件接受远端版本"""
        # checkout --ours 会对本地不存在的文件报错，需要逐个处理
        try:
            # 获取所有冲突文件
            conflicts = repo.index.unmerged_blobs()
            for filepath in conflicts:
                try:
                    repo.git.checkout("--ours", "--", filepath)
                except Exception:
                    # 本地不存在的文件（如远端新增的备份），接受远端版本
                    try:
                        repo.git.checkout("--theirs", "--", filepath)
                    except Exception:
                        pass
        except Exception:
            # 如果逐个处理也失败，尝试整体 checkout --ours（忽略错误）
            try:
                repo.git.checkout("--ours", ".")
            except Exception:
                pass

    def _is_first_sync(self) -> bool:
        """判断是否为首次同步（本地从未从远程拉取过数据）"""
        try:
            repo = self.git.Repo(self.repo_path)
            if not repo.remotes:
                return False
            # 检查是否有远程跟踪分支，没有则说明从未同步过
            origin = repo.remotes.origin
            try:
                origin.fetch()
            except Exception:
                return False
            remote_branch = "origin/main"
            if remote_branch not in [ref.name for ref in origin.refs]:
                return False
            # 本地有 main 分支但从未 merge 过远程 → 首次同步
            local_commits = set(c.hexsha for c in repo.iter_commits("main"))
            remote_commits = set(c.hexsha for c in repo.iter_commits("origin/main"))
            # 如果本地和远程没有共同祖先，说明是首次同步
            return not local_commits.intersection(remote_commits)
        except Exception:
            return False

    def _pull_first_sync(self) -> Tuple[bool, str]:
        """首次同步拉取：优先使用远程版本"""
        try:
            repo = self.git.Repo(self.repo_path)
            origin = repo.remotes.origin
            target_branch = "main"

            try:
                repo.git.pull("origin", target_branch, "--allow-unrelated-histories",
                              "--no-rebase", "-X", "theirs")
            except Exception as e:
                error_msg = str(e)
                if "CONFLICT" in error_msg.upper() or "Merge conflict" in error_msg:
                    # 首次同步冲突时保留远程版本
                    try:
                        repo.git.checkout("--theirs", ".")
                    except Exception:
                        pass
                    repo.git.add(".")
                    repo.git.commit("-m", "Merge: first sync, prefer remote data")
                    return True, "首次同步拉取完成（冲突已使用远程数据）"
                raise e

            return True, "首次同步拉取成功"
        except Exception as e:
            return False, f"首次同步拉取失败: {e}"

    def sync(self, data_service=None) -> Tuple[bool, str]:
        """同步：备份 -> [首次: 先pull远程] -> 提交 -> 拉取 -> 推送"""
        # 同步前先创建备份
        if data_service:
            try:
                backup_path = data_service.backup()
                print(f"已创建备份: {backup_path}")
            except Exception as e:
                print(f"备份失败: {e}")

        # 首次同步：先拉取远程数据（优先远程版本）
        if self.has_remote() and self._is_first_sync():
            success, msg = self._pull_first_sync()
            if not success:
                return False, msg

        # 提交本地更改
        success, msg = self.commit(f"Sync at {datetime.now().isoformat()}")
        if not success and "没有更改" not in msg:
            return False, msg

        # 拉取远程更改
        success, msg = self.pull()
        if not success:
            return False, msg

        # 推送
        success, msg = self.push()
        if not success:
            return False, msg

        return True, "同步完成"
