from datetime import datetime
from sqlalchemy import DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base_class import Base


class Reservation(Base):
    """
    Бронирование времени заправки.
    status: booked / cancelled / completed / no_show
    """

    __tablename__ = "reservations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)

    station_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("stations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    driver_user_id: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)
    driver_phone: Mapped[str | None] = mapped_column(String(30), nullable=True)

    fuel_type: Mapped[str] = mapped_column(String(50), nullable=False, index=True)

    # Время бронирования
    start_time: Mapped[datetime] = mapped_column(DateTime, nullable=False, index=True)
    end_time: Mapped[datetime] = mapped_column(DateTime, nullable=False, index=True)

    status: Mapped[str] = mapped_column(String(20), nullable=False, default="booked", index=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow)

    station = relationship("Station", back_populates="reservations")
