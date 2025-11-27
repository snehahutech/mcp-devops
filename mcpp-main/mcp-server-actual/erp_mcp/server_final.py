# server_final.py — ENTERPRISE MCP SERVER (WORKING FASTMCP VERSION)
import os, json, logging, sys
from urllib.parse import urlparse, parse_qs
import httpx
from dotenv import load_dotenv

from mcp.server.fastmcp import FastMCP
from erp_mcp.mapping_loader import load_mapping
from erp_mcp.validator import validate_payload


logging.basicConfig(
    level=logging.INFO,
    stream=sys.stderr,     # required for stdio transport
    format="%(levelname)s:%(name)s:%(message)s"
)
logger = logging.getLogger("erp_mcp")

load_dotenv()


BASE_URL = os.environ.get("ERP_BASE_URL", "").rstrip("/")
API_TOKEN = os.environ.get("API_TOKEN")

if not BASE_URL:
    raise ValueError("Missing ERP_BASE_URL")
if not API_TOKEN:
    raise ValueError("Missing API_TOKEN")


def auth_header():
    t = API_TOKEN.strip()
    return t if t.lower().startswith("bearer ") else f"Bearer {t}"


AUTH = auth_header()
TIMEOUT = 30


class Client:
    async def call(self, method, url, body=None, params=None):
        try:
            headers = {
                "Accept": "application/json",
                "Authorization": AUTH
            }

            if method in ("POST", "PUT", "PATCH"):
                headers["Content-Type"] = "application/json"

            full = f"{BASE_URL}{url}"

            async with httpx.AsyncClient(timeout=TIMEOUT) as c:
                r = await c.request(
                    method,
                    full,
                    json=body,
                    params=params or {},
                    headers=headers,
                )

            try:
                data = r.json()
            except:
                data = {"raw": r.text}

            return {
                "error": r.status_code >= 400,
                "status": r.status_code,
                "url": full,
                "body": data
            }

        except Exception as e:
            logger.exception("HTTP call failed")
            return {"error": True, "message": str(e)}


client = Client()

CANONICAL = load_mapping()
mcp = FastMCP("ERP-MCP")


def make_handler(tool_name, method):
    cfg = CANONICAL[tool_name]
    raw_url = cfg.get("url")
    body_schema = cfg.get("body_schema")
    body_example = cfg.get("body_example")

    parsed = urlparse(raw_url)
    path = parsed.path
    query_defaults = {k: v[0] for k, v in parse_qs(parsed.query).items()}

    if method == "GET":

        async def handler():
            res = await client.call("GET", path, None, query_defaults)
            return {
                "tool": tool_name,
                "method": "GET",
                "endpoint": path,
                "params_sent": query_defaults,
                "response": res
            }

        return handler

    # POST / PUT
    async def handler(data: dict = None):
        if data is None:
            data = body_example or {}

        clean, notes = validate_payload(data, body_schema)
        body = {"data": clean}

        res = await client.call(method, path, body, query_defaults)

        return {
            "tool": tool_name,
            "method": method,
            "endpoint": path,
            "params_sent": query_defaults,
            "body_sent": body,
            "response": res,
            "notes": notes
        }

    return handler


# -------------------------------
# REGISTER TOOLS (NO parameters=)
# -------------------------------
for key, cfg in CANONICAL.items():
    method = cfg.get("method", "GET")

    mcp.tool(
        name=key,
        description=f"Backend endpoint {cfg.get('url')}"
    )(make_handler(key, method))


if __name__ == "__main__":
    transport = sys.argv[1] if len(sys.argv) > 1 else "stdio"
    logger.info(f"Starting ERP MCP server using transport={transport}")
    mcp.run(transport)
