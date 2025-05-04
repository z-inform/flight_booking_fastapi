from sqlmodel import SQLModel, Field, Column, CheckConstraint, String


class Ticket(SQLModel, table=True):
    __tablename__ = "tickets"
    id: int = Field(primary_key=True)
    user_id: int = Field(nullable=False, foreign_key="users.id")
    flight_id: int = Field(nullable=False, foreign_key="flights.id")
    price: int = Field(nullable=False)
    status: str = Field(sa_column=Column(String, nullable=False))

    __table_args__ = (CheckConstraint("status in ('PAID', 'CANCELED')"),)
