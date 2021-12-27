FROM python:3-slim

WORKDIR /app

COPY . .

RUN python3 -m pip install -U -r requirements.txt

ENTRYPOINT exec gunicorn -b :$PORT -w 2 main:app
