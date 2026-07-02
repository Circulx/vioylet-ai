# Database bootstrap code centralizes SQLAlchemy metadata and session lifecycle for repositories.
from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    # Shared SQLAlchemy base class; model modules attach their table metadata here for migrations and sessions.
    pass

