import os
from typing import Annotated

from sqlmodel import create_engine, Session, SQLModel
from fastapi import Depends

database_url = os.environ["DATABASE_URL"]
print(database_url)
engine = create_engine(database_url)


print(f"Строка подключения к БД: {database_url}")
engine = create_engine(database_url)


def create_db_and_tables():
    SQLModel.metadata.create_all(engine)


def get_session():
    with Session(engine) as session:
        yield session


SessionDep = Annotated[Session, Depends(get_session)]
