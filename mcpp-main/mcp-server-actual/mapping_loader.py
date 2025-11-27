
import json
from pathlib import Path

def load_mapping(path: str = None):
    """Load canonical functional->endpoint mapping from JSON file."""
    if path is None:
        path = Path(__file__).resolve().parent / "canonical_map.json"
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(f"Mapping file not found: {p}")
    data = json.loads(p.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError("canonical_map.json must contain a JSON object")
    return data
