from datetime import datetime

from sqlalchemy import Boolean, DateTime, Integer, String
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import Index

from app.db.base_class import Base


class Notification(Base):
    __tablename__ = "notifications"

    __table_args__ = (
        Index("ix_notifications_ticket_id_id", "ticket_id", "id"),
        Index("ix_notifications_station_id_id", "station_id", "id"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)

    station_id: Mapped[int] = mapped_column(Integer, index=True)
    ticket_id: Mapped[int] = mapped_column(Integer, index=True)

    type: Mapped[str] = mapped_column(String(50), nullable=False)
    message: Mapped[str] = mapped_column(String(255), nullable=False)

    is_read: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow)