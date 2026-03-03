from datetime import datetime

from sqlalchemy import Column, DateTime, Integer, String, Text, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import JSONB

# ВАЖНО: Base берем из app.db.session, потому что у тебя Base_class нет
from app.db.session import Base


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True, index=True)

    # кто сделал действие (может быть None если, например, системное)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)

    # где / что сделали
    action = Column(String(64), nullable=False, index=True)          # например: "queue.call_next"
    entity = Column(String(64), nullable=True, index=True)           # например: "QueueTicket"
    entity_id = Column(Integer, nullable=True, index=True)           # ticket_id
    station_id = Column(Integer, nullable=True, index=True)

    # дополнительные данные (любой JSON)
    meta = Column(JSONB, nullable=True)

    # человекочитаемое описание
    message = Column(Text, nullable=True)

    created_at = Column(DateTime, nullable=False, default=datetime.utcnow, index=True)

    user = relationship("User", lazy="selectin", foreign_keys=[user_id])
