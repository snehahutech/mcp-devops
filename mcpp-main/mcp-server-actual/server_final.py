
# server_final.py - enterprise MCP server skeleton
import os, json, logging
from mcp.server.fastmcp import FastMCP
from erp_mcp.mapping_loader import load_mapping
from erp_mcp.router import choose_update_endpoint
from erp_mcp.validator import validate_payload
import httpx

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("erp_mcp")

BASE_URL = os.environ.get("ERP_BASE_URL","https://apis.dev.smnl.in").rstrip("/")
API_TOKEN = os.environ.get("API_TOKEN","")

def auth_header():
    t = API_TOKEN.strip()
    if not t: return ""
    return t if t.lower().startswith("bearer ") else f"Bearer {t}"

AUTH = auth_header()
TIMEOUT = 30

class Client:
    async def call(self, method, url, body=None, params=None):
        headers = {"Accept":"application/json"}
        if AUTH: headers["Authorization"]=AUTH
        if body is not None: headers["Content-Type"]="application/json"
        full = url if url.startswith("http") else BASE_URL + "/" + url.lstrip("/")
        async with httpx.AsyncClient(timeout=TIMEOUT) as c:
            r = await c.request(method, full, json=body, params=params or {}, headers=headers)
            try: data = r.json()
            except: data = {"raw": r.text}
            return {"status": r.status_code, "body": data}

client = Client()
CANONICAL = load_mapping()

mcp = FastMCP("ERP-MCP")

def make_handler(tool_name, method):
    endpoint = CANONICAL.get(tool_name)
    async def handler(**kwargs):
        params={}
        data={}
        example={}
        if "data" in kwargs and isinstance(kwargs["data"], dict):
            data.update(kwargs["data"])
        for k,v in kwargs.items():
            if k=="data": continue
            if k.startswith("query_"): params[k[6:]]=v
            else: data[k]=v

        if tool_name.endswith(".update") and endpoint is None:
            resource = tool_name.split(".")[0]
            chosen = choose_update_endpoint(resource, data, CANONICAL)
            endpoint = chosen

        example = {}
        clean, notes = validate_payload(data, example)
        body = {"data": clean} if method in ("POST","PUT") else None
        res = await client.call(method, endpoint, body=body, params=params)
        return {"endpoint": endpoint, "notes": notes, "response": res}
    return handler

# Register functional tools dynamically
for key, url in CANONICAL.items():
    method = "GET"
    if key.endswith("create"): method="POST"
    if key.endswith("update"): method="PUT"
    if key.endswith("approve") or key.endswith("reject"): method="POST"
    mcp.tool(name=key, description=f"Mapped to {url}")(make_handler(key, method))

@mcp.tool()
async def debug_show_mapping():
    return CANONICAL

@mcp.tool()
async def debug_raw_call(method: str, url: str, data: dict=None, params: dict=None):
    return await client.call(method, url, body=data, params=params)

if __name__=='__main__':
    import sys
    transport = sys.argv[1] if len(sys.argv)>1 else "stdio"
    mcp.run(transport)
