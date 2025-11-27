#!/usr/bin/env python3
"""
FastMCP server for HRMS Postman collection (Claude Desktop ready).

Usage:
  - Ensure HRMS.postman_collection.json is at /mnt/data/HRMS.postman_collection.json
  - Export your Bearer token: export API_TOKEN="your_jwt_here"
    (On Windows PowerShell: $env:API_TOKEN="your_jwt_here")
  - Run:
      python server.py stdio      # run in stdio mode
      python server.py uv         # run in uv (recommended) mode for Claude Desktop
"""

import os
import re
import json
import hashlib
import logging
from pathlib import Path
from urllib.parse import urljoin
from typing import Any, Dict, List, Optional
from dotenv import load_dotenv
load_dotenv()


import httpx
from mcp.server.fastmcp import FastMCP

# -------------------------
# Logging (ensure goes to stderr)
# -------------------------
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger("erp-mcp")

# -------------------------
# Config
# -------------------------
BASE_URL = os.environ.get("ERP_BASE_URL", "https://apis.dev.smnl.in")
API_TOKEN = os.environ.get("API_TOKEN", "")  # must be just the token string (without Bearer)
COLLECTION_PATH = os.environ.get("POSTMAN_COLLECTION_PATH", "/mnt/data/HRMS.postman_collection.json")
TIMEOUT = 30.0

if not API_TOKEN:
    logger.warning("API_TOKEN not set in env — calls will be unauthenticated unless you set it.")

# normalize bearer header
def build_auth_header(token: str) -> str:
    if not token:
        return ""
    token = token.strip()
    if token.lower().startswith("bearer "):
        return token
    return f"Bearer {token}"

AUTH_HEADER = build_auth_header(API_TOKEN)

# -------------------------
# Utilities
# -------------------------
def claude_safe_tool_name(name: str) -> str:
    """Sanitize and ensure <=64 chars (append 6-char md5 hash when truncated)."""
    cleaned = re.sub(r'[^a-zA-Z0-9_.]', '_', name)
    cleaned = re.sub(r'_+', '_', cleaned).strip('_').lower()
    if len(cleaned) <= 64:
        return cleaned
    h = hashlib.md5(cleaned.encode()).hexdigest()[:6]
    allowed = 64 - 7  # space for '_' + 6 chars
    return f"{cleaned[:allowed]}_{h}"

def safe_identifier(s: str) -> str:
    s = s or ""
    s = s.strip().lower()
    s = re.sub(r'[^a-z0-9]', '_', s)
    s = re.sub(r'_+', '_', s).strip('_')
    if not s:
        s = "x"
    return s

# -------------------------
# Postman collection parser (lightweight)
# -------------------------
class PostmanCollectionParser:
    def __init__(self, path: str):
        p = Path(path)
        if not p.exists():
            raise FileNotFoundError(f"Postman collection not found at: {path}")
        self.data = json.loads(p.read_text(encoding="utf-8"))
        self.name = self.data.get("info", {}).get("name", "collection")
        self.endpoints = []
        self._parse_items(self.data.get("item", []), parent="")

    def _parse_items(self, items: List, parent: str):
        for item in items:
            name = item.get("name", "")
            full = f"{parent}/{name}" if parent else name
            if "request" in item:
                req = item["request"]
                method = (req.get("method") or "GET").upper()
                url_info = req.get("url", {})
                if isinstance(url_info, str):
                    url_raw = url_info
                else:
                    url_raw = url_info.get("raw") or ""
                body = req.get("body", {})
                query_params = {}
                if isinstance(url_info, dict):
                    for q in url_info.get("query", []):
                        if isinstance(q, dict) and q.get("key"):
                            query_params[q.get("key")] = q.get("value", "")
                self.endpoints.append({
                    "name": name,
                    "full_name": full,
                    "method": method,
                    "url": url_raw,
                    "body": body,
                    "query_params": query_params,
                    "request": req
                })
            if "item" in item:
                self._parse_items(item["item"], parent=full)

# -------------------------
# Simple API client
# -------------------------
class ERPAPIClient:
    def __init__(self, base_url: str, auth_header: str):
        self.base_url = base_url.rstrip("/")
        self.auth_header = auth_header

    async def call(self, method: str, url: str, json_body: Optional[dict] = None, params: dict = None) -> Dict[str, Any]:
        full = url if url.startswith("http") else urljoin(self.base_url + "/", url.lstrip("/"))
        headers = {"Accept": "application/json"}
        if self.auth_header:
            headers["Authorization"] = self.auth_header
        if json_body is not None:
            headers["Content-Type"] = "application/json"
        try:
            async with httpx.AsyncClient(timeout=TIMEOUT) as client:
                resp = await client.request(method=method, url=full, json=json_body, params=params or {}, headers=headers)
                # Try to parse JSON
                text = resp.text
                try:
                    data = resp.json() if text else {}
                except Exception:
                    data = {"raw_text": text}
                if resp.status_code >= 400:
                    return {"error": f"Upstream returned {resp.status_code}", "status": resp.status_code, "body": data}
                return {"status": resp.status_code, "body": data}
        except Exception as e:
            logger.exception("API call failed")
            return {"error": str(e)}

# -------------------------
# Create FastMCP server and register tools
# -------------------------
mcp = FastMCP("ERP-MCP-Server")

# Load Postman collection
try:
    parser = PostmanCollectionParser(COLLECTION_PATH)
    logger.info(f"Loaded Postman collection '{parser.name}' with {len(parser.endpoints)} endpoints.")
except Exception as e:
    logger.exception("Failed loading postman collection")
    raise

api_client = ERPAPIClient(BASE_URL, AUTH_HEADER)

