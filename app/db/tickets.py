from sqlmodel import *
import datetime as dt
import uuid


class TicketDataJSON(SQLModel):
    username: str
    flightNumber: str
    price: int


class TicketJSON(SQLModel):
    id: int
    user_id: int
    flightNumber: str
    price: int
    status: str

class TicketResponse(SQLModel):
    ticket_id: int
    flightNumber: str
    fromAirport: str
    toAirport: str
    date: str
    price: int
    status: str


class Ticket(SQLModel, table=True):
    __tablename__ = "tickets"
    id: int = Field(primary_key=True)
    #ticket_uid: uuid.UUID = Field(nullable=False, unique=True)
    user_id: int = Field(nullable=False, foreign_key='users.id')
    flight_id: int = Field(nullable=False, foreign_key='flights.id')
    price: int = Field(nullable=False)
    status: str = Field(sa_column=Column(String, nullable=False))

    __table_args__ = (CheckConstraint("status in ('PAID', 'CANCELED')"),)
