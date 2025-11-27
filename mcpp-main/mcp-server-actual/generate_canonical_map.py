#!/usr/bin/env python3
"""
generate_canonical_mapping.py — FINAL CLEAN VERSION
(Claude-safe + DATA WRAP FIX + BODY EXAMPLE + FORMDATA SUPPORT)
"""

import json, argparse, pathlib, re, urllib.parse

# ---------------------------------------------------------
# Helpers
# ---------------------------------------------------------
def safe_ident(s: str) -> str:
    s = (s or "").strip().lower()
    s = re.sub(r"[^a-z0-9]+", "_", s)
    s = re.sub(r"_+", "_", s).strip("_")
    return s or "x"


def detect_action(method, url_raw, name):
    u = (url_raw or "").lower()
    n = (name or "").lower()
    method = method.upper()

    if "approve" in u or "approve" in n: return "approve"
    if "reject" in u or "reject" in n: return "reject"
    if "get_records_by_id" in u or "get_records_by_id" in n: return "get_by_id"
    if method == "GET" and "name=" in u: return "get_by_id"
    if "create" in u or "create" in n or method == "POST": return "create"
    if "update" in u or "update" in n or method in ("PUT", "PATCH"): return "update"
    if method == "DELETE": return "delete"
    if method == "GET": return "get"
    return method.lower()


def build_url(url_field):
    if not url_field:
        return ""

    if isinstance(url_field, str):
        return url_field

    raw = url_field.get("raw")
    if raw:
        return raw

    protocol = url_field.get("protocol", "https")
    host_arr = url_field.get("host", [])
    host = ".".join(host_arr) if isinstance(host_arr, list) else host_arr
    path = "/".join(url_field.get("path", []))

    query = url_field.get("query", [])
    qs = "&".join(
        f"{urllib.parse.quote(item['key'])}={urllib.parse.quote(item.get('value',''))}"
        for item in query if isinstance(item, dict) and item.get("key")
    )

    url = f"{protocol}://{host}/{path}"
    return f"{url}?{qs}" if qs else url


def rewrite_host(url, new_host):
    parsed = urllib.parse.urlparse(url)
    if not parsed.scheme:
        return new_host.rstrip("/") + "/" + url.lstrip("/")

    tgt = urllib.parse.urlparse(new_host)
    updated = parsed._replace(scheme=tgt.scheme, netloc=tgt.netloc)
    return urllib.parse.urlunparse(updated)


# ---------------------------------------------------------
# JSON Schema handling
# ---------------------------------------------------------
def sanitize_schema(obj):
    """Convert raw JSON body → JSON Schema."""
    if obj is None:
        return {"type": ["string", "null"]}

    if isinstance(obj, bool): return {"type": "boolean"}
    if isinstance(obj, (int, float)): return {"type": "number"}
    if isinstance(obj, str): return {"type": "string"}

    if isinstance(obj, dict):
        return {
            "type": "object",
            "properties": {k: sanitize_schema(v) for k, v in obj.items()},
            "additionalProperties": True
        }

    if isinstance(obj, list):
        if not obj:
            return {"type": "array", "items": {}}
        return {"type": "array", "items": sanitize_schema(obj[0])}

    return {"type": "string"}


# ---------------------------------------------------------
# Generate body_example from schema
# ---------------------------------------------------------
def make_default(schema):
    if not isinstance(schema, dict):
        return None

    stype = schema.get("type")

    if stype == "object":
        props = schema.get("properties", {})
        return {k: make_default(v) for k, v in props.items()}

    if stype == "array":
        return []

    if stype == "number":
        return 0

    if stype == "boolean":
        return False

    if stype == "string":
        return ""

    if isinstance(stype, list) and "null" in stype:
        return None

    return None


# ---------------------------------------------------------
# Read Postman Collection
# ---------------------------------------------------------
def parse_collection(items, parent=""):
    out = []
    for item in items:
        name = item.get("name", "")
        full = f"{parent}/{name}" if parent else name

        if "request" in item:
            req = item["request"]
            out.append({
                "name": name,
                "full_name": full,
                "method": req.get("method", "GET").upper(),
                "url_field": req.get("url"),
                "body": req.get("body") or {}
            })

        if "item" in item:
            out.extend(parse_collection(item["item"], full))

    return out


# ---------------------------------------------------------
# MAIN
# ---------------------------------------------------------
def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--collection", required=True)
    parser.add_argument("--out", required=True)
    parser.add_argument("--host", required=True)
    args = parser.parse_args()

    col = json.loads(pathlib.Path(args.collection).read_text(encoding="utf-8"))
    items = parse_collection(col.get("item", []))

    mapping = {}

    for ep in items:
        parts = [p for p in ep["full_name"].split("/") if p]

        module = safe_ident(parts[0]) if parts else "hr"
        resource = safe_ident(parts[1]) if len(parts) >= 2 else safe_ident(ep["name"])
        action = detect_action(ep["method"], build_url(ep["url_field"]), ep["name"])

        key = safe_ident(f"{module}_{resource}_{action}")[:55]
        base_key = key
        i = 1
        while key in mapping:
            key = base_key[: (64 - len(f"_{i}"))] + f"_{i}"
            i += 1

        raw_url = build_url(ep["url_field"])
        final_url = rewrite_host(raw_url, args.host)

        entry = {"method": ep["method"], "url": final_url}

        # ----------------------------- BODY HANDLING -----------------------------
        if ep["method"] in ("POST", "PUT"):
            body = ep["body"]
            mode = body.get("mode")

            # RAW JSON
            if mode == "raw":
                try:
                    parsed = json.loads(body.get("raw", ""))

                    if "data" in parsed:
                        entry["body_schema"] = sanitize_schema(parsed)
                    else:
                        entry["body_schema"] = {
                            "type": "object",
                            "properties": {
                                "data": sanitize_schema(parsed)
                            },
                            "additionalProperties": False
                        }

                except:
                    pass

            # FORMDATA & URL-ENCODED
            elif mode in ("formdata", "urlencoded"):
                schema = {}
                for field in body.get("formdata") or body.get("urlencoded") or []:
                    if field.get("key"):
                        schema[field["key"]] = {"type": "string"}

                if schema:
                    entry["body_schema"] = {
                        "type": "object",
                        "properties": {
                            "data": {
                                "type": "object",
                                "properties": schema
                            }
                        },
                        "additionalProperties": False
                    }

            # Add example
            if "body_schema" in entry:
                entry["body_example"] = make_default(entry["body_schema"])

        mapping[key] = entry

    out_file = pathlib.Path(args.out)
    out_file.write_text(json.dumps(mapping, indent=2), encoding="utf-8")

    print("✔ canonical_mapping.json generated!")
    print("→ File:", out_file)
    print("→ Total tools:", len(mapping))


if __name__ == "__main__":
    main()
