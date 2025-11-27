#!/usr/bin/env python3
"""
server_functional.py
FastMCP functional-tool server (Hybrid routing) for HRMS Postman collection.

Place next to:
 - HRMS.postman_collection.json
 - .env (API_TOKEN=Bearer <token>, ERP_BASE_URL=https://apis.dev.smnl.in)
Run:
  python server_functional.py uv
"""

import os
import json
import logging
from typing import Dict, Any, Optional
from pathlib import Path
from urllib.parse import urljoin
from dotenv import load_dotenv
load_dotenv()

import httpx
from mcp.server.fastmcp import FastMCP

# --- Logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger("erp-functional-mcp")

# --- Config
BASE_URL = os.environ.get("ERP_BASE_URL", "https://apis.dev.smnl.in").rstrip("/")
API_TOKEN = os.environ.get("API_TOKEN", "")
COLLECTION_PATH = os.environ.get("POSTMAN_COLLECTION_PATH", "HRMS.postman_collection.json")
TIMEOUT = float(os.environ.get("REQUEST_TIMEOUT", "30"))

if not API_TOKEN:
    logger.warning("API_TOKEN not set. Set API_TOKEN=Bearer <token> in .env")

def build_auth_header(token: str) -> str:
    t = token.strip()
    if not t:
        return ""
    return t if t.lower().startswith("bearer ") else f"Bearer {t}"

AUTH_HEADER = build_auth_header(API_TOKEN)

# --- Simple HTTP client
class ERPClient:
    def __init__(self, base_url: str, auth_header: str):
        self.base = base_url
        self.auth = auth_header

    async def request(self, method: str, url: str, json_body: Optional[dict]=None, params: Optional[dict]=None) -> Dict[str, Any]:
        full = url if url.startswith("http") else urljoin(self.base + "/", url.lstrip("/"))
        headers = {"Accept": "application/json"}
        if self.auth:
            headers["Authorization"] = self.auth
        if json_body is not None:
            headers["Content-Type"] = "application/json"
        try:
            async with httpx.AsyncClient(timeout=TIMEOUT) as client:
                resp = await client.request(method=method, url=full, json=json_body, params=params or {}, headers=headers)
                text = resp.text or ""
                try:
                    body = resp.json() if text else {}
                except Exception:
                    body = {"raw_text": text}
                if resp.status_code >= 400:
                    return {"error": True, "status": resp.status_code, "body": body}
                return {"error": False, "status": resp.status_code, "body": body}
        except Exception as e:
            logger.exception("Upstream request failed")
            return {"error": True, "status": None, "body": str(e)}

api_client = ERPClient(BASE_URL, AUTH_HEADER)

# --- Load Postman collection for schema extraction (optional)
def load_collection(path: str) -> dict:
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(f"Collection file not found at {path}")
    return json.loads(p.read_text(encoding="utf-8"))

collection = load_collection(COLLECTION_PATH)
# Build a tiny lookup of endpoint example bodies to drive expected keys
endpoint_examples: Dict[str, dict] = {}
for itm in collection.get("item", []):
    # recursive traversal
    def walk(items, parent=""):
        for it in items:
            name = it.get("name", "")
            if "request" in it:
                req = it["request"]
                url_info = req.get("url", {})
                raw = url_info.get("raw") if isinstance(url_info, dict) else (url_info if isinstance(url_info,str) else "")
                endpoint_examples[raw] = req.get("body", {})
            if "item" in it:
                walk(it["item"], parent + "/" + name if parent else name)
    walk([itm])

