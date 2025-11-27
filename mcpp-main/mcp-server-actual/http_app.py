# http_app.py - small HTTP wrapper for your MCP server

from fastapi import FastAPI

app = FastAPI(title="ERP MCP Wrapper")

@app.get("/health")
def health():
    """
    Simple health check to prove the container + app are running.
    """
    return {
        "status": "ok",
        "service": "erp-mcp-wrapper",
        "message": "MCP server container is up and HTTP wrapper is responding."
    }
