from typing import List

from sqlmodel import SQLModel

class FlightPath(SQLModel):
    flight_number: str
    from_airport: str
    to_airport: str
    price: int
    date: str


class CheapestRouteResponse(SQLModel):
    total_price: int
    flights: List[FlightPath]


class FlightResponse(SQLModel):
    flightNumber: str
    fromAirport: str
    toAirport: str
    date: str
    price: int


class OpenUser(SQLModel):
    id: int
    login: str
    email: str


class PaginationResponse(SQLModel):
    page: int
    pageSize: int
    totalElements: int
    items: list[FlightResponse]


class TicketResponse(SQLModel):
    ticket_id: int
    flightNumber: str
    fromAirport: str
    toAirport: str
    date: str
    price: int
    status: str


class Token(SQLModel):
    access_token: str
    token_type: str


class TicketPurchaseRequest(SQLModel):
    flightNumber: str
    paidFromBalance: bool
    bonus_amount: int


class PrivilegeDataJSON(SQLModel):
    balance: int
    status: str


class TicketPurchaseResponse(SQLModel):
    ticket_id: int
    flightNumber: str
    fromAirport: str
    toAirport: str
    date: str
    price: int
    paidByMoney: int
    paidByBonuses: int
    status: str
    privilege: PrivilegeDataJSON


class UserInfoResponse(SQLModel):
    tickets: list[TicketResponse]
    privilege: PrivilegeDataJSON


class HistoryData(SQLModel):
    date: str
    ticket_id: int
    balanceDiff: int
    operationType: str


class PrivilegeInfoResponse(SQLModel):
    balance: int
    status: str
    history: list[HistoryData]


class PrivilegeHistoryDataJSON(SQLModel):
    status: str
    balance: int
    history: list[HistoryData]


class ChangeBonusesJSON(SQLModel):
    ticket_uid: str
    name: str
    bonuses: int


class CalculatePriceJSON(SQLModel):
    name: str
    price: int
    paidFromBalance: bool
    ticketUid: str


class CancelTicketJSON(SQLModel):
    name: str
    ticketUid: str


class PaymentDataJSON(SQLModel):
    paidByMoney: int
    paidByBonuses: int


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


class FlightData(SQLModel):
    flightNumber: str
    fromAirport: str
    toAirport: str
    date: str
    price: int


class FlightsResponse(SQLModel):
    page: int
    pageSize: int
    totalElements: int
    items: list[FlightData]
