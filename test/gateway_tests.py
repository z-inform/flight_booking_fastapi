from typing import Dict

import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session, select

from ..app.main import app
from ..app.db.session import engine
from ..app.db.users import User
from .init_db import fill_test_db

fill_test_db()

client = TestClient(app)
session = Session(engine)

# Test data constants
TEST_USERNAME = "testuser"
TEST_PASSWORD = "testpassword"
TEST_CLIENT_ID = "testclient"
TEST_CLIENT_SECRET = "testsecret"
FLIGHT_NUMBER = "AFL031"
TICKET_PRICE = 1500


# Helper functions
def get_auth_headers() -> Dict[str, str]:
    """Get authorization headers with valid token"""
    # First get the token
    token_response = client.post(
        "/api/v1/authorize",
        data={
            "username": TEST_USERNAME,
            "password": TEST_PASSWORD,
            "client_id": TEST_CLIENT_ID,
            "client_secret": TEST_CLIENT_SECRET,
            "grant_type": "password",
            "scope": "openid",
        },
    )
    assert token_response.status_code == 200
    token = token_response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def test_register_new_user():
    """Test successful user registration"""
    # Test user data
    test_user_data = {
        "login": "new_test_user",
        "email": "new_test@example.com",
        "password": "securepassword123",
    }

    try:
        # 1. Make registration request
        response = client.post("/api/v1/register", json=test_user_data)

        # 2. Verify successful response
        assert response.status_code == 201
        response_data = response.json()
        assert response_data["login"] == test_user_data["login"]
        assert response_data["email"] == test_user_data["email"]
        assert (
            "hashed_password" not in response_data
        )  # Sensitive field should not be returned

        # 3. Verify user exists in database
        db_user = session.exec(
            select(User).where(User.login == test_user_data["login"])
        ).first()
        assert db_user is not None
        assert db_user.email == test_user_data["email"]

    finally:
        # 4. Cleanup - delete test user
        if "db_user" not in locals():
            db_user = session.exec(
                select(User).where(User.login == test_user_data["login"])
            ).first()

    session.delete(db_user)
    session.commit()
    # Verify deletion
    deleted_user = session.exec(
        select(User).where(User.login == test_user_data["login"])
    ).first()
    assert deleted_user is None


def test_register_existing_username():
    """Test registration with existing username"""
    # First create a test user
    existing_user = User(
        login="existing_user",
        email="existing@example.com",
        hashed_password="hashedpassword123",
    )
    session.add(existing_user)
    session.commit()

    try:
        # Attempt to register with same username
        response = client.post(
            "/api/v1/register",
            json={
                "login": "existing_user",
                "email": "new@example.com",
                "password": "newpassword123",
            },
        )

        assert response.status_code == 404
        assert "Username already registered" in response.json()["detail"]

    finally:
        # Cleanup
        session.delete(existing_user)
        session.commit()


def test_register_existing_email():
    """Test registration with existing email"""
    # First create a test user
    existing_user = User(
        login="unique_user",
        email="existing_email@example.com",
        hashed_password="hashedpassword123",
    )
    session.add(existing_user)
    session.commit()

    try:
        # Attempt to register with same email
        response = client.post(
            "/api/v1/register",
            json={
                "login": "new_user",
                "email": "existing_email@example.com",
                "password": "newpassword123",
            },
        )

        assert response.status_code == 404
        assert "Email already registered" in response.json()["detail"]

    finally:
        # Cleanup
        session.delete(existing_user)
        session.commit()


def test_get_token():
    """Test obtaining an access token"""
    response = client.post(
        "/api/v1/authorize",
        data={
            "username": TEST_USERNAME,
            "password": TEST_PASSWORD,
            "client_id": TEST_CLIENT_ID,
            "client_secret": TEST_CLIENT_SECRET,
            "grant_type": "password",
            "scope": "openid",
        },
    )

    assert response.status_code == 200
    assert "application/json" in response.headers["content-type"]
    assert "access_token" in response.json()
    assert response.json()["access_token"] is not None


