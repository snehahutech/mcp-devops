FROM python:3.11-slim

# Create app folder
WORKDIR /app

# Copy ONLY the MCP server actual code
COPY mcp-server-actual/ /app/

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Expose port
EXPOSE 8000

# Start FastAPI wrapper
CMD ["uvicorn", "http_app:app", "--host", "0.0.0.0", "--port", "8000"]
