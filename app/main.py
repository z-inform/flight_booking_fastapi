from typing import Annotated
from datetime import datetime
from contextlib import asynccontextmanager

from fastapi import FastAPI, Depends, HTTPException, status, Request
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from fastapi.security import (
    OAuth2PasswordRequestForm,
    HTTPBearer,
    HTTPAuthorizationCredentials,
)
from sqlmodel import select

from .db.api_responses import (
    Token,
    PaginationResponse,
    TicketResponse,
    TicketPurchaseRequest,
    TicketPurchaseResponse,
    UserInfoResponse,
    PrivilegeHistoryDataJSON,
    PrivilegeDataJSON,
    FlightData,
    OpenUser,
)
from .db.session import create_db_and_tables, SessionDep
from .db.users import User, UserCreate
from .db.bonuses import Privilege, PrivilegeHistory
from .db.flights import Flight, Airport
from .db.tickets import Ticket
from .auth.token import validate_jwt, create_jwt, get_user_from_token
from .services.flight import get_all_flights, get_flight
from .services.bonus import get_user_privileges, get_privilege_history
from .services.ticket import get_user_tickets, get_ticket, cancel_ticket


@asynccontextmanager
async def lifespan(application: FastAPI):
    del application
    create_db_and_tables()
    yield


app = FastAPI(lifespan=lifespan)


