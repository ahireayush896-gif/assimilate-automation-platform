import os
import sys
import getpass
from pathlib import Path
from urllib.parse import quote_plus
from sqlalchemy import create_engine, text

def run_sql_file(engine, file_path: Path):
    with open(file_path, "r", encoding="utf-8") as f:
        sql_content = f.read()
    
    raw_conn = engine.raw_connection()
    try:
        with raw_conn.cursor() as cursor:
            cursor.execute(sql_content)
        raw_conn.commit()
    finally:
        raw_conn.close()

def setup_databases():
    print("=" * 65)
    print("  Assimilate Automation Platform — PostgreSQL Database Setup")
    print("=" * 65)
    
    host = os.getenv("PGHOST", "localhost")
    port = os.getenv("PGPORT", "5432")
    user = os.getenv("PGUSER", "postgres")
    
    password = os.getenv("PGPASSWORD")
    if not password:
        password = getpass.getpass(f"Enter PostgreSQL password for user '{user}': ")

    encoded_password = quote_plus(password)
    base_url = f"postgresql://{user}:{encoded_password}@{host}:{port}/"
    maintenance_url = f"{base_url}postgres"

    print(f"\n[1/5] Connecting to PostgreSQL at {host}:{port}...")
    try:
        m_engine = create_engine(maintenance_url, isolation_level="AUTOCOMMIT")
        with m_engine.connect() as conn:
            conn.execute(text("SELECT 1;"))
        print("  --> Connection successful!")
    except Exception as e:
        print(f"  [ERROR] Could not connect to PostgreSQL: {e}")
        sys.exit(1)

    # 1. Create assimilate_master_db
    print("\n[2/5] Creating 'assimilate_master_db'...")
    with m_engine.connect() as conn:
        exists = conn.execute(text("SELECT 1 FROM pg_database WHERE datname = 'assimilate_master_db'")).scalar()
        if not exists:
            conn.execute(text('CREATE DATABASE "assimilate_master_db";'))
            print("  --> 'assimilate_master_db' created successfully.")
        else:
            print("  --> 'assimilate_master_db' already exists.")

    # 2. Create tenant_template_db
    print("\n[3/5] Creating 'tenant_template_db'...")
    with m_engine.connect() as conn:
        exists = conn.execute(text("SELECT 1 FROM pg_database WHERE datname = 'tenant_template_db'")).scalar()
        if not exists:
            conn.execute(text('CREATE DATABASE "tenant_template_db";'))
            print("  --> 'tenant_template_db' created successfully.")
        else:
            print("  --> 'tenant_template_db' already exists.")

    scripts_dir = Path(__file__).parent

    # 3. Apply Schema A to assimilate_master_db
    print("\n[4/5] Executing Script A (Master DB Tables)...")
    master_engine = create_engine(f"{base_url}assimilate_master_db")
    run_sql_file(master_engine, scripts_dir / "01_init_master_db.sql")
    print("  --> Control Plane tables created (tenants, users, audit_auth_logs, invitations).")

    # 4. Apply Schema B to tenant_template_db
    print("\n[5/5] Executing Script B (Tenant Template DB Tables)...")
    template_engine = create_engine(f"{base_url}tenant_template_db")
    run_sql_file(template_engine, scripts_dir / "02_init_tenant_template_db.sql")
    print("  --> Tenant Data Plane tables created (repositories, tickets, attachments, revisions, executions, pull_requests).")

    # 5. Generate / Update .env file
    env_file = scripts_dir.parent / ".env"
    env_example = scripts_dir.parent / ".env.example"
    
    if not env_file.exists() and env_example.exists():
        with open(env_example, "r", encoding="utf-8") as f:
            env_content = f.read()
        
        env_content = env_content.replace(
            "postgresql://postgres:postgres@localhost:5432/assimilate_master_db",
            f"postgresql://{user}:{encoded_password}@{host}:{port}/assimilate_master_db"
        )
        env_content = env_content.replace(
            "postgresql://postgres:postgres@localhost:5432/",
            f"postgresql://{user}:{encoded_password}@{host}:{port}/"
        )
        with open(env_file, "w", encoding="utf-8") as f:
            f.write(env_content)
        print(f"\n[INFO] Generated backend/.env with your database credentials.")

    print("\n" + "=" * 65)
    print("  ALL DATABASES & TABLES INITIALIZED SUCCESSFULLY! 🚀")
    print("=" * 65)

if __name__ == "__main__":
    setup_databases()