# --- Functional tool -> canonical backend endpoint mapping (from Phase 2)
# (Shortened keys: full list from prior mapping; add or tune as needed)
CANONICAL_MAP: Dict[str, str] = {
    # HRMS master data
    "hr.state.get": "/api/method/htssuite.master_data.doctype.states.api.get_records",
    "hr.state.get_by_id": "/api/method/htssuite.master_data.doctype.states.api.get_records_by_id",
    "hr.state.create": "/api/method/htssuite.master_data.doctype.states.api.create_record",
    "hr.state.update": "/api/method/htssuite.master_data.doctype.states.api.update_record",

    "hr.company.get": "/api/method/htssuite.master_data.doctype.company_setup.api.get_records",
    "hr.company.get_by_id": "/api/method/htssuite.master_data.doctype.company_setup.api.get_records_by_id",
    "hr.company.create": "/api/method/htssuite.master_data.doctype.company_setup.api.create_record",
    "hr.company.update": "/api/method/htssuite.master_data.doctype.company_setup.api.update_record",

    # Employee consolidated
    "employee.get": "/api/method/htssuite.employee_management.doctype.employee.api.get_records",
    "employee.get_by_id": "/api/method/htssuite.employee_management.doctype.employee.api.get_records_by_id",
    "employee.create": "/api/method/htssuite.employee_management.doctype.employee.api.create_record",
    # employee.update will be hybrid/routed, see handler

    # Employee sub-resources
    "employee.details.get": "/api/method/htssuite.employee_management.doctype.personal_details.api.get_records",
    "employee.details.get_by_id": "/api/method/htssuite.employee_management.doctype.personal_details.api.get_records_by_id",
    "employee.details.create": "/api/method/htssuite.employee_management.doctype.personal_details.api.create_record",
    "employee.details.update": "/api/method/htssuite.employee_management.doctype.personal_details.api.update_record",

    "employee.address.get": "/api/method/htssuite.employee_management.doctype.address_details.api.get_records",
    "employee.address.get_by_id": "/api/method/htssuite.employee_management.doctype.address_details.api.get_records_by_id",
    "employee.address.update": "/api/method/htssuite.employee_management.doctype.address_details.api.update_record",

    "employee.document.get": "/api/method/htssuite.employee_management.doctype.document_details.api.get_records",
    "employee.document.get_by_id": "/api/method/htssuite.employee_management.doctype.document_details.api.get_records_by_id",
    "employee.document.create": "/api/method/htssuite.employee_management.doctype.document_details.api.create_record",
    "employee.document.update": "/api/method/htssuite.employee_management.doctype.document_details.api.update_record",

    # Attendance
    "attendance.record.get": "/api/method/htssuite.attendance_management.doctype.attendance.api.get_records",
    "attendance.record.get_by_id": "/api/method/htssuite.attendance_management.doctype.attendance.api.get_records_by_id",
    "attendance.record.update": "/api/method/htssuite.attendance_management.doctype.attendance.api.update_record",
    "attendance.record.approve": "/api/method/htssuite.leave_management.doctype.attendance_reconcilation.api.approval",
    "attendance.record.reject": "/api/method/htssuite.leave_management.doctype.attendance_reconcilation.api.rejection",
    "attendance.record.reconcile": "/api/method/htssuite.leave_management.doctype.attendance_reconcilation.api.erp_status_filters",

    # Leave
    "leave.request.get": "/api/method/htssuite.leave_management.doctype.leave_request.api.get_records",
    "leave.request.create": "/api/method/htssuite.leave_management.doctype.leave_request.api.create_record",
    "leave.request.update": "/api/method/htssuite.leave_management.doctype.leave_request.api.update_record",
    "leave.request.approve": "/api/method/htssuite.leave_management.doctype.leave_request.api.approve",
    "leave.request.reject": "/api/method/htssuite.leave_management.doctype.leave_request.api.reject",

    # Payroll (examples)
    "payroll.allowance.get": "/api/method/htssuite.payroll_configurations.doctype.additional_allowance.api.get_records",
    "payroll.allowance.create": "/api/method/htssuite.payroll_configurations.doctype.additional_allowance.api.create_record",
    "payroll.allowance.update": "/api/method/htssuite.payroll_configurations.doctype.additional_allowance.api.update_record",

    "payroll.overtime.get": "/api/method/htssuite.payroll_configurations.doctype.over_time_category_details.api.get_records",
    "payroll.overtime.create": "/api/method/htssuite.payroll_configurations.doctype.over_time_category_details.api.create_record",
    "payroll.overtime.update": "/api/method/htssuite.payroll_configurations.doctype.over_time_category_details.api.update_record",

    # Assets
    "asset.master.get": "/api/method/htssuite.assets_management.doctype.assets_master.api.get_records",
    "asset.master.create": "/api/method/htssuite.assets_management.doctype.assets_master.api.create_record",
    "asset.master.update": "/api/method/htssuite.assets_management.doctype.assets_master.api.update_record",

    "asset.request.get": "/api/method/htssuite.assets_management.doctype.asset_request.api.get_records",
    "asset.request.create": "/api/method/htssuite.assets_management.doctype.asset_request.api.create_record",
    "asset.request.update": "/api/method/htssuite.assets_management.doctype.asset_request.api.update_record",
    "asset.request.approve": "/api/method/htssuite.assets_management.doctype.asset_request.api.approve_record",
    "asset.request.reject": "/api/method/htssuite.assets_management.doctype.asset_request.api.reject_record",

    # Reimbursement
    "reimbursement.get": "/api/method/htssuite.reimbursement.doctype.reimbursement_request.api.get_records",
    "reimbursement.get_by_id": "/api/method/htssuite.reimbursement.doctype.reimbursement_request.api.get_records_by_id",
    "reimbursement.create": "/api/method/htssuite.reimbursement.doctype.reimbursement_request.api.create_record",
    "reimbursement.update": "/api/method/htssuite.reimbursement.doctype.reimbursement_request.api.update_record",

    # Inventory (examples)
    "inv.country.get": "/api/method/htsinventory.inventory_general_setup.doctype.inventory_country.api.get_records",
    "inv.country.create": "/api/method/htsinventory.inventory_general_setup.doctype.inventory_country.api.create_record",
    "inv.state.get": "/api/method/htsinventory.inventory_general_setup.doctype.inventory_state.api.get_records",
    "inv.stock.get": "/api/method/htsinventory.inventory_management.doctype.inventory_stock.api.get_records",
    "inv.reconciliation.get": "/api/method/htsinventory.inventory_management.doctype.inventory_reconciliation.api.get_records_v1",
    "inv.reconciliation.create": "/api/method/htsinventory.inventory_management.doctype.inventory_reconciliation.api.create_record",
}

