FROM python:3.10-slim

WORKDIR /app

RUN apt-get update && apt-get install -y gcc g++ libpq-dev

COPY app/requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

# Copy application source from app/ subdirectory into /app
COPY app/ .

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
