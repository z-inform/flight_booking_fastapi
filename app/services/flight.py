from fastapi import *
from fastapi.responses import *
from fastapi.exceptions import RequestValidationError
from sqlmodel import *
from ..db.flights import *
from ..db.session import SessionDep
from typing import Annotated
from fastapi.encoders import jsonable_encoder
from contextlib import asynccontextmanager
import uvicorn
from multiprocessing import Process
import os


def get_all_flights(page: int, size: int, session: SessionDep) -> FlightsResponse:
    query = text(
        f"""SELECT flights.flight_number, flights.datetime, flights.price, a1.name as n1, a1.city as c1, a2.name as n2, a2.city as c2
from flights join airports a1 on flights.from_airport_id = a1.id join airports a2 on flights.to_airport_id = a2.id"""
    )
    flights = session.exec(query).all()
    items: list[FlightData] = []
    if size == -1:
        slice = flights
    else:
        start_index = (page - 1) * size
        end_index = page * size
        slice = flights[start_index:end_index]
    for flight in slice:
        fromAirport = flight.c1 + " " + flight.n1
        toAirport = flight.c2 + " " + flight.n2
        date = flight.datetime.astimezone().strftime("%Y-%m-%d %H:%M")
        items.append(
            FlightData(
                flightNumber=flight.flight_number,
                fromAirport=fromAirport,
                toAirport=toAirport,
                date=date,
                price=flight.price,
            )
        )
    responseBody = FlightsResponse(
        page=page, pageSize=len(items), totalElements=len(flights), items=items
    )
    return responseBody


def get_flight(flightNumber: str, session: SessionDep) -> FlightData:
    query = text(
        f"""SELECT flights.flight_number, flights.datetime, flights.price, a1.name as n1, a1.city as c1, a2.name as n2, a2.city as c2
from flights join airports a1 on flights.from_airport_id = a1.id join airports a2 on flights.to_airport_id = a2.id where flights.flight_number=:flight_num"""
    )
    flight = session.exec(query, params={"flight_num": flightNumber}).first()
    if not flight:
        return JSONResponse(content={"message": "Flight not found"}, status_code=404)
    fromAirport = flight.c1 + " " + flight.n1
    toAirport = flight.c2 + " " + flight.n2
    date = flight.datetime.astimezone().strftime("%Y-%m-%d %H:%M")
    return FlightData(
        flightNumber=flight.flight_number,
        fromAirport=fromAirport,
        toAirport=toAirport,
        date=date,
        price=flight.price,
    )
