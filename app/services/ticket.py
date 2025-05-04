from sqlmodel import select, Session, update
from fastapi import HTTPException
from ..db.tickets import Ticket, TicketDataJSON, TicketJSON, TicketResponse
from ..db.flights import FlightData, Flight, Airport
from ..db.bonuses import Privilege, PrivilegeHistory, PaymentDataJSON
import datetime as dt
from typing import Optional


def get_user_tickets(user_id: int, session: Session) -> list[TicketResponse]:
    """Get all tickets for a user"""
    query = select(Ticket).where(Ticket.user_id == user_id)
    tickets = session.exec(query).all()

    response = []
    for ticket in tickets:
        # Get flight info for each ticket
        flight = session.exec(
            select(Flight).where(Flight.id == ticket.flight_id)
        ).first()

        if flight:
            from_airport = session.exec(
                select(Airport).where(Airport.id == flight.from_airport_id)
            ).first()
            to_airport = session.exec(
                select(Airport).where(Airport.id == flight.to_airport_id)
            ).first()

            response.append(
                TicketResponse(
                    ticket_id=ticket.id,
                    flightNumber=flight.flight_number,
                    fromAirport=f"{from_airport.city} {from_airport.name}",
                    toAirport=f"{to_airport.city} {to_airport.name}",
                    date=flight.datetime.astimezone().strftime("%Y-%m-%d %H:%M"),
                    price=flight.price,
                    status=ticket.status,
                )
            )

    return response


def get_ticket(user_id: int, ticket_id: int, session: Session) -> TicketResponse:
    """Get single ticket by ID for a specific user"""
    ticket = session.exec(
        select(Ticket).where(
            (Ticket.id == ticket_id) & (Ticket.user_id == user_id)
        )
    ).first()

    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")

    flight = session.exec(
        select(Flight).where(Flight.id == ticket.flight_id)
    ).first()

    if not flight:
        raise HTTPException(status_code=404, detail="Flight not found")

    from_airport = session.exec(
        select(Airport).where(Airport.id == flight.from_airport_id)
    ).first()
    to_airport = session.exec(
        select(Airport).where(Airport.id == flight.to_airport_id)
    ).first()

    return TicketResponse(
        ticket_id=ticket.id,
        flightNumber=flight.flight_number,
        fromAirport=f"{from_airport.city} {from_airport.name}",
        toAirport=f"{to_airport.city} {to_airport.name}",
        date=flight.datetime.astimezone().strftime("%Y-%m-%d %H:%M"),
        price=flight.price,
        status=ticket.status,
    )


def create_ticket(
    user_id: int, ticket_data: TicketDataJSON, session: Session
) -> TicketJSON:
    """Create a new ticket"""
    # Check if flight exists
    flight = session.exec(
        select(Flight).where(Flight.flight_number == ticket_data.flightNumber)
    ).first()
    if not flight:
        raise HTTPException(status_code=404, detail="Flight not found")

    # Create ticket
    ticket = Ticket(
        user_id=user_id,
        flight_id=flight.id,
        price=ticket_data.price,
        status="PAID",
    )
    session.add(ticket)
    session.commit()
    session.refresh(ticket)

    return TicketJSON(
        id=ticket.id,
        user_id=ticket.user_id,
        flightNumber=ticket_data.flightNumber,
        price=ticket.price,
        status=ticket.status,
    )


def cancel_ticket(
    user_id: int, ticket_id: int, session: Session
) -> Optional[TicketJSON]:
    """Cancel a ticket and refund bonuses if applicable"""
    ticket = session.exec(
        select(Ticket).where(
            (Ticket.id == ticket_id) & (Ticket.user_id == user_id)
        )
    ).first()

    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")

    if ticket.status == "CANCELED":
        return None

    flight = session.exec(
        select(Flight).where(Flight.id == ticket.flight_id)
    ).first()

    # Update ticket status
    ticket.status = "CANCELED"
    session.add(ticket)

    # Refund bonuses if any were used
    privilege = session.exec(
        select(Privilege).where(Privilege.user_id == user_id)
    ).first()

    if privilege:
        history = session.exec(
            select(PrivilegeHistory).where(
                (PrivilegeHistory.ticket_id == ticket_id)
                & (PrivilegeHistory.privilege_id == privilege.id)
            )
        ).first()

        if history:
            if history.operation_type == "FILL_IN_BALANCE":
                # Remove the bonus that was added
                privilege.balance -= history.balance_diff
            else:
                # Return the bonus that was used
                privilege.balance += history.balance_diff

            session.add(privilege)

    session.commit()
    session.refresh(ticket)

    return TicketJSON(
        id=ticket.id,
        user_id=ticket.user_id,
        flightNumber=flight.flight_number,
        price=ticket.price,
        status=ticket.status,
    )


def calculate_ticket_price(
    user_id: int,
    price: int,
    paid_from_balance: bool,
    ticket_id: int,
    session: Session,
) -> PaymentDataJSON:
    """Calculate how much to pay with money vs bonuses"""
    privilege = session.exec(
        select(Privilege).where(Privilege.user_id == user_id)
    ).first()

    if not privilege:
        privilege = Privilege(user_id=user_id, status="BRONZE", balance=0)
        session.add(privilege)
        session.commit()

    if not paid_from_balance:
        # Add 10% bonus
        bonus = round(0.1 * price)
        privilege.balance += bonus
        session.add(privilege)

        # Record bonus history
        session.add(
            PrivilegeHistory(
                privilege_id=privilege.id,
                ticket_id=ticket_id,
                datetime=dt.datetime.now(),
                balance_diff=bonus,
                operation_type="FILL_IN_BALANCE",
            )
        )
        session.commit()

        return PaymentDataJSON(paidByMoney=price, paidByBonuses=0)

    # Pay from balance
    if privilege.balance >= price:
        paid_by_money = 0
        paid_by_bonuses = price
    else:
        paid_by_money = price - privilege.balance
        paid_by_bonuses = privilege.balance

    # Deduct bonuses
    privilege.balance -= paid_by_bonuses
    session.add(privilege)

    # Record bonus usage
    if paid_by_bonuses > 0:
        session.add(
            PrivilegeHistory(
                privilege_id=privilege.id,
                ticket_id=ticket_id,
                datetime=dt.datetime.now(),
                balance_diff=paid_by_bonuses,
                operation_type="DEBIT_THE_ACCOUNT",
            )
        )
    session.commit()

    return PaymentDataJSON(paidByMoney=paid_by_money, paidByBonuses=paid_by_bonuses)
