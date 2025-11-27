
import json
from typing import Dict, Any, Tuple

def _infer_type(value: Any):
    if value is None:
        return None
    if isinstance(value, (int, float, bool)):
        return value
    if isinstance(value, str):
        v = value.strip().lower()
        if v == "":
            return None
        if v in ("true","false"):
            return v == "true"
        try:
            if "." in v:
                return float(v)
            return int(v)
        except:
            return value
    return value

def extract_expected_keys(example_body: dict) -> Dict[str, Any]:
    if not example_body:
        return {}
    if example_body.get("mode") == "raw":
        raw = example_body.get("raw", "").strip()
        try:
            data = json.loads(raw)
            if isinstance(data, dict) and "data" in data:
                return data["data"]
        except:
            return {}
    return {}

def validate_payload(payload: Dict[str, Any], example_body: dict) -> Tuple[Dict[str, Any], Dict[str, Any]]:
    expected = extract_expected_keys(example_body)
    corrections = {"removed":[], "added":[], "type_fixed":{}}

    if not expected:
        clean = {k: _infer_type(v) for k,v in payload.items()}
        return clean, corrections

    clean = {}
    for k in expected.keys():
        if k in payload:
            new = _infer_type(payload[k])
            clean[k] = new
            if new != payload[k]:
                corrections["type_fixed"][k] = new
        else:
            clean[k] = None
            corrections["added"].append(k)

    for k in payload:
        if k not in expected:
            corrections["removed"].append(k)

    return clean, corrections
