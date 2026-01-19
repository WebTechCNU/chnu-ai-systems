from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
import os
from dotenv import load_dotenv

load_dotenv()

# ------------------------
# Resolve database path
# ------------------------

# DATABASE_URL = os.getenv("DATABASE_URL")

# if not DATABASE_URL:
#     # absolute path to /data/app.db
#     BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
#     DATA_DIR = os.path.join(BASE_DIR, "data")
#     os.makedirs(DATA_DIR, exist_ok=True)

#     DATABASE_URL = f"sqlite:///{os.path.join(DATA_DIR, 'app.db')}"

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, "data")
os.makedirs(DATA_DIR, exist_ok=True)
DATABASE_URL = f"sqlite:///{os.path.join(DATA_DIR, 'app.db')}"

print("Using database at:", DATABASE_URL)

engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False}
)

SessionLocal = sessionmaker(
    bind=engine,
    autoflush=False,
    autocommit=False
)

Base = declarative_base()
