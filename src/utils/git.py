"""Git operations utility module.

This module provides utilities for Git repository operations,
including cloning, committing, branching, and status checking.
"""

import os
import subprocess
from typing import Dict, Any, Optional, List, Tuple, Union
from pathlib import Path
from dataclasses import dataclass

from ..core.execution import ExecutionResult, execution_context_manager


@dataclass
class GitStatus:
    """Git repository status information."""

    is_git_repo: bool
    current_branch: Optional[str] = None
    is_dirty: bool = False
    untracked_files: List[str] = None
    modified_files: List[str] = None
    staged_files: List[str] = None
    ahead_behind: Optional[Tuple[int, int]] = None  # (ahead, behind)

    def __post_init__(self):
        if self.untracked_files is None:
            self.untracked_files = []
        if self.modified_files is None:
            self.modified_files = []
        if self.staged_files is None:
            self.staged_files = []


@dataclass
class GitCommit:
    """Git commit information."""

    hash: str
    author: str
    email: str
    message: str
    timestamp: str
    files_changed: List[str]


class GitOperations:
    """Git operations utility class."""

    def __init__(self, repo_path: Optional[Union[str, Path]] = None):
        """Initialize Git operations.

        Args:
            repo_path: Path to Git repository (defaults to current directory)
        """
        self.repo_path = Path(repo_path) if repo_path else Path.cwd()

    async def get_status(self) -> GitStatus:
        """Get the status of the Git repository.

        Returns:
            GitStatus: Repository status information
        """
        if not self._is_git_repository():
            return GitStatus(is_git_repo=False)

        status = GitStatus(is_git_repo=True)

        # Get current branch
        try:
            result = await self._run_git_command(["branch", "--show-current"])
            status.current_branch = result.stdout.strip() if result.success else None
        except Exception:
            status.current_branch = None

        # Check if working directory is dirty
        try:
            result = await self._run_git_command(["status", "--porcelain"])
            if result.success and result.stdout.strip():
                status.is_dirty = True

                # Parse status output
                lines = result.stdout.strip().split('\n')
                for line in lines:
                    if not line.strip():
                        continue
                    status_code = line[:2]
                    filename = line[3:]

                    if status_code[0] in ['M', 'A', 'D', 'R', 'C', 'U']:
                        status.staged_files.append(filename)
                    if status_code[1] in ['M', 'A', 'D', 'R', 'C', 'U']:
                        status.modified_files.append(filename)
                    elif status_code == '??':
                        status.untracked_files.append(filename)
        except Exception:
            pass

        # Get ahead/behind information
        try:
            result = await self._run_git_command(["rev-list", "--count", "--left-right", "@{upstream}...HEAD"])
            if result.success:
                parts = result.stdout.strip().split()
                if len(parts) == 2:
                    behind = int(parts[0])
                    ahead = int(parts[1])
                    status.ahead_behind = (ahead, behind)
        except Exception:
            pass

        return status

    async def clone_repository(
        self,
        url: str,
        target_path: Optional[Union[str, Path]] = None,
        branch: Optional[str] = None,
        depth: Optional[int] = None
    ) -> ExecutionResult:
        """Clone a Git repository.

        Args:
            url: Repository URL to clone
            target_path: Target directory (defaults to repo name)
            branch: Branch to clone
            depth: Clone depth for shallow clone

        Returns:
            ExecutionResult: Clone operation result
        """
        cmd = ["git", "clone"]

        if branch:
            cmd.extend(["--branch", branch])

        if depth:
            cmd.extend(["--depth", str(depth)])

        cmd.append(url)

        if target_path:
            cmd.append(str(target_path))

        return await self._run_git_command(cmd, cwd=self.repo_path.parent)

    async def create_branch(self, branch_name: str, checkout: bool = True) -> ExecutionResult:
        """Create a new Git branch.

        Args:
            branch_name: Name of the new branch
            checkout: Whether to checkout the new branch

        Returns:
            ExecutionResult: Branch creation result
        """
        cmd = ["git", "checkout", "-b", branch_name] if checkout else ["git", "branch", branch_name]
        return await self._run_git_command(cmd)

    async def checkout_branch(self, branch_name: str) -> ExecutionResult:
        """Checkout a Git branch.

        Args:
            branch_name: Name of the branch to checkout

        Returns:
            ExecutionResult: Checkout result
        """
        return await self._run_git_command(["git", "checkout", branch_name])

    async def add_files(self, files: Optional[List[str]] = None) -> ExecutionResult:
        """Add files to Git staging area.

        Args:
            files: List of files to add (adds all if None)

        Returns:
            ExecutionResult: Add operation result
        """
        cmd = ["git", "add"]
        if files:
            cmd.extend(files)
        else:
            cmd.append(".")
        return await self._run_git_command(cmd)

    async def commit_changes(
        self,
        message: str,
        author: Optional[str] = None,
        email: Optional[str] = None
    ) -> ExecutionResult:
        """Commit staged changes.

        Args:
            message: Commit message
            author: Author name
            email: Author email

        Returns:
            ExecutionResult: Commit result
        """
        cmd = ["git", "commit", "-m", message]

        # Set author if provided
        env = os.environ.copy()
        if author and email:
            env["GIT_AUTHOR_NAME"] = author
            env["GIT_AUTHOR_EMAIL"] = email
            env["GIT_COMMITTER_NAME"] = author
            env["GIT_COMMITTER_EMAIL"] = email

        return await self._run_git_command(cmd, env=env)

    async def push_changes(self, remote: str = "origin", branch: Optional[str] = None) -> ExecutionResult:
        """Push changes to remote repository.

        Args:
            remote: Remote name
            branch: Branch to push (uses current if None)

        Returns:
            ExecutionResult: Push result
        """
        cmd = ["git", "push", remote]
        if branch:
            cmd.append(branch)
        return await self._run_git_command(cmd)

    async def pull_changes(self, remote: str = "origin", branch: Optional[str] = None) -> ExecutionResult:
        """Pull changes from remote repository.

        Args:
            remote: Remote name
            branch: Branch to pull (uses current if None)

        Returns:
            ExecutionResult: Pull result
        """
        cmd = ["git", "pull", remote]
        if branch:
            cmd.append(branch)
        return await self._run_git_command(cmd)

    async def get_commits(
        self,
        count: int = 10,
        branch: Optional[str] = None
    ) -> List[GitCommit]:
        """Get recent commits from repository.

        Args:
            count: Number of commits to retrieve
            branch: Branch to get commits from

        Returns:
            List of GitCommit objects
        """
        cmd = [
            "git", "log",
            f"-{count}",
            "--pretty=format:%H|%an|%ae|%s|%ad",
            "--date=iso",
            "--name-only"
        ]

        if branch:
            cmd.append(branch)

        result = await self._run_git_command(cmd)
        if not result.success:
            return []

        commits = []
        lines = result.stdout.strip().split('\n\n')
        current_commit = None

        for line in lines:
            if not line.strip():
                continue

            parts = line.split('\n', 1)
            if len(parts) >= 1:
                commit_info = parts[0].split('|')
                if len(commit_info) >= 5:
                    current_commit = GitCommit(
                        hash=commit_info[0],
                        author=commit_info[1],
                        email=commit_info[2],
                        message=commit_info[3],
                        timestamp=commit_info[4],
                        files_changed=[]
                    )

                    if len(parts) > 1:
                        files = [f.strip() for f in parts[1].split('\n') if f.strip()]
                        current_commit.files_changed = files

                    commits.append(current_commit)

        return commits

    async def create_tag(self, tag_name: str, message: Optional[str] = None) -> ExecutionResult:
        """Create a Git tag.

        Args:
            tag_name: Name of the tag
            message: Tag message

        Returns:
            ExecutionResult: Tag creation result
        """
        cmd = ["git", "tag"]
        if message:
            cmd.extend(["-a", tag_name, "-m", message])
        else:
            cmd.append(tag_name)
        return await self._run_git_command(cmd)

    async def get_diff(self, commit1: Optional[str] = None, commit2: Optional[str] = None) -> str:
        """Get diff between commits or working directory.

        Args:
            commit1: First commit (HEAD if None)
            commit2: Second commit (working directory if None)

        Returns:
            Diff output as string
        """
        cmd = ["git", "diff"]
        if commit1:
            cmd.append(commit1)
        if commit2:
            cmd.append(commit2)

        result = await self._run_git_command(cmd)
        return result.stdout if result.success else ""

    def _is_git_repository(self) -> bool:
        """Check if the current directory is a Git repository.

        Returns:
            True if it's a Git repository
        """
        git_dir = self.repo_path / ".git"
        return git_dir.exists() and git_dir.is_dir()

    async def _run_git_command(
        self,
        cmd: List[str],
        cwd: Optional[Path] = None,
        env: Optional[Dict[str, str]] = None
    ) -> ExecutionResult:
        """Run a Git command.

        Args:
            cmd: Git command to run
            cwd: Working directory
            env: Environment variables

        Returns:
            ExecutionResult: Command execution result
        """
        if cwd is None:
            cwd = self.repo_path

        # Create execution environment
        execution_id = f"git_{hash(str(cmd))}"

        async with execution_context_manager.create_execution_context(
            execution_id,
            base_workspace=cwd,
            isolation_mode="subprocess"
        ) as env_context:
            return await execution_context_manager.execute_with_isolation(
                execution_id,
                cmd,
                env_context,
                timeout=300,  # 5 minutes timeout for Git operations
                capture_output=True
            )


# Convenience functions
async def clone_repo(url: str, target_path: Optional[str] = None) -> ExecutionResult:
    """Clone a Git repository.

    Args:
        url: Repository URL
        target_path: Target path

    Returns:
        Clone result
    """
    git_ops = GitOperations()
    return await git_ops.clone_repository(url, target_path)


async def get_repo_status(repo_path: Optional[str] = None) -> GitStatus:
    """Get Git repository status.

    Args:
        repo_path: Repository path

    Returns:
        Repository status
    """
    git_ops = GitOperations(repo_path)
    return await git_ops.get_status()