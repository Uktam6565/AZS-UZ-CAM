from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime
from app.db.session import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, index=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    role = Column(String(20), nullable=False)  # admin | operator

    is_active = Column(Integer, default=1)
    created_at = Column(DateTime, default=datetime.utcnow)
