FROM python:3.11-slim

# Install curl (for GitHub Actions testing)
RUN apt update && apt install -y curl

# Copy all project files into the image
WORKDIR /app
COPY . /app

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Expose FastAPI port
EXPOSE 8000

# Correct entrypoint - http_app.py exists in /app
CMD ["uvicorn", "http_app:app", "--host", "0.0.0.0", "--port", "8000"]
