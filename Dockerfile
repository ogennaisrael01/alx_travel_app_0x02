FROM python:alpine3.23 AS builder

WORKDIR /app

RUN pip install --upgrade pip

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

COPY . .

COPY requirements.txt /app

RUN pip install --no-cache-dir -r requirements.txt

COPY . /app

EXPOSE 8000

ENV PYTHONPATH='/app'

CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]
