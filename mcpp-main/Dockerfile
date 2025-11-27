FROM python:3.11-slim

# Set working directory inside container
WORKDIR /app

# Copy ONLY the actual server code
COPY mcpp-main/mcp-server-actual/ /app/

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Expose port
EXPOSE 8000

# Run the FastAPI wrapper
CMD ["uvicorn", "http_app:app", "--host", "0.0.0.0", "--port", "8000"]
