FROM python:3.11

# Install curl (for GitHub Actions health test)
RUN apt update && apt install -y curl

# Set working directory
WORKDIR /app

# Copy ALL project files into container
COPY . /app

# ❗ Install dependencies from the correct file
RUN pip install --no-cache-dir -r mcp-server-actual/requirements.txt

# Expose FastAPI port
EXPOSE 8000

# Run FastAPI wrapper
CMD ["uvicorn", "http_app:app", "--host", "0.0.0.0", "--port", "8000"]