@app.post("/api/v1/authorize", response_model=Token)
def login_for_access_token_endpoint(
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()],
    db: SessionDep,
):
    """
    Authenticate user and return access token
    """
    user = db.exec(select(User).where(User.login == form_data.username)).first()

    if not user:
        raise HTTPException(
            status_code=401,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not user.verify_password(form_data.password):
        raise HTTPException(
            status_code=401,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    access_token = create_jwt(
        data={"sub": user.login, "id": user.id},  # JWT subject identifier
    )

    return {"access_token": access_token, "token_type": "bearer"}


security = HTTPBearer(auto_error=False)


def auth_dependency(credentials: HTTPAuthorizationCredentials = Depends(security)):
    if credentials is None:
        raise HTTPException(401, "Not authenticated")
    token = credentials.credentials
    try:
        payload = validate_jwt(token)
    except Exception as e:
        raise HTTPException(401, "Bad Token") from e
    return payload


@app.post(
    "/api/v1/register",
    status_code=201,
    summary="Create a new user account",
    responses={
        201: {"description": "User created successfully"},
        400: {"description": "Invalid input or username/email already exists"},
    },
)
def create_user_endpoint(user_create: UserCreate, db: SessionDep) -> OpenUser:
    """
    Create a new user account from email, login and password
    """

    # Check if username already exists
    existing_user = db.exec(select(User).where(User.login == user_create.login)).first()
    if existing_user:
        raise HTTPException(
            status_code=404,
            detail="Username already registered",
        )

    # Check if email already exists
    existing_email = db.exec(
        select(User).where(User.email == user_create.email)
    ).first()
    if existing_email:
        raise HTTPException(status_code=404, detail="Email already registered")

    # Create hashed user
    user = user_create.create_hashed()

    # Add to database
    db.add(user)
    db.commit()
    db.refresh(user)

    open_user = OpenUser(id=user.id, login=user.login, email=user.email)

    return open_user


# Flight endpoints
@app.get("/api/v1/flights", status_code=200)
def get_flights_endpoint(
    page: int,
    size: int,
    session: SessionDep,
    user_info: dict = Depends(auth_dependency),
) -> PaginationResponse:
    del user_info
    return get_all_flights(page, size, session)


# Flight endpoints
@app.get("/api/v1/flights/{flight_number}", status_code=200)
def get_flight_endpoint(
    flight_number: str, session: SessionDep, user_info: dict = Depends(auth_dependency)
) -> FlightData:
    del user_info
    return get_flight(flight_number, session)


# Ticket endpoints
@app.get("/api/v1/tickets", status_code=200)
def get_tickets_endpoint(
    session: SessionDep, user_info: dict = Depends(auth_dependency)
) -> list[TicketResponse]:
    user_id = user_info["id"]
    return get_user_tickets(user_id, session)


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc):
    del request
    return JSONResponse({"message": "what", "errors": exc.errors()[0]}, status_code=400)


@app.post("/api/v1/tickets", status_code=200)
def create_ticket_endpoint(
    ticket_purchase_request: TicketPurchaseRequest,
    session: SessionDep,
    user_info: dict = Depends(auth_dependency),
) -> TicketPurchaseResponse:
    user_id = user_info["id"]

    # Get flight info
    flight = session.exec(
        select(Flight).where(
            Flight.flight_number == ticket_purchase_request.flightNumber
        )
    ).first()
    if not flight:
        raise HTTPException(status_code=404, detail="Flight not found")

    # Create ticket
    ticket = Ticket(
        user_id=user_id,
        flight_id=flight.id,
        price=ticket_purchase_request.price,
        status="PAID",
    )
    session.add(ticket)
    session.commit()
    session.refresh(ticket)

    # Calculate price with bonuses
    privilege = session.exec(
        select(Privilege).where(Privilege.user_id == user_id)
    ).first()

    if not privilege:
        privilege = Privilege(user_id=user_id, status="BRONZE", balance=0)
        session.add(privilege)
        session.commit()

    if ticket_purchase_request.paidFromBalance:
        if privilege.balance >= ticket_purchase_request.price:
            paid_by_money = 0
            paid_by_bonuses = ticket_purchase_request.price
            new_balance = privilege.balance - paid_by_bonuses
        else:
            paid_by_money = ticket_purchase_request.price - privilege.balance
            paid_by_bonuses = privilege.balance
            new_balance = 0
    else:
        paid_by_money = ticket_purchase_request.price
        paid_by_bonuses = 0
        new_balance = privilege.balance + int(
            ticket_purchase_request.price * 0.1
        )  # 10% bonus

    # Update privilege
    privilege.balance = new_balance
    session.add(privilege)

    # Add privilege history
    history = PrivilegeHistory(
        privilege_id=privilege.id,
        ticket_id=ticket.id,
        datetime=datetime.now(),
        balance_diff=int(ticket_purchase_request.price * 0.1)
        if not ticket_purchase_request.paidFromBalance
        else -paid_by_bonuses,
        operation_type="FILL_IN_BALANCE"
        if not ticket_purchase_request.paidFromBalance
        else "DEBIT_THE_ACCOUNT",
    )
    session.add(history)
    session.commit()

    # Prepare airports info
    from_airport = session.exec(
        select(Airport).where(Airport.id == flight.from_airport_id)
    ).first()
    to_airport = session.exec(
        select(Airport).where(Airport.id == flight.to_airport_id)
    ).first()

    return TicketPurchaseResponse(
        ticket_id=ticket.id,
        flightNumber=flight.flight_number,
        fromAirport=f"{from_airport.city} {from_airport.name}",
        toAirport=f"{to_airport.city} {to_airport.name}",
        date=flight.datetime.astimezone().strftime("%Y-%m-%d %H:%M"),
        price=flight.price,
        paidByMoney=paid_by_money,
        paidByBonuses=paid_by_bonuses,
        status=ticket.status,
        privilege=PrivilegeDataJSON(balance=privilege.balance, status=privilege.status),
    )


@app.get("/api/v1/tickets/{ticket_id}", status_code=200)
def ticket_info_endpoint(
    ticket_id: str, session: SessionDep, user_info: dict = Depends(auth_dependency)
) -> TicketResponse:
    user_id = user_info["id"]
    return get_ticket(user_id, ticket_id, session)


@app.delete("/api/v1/tickets/{ticket_id}", status_code=204)
def ticket_cancel_endpoint(
    ticket_id: int, session: SessionDep, user_info: dict = Depends(auth_dependency)
):
    user_id = user_info["id"]
    return cancel_ticket(user_id, ticket_id, session)


@app.get("/api/v1/current_user", status_code=200)
def get_current_user_endpoint(
    token: Annotated[HTTPAuthorizationCredentials, Depends(security)],
    db: SessionDep,
) -> OpenUser:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        username = get_user_from_token(token.credentials)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Bad Token",
            headers={"WWW-Authenticate": "Bearer"},
        ) from e

    if username is None:
        raise credentials_exception

    user = db.exec(select(User).where(User.login == username)).first()
    if user is None:
        raise credentials_exception
    return OpenUser(id=user.id, login=user.login, email=user.email)


# User endpoints
@app.get("/api/v1/me", status_code=200)
def get_user_info_endpoint(
    session: SessionDep, user_info: dict = Depends(auth_dependency)
) -> UserInfoResponse:
    user_id = user_info["id"]
    tickets = get_user_tickets(user_id, session)
    privilege = get_user_privileges(user_id, session)

    return UserInfoResponse(tickets=tickets, privilege=privilege)


@app.get("/api/v1/privilege", status_code=200)
def privilege_info_endpoint(
    session: SessionDep, user_info: dict = Depends(auth_dependency)
) -> PrivilegeHistoryDataJSON:
    user_id = user_info["id"]
    return get_privilege_history(user_id, session)