# --- Helper: choose best endpoint for updates (hybrid logic)
def choose_update_endpoint(resource: str, payload: Dict[str, Any]) -> Optional[str]:
    """
    Given a resource like 'employee' and payload keys, pick the most specific canonical endpoint.
    Strategy:
      - If payload contains doc_id or name and a matching sub-resource endpoint exists, prefer sub-resource update.
      - If payload contains fields specific to personal_details (e.g., 'father_name', 'spouse_name'), choose personal_details update.
      - Fallback to main resource update endpoint if present.
    """
    # specific heuristics (extend as needed)
    keys = set(payload.keys())
    # personal-details hint
    personal_hint = {"father_name", "mother_name", "spouse_name", "dob", "gender", "marital_status"}
    address_hint = {"permanent_door_no", "permanent_state", "permanent_city", "permanent_pin"}
    document_hint = {"file", "doc_type", "doc_id", "filename"}

    if keys & personal_hint and "employee.details.update" in CANONICAL_MAP:
        return CANONICAL_MAP["employee.details.update"]
    if keys & address_hint and "employee.address.update" in CANONICAL_MAP:
        return CANONICAL_MAP["employee.address.update"]
    if keys & document_hint and "employee.document.update" in CANONICAL_MAP:
        return CANONICAL_MAP["employee.document.update"]

    # if doc_id provided and a specific update exists
    if ("doc_id" in payload or "name" in payload):
        # try personal, address, document in order
        for k in ("employee.details.update","employee.address.update","employee.document.update","employee.update"):
            if k in CANONICAL_MAP:
                return CANONICAL_MAP[k]

    # fallback
    return CANONICAL_MAP.get(f"{resource}.update") or None

# --- FastMCP server
mcp = FastMCP("ERP-Functional-MCP")

# Generic tool handler generator
def make_tool_handler(tool_name: str, method: str = "GET"):
    canonical = CANONICAL_MAP.get(tool_name)

    async def handler(**kwargs):
        # Build params and body
        params = {}
        data = {}
        # kwargs might be 'page', 'page_length', 'data' or individual fields.
        for k,v in kwargs.items():
            if k in ("page", "page_length"):
                params[k] = v
            elif k == "data" and isinstance(v, dict):
                data.update(v)
            elif k.startswith("query_"):
                params[k[6:]] = v
            else:
                data[k] = v

        # If GET: pass params; if POST/PUT: wrap in {"data": {...}}
        if method.upper() == "GET":
            res = await api_client.request("GET", canonical or tool_name, json_body=None, params=params)
            return res
        elif method.upper() in ("POST","PUT","PATCH"):
            # If tool is an 'update' tool with hybrid routing, pick the best endpoint
            if tool_name.endswith(".update") and canonical is None:
                # choose based on resource prefix (e.g., employee.update -> 'employee')
                resource = tool_name.split(".")[0]
                chosen = choose_update_endpoint(resource, data)
                if not chosen:
                    return {"error": True, "body": f"No backend endpoint mapped for {tool_name} with provided payload"}
                request_body = {"data": data}
                res = await api_client.request(method.upper(), chosen, json_body=request_body, params=params)
                return res
            else:
                # use canonical endpoint
                if not canonical:
                    return {"error": True, "body": f"No canonical endpoint defined for {tool_name}"}
                request_body = {"data": data}
                res = await api_client.request(method.upper(), canonical, json_body=request_body, params=params)
                return res
        else:
            # DELETE or others
            if not canonical:
                return {"error": True, "body": f"No canonical endpoint defined for {tool_name}"}
            res = await api_client.request(method.upper(), canonical, json_body={"data": data} if data else None, params=params)
            return res

    # attach metadata
    handler._tool_name = tool_name
    handler._canonical = canonical
    return handler

