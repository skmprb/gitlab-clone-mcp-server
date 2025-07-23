#!/usr/bin/env python3
"""
Headers Integration Example for GitLab MCP Server

This example demonstrates how to integrate GitLab MCP Server 
using headers for authentication.
"""

import os
import asyncio
from mcp_toolset import MCPToolset, SseServerParams

gitlab_tools = MCPToolset(
    connection_params=SseServerParams(
        url="http://localhost:8000/sse",
        headers={"GITLAB_TOKEN": os.getenv("GITLAB_TOKEN")},
    )
)

async def main():
    if not os.getenv("GITLAB_TOKEN"):
        print("Error: GITLAB_TOKEN not set")
        return
    
    async with gitlab_tools:
        result = await gitlab_tools.call_tool("list_projects", {"per_page": 10})
        print(result)

if __name__ == "__main__":
    asyncio.run(main())