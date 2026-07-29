FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY main.py .

# Railway sets $PORT — use shell form so it expands
CMD uvicorn main:app --host 0.0.0.0 --port $PORT
