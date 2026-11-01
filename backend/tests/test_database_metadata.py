"""Database metadata import contract used before adding Alembic migrations.

The existing application imports shared modules with the backend directory on
PYTHONPATH. Keep that convention explicit so Alembic and runtime code register
ORM models against the same SQLAlchemy Base metadata.
"""
import os
import sys
from pathlib import Path

# Match the repository's current service import convention.
BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

os.environ.setdefault("DATABASE_URL", "sqlite:///./test.db")
os.environ.setdefault("REDIS_URL", "redis://localhost:6379/0")
os.environ.setdefault("JWT_SECRET_KEY", "test-only-secret")

from shared.database import Base
from services.scanner.models import Scan, ScanResult


def test_existing_orm_models_register_on_the_shared_base():
    """Alembic must see existing ORM models without creating a second Base."""
    assert Scan.__table__.metadata is Base.metadata
    assert ScanResult.__table__.metadata is Base.metadata
    assert {"scans", "scan_results"} <= set(Base.metadata.tables)


def test_scanner_relationship_metadata_is_registered():
    """Relationship targets must resolve from the same metadata registry."""
    assert Scan.__mapper__.relationships["results"].mapper.class_ is ScanResult
    assert ScanResult.__mapper__.relationships["scan"].mapper.class_ is Scan
