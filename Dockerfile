FROM python:3.11-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
    curl && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

RUN adduser --disabled-password --gecos '' appuser
USER appuser

EXPOSE 8000

CMD ["python", "-m", "uvicorn", "web_ui.app:app", "--host", "0.0.0.0", "--port", "8000"]
