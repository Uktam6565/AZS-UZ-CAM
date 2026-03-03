from datetime import datetime
from sqlalchemy import Boolean, DateTime, Float, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base_class import Base


class Station(Base):
    __tablename__ = "stations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)

    # Владелец/админ (позже добавим таблицу пользователей)
    owner_user_id: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)

    # Основные данные
    name: Mapped[str] = mapped_column(String(200), nullable=False, index=True)
    address: Mapped[str] = mapped_column(String(300), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Геолокация
    latitude: Mapped[float] = mapped_column(Float, nullable=False, index=True)
    longitude: Mapped[float] = mapped_column(Float, nullable=False, index=True)

    # Типы топлива, которые поддерживает АЗС (просто строка: "gasoline,diesel,lpg,ev")
    # Позже можно заменить на отдельную таблицу/enum
    fuel_types: Mapped[str] = mapped_column(String(100), nullable=False, default="gasoline,diesel")
    avg_service_min: Mapped[int] = mapped_column(Integer, nullable=False, default=5)  # 5 мин/машина
    pumps_count: Mapped[int] = mapped_column(Integer, nullable=False, default=1)     # 1 колонка

    # Услуги (есть/нет)
    has_cafe: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    has_shop: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    has_service: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)  # СТО
    has_toilet: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    has_wifi: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    # Видимость/работает ли АЗС сейчас
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow)

    # Связи (таблицы добавим дальше)
    pumps = relationship("Pump", back_populates="station", cascade="all, delete-orphan")
    queue_tickets = relationship("QueueTicket", back_populates="station", cascade="all, delete-orphan")
    ratings = relationship("Rating", back_populates="station", cascade="all, delete-orphan")
    reservations = relationship("Reservation", back_populates="station", cascade="all, delete-orphan")
