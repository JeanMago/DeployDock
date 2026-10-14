import os
import shutil

# Auto-detect git executable if not in system PATH
if not shutil.which("git"):
    candidates = [
        "C:\\Program Files\\Git\\cmd\\git.exe",
        "C:\\Program Files (x86)\\Git\\cmd\\git.exe",
    ]
    gh_desktop = os.path.expanduser("~\\AppData\\Local\\GitHubDesktop")
    if os.path.exists(gh_desktop):
        for entry in sorted(os.listdir(gh_desktop), reverse=True):
            candidate = os.path.join(gh_desktop, entry, "resources", "app", "git", "cmd", "git.exe")
            if os.path.isfile(candidate):
                candidates.insert(0, candidate)

    for c in candidates:
        if os.path.isfile(c):
            os.environ["GIT_PYTHON_GIT_EXECUTABLE"] = c
            git_dir = os.path.dirname(c)
            if git_dir not in os.environ.get("PATH", ""):
                os.environ["PATH"] = git_dir + os.pathsep + os.environ.get("PATH", "")
            break

os.environ.setdefault("GIT_PYTHON_REFRESH", "quiet")

import git
import asyncio
from typing import Dict, Any

class GitService:
    async def clone_repo(self, repo_url: str, dest_path: str, branch: str = 'main') -> str:
        def _clone():
            if not os.path.exists(dest_path):
                repo = git.Repo.clone_from(repo_url, dest_path, branch=branch)
            else:
                repo = git.Repo(dest_path)
                repo.remotes.origin.fetch()
                repo.git.checkout(branch)
                repo.remotes.origin.pull()
            return repo.head.commit.hexsha
        return await asyncio.to_thread(_clone)

    async def pull_repo(self, repo_path: str, branch: str = 'main') -> str:
        def _pull():
            repo = git.Repo(repo_path)
            repo.remotes.origin.fetch()
            repo.git.checkout(branch)
            repo.remotes.origin.pull()
            return repo.head.commit.hexsha
        return await asyncio.to_thread(_pull)

    async def get_current_commit(self, repo_path: str) -> Dict[str, Any]:
        def _get():
            repo = git.Repo(repo_path)
            commit = repo.head.commit
            return {
                "sha": commit.hexsha,
                "message": commit.message,
                "author": commit.author.name,
                "timestamp": commit.committed_datetime.isoformat()
            }
        return await asyncio.to_thread(_get)
