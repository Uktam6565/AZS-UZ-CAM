from datetime import datetime
from sqlalchemy import DateTime, ForeignKey, Integer, String, UniqueConstraint, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import Column

from app.db.base_class import Base

class QueueTicket(Base):
    __tablename__ = "queue_tickets"

    __table_args__ = (
        # 1) claim_code должен быть уникален (секретный код)
        UniqueConstraint("claim_code", name="uq_queue_tickets_claim_code"),

        # 2) ticket_no уникален в рамках одной станции (station_id + ticket_no)
        UniqueConstraint("station_id", "ticket_no", name="uq_queue_tickets_station_ticket_no"),

        # Индексы под основные запросы (panel/list/call-next/cleanup)
        Index("ix_queue_tickets_station_status_created", "station_id", "status", "created_at"),
        Index("ix_queue_tickets_station_status_calledat", "station_id", "status", "called_at"),
        Index("ix_queue_tickets_station_pump_status", "station_id", "pump_no", "status"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)

    claim_code = Column(String(32), nullable=True, index=True)
    check_in_at = Column(DateTime, nullable=True)

    station_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("stations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    driver_state: Mapped[str] = mapped_column(String(20), nullable=False, default="idle", index=True)
    heading_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    arrived_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    fuel_type: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    ticket_no: Mapped[str] = mapped_column(String(10), nullable=False, index=True)

    # waiting / called / fueling / done / cancelled
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="waiting", index=True)

    driver_phone: Mapped[str | None] = mapped_column(String(30), nullable=True)
    driver_user_id: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)
    source: Mapped[str] = mapped_column(String(20), nullable=False, default="app")

    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow)
    called_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    done_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    # ✅ НОВОЕ: привязка к колонке (как у тебя уже показывается в panel)
    pump_no: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)

    # ✅ НОВОЕ: отмена
    cancelled_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    cancel_reason: Mapped[str | None] = mapped_column(String(50), nullable=True)

    station = relationship("Station")










