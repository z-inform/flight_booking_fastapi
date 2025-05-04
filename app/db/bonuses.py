from sqlmodel import *
import datetime as dt
import uuid


class HistoryData(SQLModel):
    date: str
    ticket_id: int
    balanceDiff: int
    operationType: str


class PrivilegeHistoryDataJSON(SQLModel):
    status: str
    balance: int
    history: list[HistoryData]


class ChangeBonusesJSON(SQLModel):
    ticket_id: int
    user_id: int
    bonuses: int


class CalculatePriceJSON(SQLModel):
    user_id: int
    price: int
    paidFromBalance: bool
    ticket_id: int


class CancelTicketJSON(SQLModel):
    user_id: int
    ticket_id: int


class PaymentDataJSON(SQLModel):
    paidByMoney: int
    paidByBonuses: int


class PrivilegeDataJSON(SQLModel):
    balance: int
    status: str


class Privilege(SQLModel, table=True):
    __tablename__ = "privilege"
    id: int = Field(primary_key=True)
    user_id: int = Field(nullable=False, unique=True, foreign_key='users.id')
    status: str = Field(sa_column=Column(String, nullable=False, default="BRONZE"))
    balance: int

    __table_args__ = (CheckConstraint("status in ('BRONZE', 'SILVER', 'GOLD')"),)


class PrivilegeHistory(SQLModel, table=True):
    __tablename__ = "privilege_history"
    id: int = Field(primary_key=True)
    privilege_id: int = Field(foreign_key="privilege.id")
    ticket_id: int = Field(nullable=False, foreign_key='tickets.id')
    datetime: dt.datetime = Field(sa_column=Column(TIMESTAMP, nullable=False))
    balance_diff: int = Field(nullable=False)
    operation_type: str = Field(sa_column=Column(String, nullable=False))

    __table_args__ = (
        CheckConstraint("operation_type in ('FILL_IN_BALANCE', 'DEBIT_THE_ACCOUNT')"),
    )
