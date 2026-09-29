import time
import os
import logging
from typing import Dict, Any, Optional
import jwt
import httpx
from app.core.config import settings

logger = logging.getLogger(__name__)


class GitHubAppService:
    """
    Manages the two-tier cryptographic authentication lifecycle and REST API execution
    for the Assimilate Automation GitHub App.
    """

    def __init__(self):
        self.app_id = settings.GITHUB_APP_ID
        self.private_key_path = settings.GITHUB_APP_PRIVATE_KEY_PATH
        self._cached_tokens: Dict[int, Dict[str, Any]] = {}

    def _get_private_key(self) -> str:
        """Reads RSA 2048-bit private key from file or environment."""
        if os.path.exists(self.private_key_path):
            with open(self.private_key_path, "r") as f:
                return f.read()
        # Fallback to direct environment variable if configured
        private_key = os.getenv("GITHUB_APP_PRIVATE_KEY")
        if private_key:
            return private_key.replace("\\n", "\n")
        raise FileNotFoundError(
            f"GitHub App Private Key not found at '{self.private_key_path}'. "
            "Please place 'private-key.pem' in the backend root or set GITHUB_APP_PRIVATE_KEY."
        )

    def generate_app_jwt(self) -> str:
        """
        Tier 1: Mints an RS256 JWT valid for 9 minutes using the GitHub App's RSA Private Key.
        """
        now = int(time.time())
        payload = {
            "iat": now - 60,       # 60s in the past to account for clock drift
            "exp": now + (9 * 60), # 9 minutes lifetime (GitHub max is 10 min)
            "iss": str(self.app_id)
        }
        private_key = self._get_private_key()
        return jwt.encode(payload, private_key, algorithm="RS256")

    async def get_installation_access_token(self, installation_id: int) -> str:
        """
        Tier 2: Exchanges the App JWT for a temporary, 60-minute Installation Access Token (ghs_...).
        Caches the token in memory for 50 minutes (10-minute safety buffer).
        """
        now = time.time()
        # Check cache
        if installation_id in self._cached_tokens:
            cache = self._cached_tokens[installation_id]
            if cache["expires_at"] > now + 600:  # 10 minutes buffer
                return cache["token"]

        # Mint App JWT and request new Installation Access Token
        app_jwt = self.generate_app_jwt()
        url = f"https://api.github.com/app/installations/{installation_id}/access_tokens"
        headers = {
            "Authorization": f"Bearer {app_jwt}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28"
        }

        async with httpx.AsyncClient() as client:
            response = await client.post(url, headers=headers)
            if response.status_code != 201:
                logger.error(f"GitHub token exchange failed ({response.status_code}): {response.text}")
                raise RuntimeError(f"GitHub token exchange error: {response.text}")

            data = response.json()
            token = data["token"]
            # Cache token
            self._cached_tokens[installation_id] = {
                "token": token,
                "expires_at": now + (50 * 60)  # 50 minutes
            }
            return token

    # --- REST API Operations ---

    async def create_organization_repository(
        self,
        installation_id: int,
        org_name: str,
        repo_name: str,
        description: str,
        private: bool = True
    ) -> Dict[str, Any]:
        """
        Capability 1 (Prompt-to-Repo): Creates a brand-new repository in the organization.
        """
        token = await self.get_installation_access_token(installation_id)
        url = f"https://api.github.com/orgs/{org_name}/repos"
        headers = {
            "Authorization": f"Bearer {token}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28"
        }
        payload = {
            "name": repo_name,
            "description": description,
            "private": private,
            "auto_init": True
        }

        async with httpx.AsyncClient() as client:
            response = await client.post(url, headers=headers, json=payload)
            if response.status_code not in (200, 201):
                raise RuntimeError(f"Failed to create repo '{repo_name}': {response.text}")
            return response.json()

    async def create_pull_request(
        self,
        installation_id: int,
        owner: str,
        repo: str,
        title: str,
        body: str,
        head_branch: str,
        base_branch: str = "main"
    ) -> Dict[str, Any]:
        """
        Capability 2 (PR Pipeline): Opens an automated Pull Request against the base branch.
        """
        token = await self.get_installation_access_token(installation_id)
        url = f"https://api.github.com/repos/{owner}/{repo}/pulls"
        headers = {
            "Authorization": f"Bearer {token}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28"
        }
        payload = {
            "title": title,
            "body": body,
            "head": head_branch,
            "base": base_branch
        }

        async with httpx.AsyncClient() as client:
            response = await client.post(url, headers=headers, json=payload)
            if response.status_code not in (200, 201):
                raise RuntimeError(f"Failed to create PR in '{repo}': {response.text}")
            return response.json()


github_app_service = GitHubAppService()