def test_get_current_user_success():
    """Test successful current user retrieval using authorization endpoint"""
    # 1. First authenticate to get JWT token
    auth_response = client.post(
        "/api/v1/authorize",
        data={
            "username": "testuser",
            "password": "testpassword",
            "grant_type": "password",
            "scope": "openid",
        },
    )
    assert auth_response.status_code == 200
    token = auth_response.json()["access_token"]

    # 2. Now make authenticated request to current_user endpoint
    response = client.get(
        "/api/v1/current_user", headers={"Authorization": f"Bearer {token}"}
    )

    # 3. Verify response
    assert response.status_code == 200
    data = response.json()
    assert data["login"] == "testuser"
    assert "email" in data
    assert "hashed_password" not in data


def test_get_current_user_invalid_token():
    """Test with invalid token"""
    response = client.get(
        "/api/v1/current_user", headers={"Authorization": "Bearer invalidtoken123"}
    )
    assert response.status_code == 401
    assert response.json()["detail"] == "Bad Token"


def test_get_flights_unauthorized():
    """Test unauthorized access to flights list"""
    response = client.get("/api/v1/flights?page=1&size=10")
    assert response.status_code == 401


def test_get_flight_unauthorized():
    """Test unauthorized access to single flight data"""
    response = client.get(f"/api/v1/flights/{FLIGHT_NUMBER}")
    assert response.status_code == 401


def test_get_flights_authorized():
    """Test authorized access to flights list"""
    headers = get_auth_headers()
    response = client.get("/api/v1/flights?page=1&size=10", headers=headers)

    assert response.status_code == 200
    assert "application/json" in response.headers["content-type"]

    data = response.json()
    assert isinstance(data["items"], list)
    assert data["page"] is not None
    assert data["pageSize"] <= 10
    assert data["totalElements"] is not None


def test_get_flight_authorized():
    """Test authorized access to single flight data"""
    headers = get_auth_headers()
    response = client.get(f"/api/v1/flights/{FLIGHT_NUMBER}", headers=headers)

    assert response.status_code == 200
    assert "application/json" in response.headers["content-type"]

    test_flight = response.json()

    # Find our test flight
    assert test_flight is not None
    assert test_flight["fromAirport"] == "Санкт-Петербург Пулково"
    assert test_flight["toAirport"] == "Москва Шереметьево"
    assert test_flight["date"] is not None
    assert test_flight["price"] == TICKET_PRICE


def test_get_privilege_unauthorized():
    """Test unauthorized access to privilege info"""
    response = client.get("/api/v1/privilege")
    assert response.status_code == 401


def test_get_privilege_authorized():
    """Test authorized access to privilege info"""
    headers = get_auth_headers()
    response = client.get("/api/v1/privilege", headers=headers)

    assert response.status_code == 200
    assert "application/json" in response.headers["content-type"]

    data = response.json()
    assert data["balance"] is not None
    assert data["status"] is not None


def test_buy_ticket_unauthorized():
    """Test unauthorized ticket purchase"""
    response = client.post(
        "/api/v1/tickets",
        json={
            "flightNumber": FLIGHT_NUMBER,
            "price": TICKET_PRICE,
            "paidFromBalance": False,
        },
    )
    assert response.status_code == 401


def test_buy_ticket_authorized():
    """Test authorized ticket purchase"""
    headers = get_auth_headers()
    response = client.post(
        "/api/v1/tickets",
        headers=headers,
        json={
            "flightNumber": FLIGHT_NUMBER,
            "bonus_amount": 0,
            "paidFromBalance": False,
        },
    )

    assert response.status_code == 200
    assert "application/json" in response.headers["content-type"]

    data = response.json()
    assert data["ticket_id"] is not None
    assert data["flightNumber"] == FLIGHT_NUMBER
    assert data["fromAirport"] == "Санкт-Петербург Пулково"
    assert data["toAirport"] == "Москва Шереметьево"
    assert data["date"] is not None
    assert data["price"] == TICKET_PRICE
    assert data["paidByMoney"] == TICKET_PRICE
    assert data["paidByBonuses"] == 0
    assert data["status"] == "PAID"
    assert data["privilege"]["balance"] >= 150
    assert data["privilege"]["status"] is not None

    # Save ticket ID for subsequent tests
    pytest.ticket_id = data["ticket_id"]


