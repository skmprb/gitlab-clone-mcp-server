# GitLab MCP Server

[![PyPI version](https://badge.fury.io/py/gitlab-clone-mcp-server.svg)](https://badge.fury.io/py/gitlab-clone-mcp-server)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

A comprehensive Model Context Protocol (MCP) server that provides seamless GitLab API integration for Claude Desktop and other MCP clients. Manage your entire GitLab workflow through natural language commands - from project creation to repository operations, CI/CD management, and team collaboration.

## 🚀 Quick Start

```bash
# Install with uvx (recommended)
uvx --from gitlab-clone-mcp-server gitlab-mcp

# Or install as a tool
uv tool install gitlab-clone-mcp-server
```

## 🔌 Transport Options

GitLab MCP Server supports three transport types:

```bash
# Run with stdio transport (default)
gitlab-mcp stdio

# Run with SSE transport
gitlab-mcp sse --host localhost --port 8000

# Run with Streamable HTTP transport (recommended for production)
gitlab-mcp streamable-http --host localhost --port 8000
```

See [TRANSPORT_OPTIONS.md](TRANSPORT_OPTIONS.md) for detailed configuration.

## ✨ Key Features

- **Complete GitLab Integration**: 46+ tools covering all major GitLab operations
- **Natural Language Interface**: Control GitLab through conversational commands
- **Zero Configuration**: Works out-of-the-box with your GitLab Personal Access Token
- **Comprehensive Coverage**: Projects, repositories, issues, merge requests, CI/CD, and more
- **Local Repository Cloning**: Clone repositories directly to your local machine
- **Batch Operations**: Perform bulk operations across multiple projects

## 🛠️ Available Tools (46 Total)

### 📁 Project Management (12 tools)
| Tool | Description |
|------|-------------|
| `create_project` | Create new GitLab projects with custom settings |
| `delete_project` | Permanently delete GitLab projects |
| `update_project` | Modify project name, description, visibility |
| `fork_project` | Fork projects to different namespaces |
| `archive_project` | Archive projects for long-term storage |
| `unarchive_project` | Restore archived projects |
| `list_projects` | List all accessible projects with filters |
| `search_projects` | Search projects by name or keywords |
| `get_project_milestones` | View project milestones and deadlines |
| `get_project_labels` | List all project labels and colors |
| `list_project_hooks` | View configured webhooks |
| `get_current_user` | Get current user information and permissions |

### 📝 Issue Management (4 tools)
| Tool | Description |
|------|-------------|
| `get_project_issues` | List issues with state filtering |
| `create_issue` | Create new issues with descriptions |
| `update_issue` | Modify issue title, description, state |
| `close_issue` | Close specific issues |

### 🔀 Merge Request Management (2 tools)
| Tool | Description |
|------|-------------|
| `get_merge_requests` | List merge requests by state |
| `create_merge_request` | Create new merge requests |
| `merge_merge_request` | Merge approved merge requests |

### 📄 File Operations (5 tools)
| Tool | Description |
|------|-------------|
| `create_file` | Create new files with content |
| `update_file` | Modify existing file content |
| `delete_file` | Remove files from repository |
| `get_file_content` | Read file contents |
| `get_repository_files` | Browse directory structures |

### 🌿 Repository & Git Operations (15 tools)
| Tool | Description |
|------|-------------|
| `get_project_branches` | List all repository branches |
| `create_branch` | Create new branches from any reference |
| `delete_branch` | Remove branches safely |
| `get_commits` | View commit history |
| `create_commit` | Create commits with multiple file changes |
| `compare_branches` | Compare differences between branches |
| `revert_commit` | Revert specific commits |
| `cherry_pick_commit` | Cherry-pick commits between branches |
| `get_repository_tags` | List all repository tags |
| `create_tag` | Create release tags |
| `delete_tag` | Remove tags |
| `clone_repository` | Clone single repository locally |
| `clone_group_repositories` | Batch clone all group repositories |

### 🚀 CI/CD Operations (3 tools)
| Tool | Description |
|------|-------------|
| `get_pipelines` | Monitor pipeline status |
| `get_pipeline_jobs` | View individual job details |
| `trigger_pipeline` | Start new pipeline runs |

### 👥 Groups & Collaboration (3 tools)
| Tool | Description |
|------|-------------|
| `list_groups` | List accessible GitLab groups |
| `get_group_members` | View group membership |
| `get_current_user` | Get user profile information |

## Installation

### Using uvx (Recommended)
```bash
uvx --from gitlab-clone-mcp-server gitlab-mcp
```

### Using uv
```bash
uv tool install gitlab-mcp-server
```

### From source
```bash
git clone <repository-url>
cd gitlab-mcp
uv sync
```

## Setup

1. Get GitLab Personal Access Token:
   - Go to GitLab → Settings → Access Tokens
   - Create token with `api` scope
   - Copy the token

2. Set environment variables:
   ```bash
   export GITLAB_TOKEN="your_token_here"
   export GITLAB_URL="https://gitlab.com"  # optional
   ```

3. Test the server:
   ```bash
   gitlab-mcp
   ```

## Configuration

### Claude Desktop Configuration

Add to your Claude Desktop config (`%APPDATA%\Claude\claude_desktop_config.json`):

#### Using stdio transport (recommended)

```json
{
  "mcpServers": {
    "gitlab": {
      "command": "uvx",
      "args": [
        "--from", "gitlab-clone-mcp-server",
        "gitlab-mcp", "stdio"
      ],
      "env": {
        "GITLAB_URL": "https://gitlab.com",
        "GITLAB_TOKEN": "your_gitlab_token_here"
      }
    }
  }
}
```

#### Using HTTP transport

If you're running the server with Streamable HTTP transport:

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

### Headers Integration

For applications using MCPToolset, connect with headers:

```python
import os
from mcp_toolset import MCPToolset, SseServerParams

gitlab_tools = MCPToolset(
    connection_params=SseServerParams(
        url="http://localhost:8000/sse",
        headers={"GITLAB_TOKEN": os.getenv("GITLAB_TOKEN")},
    )
)
```

## 💬 Usage Examples

Control GitLab through natural language commands:

**Project Management:**
- "Create a new private project called 'microservice-api'"
- "Fork the kubernetes/dashboard project to my namespace"
- "Archive the old legacy-system project"

**Issue & Code Review:**
- "Show all open issues in the backend-service project"
- "Create merge request from feature/auth-system to main branch"
- "Merge the approved MR #23 in mobile-app project"

**Repository Operations:**
- "Create a new config.yaml file with database configuration"
- "Show all branches in the web-application project"
- "Clone the microservices-platform project to ./local-dev"

**CI/CD & Teams:**
- "Show running pipelines for the deployment project"
- "List all my GitLab groups and their members"

## 🔧 Authentication Setup

### GitLab Personal Access Token

1. Go to GitLab → Settings → Access Tokens
2. Create token with these scopes:
   - ✅ `api` - Full API access
   - ✅ `read_repository` - Read repository data
   - ✅ `write_repository` - Write repository data
   - ✅ `read_user` - Read user information
3. Copy the generated token

### Environment Variables

| Variable | Description | Default |
|----------|-------------|----------|
| `GITLAB_TOKEN` | Personal Access Token | Required |
| `GITLAB_URL` | GitLab instance URL | `https://gitlab.com` |

## 🔒 Security Best Practices

- **Never commit tokens** to version control
- **Use environment variables** for token storage
- **Set token expiration** dates when possible
- **Rotate tokens regularly** for enhanced security
- **Use minimal required scopes** for your use case

## 🐛 Troubleshooting

**Token Issues:**
- ❌ `GITLAB_TOKEN not set` → Set environment variable or provide in headers
- ❌ `401 Unauthorized` → Check token permissions and validity
- ❌ `403 Forbidden` → Verify project access permissions

**Git Operations:**
- ❌ `Git command not found` → Install Git and add to PATH

**Test Connection:**
```bash
curl -H "PRIVATE-TOKEN: your_token" "https://gitlab.com/api/v4/user"
```

## 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🔗 Related Projects

- [Model Context Protocol](https://github.com/modelcontextprotocol/python-sdk)
- [Claude Desktop](https://claude.ai/desktop)
- [GitLab API Documentation](https://docs.gitlab.com/ee/api/)

---

**Made with ❤️ for the GitLab and MCP community**