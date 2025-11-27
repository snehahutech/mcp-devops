FROM python:3.11-slim

# Install curl (needed for GitHub Actions health check)
RUN apt update && apt install -y curl

WORKDIR /app

# Copy ONLY the server folder
COPY mcp-server-actual/ /app/

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

EXPOSE 8000

CMD ["uvicorn", "http_app:app", "--host", "0.0.0.0", "--port", "8000"]
