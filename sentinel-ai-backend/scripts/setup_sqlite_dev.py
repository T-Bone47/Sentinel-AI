import asyncio
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

# Configure SQLite for zero-dependency local backend database
db_path = ROOT / "sentinel.db"
os.environ["DATABASE_URL"] = f"sqlite+aiosqlite:///{db_path}"
os.environ["DATABASE_URL_SYNC"] = f"sqlite:///{db_path}"

async def create_tables():
    print("Creating SQLite tables...")
    from app.database.session import engine, Base
    import app.models  # Load all 18 models

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    print("Tables created successfully!")

def run_ingestion():
    print("Ingesting all 15 datasets into SQLite database...")
    from app.ingestion.run import main as ingestion_main
    ingestion_main([])

if __name__ == "__main__":
    asyncio.run(create_tables())
    run_ingestion()
