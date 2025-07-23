# GitLab MCP Server Examples

This directory contains examples demonstrating different ways to run and integrate the GitLab MCP Server.

## Running the Server

### Basic Transport Examples

- **`run_stdio.py`** - Run with stdio transport (for Claude Desktop)
- **`run_sse.py`** - Run with Server-Sent Events transport
- **`run_streamable_http.py`** - Run with Streamable HTTP transport

### Integration Examples

- **`client_example.py`** - Simple MCP client example
- **`headers_integration.py`** - Headers authentication integration example
- **`mount_to_asgi.py`** - Mount to existing ASGI application

## Usage

### Run Server Examples

```bash
# stdio transport
python examples/run_stdio.py

# SSE transport
python examples/run_sse.py

# Streamable HTTP transport
python examples/run_streamable_http.py
```

### Client Examples

```bash
# Test client with stdio
python examples/client_example.py

# Test client with HTTP
python examples/client_example.py http
```

### Headers Integration

```bash
# Set your GitLab token
export GITLAB_TOKEN="your_token_here"

# Run headers integration example
python examples/headers_integration.py
```

## Environment Variables

All examples expect the following environment variables:

- `GITLAB_TOKEN` - Your GitLab Personal Access Token
- `GITLAB_URL` - GitLab instance URL (optional, defaults to https://gitlab.com)