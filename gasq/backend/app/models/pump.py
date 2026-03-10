from datetime import datetime
from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base_class import Base


class Pump(Base):
    __tablename__ = "pumps"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)

    station_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("stations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    name: Mapped[str] = mapped_column(String(50), nullable=False)
    fuel_type: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    price: Mapped[float] = mapped_column(Float, nullable=False)

    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    is_busy: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    last_status_change: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        default=datetime.utcnow,
    )

    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow)

    station = relationship("Station", back_populates="pumps")