FROM python:3.10.12-slim

WORKDIR /app


RUN apt-get update && apt-get install -y libgl1-mesa-glx libglib2.0-0 libgles2 libegl1

WORKDIR /app

COPY requirements.txt .

RUN pip install -r requirements.txt

COPY . .

ENV PYTHONUNBUFFERED=1

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
