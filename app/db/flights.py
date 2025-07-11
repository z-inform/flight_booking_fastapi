import datetime as dt

from sqlmodel import SQLModel, Field, Column, TIMESTAMP


class Flight(SQLModel, table=True):
    __tablename__ = "flights"
    id: int = Field(primary_key=True)
    flight_number: str = Field(nullable=False)
    datetime: dt.datetime = Field(
        sa_column=Column(TIMESTAMP(timezone=True), nullable=False)
    )
    from_airport_id: int = Field(foreign_key="airports.id")
    to_airport_id: int = Field(foreign_key="airports.id")
    price: int = Field(nullable=False)

    def __repr__(self):
        return (
            f"id={self.id}, flight_number={self.flight_number},"
            f"datetime={self.datetime}, from_airport_id={self.from_airport_id},"
            f"to_airport_id={self.to_airport_id}, price={self.price}"
        )


class Airport(SQLModel, table=True):
    __tablename__ = "airports"
    id: int = Field(primary_key=True)
    name: str = Field()
    city: str = Field()
    country: str = Field()

    def __repr__(self):
        return (
            f"id={self.id}, name={self.name}, city={self.city}, country={self.country}"
        )