# --- Register functional tools (only; keep inspector clean)
REGISTRATION_LIST = [
    # HRMS
    ("hr.state.get","GET"),("hr.state.get_by_id","GET"),("hr.state.create","POST"),("hr.state.update","PUT"),
    ("hr.company.get","GET"),("hr.company.get_by_id","GET"),("hr.company.create","POST"),("hr.company.update","PUT"),
    ("hr.department.get","GET"),("hr.department.create","POST"),("hr.department.update","PUT"),
    ("hr.designation.get","GET"),("hr.designation.create","POST"),("hr.designation.update","PUT"),
    ("hr.location.get","GET"),("hr.location.create","POST"),("hr.location.update","PUT"),

    # Employee
    ("employee.get","GET"),("employee.get_by_id","GET"),("employee.create","POST"),("employee.update","PUT"),
    ("employee.details.get","GET"),("employee.details.get_by_id","GET"),("employee.details.create","POST"),("employee.details.update","PUT"),
    ("employee.address.get","GET"),("employee.address.get_by_id","GET"),("employee.address.update","PUT"),
    ("employee.document.get","GET"),("employee.document.get_by_id","GET"),("employee.document.create","POST"),("employee.document.update","PUT"),

    # Attendance
    ("attendance.record.get","GET"),("attendance.record.get_by_id","GET"),("attendance.record.update","PUT"),
    ("attendance.record.approve","POST"),("attendance.record.reject","POST"),("attendance.record.reconcile","GET"),

    # Leave & Payroll
    ("leave.request.get","GET"),("leave.request.create","POST"),("leave.request.update","PUT"),
    ("leave.request.approve","POST"),("leave.request.reject","POST"),
    ("payroll.allowance.get","GET"),("payroll.allowance.create","POST"),("payroll.allowance.update","PUT"),
    ("payroll.overtime.get","GET"),("payroll.overtime.create","POST"),("payroll.overtime.update","PUT"),

    # Assets
    ("asset.master.get","GET"),("asset.master.create","POST"),("asset.master.update","PUT"),
    ("asset.request.get","GET"),("asset.request.create","POST"),("asset.request.update","PUT"),
    ("asset.request.approve","POST"),("asset.request.reject","POST"),

    # Reimbursement
    ("reimbursement.get","GET"),("reimbursement.get_by_id","GET"),("reimbursement.create","POST"),("reimbursement.update","PUT"),

    # Inventory
    ("inv.country.get","GET"),("inv.country.create","POST"),("inv.state.get","GET"),
    ("inv.stock.get","GET"),("inv.reconciliation.get","GET"),("inv.reconciliation.create","POST"),

    # Reports
    ("report.attendance","GET"),("report.asset","GET"),("report.employee","GET"),
    ("report.leave","GET"),("report.payroll","GET"),("report.reimbursement","GET"),
]

registered = 0
for tool_name, method in REGISTRATION_LIST:
    handler = make_tool_handler(tool_name, method=method)
    desc = f"Functional tool: {tool_name} -> {CANONICAL_MAP.get(tool_name,'(hybrid/mapped at runtime)')}"
    try:
        mcp.tool(name=tool_name, description=desc)(handler)
        registered += 1
    except Exception as e:
        logger.exception(f"Failed to register {tool_name}: {e}")

logger.info(f"Registered {registered} functional tools.")

# Add a helper tool
@mcp.tool()
async def list_functional_tools() -> Dict[str, Any]:
    items = []
    for t, _ in REGISTRATION_LIST:
        items.append({"tool": t, "backend": CANONICAL_MAP.get(t, "hybrid/runtime")})
    return {"total": len(items), "tools": items}

# health
@mcp.tool()
async def api_health_check() -> Dict[str, Any]:
    # use states list as quick healthcheck
    res = await api_client.request("GET", CANONICAL_MAP["hr.state.get"], json_body=None, params={"page":1,"page_length":1})
    return {"base_url": BASE_URL, "health": res}

# run
if __name__ == "__main__":
    import sys
    transport = sys.argv[1] if len(sys.argv) > 1 else "stdio"
    logger.info(f"Starting ERP Functional MCP (transport={transport}) base={BASE_URL}")
    mcp.run(transport)
