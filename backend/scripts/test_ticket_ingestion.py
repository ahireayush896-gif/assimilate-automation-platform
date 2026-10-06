import asyncio
import os
import sys
import uuid
from pathlib import Path

# Add backend directory to sys.path
backend_dir = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(backend_dir))
os.chdir(backend_dir)

import httpx
from fastapi.testclient import TestClient
from app.main import app
from app.db.session import get_master_db, provision_tenant_database
from app.models.auth import Tenant, User
from app.core.security import get_password_hash, create_access_token

def test_ticket_ingestion_flow():
    print("=" * 65)
    print("  Testing Milestone 2: Repository & Ticket Ingestion Flow")
    print("=" * 65)

    client = TestClient(app)

    # 1. Setup / Identify Test Tenant and Admin User in Master DB
    db = next(get_master_db())
    try:
        tenant_slug = "sandbox-corp"
        tenant = db.query(Tenant).filter(Tenant.slug == tenant_slug).first()
        
        if not tenant:
            db_name = f"tenant_{tenant_slug.replace('-', '_')}_db"
            tenant = Tenant(
                organization_name="Sandbox Innovations",
                slug=tenant_slug,
                db_name=db_name,
                status="ACTIVE"
            )
            db.add(tenant)
            db.flush()

            admin = User(
                tenant_id=tenant.tenant_id,
                employee_id="EMP-001",
                name="Ayush Ahire",
                email="ayush@sandbox.io",
                password_hash=get_password_hash("SandboxPass@2026"),
                role="ORG_ADMIN",
                status="ACTIVE",
                is_active=True
            )
            db.add(admin)
            db.commit()
            db.refresh(tenant)
            db.refresh(admin)
        else:
            admin = db.query(User).filter(User.tenant_id == tenant.tenant_id).first()

        # Ensure physical tenant database is cloned from template
        provision_tenant_database(tenant.db_name)

        print(f"\n[Step 1] Authenticated Context Prepared:")
        print(f"  --> Organization: {tenant.organization_name} (Slug: {tenant.slug})")
        print(f"  --> Tenant DB: {tenant.db_name}")
        print(f"  --> Employee: {admin.name} ({admin.email}) [Role: {admin.role}]")

        # 2. Mint JWT Token
        token = create_access_token(
            subject=admin.user_id,
            tenant_id=str(tenant.tenant_id),
            tenant_slug=tenant.slug,
            db_name=tenant.db_name,
            role=admin.role,
            employee_id=admin.employee_id,
            email=admin.email
        )
        headers = {"Authorization": f"Bearer {token}"}

        # 3. Connect Sandbox Repository (Module 2.2)
        print(f"\n[Step 2] Connecting Sandbox Repository via POST /api/v1/repos/connect...")
        repo_payload = {
            "repo_name": "ahireayush896-gif/assimilate-sandbox",
            "github_repo_url": "https://github.com/ahireayush896-gif/assimilate-sandbox",
            "default_branch": "main",
            "github_installation_id": 168048972
        }
        repo_res = client.post("/api/v1/repos/connect", json=repo_payload, headers=headers)
        
        if repo_res.status_code == 201:
            repo_data = repo_res.json()
            print(f"  --> Connected successfully! Repo ID: {repo_data['repository_id']}")
        elif repo_res.status_code == 400 and "already connected" in repo_res.text:
            # Query existing
            list_res = client.get("/api/v1/repos", headers=headers)
            repo_data = list_res.json()[0]
            print(f"  --> Repository already connected. Found Repo ID: {repo_data['repository_id']}")
        else:
            print(f"  [ERROR] Failed to connect repo: {repo_res.status_code} {repo_res.text}")
            return

        repo_id = repo_data["repository_id"]

        # 4. Ingest Ticket with Attachment (Module 2.3)
        print(f"\n[Step 3] Submitting Automation Ticket via POST /api/v1/tickets...")
        
        # Create a small dummy screenshot bytes
        dummy_screenshot = b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x06\x00\x00\x00\x1f\x15c4"
        files = {
            "attachment": ("broken_checkout_button.png", dummy_screenshot, "image/png")
        }
        form_data = {
            "repo_id": repo_id,
            "prompt": "Fix checkout button flexbox alignment and z-index overlap on mobile viewports (< 768px).",
            "category": "BUG_FIX",
            "priority": "P1"
        }

        ticket_res = client.post("/api/v1/tickets", data=form_data, files=files, headers=headers)
        
        if ticket_res.status_code == 201:
            res_json = ticket_res.json()
            ticket = res_json["ticket"]
            print(f"  --> Ticket Ingested Successfully! ID: {ticket['ticket_id']}")
            print(f"  --> Category: {ticket['category']} | Priority: {ticket['priority']}")
            print(f"  --> Current Status: {ticket['status']}")
            print(f"  --> Attachments Count: {len(ticket['attachments'])}")
            if ticket['attachments']:
                print(f"      Attachment URL: {ticket['attachments'][0]['file_url']}")
        else:
            print(f"  [ERROR] Failed to create ticket: {ticket_res.status_code} {ticket_res.text}")
            return

        # 5. Fetch Full Ticket Details
        print(f"\n[Step 4] Querying Ticket Details via GET /api/v1/tickets/{ticket['ticket_id']}...")
        get_res = client.get(f"/api/v1/tickets/{ticket['ticket_id']}", headers=headers)
        if get_res.status_code == 200:
            ticket_details = get_res.json()
            print(f"  --> Status Code: 200 OK")
            print(f"  --> Prompt: '{ticket_details['prompt']}'")
            print(f"  --> Ready for AI Diff Engine (Gemini)!")
            print("\n" + "=" * 65)
            print("  SUCCESS! [DONE] MILESTONE 2 (GOAL 2) VERIFIED AND WORKING!")
            print("=" * 65)
        else:
            print(f"  [ERROR] Failed to fetch ticket: {get_res.status_code} {get_res.text}")

    finally:
        db.close()

if __name__ == "__main__":
    test_ticket_ingestion_flow()
