import os
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
