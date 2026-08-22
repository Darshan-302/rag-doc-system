#!/usr/bin/env python3
"""Initialize PostgreSQL database schema."""

import logging
from sqlalchemy import create_engine
from src.db.models import Base
from src.config import settings

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def setup_database():
    """Create database tables from SQLAlchemy models."""
    logger.info(f"Connecting to database: {settings.DATABASE_URL}")

    try:
        engine = create_engine(settings.DATABASE_URL)

        # Create all tables
        Base.metadata.create_all(engine)

        logger.info("✓ Database tables created successfully")

        # Run migrations (Alembic)
        logger.info("Running Alembic migrations...")
        # TODO: Add Alembic migration execution

    except Exception as e:
        logger.error(f"✗ Database setup failed: {str(e)}")
        raise


if __name__ == "__main__":
    setup_database()