def test_get_ticket_unauthorized():
    """Test unauthorized ticket info access"""
    response = client.get(f"/api/v1/tickets/{pytest.ticket_id}")
    assert response.status_code == 401


def test_get_ticket_authorized():
    """Test authorized ticket info access"""
    headers = get_auth_headers()
    response = client.get(f"/api/v1/tickets/{pytest.ticket_id}", headers=headers)

    assert response.status_code == 200
    assert "application/json" in response.headers["content-type"]

    data = response.json()
    assert data["ticket_id"] == pytest.ticket_id
    assert data["flightNumber"] == FLIGHT_NUMBER
    assert data["fromAirport"] == "Санкт-Петербург Пулково"
    assert data["toAirport"] == "Москва Шереметьево"
    assert data["date"] is not None
    assert data["price"] == TICKET_PRICE
    assert data["status"] == "PAID"


def test_get_user_info_unauthorized():
    """Test unauthorized user info access"""
    response = client.get("/api/v1/me")
    assert response.status_code == 401


def test_get_user_info_authorized():
    """Test authorized user info access"""
    headers = get_auth_headers()
    response = client.get("/api/v1/me", headers=headers)

    assert response.status_code == 200
    assert "application/json" in response.headers["content-type"]

    data = response.json()
    # Find our test ticket in user's tickets
    test_ticket = next(
        (t for t in data["tickets"] if t["ticket_id"] == pytest.ticket_id), None
    )
    assert test_ticket is not None
    assert test_ticket["flightNumber"] == FLIGHT_NUMBER
    assert test_ticket["fromAirport"] == "Санкт-Петербург Пулково"
    assert test_ticket["toAirport"] == "Москва Шереметьево"
    assert test_ticket["date"] is not None
    assert test_ticket["price"] == TICKET_PRICE
    assert test_ticket["status"] == "PAID"

    assert data["privilege"] is not None
    assert data["privilege"]["balance"] is not None
    assert data["privilege"]["status"] is not None


def test_refund_ticket_unauthorized():
    """Test unauthorized ticket refund"""
    response = client.delete(f"/api/v1/tickets/{pytest.ticket_id}")
    assert response.status_code == 401


def test_refund_ticket_authorized():
    """Test authorized ticket refund"""
    headers = get_auth_headers()
    response = client.delete(f"/api/v1/tickets/{pytest.ticket_id}", headers=headers)
    assert response.status_code == 204


def test_find_cheapest_route_unauthorized():
    """Test direct flight route"""
    response = client.get(
        "/api/v1/routes/cheapest?from_airport=Пулково&to_airport=Шереметьево",
    )

    assert response.status_code == 401


def test_find_cheapest_route_direct():
    """Test direct flight route"""
    headers = get_auth_headers()
    response = client.get(
        "/api/v1/routes/cheapest?from_airport=Пулково&to_airport=Домодедово",
        headers=headers,
    )

    assert response.status_code == 200
    data = response.json()
    assert data["total_price"] == 500  # Known price from test data
    assert len(data["flights"]) == 1
    assert data["flights"][0]["flight_number"] == "AFL032"


def test_find_cheapest_route_with_connection():
    """Test multi-flight route with connection"""
    headers = get_auth_headers()
    response = client.get(
        "/api/v1/routes/cheapest?from_airport=Пулково&to_airport=Шереметьево",
        headers=headers,
    )

    assert response.status_code == 200
    data = response.json()
    # Should find the cheaper connecting route
    assert len(data["flights"]) == 2
    assert data["flights"][0]["flight_number"] == "AFL032"
    assert data["flights"][1]["flight_number"] == "AFL033"
    assert data["total_price"] == 1200  # Sum of both flight prices


def test_missing_airport():
    """Test when departure airport doesn't exist"""
    headers = get_auth_headers()
    response = client.get(
        "/api/v1/routes/cheapest?from_airport=Unknown&to_airport=Шереметьево",
        headers=headers,
    )

    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()


def test_same_source_and_destination():
    """Test when from and to airports are the same"""
    headers = get_auth_headers()
    response = client.get(
        "/api/v1/routes/cheapest?from_airport=Пулково&to_airport=Пулково",
        headers=headers,
    )

    assert response.status_code == 200
    data = response.json()
    assert data["total_price"] == 0
