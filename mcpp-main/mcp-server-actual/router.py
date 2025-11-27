
from typing import Dict, Any, Optional, List, Set

# Field hint sets for decision making
PERSONAL_HINTS: Set[str] = {
    "first_name","middle_name","last_name","father_name","mother_name","spouse_name",
    "dob","date_of_birth","gender","marital_status","nationality",
    "blood_group","personal_email","personal_contact"
}

ADDRESS_HINTS: Set[str] = {
    "permanent_address","present_address","permanent_city","present_city",
    "permanent_state","present_state","permanent_pin","present_pin",
    "permanent_door_no","present_door_no"
}

DOCUMENT_HINTS: Set[str] = {
    "doc_type","doc_id","file","document_number","document_type","filename",
    "aadhar_number","pan_number","voter_id","passport_number"
}

BANK_HINTS: Set[str] = {
    "bank_account_no","ifsc","bank_name","branch_name","account_holder_name"
}

EMERGENCY_HINTS: Set[str] = {
    "emergency_contact","emergency_phone","emergency_name","emergency_relation"
}

GENERAL_HINTS: Set[str] = {
    "status","active","remarks","description","notes","comments"
}

def choose_update_endpoint(resource: str, payload: Dict[str, Any], canonical_map: Dict[str, str]) -> Optional[str]:
    """
    Decide the most specific endpoint for an 'update' operation based on payload keys.
    - resource: e.g. 'employee', 'attendance', 'leave'
    - payload: dict of provided fields
    - canonical_map: mapping of functional tool -> endpoint
    """
    keys = set(k.lower() for k in payload.keys())

    # Employee specific routing
    if resource == "employee":
        if keys & DOCUMENT_HINTS and "employee.document.update" in canonical_map:
            return canonical_map["employee.document.update"]
        if keys & BANK_HINTS and "employee.bank.update" in canonical_map:
            return canonical_map["employee.bank.update"]
        if keys & EMERGENCY_HINTS and "employee.emergency.update" in canonical_map:
            return canonical_map["employee.emergency.update"]
        if keys & ADDRESS_HINTS and "employee.address.update" in canonical_map:
            return canonical_map["employee.address.update"]
        if keys & PERSONAL_HINTS and "employee.details.update" in canonical_map:
            return canonical_map["employee.details.update"]
        # doc_id or name heuristic
        if "doc_id" in keys or "name" in keys:
            # prefer details -> address -> document
            for k in ("employee.details.update","employee.address.update","employee.document.update","employee.update"):
                if k in canonical_map:
                    return canonical_map[k]
        # fallback to employee.update
        return canonical_map.get("employee.update")

    # Attendance routing
    if resource == "attendance":
        # if approving flag present or action=approve
        if "approve" in keys or "action" in keys and payload.get("action") == "approve":
            return canonical_map.get("attendance.record.approve")
        if "reject" in keys or "action" in keys and payload.get("action") == "reject":
            return canonical_map.get("attendance.record.reject")
        # fallback to attendance update
        return canonical_map.get("attendance.record.update")

    # Leave routing
    if resource == "leave":
        if "approve" in keys or payload.get("action") == "approve":
            return canonical_map.get("leave.request.approve")
        if "reject" in keys or payload.get("action") == "reject":
            return canonical_map.get("leave.request.reject")
        return canonical_map.get("leave.request.update")

    # Asset routing
    if resource == "asset":
        if "approve" in keys or payload.get("action") == "approve":
            return canonical_map.get("asset.request.approve")
        if "reject" in keys or payload.get("action") == "reject":
            return canonical_map.get("asset.request.reject")
        return canonical_map.get("asset.request.update") or canonical_map.get("asset.master.update")

    # Inventory or general fallback
    # try resource.update, else return None
    return canonical_map.get(f"{resource}.update") or None
