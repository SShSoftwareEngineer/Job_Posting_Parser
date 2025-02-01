from dataclasses import dataclass
from datetime import datetime
from typing import Optional, List

from sqlalchemy import create_engine, Column, Integer, String, DateTime, ForeignKey, Text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship, sessionmaker


class Base(DeclarativeBase):
    pass


# Модель для исходных сообщений
class SourceMessage(Base):
    __tablename__ = 'source_messages'
    id: Mapped[int] = mapped_column(primary_key=True)
    message_id: Mapped[int] = mapped_column(Integer, unique=True)
    date: Mapped[datetime]
    message_type: Mapped[str]
    text: Mapped[str] = mapped_column(Text)
    urls: Mapped[str] = mapped_column(Text)

    def message_type_detection(self):
        pass


def connect_database():
    engine = create_engine('sqlite:///vacancies.db')
    Base.metadata.create_all(engine)
    session = sessionmaker(bind=engine)
    return session()

if __name__ == '__main__':
    pass
