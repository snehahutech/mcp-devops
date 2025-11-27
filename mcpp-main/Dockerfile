FROM python:3.11-slim

WORKDIR /app

# Copy only the MCP server code
COPY mcp-server-actual/ /app

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

EXPOSE 8000

CMD ["uvicorn", "http_app:app", "--host", "0.0.0.0", "--port", "8000"]
