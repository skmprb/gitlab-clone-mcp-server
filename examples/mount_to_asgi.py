#!/usr/bin/env python3
"""Mount GitLab MCP Server to an existing ASGI application."""

import os
import sys
import contextlib
from pathlib import Path
from starlette.applications import Starlette
from starlette.routing import Mount
from starlette.responses import PlainTextResponse

sys.path.insert(0, str(Path(__file__).parent.parent))
from gitlab_clone_mcp_server.server import mcp

app = Starlette()

@app.route("/")
async def homepage(request):
    return PlainTextResponse("GitLab MCP Server - Welcome Page")

@contextlib.asynccontextmanager
async def lifespan(app):
    async with contextlib.AsyncExitStack() as stack:
        await stack.enter_async_context(mcp.session_manager.run())
        yield

app.router.routes.append(Mount("/mcp", mcp.streamable_http_app()))
app.router.routes.append(Mount("/sse", mcp.sse_app()))
app.lifespan = lifespan

if __name__ == "__main__":
    import uvicorn
    host = os.getenv("HOST", "localhost")
    port = int(os.getenv("PORT", "8000"))
    print(f"Starting combined ASGI app on {host}:{port}...")
    uvicorn.run(app, host=host, port=port)