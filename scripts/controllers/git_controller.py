import os
import subprocess
from pathlib import Path
from typing import Optional, Tuple

from scripts.controllers.utils.decorators.try_catch import try_catch
from scripts.logging_config import get_utility_logger
from scripts.controllers.utils.singleton import SingletonMeta


class GitController(metaclass=SingletonMeta):

    def __init__(self):
        self.logger = get_utility_logger('GitController')

    def _run_command(self, command: list[str], cwd: Optional[str] = None) -> Tuple[bool, str, str]:
        try:
            result = subprocess.run(
                command,
                cwd=cwd,
                capture_output=True,
                text=True,
                shell=False
            )
            success = result.returncode == 0
            return success, result.stdout.strip(), result.stderr.strip()
        except Exception as e:
            self.logger.error(f"Command execution failed: {str(e)}")
            return False, "", str(e)

    @try_catch
    def is_git_repo(self, path: str) -> bool:
        git_dir = os.path.join(path, '.git')
        return os.path.exists(git_dir) and os.path.isdir(git_dir)

    @try_catch
    def clone_repository(self, repo_url: str, target_path: str, remove_existing: bool = False) -> bool:
        target_path = str(Path(target_path))

        if os.path.exists(target_path):
            if not remove_existing:
                self.logger.error(f"Target path already exists: {target_path}")
                return False

            self.logger.info(f"Removing existing directory: {target_path}")
            import shutil
            shutil.rmtree(target_path)

        self.logger.info(f"Cloning {repo_url} into {target_path}")

        parent_dir = str(Path(target_path).parent)
        target_name = Path(target_path).name

        success, stdout, stderr = self._run_command(
            ['git', 'clone', repo_url, target_name],
            cwd=parent_dir
        )

        if success:
            self.logger.info(f"Successfully cloned repository to {target_path}")
            return True
        else:
            self.logger.error(f"Failed to clone repository: {stderr}")
            return False

    @try_catch
    def fetch_origin(self, repo_path: str) -> bool:
        self.logger.info("Fetching remote branches from origin")
        success, stdout, stderr = self._run_command(
            ['git', 'fetch', 'origin'],
            cwd=repo_path
        )

        if success:
            self.logger.info("Successfully fetched remote branches")
            return True
        else:
            self.logger.error(f"Failed to fetch: {stderr}")
            return False

    @try_catch
    def branch_exists_on_remote(self, repo_path: str, branch_name: str) -> bool:
        success, stdout, stderr = self._run_command(
            ['git', 'ls-remote', '--heads', 'origin', branch_name],
            cwd=repo_path
        )

        if success and branch_name in stdout:
            self.logger.info(f"Branch '{branch_name}' exists on remote")
            return True
        else:
            self.logger.warning(f"Branch '{branch_name}' does not exist on remote")
            return False

    @try_catch
    def get_current_branch(self, repo_path: str) -> Optional[str]:
        success, stdout, stderr = self._run_command(
            ['git', 'rev-parse', '--abbrev-ref', 'HEAD'],
            cwd=repo_path
        )

        if success:
            return stdout
        else:
            self.logger.error(f"Failed to get current branch: {stderr}")
            return None

    @try_catch
    def branch_exists_locally(self, repo_path: str, branch_name: str) -> bool:
        success, stdout, stderr = self._run_command(
            ['git', 'show-ref', '--verify', '--quiet', f'refs/heads/{branch_name}'],
            cwd=repo_path
        )

        return success

    @try_catch
    def checkout_branch(self, repo_path: str, branch_name: str, create_from_remote: bool = False) -> bool:
        if create_from_remote:
            self.logger.info(f"Creating and checking out branch '{branch_name}' from origin")
            success, stdout, stderr = self._run_command(
                ['git', 'checkout', '-b', branch_name, f'origin/{branch_name}'],
                cwd=repo_path
            )
        else:
            self.logger.info(f"Checking out branch '{branch_name}'")
            success, stdout, stderr = self._run_command(
                ['git', 'checkout', branch_name],
                cwd=repo_path
            )

        if success:
            self.logger.info(f"Successfully checked out to branch '{branch_name}'")
            return True
        else:
            self.logger.error(f"Failed to checkout: {stderr}")
            return False

    @try_catch
    def pull_from_origin(self, repo_path: str, branch_name: str) -> bool:
        self.logger.info(f"Pulling latest changes from origin/{branch_name}")
        success, stdout, stderr = self._run_command(
            ['git', 'pull', 'origin', branch_name],
            cwd=repo_path
        )

        if success:
            self.logger.info("Successfully pulled latest changes")
            return True
        else:
            self.logger.error(f"Failed to pull: {stderr}")
            return False

    @try_catch
    def create_and_push_branch(self, repo_path: str, branch_name: str) -> bool:
        self.logger.info(f"Creating new branch '{branch_name}'")
        success, stdout, stderr = self._run_command(
            ['git', 'checkout', '-b', branch_name],
            cwd=repo_path
        )

        if not success:
            self.logger.error(f"Failed to create branch: {stderr}")
            return False

        self.logger.info(f"Pushing new branch '{branch_name}' to origin")
        success, stdout, stderr = self._run_command(
            ['git', 'push', '-u', 'origin', branch_name],
            cwd=repo_path
        )

        if success:
            self.logger.info(f"Successfully created and pushed branch '{branch_name}'")
            return True
        else:
            self.logger.error(f"Failed to push branch: {stderr}")
            return False

    @try_catch
    def find_available_branch_name(self, repo_path: str, base_branch_name: str) -> str:
        if not self.branch_exists_on_remote(repo_path, base_branch_name):
            return base_branch_name

        version = 1
        while True:
            versioned_name = f"{base_branch_name}-v{version}"
            if not self.branch_exists_on_remote(repo_path, versioned_name):
                self.logger.info(f"Branch '{base_branch_name}' exists, using '{versioned_name}'")
                return versioned_name
            version += 1

    @try_catch
    def checkout_and_sync_branch(
        self,
        repo_path: str,
        branch_name: str,
        repo_url: Optional[str] = None,
        clone_if_missing: bool = False
    ) -> bool:
        if not self.is_git_repo(repo_path):
            if clone_if_missing and repo_url:
                self.logger.info(f"Repository not found at {repo_path}, cloning...")
                if not self.clone_repository(repo_url, repo_path, remove_existing=True):
                    return False
            else:
                self.logger.error(f"Repository not found at {repo_path}")
                return False

        if not self.fetch_origin(repo_path):
            return False

        available_branch = self.find_available_branch_name(repo_path, branch_name)

        if available_branch != branch_name:
            self.logger.info(f"Creating new versioned branch: {available_branch}")
            return self.create_and_push_branch(repo_path, available_branch)

        if not self.branch_exists_on_remote(repo_path, branch_name):
            self.logger.info(f"Branch '{branch_name}' does not exist, creating it")
            return self.create_and_push_branch(repo_path, branch_name)

        current_branch = self.get_current_branch(repo_path)

        if current_branch == branch_name:
            self.logger.info(f"Already on branch '{branch_name}', pulling latest changes")
            return self.pull_from_origin(repo_path, branch_name)

        if self.branch_exists_locally(repo_path, branch_name):
            if not self.checkout_branch(repo_path, branch_name):
                return False
            return self.pull_from_origin(repo_path, branch_name)
        else:
            return self.checkout_branch(repo_path, branch_name, create_from_remote=True)


git_controller = GitController()
