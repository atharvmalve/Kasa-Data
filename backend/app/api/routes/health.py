from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import text
from app.db.session import get_db

router = APIRouter(prefix="/health", tags=["Health"])


@router.get("")
def health_check(db: Session = Depends(get_db)):
    """Health check returning application status and database connectivity status."""
    db_status = "healthy"
    db_error = None
    try:
        db.execute(text("SELECT 1;"))
    except Exception as e:
        db_status = "unhealthy"
        db_error = str(e)

    return {
        "status": "ok" if db_status == "healthy" else "degraded",
        "database": {
            "status": db_status,
            "engine": "YugabyteDB (YSQL)",
            "error": db_error
        },
        "version": "1.0.0"
    }

