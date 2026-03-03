from sqlalchemy.orm import declarative_base
from app.db.base_class import Base  # noqa: F401

Base = declarative_base()

# Импорты моделей — ТОЛЬКО напрямую по файлам
from app.models.station import Station  # noqa: F401
from app.models.queue import QueueTicket  # noqa: F401
from app.models.notification import Notification  # noqa: F401
from app.models.user import User  # noqa
from app.models.pump import Pump  # noqa
from app.models.rating import Rating  # noqa