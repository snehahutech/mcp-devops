# run_server_dev.py
# Wrapper so MCP Inspector can find the server object

import sys, os

# 1. Add project root to PYTHONPATH
ROOT = os.path.dirname(os.path.abspath(__file__))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

# 2. Import your real MCP server module
from erp_mcp.server_final import mcp   # VERY IMPORTANT

# 3. Do NOT run mcp.run() here.
# MCP Inspector will run it automatically.
