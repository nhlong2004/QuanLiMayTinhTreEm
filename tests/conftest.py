import os
import sys

# MUST set SQLAlchemy CEXT fallback at absolute top for Windows virtual environment compatibility
os.environ["DISABLE_SQLALCHEMY_CEXT"] = "1"

import pytest
from datetime import datetime, timedelta

# Ensure python path includes project root
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if project_root not in sys.path:
    sys.path.insert(0, project_root)


from fastapi.testclient import TestClient
from server.app.main import app
from server.database.database import Base, engine, get_db

@pytest.fixture(scope="module")
def client():
    """FastAPI TestClient fixture."""
    with TestClient(app) as c:
        yield c

@pytest.fixture(scope="module")
def test_db():
    """Database session fixture."""
    Base.metadata.create_all(bind=engine)
    db = next(get_db())
    try:
        yield db
    finally:
        db.close()
