FROM python:3.14.2-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .

WORKDIR /app/evaml_2025_server

CMD ["python", "teste1.py"]