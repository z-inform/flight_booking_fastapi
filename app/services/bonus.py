from fastapi import *
from fastapi.responses import *
from fastapi.exceptions import RequestValidationError
from sqlmodel import *
from ..db.bonuses import *
from ..db.session import SessionDep
from ..db.api_responses import PrivilegeDataJSON, PrivilegeHistoryDataJSON, HistoryData
from typing import Annotated
from fastapi.encoders import jsonable_encoder
from contextlib import asynccontextmanager
import uvicorn
from multiprocessing import Process
import os
import datetime as dt


def get_user_privileges(user_id: int, session: SessionDep) -> PrivilegeDataJSON:
    privilege = session.exec(
        select(Privilege).where(Privilege.user_id == user_id)
    ).first()
    if not privilege:
        return JSONResponse(content={"message": "User not found"}, status_code=404)
    return privilege


def get_privilege_history(
    user_id: int, session: SessionDep
) -> PrivilegeHistoryDataJSON:
    query = select(Privilege).where(Privilege.user_id == user_id)
    privilege = session.exec(query).first()
    if not privilege:
        return JSONResponse(content={"message": "User not found"}, status_code=404)
    query = (
        select(Privilege, PrivilegeHistory)
        .where(Privilege.user_id == user_id)
        .join(PrivilegeHistory, Privilege.id == PrivilegeHistory.privilege_id)
    )
    history = session.exec(query).all()
    items = []
    for h in history:
        items.append(
            HistoryData(
                date=str(h[1].datetime),
                ticket_id=str(h[1].ticket_id),
                balanceDiff=h[1].balance_diff,
                operationType=h[1].operation_type,
            )
        )
    return PrivilegeHistoryDataJSON(
        status=privilege.status, balance=privilege.balance, history=items
    )


def reduce_bonuses(reduce: ChangeBonusesJSON, session: SessionDep) -> PrivilegeDataJSON:
    query = select(Privilege).where(Privilege.user_id == reduce.user_id)
    privilege = session.exec(query).first()
    if not privilege:
        return JSONResponse(content={"message": "User not found"}, status_code=404)
    new_balance = privilege.balance - reduce.bonuses
    if new_balance < 0:
        new_balance = 0
    query = (
        update(Privilege)
        .where(Privilege.id == privilege.id)
        .values(balance=new_balance)
    )
    session.exec(query)
    session.commit()
    session.refresh(privilege)
    session.add(
        PrivilegeHistory(
            privilege_id=privilege.id,
            ticket_id=reduce.ticket_id,
            datetime=dt.datetime.now(),
            balance_diff=reduce.bonuses,
            operation_type="DEBIT_THE_ACCOUNT",
        )
    )
    session.commit()
    return privilege


def add_bonuses(add: ChangeBonusesJSON, session: SessionDep) -> PrivilegeDataJSON:
    query = select(Privilege).where(Privilege.user_id == add.user_id)
    privilege = session.exec(query).first()
    if not privilege:
        return JSONResponse(content={"message": "User not found"}, status_code=404)
    new_balance = privilege.balance + add.bonuses
    query = (
        update(Privilege)
        .where(Privilege.id == privilege.id)
        .values(balance=new_balance)
    )
    session.exec(query)
    session.commit()
    session.refresh(privilege)
    session.add(
        PrivilegeHistory(
            privilege_id=privilege.id,
            ticket_id=add.ticket_id,
            datetime=dt.datetime.now(),
            balance_diff=add.bonuses,
            operation_type="FILL_IN_BALANCE",
        )
    )
    session.commit()
    return privilege


def calculate_price(
    calculatePriceJSON: CalculatePriceJSON, session: SessionDep
) -> PaymentDataJSON:
    query = select(Privilege).where(Privilege.user_id == calculatePriceJSON.user_id)
    privilege = session.exec(query).first()

    if not privilege:
        return JSONResponse(content={"message": "User not found"}, status_code=404)

    if not calculatePriceJSON.paidFromBalance:
        additional_bonuses = round(0.1 * calculatePriceJSON.price)
        add_bonuses(
            ChangeBonusesJSON(
                name=calculatePriceJSON.name,
                bonuses=additional_bonuses,
                ticket_id=calculatePriceJSON.ticket_id,
            ),
            session=session,
        )
        return PaymentDataJSON(paidByMoney=calculatePriceJSON.price, paidByBonuses=0)

    if privilege.balance >= calculatePriceJSON.price:
        paidByMoney = 0
        paidByBonuses = calculatePriceJSON.price
    else:
        paidByMoney = calculatePriceJSON.price - privilege.balance
        paidByBonuses = privilege.balance

    reduce_bonuses(
        ChangeBonusesJSON(
            name=calculatePriceJSON.name,
            bonuses=paidByBonuses,
            ticket_id=calculatePriceJSON.ticket_id,
        ),
        session=session,
    )
    return PaymentDataJSON(paidByMoney=paidByMoney, paidByBonuses=paidByBonuses)


def cancel(
    cancelTicketJSON: CancelTicketJSON, session: SessionDep
) -> PrivilegeDataJSON:
    query = (
        select(Privilege, PrivilegeHistory)
        .where(Privilege.user_id == cancelTicketJSON.user_id)
        .join(PrivilegeHistory, Privilege.id == PrivilegeHistory.privilege_id)
        .where(PrivilegeHistory.ticket_id == cancelTicketJSON.ticket_id)
    )
    privilege_history = session.exec(query).first()
    if not privilege_history:
        return JSONResponse(
            content={"message": "User or ticket not found"}, status_code=404
        )

    changeBonusesJSON = ChangeBonusesJSON(
        name=cancelTicketJSON.name,
        bonuses=privilege_history[1].balance_diff,
        ticket_id=cancelTicketJSON.ticket_id,
    )
    if privilege_history[1].operation_type == "DEBIT_THE_ACCOUNT":
        return add_bonuses(changeBonusesJSON, session=session)
    else:
        return reduce_bonuses(changeBonusesJSON, session=session)
