#!/usr/bin/env python3
"""Run GitLab MCP Server with SSE transport."""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from gitlab_clone_mcp_server.server import mcp

if __name__ == "__main__":
    print("Starting GitLab MCP Server with SSE transport...")
    mcp.run(transport="sse")