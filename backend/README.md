# Assimilate Automation Platform — Core Backend

## Phase 1: Multi-Tenant Authentication & GitHub Integration

This service implements the **Master Control-Plane + Dynamic Tenant Data-Plane Architecture (Approach A)** and provides the REST API for tenant onboarding, employee role-based access control (RBAC), and GitHub App integration.

---

## 🚀 Quickstart for Local Development

### 1. Prerequisites
* **Python 3.11+** installed
* **PostgreSQL & pgAdmin** installed and running on `localhost:5432`

### 2. Database Preparation in pgAdmin
Create two databases in pgAdmin using the SQL scripts from the team brief:
1. `assimilate_master_db` (Runs Script A: `tenants`, `users`, `audit_auth_logs`, `invitations`)
2. `tenant_template_db` (Runs Script B: `repositories`, `tickets`, `attachments`, `revisions`, `executions`, `pull_requests`)

---

### 3. Virtual Environment Setup
Inside the `backend/` folder:

```bash
# Create virtual environment
python -m venv venv

# Activate on Windows PowerShell:
.\venv\Scripts\Activate.ps1

# Or on Windows Command Prompt:
.\venv\Scripts\activate.bat

# Install dependencies:
pip install -r requirements.txt
```

---

### 4. Configuration (`.env`)
Copy the example environment file:
```bash
cp .env.example .env
```
Ensure your PostgreSQL credentials in `.env` match your local pgAdmin settings:
```env
MASTER_DATABASE_URL="postgresql://postgres:postgres@localhost:5432/assimilate_master_db"
TENANT_TEMPLATE_DB_NAME="tenant_template_db"
TENANT_DATABASE_BASE_URL="postgresql://postgres:postgres@localhost:5432/"
```

---

### 5. Start the Backend Server
```bash
uvicorn app.main:app --reload --port 8000
```

Once started:
* **Interactive API Documentation (Swagger UI):**  
  👉 Open [http://localhost:8000/api/v1/docs](http://localhost:8000/api/v1/docs)
* **Health Check Endpoint:**  
  👉 Open [http://localhost:8000/health](http://localhost:8000/health)

---

## 📡 API Endpoints in Phase 1

| Method | Endpoint | Description |
| :--- | :--- | :--- |
| `POST` | `/api/v1/auth/signup` | Registers organization + Admin in Master DB, automatically clones new tenant database! |
| `POST` | `/api/v1/auth/login` | Authenticates user, issues JWT containing `role`, `employee_id`, and `db_name`. |
| `GET`  | `/api/v1/auth/me` | Returns current user profile and active organization context. |
| `POST` | `/api/v1/auth/invite` | Admin invites a new employee with `employee_id` and role. |
| `POST` | `/api/v1/auth/activate` | Employee validates activation token and sets their password. |
