FROM python:3.10

WORKDIR /code

ARG bonus_service="bonuses"
ARG flight_service="flights"
ARG ticket_service="tickets"
ARG identity_provider="keycloak"
ARG database_url

ENV BONUS_SERVICE=$bonus_service
ENV FLIGHT_SERVICE=$flight_service
ENV TICKET_SERVICE=$ticket_service
ENV DATABASE_URL=$database_url

COPY ./requirements.txt /code/requirements.txt

RUN pip install --no-cache-dir --upgrade -r /code/requirements.txt

COPY ./app /code/app

CMD ["fastapi", "run", "app/main.py", "--port", "8080"]
