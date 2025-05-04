from sqlmodel import *
from datetime import datetime, timedelta
import uuid
import random
from ..app.db.session import engine, get_session, create_db_and_tables
from ..app.db.users import User, UserCreate
from ..app.db.flights import Flight, Airport
from ..app.db.tickets import Ticket
from ..app.db.bonuses import Privilege, PrivilegeHistory


def database_has_data(session: Session) -> bool:
    """Check if database already contains test data"""
    # Check for any existing users
    existing_users = session.exec(select(User)).first()
    if existing_users:
        return True

    # Check for any existing flights
    existing_flights = session.exec(select(Flight)).first()
    if existing_flights:
        return True

    # Check for any existing tickets
    existing_tickets = session.exec(select(Ticket)).first()
    if existing_tickets:
        return True

    return False


def create_test_users(session: Session):
    """Create test user accounts"""
    users_data = [
        UserCreate(login="testuser", email="test@example.com", password="testpassword"),
        UserCreate(login="admin", email="admin@example.com", password="admin123"),
        UserCreate(
            login="traveler", email="traveler@example.com", password="travel123"
        ),
    ]

    for user_data in users_data:
        user = user_data.create_hashed()
        session.add(user)

    session.commit()
    print("Created test users")


def create_test_airports(session: Session):
    """Create test airports"""
    airports = [
        Airport(name="Пулково", city="Санкт-Петербург", country="Россия"),
        Airport(name="Шереметьево", city="Москва", country="Россия"),
        Airport(name="Домодедово", city="Москва", country="Россия"),
        Airport(name="Внуково", city="Москва", country="Россия"),
        Airport(name="Кольцово", city="Екатеринбург", country="Россия"),
    ]

    for airport in airports:
        session.add(airport)

    session.commit()
    print("Created test airports")


def create_test_flights(session: Session):
    """Create test flights"""
    # Get airports
    airports = session.exec(select(Airport)).all()

    flights = []
    for i in range(1, 21):
        from_airport = random.choice(airports)
        to_airport = random.choice([a for a in airports if a.id != from_airport.id])

        flight_date = datetime.now() + timedelta(days=random.randint(1, 30))

        flights.append(
            Flight(
                flight_number=f"AFL{str(i).zfill(3)}",
                datetime=flight_date,
                from_airport_id=from_airport.id,
                to_airport_id=to_airport.id,
                price=random.randint(1000, 5000),
            )
        )

    # Add specific test flight
    pulkovo = session.exec(select(Airport).where(Airport.name == "Пулково")).first()
    sheremetyevo = session.exec(
        select(Airport).where(Airport.name == "Шереметьево")
    ).first()

    flights.append(
        Flight(
            flight_number="AFL031",
            datetime=datetime.now() + timedelta(days=7),
            from_airport_id=pulkovo.id,
            to_airport_id=sheremetyevo.id,
            price=1500,
        )
    )

    for flight in flights:
        session.add(flight)

    session.commit()
    print("Created test flights")


def create_test_privileges(session: Session):
    """Create test privilege accounts"""
    users = session.exec(select(User)).all()
    statuses = ["BRONZE", "SILVER", "GOLD"]

    for user in users:
        privilege = Privilege(
            user_id=user.id,
            status=random.choice(statuses),
            balance=random.randint(0, 5000),
        )
        session.add(privilege)

    session.commit()
    print("Created test privileges")


def create_test_tickets(session: Session):
    """Create test tickets if they don't exist"""
    users = session.exec(select(User)).all()
    flights = session.exec(select(Flight)).all()
    privileges = session.exec(select(Privilege)).all()

    existing_ticket = session.exec(select(Ticket)).first()
    if existing_ticket:
        return

    for user, privilege in zip(users, privileges):
        for _ in range(random.randint(1, 3)):
            flight = random.choice(flights)

            # First create and commit the ticket to get an ID
            ticket = Ticket(
                ticket_uid=uuid.uuid4(),
                user_id=user.id,
                flight_id=flight.id,
                price=flight.price,
                status="PAID",
            )
            session.add(ticket)
            session.commit()  # Commit to get the ticket.id
            session.refresh(ticket)  # Refresh to populate the ID

            # Now create the privilege history with the ticket ID
            bonus = int(flight.price * 0.1)  # 10% of ticket price as bonus
            history = PrivilegeHistory(
                privilege_id=privilege.id,
                ticket_id=ticket.id,  # Now we have a valid ticket.id
                datetime=datetime.now(),
                balance_diff=bonus,
                operation_type="FILL_IN_BALANCE",
            )
            session.add(history)

            # Update privilege balance
            privilege.balance += bonus
            session.add(privilege)

    session.commit()
    print("Created test tickets")


def fill_test_db():
    # Create all tables first
    create_db_and_tables()

    # Create test data
    with Session(engine) as session:
        if database_has_data(session):
            return

        create_test_users(session)
        create_test_airports(session)
        create_test_flights(session)
        create_test_privileges(session)
        create_test_tickets(session)
