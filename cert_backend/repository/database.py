from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from sqlalchemy.ext.declarative import declarative_base
import os

# Example: read database URL from environment variable or hardcode for testing
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql+psycopg2://cert_user:cert_password@localhost:5432/cert_db")

engine = create_engine(DATABASE_URL, echo=True)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()



# Usage example:
# with SessionLocal() as session:
#     result = session.execute("SELECT 1")
#     print(result.scalar())