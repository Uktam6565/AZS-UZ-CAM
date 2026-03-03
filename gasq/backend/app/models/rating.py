from datetime import datetime
from sqlalchemy import DateTime, ForeignKey, Integer, SmallInteger, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base


class Rating(Base):
    __tablename__ = "ratings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)

    station_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("stations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Водитель (позже будет отдельная таблица users)
    driver_user_id: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)

    # 1..5
    stars: Mapped[int] = mapped_column(SmallInteger, nullable=False)

    title: Mapped[str | None] = mapped_column(String(120), nullable=True)
    comment: Mapped[str | None] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow)

    station = relationship("Station", back_populates="ratings")
