from sqlmodel import SQLModel
from src.db.database import engine

def init_db():
    SQLModel.metadata.drop_all(bind=engine)  # ⚠️ Drops all tables
    SQLModel.metadata.create_all(bind=engine)

if __name__ == "__main__":
    init_db()