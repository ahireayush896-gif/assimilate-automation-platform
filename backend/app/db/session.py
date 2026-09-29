import logging
from typing import Dict, Generator
from sqlalchemy import create_engine, text
from sqlalchemy.orm import declarative_base, sessionmaker, Session
from app.core.config import settings

logger = logging.getLogger(__name__)

Base = declarative_base()

# 1. Master Control-Plane Database Engine
master_engine = create_engine(
    settings.MASTER_DATABASE_URL,
    pool_size=10,
    max_overflow=20,
    pool_pre_ping=True
)

MasterSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=master_engine)


def get_master_db() -> Generator[Session, None, None]:
    """Dependency for Master Database session."""
    db = MasterSessionLocal()
    try:
        yield db
    finally:
        db.close()


# 2. Dynamic Tenant Database Provisioning
def provision_tenant_database(db_name: str, template_db: str = settings.TENANT_TEMPLATE_DB_NAME) -> bool:
    """
    Dynamically clones the template database to create a new tenant database in PostgreSQL.
    Note: PostgreSQL requires AUTOCOMMIT isolation level for CREATE DATABASE.
    """
    # Connect to the default postgres maintenance database to execute CREATE DATABASE
    maintenance_url = f"{settings.TENANT_DATABASE_BASE_URL}postgres"
    admin_engine = create_engine(maintenance_url, isolation_level="AUTOCOMMIT")

    try:
        with admin_engine.connect() as conn:
            # Check if database already exists
            check_sql = text("SELECT 1 FROM pg_database WHERE datname = :dbname")
            exists = conn.execute(check_sql, {"dbname": db_name}).scalar()

            if not exists:
                logger.info(f"Cloning template database '{template_db}' to '{db_name}'...")
                # Disconnect any idle connections to template database before cloning
                conn.execute(text(f"""
                    SELECT pg_terminate_backend(pg_stat_activity.pid)
                    FROM pg_stat_activity
                    WHERE pg_stat_activity.datname = '{template_db}'
                      AND pid <> pg_backend_pid();
                """))
                # Clone the database
                conn.execute(text(f'CREATE DATABASE "{db_name}" WITH TEMPLATE "{template_db}";'))
                logger.info(f"Successfully provisioned tenant database: '{db_name}'")
                return True
            else:
                logger.info(f"Tenant database '{db_name}' already exists.")
                return True
    except Exception as e:
        logger.error(f"Failed to provision tenant database '{db_name}': {str(e)}")
        raise RuntimeError(f"Database provisioning failed: {str(e)}")
    finally:
        admin_engine.dispose()


# 3. Dynamic Tenant Database Connection Pooler / Cache
_tenant_engines: Dict[str, any] = {}


def get_tenant_session(db_name: str) -> Session:
    """
    Provides a dynamic session connected to a specific tenant database.
    Reuses cached engines to maintain performance.
    """
    if db_name not in _tenant_engines:
        tenant_url = f"{settings.TENANT_DATABASE_BASE_URL}{db_name}"
        _tenant_engines[db_name] = create_engine(
            tenant_url,
            pool_size=5,
            max_overflow=10,
            pool_recycle=300,
            pool_pre_ping=True
        )

    engine = _tenant_engines[db_name]
    TenantSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    return TenantSessionLocal()
