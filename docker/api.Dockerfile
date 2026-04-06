FROM python:3.12-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc libpq-dev && \
    rm -rf /var/lib/apt/lists/*

COPY pyproject.toml ./
RUN pip install poetry && poetry install --no-dev

COPY . .

CMD ["uvicorn", "socialmind.api.main:app", "--host", "0.0.0.0", "--port", "8000"]