# Build a mapping: module.resource.action -> endpoint (choose heuristics)
tool_map: Dict[str, Dict] = {}

for ep in parser.endpoints:
    # derive parts
    parts = [p.strip() for p in ep["full_name"].split("/") if p.strip()]
    module = safe_identifier(parts[0]) if parts else "hrms"
    # resource heuristics: try second-level folder or last meaningful token
    resource = safe_identifier(parts[1]) if len(parts) >= 2 else safe_identifier(ep["name"])
    # action heuristics
    method = ep["method"].upper()
    url = (ep.get("url") or "").lower()
    name_lower = (ep.get("name") or "").lower()

    if "get_records_by_id" in url or "get_records_by_id" in name_lower or ("name=" in url and method == "GET"):
        action = "get_by_id"
    elif method == "GET":
        action = "get"
    elif method == "POST":
        # if 'create' or 'create_record' in url or name -> create, else create
        action = "create"
    elif method in ("PUT", "PATCH"):
        action = "update"
    elif method == "DELETE":
        action = "delete"
    else:
        action = method.lower()

    tool_key = f"{module}.{resource}.{action}"
    tool_key = claude_safe_tool_name(tool_key)

    # Avoid exact duplicate names: if exists, append short hash
    if tool_key in tool_map:
        h = hashlib.md5((ep.get("url","")+ep.get("name","")).encode()).hexdigest()[:4]
        tool_key = claude_safe_tool_name(f"{tool_key}_{h}")

    tool_map[tool_key] = ep

logger.info(f"Prepared {len(tool_map)} tools after grouping.")

# Handler factory
def make_handler(endpoint: Dict):
    async def handler(**kwargs):
        """
        Common behavior for all dynamic tools:
         - separate query params (keys starting with 'q_') and data
         - ensure complete data (if example body had 'data', fill missing with None)
         - call upstream and return native dict
        """
        # Prepare query params
        query_params = {}
        data = {}

        # kwargs might include page/page_length/query_*
        for k, v in kwargs.items():
            if k.startswith("query_"):
                query_params[k[6:]] = v
            elif k in ("page", "page_length"):
                query_params[k] = v
            elif k == "data" and isinstance(v, dict):
                data = v
            else:
                # allow passing individual fields into data
                data[k] = v

        # If the endpoint example body has "raw" JSON with {"data": {...}} we try to preserve keys
        example_body = endpoint.get("body", {}) or {}
        # If raw JSON example exists and contains a top-level "data" obj, try to extract keys
        expected_keys = {}
        if example_body.get("mode") == "raw":
            raw = example_body.get("raw", "").strip()
            try:
                parsed = json.loads(raw) if raw else {}
                if isinstance(parsed, dict) and "data" in parsed and isinstance(parsed["data"], dict):
                    expected_keys = parsed["data"]
            except Exception:
                expected_keys = {}
        elif example_body.get("mode") in ("formdata", "urlencoded"):
            # Extract keys from formdata/urlencoded arrays
            arr = example_body.get("formdata") or example_body.get("urlencoded") or []
            for it in arr:
                if isinstance(it, dict) and it.get("key"):
                    expected_keys[it.get("key")] = ""

        # Default missing expected keys to None to preserve nulls
        if isinstance(expected_keys, dict) and expected_keys:
            for k in expected_keys:
                if k not in data:
                    data[k] = None

        # Build request body and params
        method = endpoint.get("method", "GET").upper()
        url_raw = endpoint.get("url", "")

        request_body = None
        if method in ("POST", "PUT", "PATCH"):
            # upstream expects { "data": { ... } } according to your collection
            request_body = {"data": data}

        # Merge query params defined in Postman example if not present
        for k, v in endpoint.get("query_params", {}).items():
            if k not in query_params:
                query_params[k] = v

        # Call upstream
        result = await api_client.call(method=method, url=url_raw, json_body=request_body, params=query_params)

        # Normalize result as dict (already dict from ERPAPIClient)
        return result

    # attach metadata
    handler._endpoint = endpoint
    return handler

# Register tools with FastMCP
registered = 0
for tool_name, endpoint in tool_map.items():
    handler = make_handler(endpoint)
    desc = f"{endpoint.get('full_name')} ({endpoint.get('method')})"
    try:
        # Use decorator-style registration:
        mcp.tool(name=tool_name, description=desc)(handler)
        registered += 1
    except Exception as e:
        logger.exception(f"Failed registering tool {tool_name}: {e}")

logger.info(f"Registered {registered} tools to FastMCP.")

# Add an index tool for listing available tools
@mcp.tool()
async def list_tools() -> Dict[str, Any]:
    """List tools and their mapped endpoints."""
    items = []
    for tname, ep in tool_map.items():
        items.append({"tool": tname, "method": ep.get("method"), "url": ep.get("url"), "full_name": ep.get("full_name")})
    return {"total": len(items), "tools": items}

# Add a simple health check
@mcp.tool()
async def api_health_check() -> Dict[str, Any]:
    """Quick health check for ERP base URL using a lightweight endpoint (states list)."""
    sample = next((ep for ep in parser.endpoints if "states.api.get_records" in (ep.get("url") or "")), None)
    test_url = sample["url"] if sample else "/api/method/htssuite.master_data.doctype.states.api.get_records?page=1&page_length=1"
    res = await api_client.call("GET", test_url, json_body=None, params={"page": 1, "page_length": 1})
    return {"base_url": BASE_URL, "health": res}

# -------------------------
# Run server
# -------------------------
if __name__ == "__main__":
    import sys
    transport = sys.argv[1] if len(sys.argv) > 1 else "stdio"
    logger.info(f"Starting FastMCP server (transport={transport}) - base_url={BASE_URL}")
    mcp.run(transport)
