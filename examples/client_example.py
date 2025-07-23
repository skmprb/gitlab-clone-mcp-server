#!/usr/bin/env python3
"""Simple client example for GitLab MCP Server."""

import asyncio
import os
import sys
from pathlib import Path
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from mcp.client.streamable_http import streamablehttp_client

sys.path.insert(0, str(Path(__file__).parent.parent))


async def run_stdio_client():
    """Connect via stdio transport."""
    server_params = StdioServerParameters(
        command="gitlab-mcp",
        args=["stdio"],
        env={"GITLAB_TOKEN": os.getenv("GITLAB_TOKEN")},
    )

    print("Connecting via stdio...")
    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            tools = await session.list_tools()
            print(f"Available tools: {len(tools.tools)}")
            for tool in tools.tools[:5]:
                print(f"- {tool.name}: {tool.description}")


async def run_http_client():
    """Connect via HTTP transport."""
    gitlab_token = os.getenv("GITLAB_TOKEN")
    if not gitlab_token:
        print("Error: GITLAB_TOKEN not set")
        return
    
    server_url = "http://localhost:8000/mcp"
    headers = {"GITLAB_TOKEN": gitlab_token}
    
    print("Connecting via HTTP...")
    async with streamablehttp_client(server_url, headers=headers) as (read, write, _):
        async with ClientSession(read, write) as session:
            await session.initialize()
            tools = await session.list_tools()
            print(f"Available tools: {len(tools.tools)}")
            for tool in tools.tools[:5]:
                print(f"- {tool.name}: {tool.description}")


async def main():
    """Run the client example."""
    if len(sys.argv) > 1 and sys.argv[1] == "http":
        await run_http_client()
    else:
        await run_stdio_client()


if __name__ == "__main__":
    asyncio.run(main())