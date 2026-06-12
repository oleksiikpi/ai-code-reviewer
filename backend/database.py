import os
from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    raise RuntimeError("Помилка конфігурації: DATABASE_URL не задано у файлі .env")

engine = create_engine(DATABASE_URL)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

def get_db():
    """Генератор залежностей для забезпечення ізольованої сесії БД для кожного запиту."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()