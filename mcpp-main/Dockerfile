FROM python:3.11-slim

# Install curl
RUN apt update && apt install -y curl

WORKDIR /app
COPY . /app

WORKDIR /app/mcp-server-actual

RUN if [ -f requirements.txt ]; then pip install --no-cache-dir -r requirements.txt; fi

EXPOSE 8000

CMD ["uvicorn", "http_app:app", "--host", "0.0.0.0", "--port", "8000"]
