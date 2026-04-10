FROM python:3.10-slim

WORKDIR /app

RUN apt-get update && apt-get install -y gcc g++ libpq-dev

# Install CPU version of torch to save time and space
RUN pip install torch --index-url https://download.pytorch.org/whl/cpu

COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

COPY . .

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
