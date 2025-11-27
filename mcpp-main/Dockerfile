FROM python:3.11-slim

# Install curl (for GitHub Actions test)
RUN apt update && apt install -y curl

# Create working directory
WORKDIR /app

# Copy ALL FILES from mcp-server-actual into container
COPY mcp-server-actual/ /app/

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Expose wrapper port
EXPOSE 8000

# Start the health wrapper
CMD ["uvicorn", "http_app:app", "--host", "0.0.0.0", "--port", "8000"]
