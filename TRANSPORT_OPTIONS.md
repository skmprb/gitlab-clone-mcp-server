# Transport Options for GitLab MCP Server

GitLab MCP Server supports three transport types for communication with MCP clients:

## 1. stdio Transport

The stdio transport is the simplest option and is ideal for direct integration with Claude Desktop and other MCP clients that support stdio communication.

```bash
# Run with stdio transport (default)
gitlab-mcp stdio

# Or using Python directly
python -m gitlab_clone_mcp_server stdio
```

## 2. Server-Sent Events (SSE) Transport

The SSE transport provides a web-based interface using Server-Sent Events, which is suitable for web applications and services.

```bash
# Run with SSE transport
gitlab-mcp sse --host localhost --port 8000

# Or using Python directly
python -m gitlab_clone_mcp_server sse --host localhost --port 8000
```

## 3. Streamable HTTP Transport

The Streamable HTTP transport is the newest and recommended transport for production deployments, offering better scalability and reliability.

```bash
# Run with Streamable HTTP transport
gitlab-mcp streamable-http --host localhost --port 8000

# Or using Python directly
python -m gitlab_clone_mcp_server streamable-http --host localhost --port 8000
```

## Mounting to Existing ASGI Applications

You can mount the GitLab MCP Server to an existing ASGI application:

```python
from starlette.applications import Starlette
from starlette.routing import Mount
import contextlib
from gitlab_clone_mcp_server.server import mcp

# Create a Starlette app
app = Starlette()

# Create a combined lifespan
@contextlib.asynccontextmanager
async def lifespan(app):
    async with contextlib.AsyncExitStack() as stack:
        await stack.enter_async_context(mcp.session_manager.run())
        yield

# Mount the MCP server
app.router.routes.append(Mount("/mcp", mcp.streamable_http_app()))
app.router.routes.append(Mount("/sse", mcp.sse_app()))

# Set the lifespan
app.lifespan = lifespan
```

## Claude Desktop Configuration

To use GitLab MCP Server with Claude Desktop, add the following to your Claude Desktop config:

```json
{
  "mcpServers": {
    "gitlab": {
      "command": "gitlab-mcp",
      "args": ["stdio"],
      "env": {
        "GITLAB_URL": "https://gitlab.com",
        "GITLAB_TOKEN": "your_gitlab_token_here"
      }
    }
  }
}
```

For HTTP-based transports, use:

```json
{
  "mcpServers": {
    "gitlab": {
      "url": "http://localhost:8000/mcp",
      "headers": {
        "GITLAB_TOKEN": "your_gitlab_token_here"
      }
    }
  }
}
```

## MCPToolset Integration

For applications using MCPToolset:

```python
import os
from mcp_toolset import MCPToolset, SseServerParams

gitlab_tools = MCPToolset(
    connection_params=SseServerParams(
        url="http://localhost:8000/sse",
        headers={"GITLAB_TOKEN": os.getenv("GITLAB_TOKEN")},
    )
)

async def gitlab_operations():
    async with gitlab_tools:
        projects = await gitlab_tools.call_tool("list_projects", {"per_page": 20})
        return projects
```

### Available Connection Parameters

- **SseServerParams**: For Server-Sent Events transport
- **StreamableHttpServerParams**: For Streamable HTTP transport
- **StdioServerParams**: For stdio transport (local execution)

```python
# SSE Transport
from mcp_toolset import SseServerParams
sse_params = SseServerParams(
    url="http://localhost:8000/sse",
    headers={"GITLAB_TOKEN": os.getenv("GITLAB_TOKEN")}
)

# Streamable HTTP Transport
from mcp_toolset import StreamableHttpServerParams
http_params = StreamableHttpServerParams(
    url="http://localhost:8000/mcp",
    headers={"GITLAB_TOKEN": os.getenv("GITLAB_TOKEN")}
)

# Stdio Transport (for local execution)
from mcp_toolset import StdioServerParams
stdio_params = StdioServerParams(
    command="gitlab-mcp",
    args=["stdio"],
    env={"GITLAB_TOKEN": os.getenv("GITLAB_TOKEN")}
)
```