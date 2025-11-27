FROM python:3.11

# Install curl for health check
RUN apt update && apt install -y curl

# Set working directory
WORKDIR /app

# Copy full project into /app
COPY . /app

# Install requirements (correct path based on your screenshot)
RUN pip install --no-cache-dir -r requirements.txt

# Expose FastAPI port
EXPOSE 8000

# Run the FastAPI wrapper
CMD ["uvicorn", "http_app:app", "--host", "0.0.0.0", "--port", "8000"]
