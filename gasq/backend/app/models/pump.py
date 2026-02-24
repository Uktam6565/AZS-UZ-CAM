from datetime import datetime
from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base


class Pump(Base):
    __tablename__ = "pumps"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)

    station_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("stations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Название/номер колонки (например: "A1", "B2", "EV-01")
    name: Mapped[str] = mapped_column(String(50), nullable=False)

    # Тип топлива: gasoline / diesel / lpg / ev
    fuel_type: Mapped[str] = mapped_column(String(50), nullable=False, index=True)

    # Текущая цена за литр или кВт⋅ч
    price: Mapped[float] = mapped_column(Float, nullable=False)

    # Статус колонки
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    is_busy: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    # Последнее обновление статуса
    last_status_change: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        default=datetime.utcnow,
    )

    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow)

    # Связи
    station = relationship("Station", back_populates="pumps")
