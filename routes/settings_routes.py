# routes/settings_routes.py

print("🟢 settings_routes module starting up...", flush=True)

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from services.settings_service import SettingsService
from models.api_key_model import Base
import os  # ✅ Required for DATABASE_URL

router = APIRouter()
print("🟢 router initialized successfully", flush=True)

# --------------------------------------------------
# Database Setup
# --------------------------------------------------
DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    raise ValueError("DATABASE_URL not found in environment variables.")

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Create table if it doesn’t exist
Base.metadata.create_all(bind=engine)

def get_db():
    """Dependency that provides a DB session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# --------------------------------------------------
# Routes
# --------------------------------------------------

@router.get("/get")
def get_all_keys(db: Session = Depends(get_db)):
    """Return all stored API keys (masked)."""
    service = SettingsService(db)
    return {"settings": service.get_all_keys()}

@router.get("/get/{service_name}")
def get_single_key(service_name: str, db: Session = Depends(get_db)):
    """Return one stored API key (masked)."""
    service = SettingsService(db)
    result = service.get_key(service_name)
    if not result:
        raise HTTPException(status_code=404, detail="Service not found.")
    return result

@router.post("/update")
def update_key(service_name: str, key_value: str, db: Session = Depends(get_db)):
    """Add or update an API key."""
    service = SettingsService(db)
    return service.add_or_update_key(service_name, key_value)

@router.delete("/delete/{service_name}")
def delete_key(service_name: str, db: Session = Depends(get_db)):
    """Delete an API key."""
    service = SettingsService(db)
    return service.delete_key(service_name)

@router.post("/test/{service_name}")
def test_key(service_name: str, db: Session = Depends(get_db)):
    """Test a stored API key (basic validation)."""
    service = SettingsService(db)
    return service.test_key(service_name)
