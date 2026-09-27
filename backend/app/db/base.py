from sqlalchemy.orm import DeclarativeBase
from sqlalchemy import Column
from sqlalchemy.dialects.postgresql import UUID
import uuid

class Base(DeclarativeBase):
    pass
