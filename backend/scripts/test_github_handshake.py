import asyncio
import os
import sys
from pathlib import Path

# Add backend directory to sys.path so app imports work
backend_dir = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(backend_dir))
os.chdir(backend_dir)

import httpx
from app.services.github_app import GitHubAppService

async def test_handshake():
    print("=" * 65)
    print("  Testing Live GitHub App Handshake (Goal 1: Module 2.1)")
    print("=" * 65)

    service = GitHubAppService()
    
    # 1. Test JWT Generation (Tier 1)
    print("\n[Step 1] Generating RS256 App JWT using private-key.pem...")
    try:
        app_jwt = service.generate_app_jwt()
        print(f"  --> App JWT successfully minted! (Length: {len(app_jwt)} chars)")
    except Exception as e:
        print(f"  [ERROR] Failed to generate App JWT: {e}")
        return

    # 2. Test Installation Token Exchange (Tier 2)
    installation_id = 168048972
    print(f"\n[Step 2] Requesting 60-Minute Installation Access Token (ID: {installation_id})...")
    try:
        token = await service.get_installation_access_token(installation_id)
        masked_token = f"{token[:8]}...{token[-4:]}"
        print(f"  --> Token exchange successful! Token: {masked_token}")
        print(f"  --> Starts with 'ghs_': {token.startswith('ghs_')}")
    except Exception as e:
        print(f"  [ERROR] Token exchange failed: {e}")
        return

    # 3. Test API Call on Sandbox Repo
    repo_owner = "ahireayush896-gif"
    repo_name = "assimilate-sandbox"
    url = f"https://api.github.com/repos/{repo_owner}/{repo_name}/contents"
    print(f"\n[Step 3] Querying sandbox repository contents via GitHub REST API...")
    print(f"  --> Target: {repo_owner}/{repo_name}")
    
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28"
    }

    async with httpx.AsyncClient() as client:
        response = await client.get(url, headers=headers)
        if response.status_code == 200:
            items = response.json()
            file_names = [item["name"] for item in items]
            print(f"  --> Status Code: {response.status_code} OK")
            print(f"  --> Files discovered in '{repo_name}': {file_names}")
            print("\n" + "=" * 65)
            print("  SUCCESS! [DONE] GOAL 1 (MODULE 2.1) VERIFIED AND WORKING!")
            print("=" * 65)
        else:
            print(f"  [ERROR] GitHub API returned status {response.status_code}: {response.text}")

if __name__ == "__main__":
    asyncio.run(test_handshake())
