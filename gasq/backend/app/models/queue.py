from datetime import datetime
from sqlalchemy import DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import Column

from app.db.base_class import Base

class QueueTicket(Base):
    """
    Талон очереди: например A001, A002...
    """

    __tablename__ = "queue_tickets"

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

    # Для какого топлива/услуги человек встал: gasoline/diesel/lpg/ev
    fuel_type: Mapped[str] = mapped_column(String(50), nullable=False, index=True)

    # Номер талона: A001...
    ticket_no: Mapped[str] = mapped_column(String(10), nullable=False, index=True)

    # Статус: waiting / called / fueling / done / cancelled
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="waiting", index=True)

    # Телефон водителя (если есть)
    driver_phone: Mapped[str | None] = mapped_column(String(30), nullable=True)

    # Водительский идентификатор (позже будет user_id)
    driver_user_id: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)

    # Как создали: qr / manual / app
    source: Mapped[str] = mapped_column(String(20), nullable=False, default="app")

    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow)
    called_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    done_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    # Связи
    station = relationship("Station")
