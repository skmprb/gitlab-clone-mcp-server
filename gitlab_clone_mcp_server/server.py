from typing import Any, Optional
import httpx
import os
import sys
import asyncio
from mcp.server.fastmcp import FastMCP

# Initialize FastMCP server with support for all transports
mcp = FastMCP("GitLab MCP Server", host="0.0.0.0", port=8000)

async def make_gitlab_request(endpoint: str, method: str = "GET", data: dict = None, ctx=None, token: str = None) -> dict[str, Any] | None:
    """Make a request to GitLab API with proper error handling."""
    # Priority: 1. Explicit token parameter, 2. Context headers, 3. Environment variable
    
    # If no explicit token provided, try to get from context
    if not token and ctx and hasattr(ctx, 'request_context') and ctx.request_context:
        # Try to get from request headers
        if hasattr(ctx.request_context, 'headers'):
            token = ctx.request_context.headers.get('GITLAB_TOKEN')
    
    # Fallback to environment variable
    if not token:
        token = os.getenv("GITLAB_TOKEN")
    
    if not token:
        return {"error": "GitLab token not provided. Please provide a token parameter, GITLAB_TOKEN in the request headers, or set the environment variable."}
    
    # Get GitLab URL (from context or environment)
    gitlab_url = os.getenv("GITLAB_URL", "https://gitlab.com")
    
    headers = {
        "PRIVATE-TOKEN": token,
        "Content-Type": "application/json"
    }
    
    url = f"{gitlab_url}/api/v4{endpoint}"
    
    async with httpx.AsyncClient() as client:
        try:
            if method == "GET":
                response = await client.get(url, headers=headers, timeout=30.0)
            elif method == "POST":
                response = await client.post(url, headers=headers, json=data, timeout=30.0)
            elif method == "PUT":
                response = await client.put(url, headers=headers, json=data, timeout=30.0)
            elif method == "DELETE":
                response = await client.delete(url, headers=headers, timeout=30.0)
            
            response.raise_for_status()
            return response.json() if response.content else {"success": True}
        except Exception as e:
            return {"error": str(e)}

@mcp.tool()
async def create_project(name: str, description: str = "", visibility: str = "private", token: str = None, ctx=None) -> str:
    """Create a new GitLab project.
    
    Args:
        name: Project name
        description: Project description (optional)
        visibility: Project visibility (private, internal, public)
        token: GitLab Personal Access Token (optional)
        ctx: MCP context (automatically injected)
    """
    data = {
        "name": name,
        "description": description,
        "visibility": visibility,
        "initialize_with_readme": True
    }
    
    result = await make_gitlab_request("/projects", "POST", data, ctx, token=token)
    
    if isinstance(result, dict) and "error" in result:
        return f"Error creating project: {result['error']}"
    
    return f"Project created: {result['name']} (ID: {result['id']})\nURL: {result['web_url']}"

@mcp.tool()
async def delete_project(project_id: int, token: str = None, ctx=None) -> str:
    """Delete a GitLab project.
    
    Args:
        project_id: GitLab project ID
        token: GitLab Personal Access Token (optional)
        ctx: MCP context (automatically injected)
    """
    result = await make_gitlab_request(f"/projects/{project_id}", "DELETE", ctx=ctx, token=token)
    
    if isinstance(result, dict) and "error" in result:
        return f"Error deleting project: {result['error']}"
    
    return f"Project {project_id} deleted successfully"

@mcp.tool()
async def list_projects(owned: bool = False, per_page: int = 20, token: str = None, ctx=None) -> str:
    """List GitLab projects.
    
    Args:
        owned: If True, only show owned projects. If False, show all accessible projects.
        per_page: Number of projects per page (max 100)
        token: GitLab Personal Access Token (optional)
        ctx: MCP context (automatically injected)
    """
    per_page = min(per_page, 100)
    endpoint = f"/projects?membership=true&per_page={per_page}" + ("&owned=true" if owned else "")
    data = await make_gitlab_request(endpoint, ctx=ctx, token=token)
    
    if isinstance(data, dict) and "error" in data:
        return f"Error: {data['error']}"
    
    if not data:
        return "No projects found."
    
    projects = []
    for project in data:
        projects.append(f"• {project['name']} ({project['path_with_namespace']}) - ID: {project['id']}")
    
    return "\n".join(projects)

@mcp.tool()
async def get_project_issues(project_id: int, state: str = "opened", token: str = None, ctx=None) -> str:
    """Get issues for a GitLab project.
    
    Args:
        project_id: GitLab project ID
        state: Issue state (opened, closed, all)
        token: GitLab Personal Access Token (optional)
        ctx: MCP context (automatically injected)
    """
    endpoint = f"/projects/{project_id}/issues?state={state}"
    data = await make_gitlab_request(endpoint, ctx=ctx, token=token)
    
    if isinstance(data, dict) and "error" in data:
        return f"Error: {data['error']}"
    
    if not data:
        return f"No {state} issues found."
    
    issues = []
    for issue in data[:10]:  # Limit to 10 issues
        issues.append(f"#{issue['iid']}: {issue['title']} - {issue['state']} ({issue['author']['name']})")
    
    return "\n".join(issues)

@mcp.tool()
async def get_merge_requests(project_id: int, state: str = "opened", token: str = None, ctx=None) -> str:
    """Get merge requests for a GitLab project.
    
    Args:
        project_id: GitLab project ID
        state: MR state (opened, closed, merged, all)
        token: GitLab Personal Access Token (optional)
        ctx: MCP context (automatically injected)
    """
    endpoint = f"/projects/{project_id}/merge_requests?state={state}"
    data = await make_gitlab_request(endpoint, ctx=ctx, token=token)
    
    if isinstance(data, dict) and "error" in data:
        return f"Error: {data['error']}"
    
    if not data:
        return f"No {state} merge requests found."
    
    mrs = []
    for mr in data[:10]:  # Limit to 10 MRs
        mrs.append(f"!{mr['iid']}: {mr['title']} - {mr['state']} ({mr['author']['name']})")
    
    return "\n".join(mrs)

@mcp.tool()
async def create_issue(project_id: int, title: str, description: str = "", token: str = None, ctx=None) -> str:
    """Create a new issue in a GitLab project.
    
    Args:
        project_id: GitLab project ID
        title: Issue title
        description: Issue description (optional)
        token: GitLab Personal Access Token (optional)
        ctx: MCP context (automatically injected)
    """
    endpoint = f"/projects/{project_id}/issues"
    data = {
        "title": title,
        "description": description
    }
    
    result = await make_gitlab_request(endpoint, "POST", data, ctx=ctx, token=token)
    
    if isinstance(result, dict) and "error" in result:
        return f"Error creating issue: {result['error']}"
    
    return f"Issue created successfully: #{result['iid']} - {result['title']}"

@mcp.tool()
async def get_pipelines(project_id: int, status: str = "running", token: str = None, ctx=None) -> str:
    """Get CI/CD pipelines for a GitLab project.
    
    Args:
        project_id: GitLab project ID
        status: Pipeline status (running, pending, success, failed, canceled, skipped)
        token: GitLab Personal Access Token (optional)
        ctx: MCP context (automatically injected)
    """
    endpoint = f"/projects/{project_id}/pipelines?status={status}"
    data = await make_gitlab_request(endpoint, ctx=ctx, token=token)
    
    if isinstance(data, dict) and "error" in data:
        return f"Error: {data['error']}"
    
    if not data:
        return f"No {status} pipelines found."
    
    pipelines = []
    for pipeline in data[:10]:  # Limit to 10 pipelines
        pipelines.append(f"Pipeline #{pipeline['id']}: {pipeline['status']} - {pipeline['ref']} ({pipeline.get('user', {}).get('name', 'Unknown')})")
    
    return "\n".join(pipelines)

@mcp.tool()
async def get_project_branches(project_id: int, token: str = None, ctx=None) -> str:
    """Get branches for a GitLab project.
    
    Args:
        project_id: GitLab project ID
        token: GitLab Personal Access Token (optional)
        ctx: MCP context (automatically injected)
    """
    endpoint = f"/projects/{project_id}/repository/branches"
    data = await make_gitlab_request(endpoint, ctx=ctx, token=token)
    
    if isinstance(data, dict) and "error" in data:
        return f"Error: {data['error']}"
    
    if not data:
        return "No branches found."
    
    branches = []
    for branch in data[:15]:  # Limit to 15 branches
        protected = " (protected)" if branch.get('protected') else ""
        branches.append(f"• {branch['name']}{protected}")
    
    return "\n".join(branches)

# Groups
@mcp.tool()
async def list_groups(per_page: int = 20, token: str = None, ctx=None) -> str:
    """List GitLab groups.
    
    Args:
        per_page: Number of groups per page (max 100)
        token: GitLab Personal Access Token (optional)
        ctx: MCP context (automatically injected)
    """
    per_page = min(per_page, 100)
    data = await make_gitlab_request(f"/groups?per_page={per_page}", ctx=ctx, token=token)
    if isinstance(data, dict) and "error" in data:
        return f"Error: {data['error']}"
    if not data:
        return "No groups found."
    
    groups = []
    for group in data:
        groups.append(f"• {group['name']} ({group['path']}) - ID: {group['id']}")
    return "\n".join(groups)

@mcp.tool()
async def get_group_members(group_id: int, token: str = None, ctx=None) -> str:
    """Get members of a GitLab group.
    
    Args:
        group_id: GitLab group ID
        token: GitLab Personal Access Token (optional)
        ctx: MCP context (automatically injected)
    """
    data = await make_gitlab_request(f"/groups/{group_id}/members", ctx=ctx, token=token)
    if isinstance(data, dict) and "error" in data:
        return f"Error: {data['error']}"
    if not data:
        return "No members found."
    
    members = []
    for member in data[:15]:
        members.append(f"• {member['name']} ({member['username']}) - {member['access_level']}")
    return "\n".join(members)

# Repository
@mcp.tool()
async def get_repository_files(project_id: int, path: str = "", ref: str = "main", token: str = None, ctx=None) -> str:
    """Get repository files and directories.
    
    Args:
        project_id: GitLab project ID
        path: Directory path (optional)
        ref: Branch/tag reference (default: main)
        token: GitLab Personal Access Token (optional)
        ctx: MCP context (automatically injected)
    """
    endpoint = f"/projects/{project_id}/repository/tree?path={path}&ref={ref}"
    data = await make_gitlab_request(endpoint, ctx=ctx, token=token)
    
    if isinstance(data, dict) and "error" in data:
        return f"Error: {data['error']}"
    if not data:
        return "No files found."
    
    files = []
    for item in data[:20]:
        icon = "📁" if item['type'] == 'tree' else "📄"
        files.append(f"{icon} {item['name']}")
    return "\n".join(files)

@mcp.tool()
async def get_file_content(project_id: int, file_path: str, ref: str = "main", token: str = None, ctx=None) -> str:
    """Get content of a repository file.
    
    Args:
        project_id: GitLab project ID
        file_path: Path to the file
        ref: Branch/tag reference (default: main)
        token: GitLab Personal Access Token (optional)
        ctx: MCP context (automatically injected)
    """
    import urllib.parse
    encoded_path = urllib.parse.quote(file_path, safe='')
    endpoint = f"/projects/{project_id}/repository/files/{encoded_path}?ref={ref}"
    data = await make_gitlab_request(endpoint, ctx=ctx, token=token)
    
    if isinstance(data, dict) and "error" in data:
        return f"Error: {data['error']}"
    
    import base64
    try:
        content = base64.b64decode(data['content']).decode('utf-8')
        return f"File: {file_path}\n\n{content[:2000]}{'...' if len(content) > 2000 else ''}"
    except:
        return "Unable to decode file content"

@mcp.tool()
async def get_commits(project_id: int, ref_name: str = "main", token: str = None, ctx=None) -> str:
    """Get recent commits for a project.
    
    Args:
        project_id: GitLab project ID
        ref_name: Branch name (default: main)
        token: GitLab Personal Access Token (optional)
        ctx: MCP context (automatically injected)
    """
    endpoint = f"/projects/{project_id}/repository/commits?ref_name={ref_name}"
    data = await make_gitlab_request(endpoint, ctx=ctx, token=token)
    
    if isinstance(data, dict) and "error" in data:
        return f"Error: {data['error']}"
    if not data:
        return "No commits found."
    
    commits = []
    for commit in data[:10]:
        short_id = commit['short_id']
        title = commit['title'][:60] + ('...' if len(commit['title']) > 60 else '')
        author = commit['author_name']
        commits.append(f"• {short_id}: {title} ({author})")
    return "\n".join(commits)

@mcp.tool()
async def create_commit(project_id: int, branch: str, commit_message: str, file_path: str, file_content: str, action: str = "create", token: str = None, ctx=None) -> str:
    """Create a commit with file changes.
    
    Args:
        project_id: GitLab project ID
        branch: Target branch
        commit_message: Commit message
        file_path: Path to the file
        file_content: File content
        action: Action (create, update, delete)
        token: GitLab Personal Access Token (optional)
        ctx: MCP context (automatically injected)
    """
    data = {
        "branch": branch,
        "commit_message": commit_message,
        "actions": [{
            "action": action,
            "file_path": file_path,
            "content": file_content if action != "delete" else None
        }]
    }
    
    result = await make_gitlab_request(f"/projects/{project_id}/repository/commits", "POST", data, ctx=ctx, token=token)
    
    if isinstance(result, dict) and "error" in result:
        return f"Error creating commit: {result['error']}"
    
    return f"Commit created: {result['short_id']} - {result['title']}"

@mcp.tool()
async def create_branch(project_id: int, branch_name: str, ref: str = "main", token: str = None, ctx=None) -> str:
    """Create a new branch.
    
    Args:
        project_id: GitLab project ID
        branch_name: New branch name
        ref: Source branch/commit (default: main)
        token: GitLab Personal Access Token (optional)
        ctx: MCP context (automatically injected)
    """
    data = {
        "branch": branch_name,
        "ref": ref
    }
    
    result = await make_gitlab_request(f"/projects/{project_id}/repository/branches", "POST", data, ctx=ctx, token=token)
    
    if isinstance(result, dict) and "error" in result:
        return f"Error creating branch: {result['error']}"
    
    return f"Branch created: {result['name']} from {ref}"

@mcp.tool()
async def delete_branch(project_id: int, branch_name: str, token: str = None, ctx=None) -> str:
    """Delete a branch.
    
    Args:
        project_id: GitLab project ID
        branch_name: Branch name to delete
        token: GitLab Personal Access Token (optional)
        ctx: MCP context (automatically injected)
    """
    import urllib.parse
    encoded_branch = urllib.parse.quote(branch_name, safe='')
    result = await make_gitlab_request(f"/projects/{project_id}/repository/branches/{encoded_branch}", "DELETE", ctx=ctx, token=token)
    
    if isinstance(result, dict) and "error" in result:
        return f"Error deleting branch: {result['error']}"
    
    return f"Branch '{branch_name}' deleted successfully"

@mcp.tool()
async def create_merge_request(project_id: int, source_branch: str, target_branch: str, title: str, description: str = "", token: str = None, ctx=None) -> str:
    """Create a merge request.
    
    Args:
        project_id: GitLab project ID
        source_branch: Source branch
        target_branch: Target branch
        title: MR title
        description: MR description (optional)
        token: GitLab Personal Access Token (optional)
        ctx: MCP context (automatically injected)
    """
    data = {
        "source_branch": source_branch,
        "target_branch": target_branch,
        "title": title,
        "description": description
    }
    
    result = await make_gitlab_request(f"/projects/{project_id}/merge_requests", "POST", data, ctx=ctx, token=token)
    
    if isinstance(result, dict) and "error" in result:
        return f"Error creating merge request: {result['error']}"
    
    return f"Merge request created: !{result['iid']} - {result['title']}\nURL: {result['web_url']}"

@mcp.tool()
async def merge_merge_request(project_id: int, merge_request_iid: int, merge_commit_message: str = "", token: str = None, ctx=None) -> str:
    """Merge a merge request.
    
    Args:
        project_id: GitLab project ID
        merge_request_iid: Merge request IID
        merge_commit_message: Custom merge commit message (optional)
        token: GitLab Personal Access Token (optional)
        ctx: MCP context (automatically injected)
    """
    data = {}
    if merge_commit_message:
        data["merge_commit_message"] = merge_commit_message
    
    result = await make_gitlab_request(f"/projects/{project_id}/merge_requests/{merge_request_iid}/merge", "PUT", data, ctx=ctx, token=token)
    
    if isinstance(result, dict) and "error" in result:
        return f"Error merging MR: {result['error']}"
    
    return f"Merge request !{merge_request_iid} merged successfully"

@mcp.tool()
async def create_tag(project_id: int, tag_name: str, ref: str, message: str = "", token: str = None, ctx=None) -> str:
    """Create a new tag.
    
    Args:
        project_id: GitLab project ID
        tag_name: Tag name
        ref: Source branch/commit
        message: Tag message (optional)
        token: GitLab Personal Access Token (optional)
        ctx: MCP context (automatically injected)
    """
    data = {
        "tag_name": tag_name,
        "ref": ref,
        "message": message
    }
    
    result = await make_gitlab_request(f"/projects/{project_id}/repository/tags", "POST", data, ctx=ctx, token=token)
    
    if isinstance(result, dict) and "error" in result:
        return f"Error creating tag: {result['error']}"
    
    return f"Tag created: {result['name']} at {result['commit']['short_id']}"

# CI/CD
@mcp.tool()
async def get_pipeline_jobs(project_id: int, pipeline_id: int, token: str = None, ctx=None) -> str:
    """Get jobs for a specific pipeline.
    
    Args:
        project_id: GitLab project ID
        pipeline_id: Pipeline ID
        token: GitLab Personal Access Token (optional)
        ctx: MCP context (automatically injected)
    """
    endpoint = f"/projects/{project_id}/pipelines/{pipeline_id}/jobs"
    data = await make_gitlab_request(endpoint, ctx=ctx, token=token)
    
    if isinstance(data, dict) and "error" in data:
        return f"Error: {data['error']}"
    if not data:
        return "No jobs found."
    
    jobs = []
    for job in data:
        jobs.append(f"• {job['name']}: {job['status']} (Stage: {job['stage']})")
    return "\n".join(jobs)

@mcp.tool()
async def trigger_pipeline(project_id: int, ref: str = "main", token: str = None, ctx=None) -> str:
    """Trigger a new pipeline.
    
    Args:
        project_id: GitLab project ID
        ref: Branch/tag to run pipeline on (default: main)
        token: GitLab Personal Access Token (optional)
        ctx: MCP context (automatically injected)
    """
    endpoint = f"/projects/{project_id}/pipeline"
    data = {"ref": ref}
    result = await make_gitlab_request(endpoint, "POST", data, ctx=ctx, token=token)
    
    if isinstance(result, dict) and "error" in result:
        return f"Error triggering pipeline: {result['error']}"
    
    return f"Pipeline triggered successfully: #{result['id']} on {ref}"

# Users
@mcp.tool()
async def get_current_user(token: str = None, ctx=None) -> str:
    """Get current user information.
    
    Args:
        token: GitLab Personal Access Token (optional)
        ctx: MCP context (automatically injected)
    """
    data = await make_gitlab_request("/user", ctx=ctx, token=token)
    if isinstance(data, dict) and "error" in data:
        return f"Error: {data['error']}"
    
    return f"User: {data['name']} (@{data['username']})\nEmail: {data['email']}\nID: {data['id']}"

@mcp.tool()
async def search_projects(query: str, token: str = None, ctx=None) -> str:
    """Search for projects.
    
    Args:
        query: Search query
        token: GitLab Personal Access Token (optional)
        ctx: MCP context (automatically injected)
    """
    import urllib.parse
    encoded_query = urllib.parse.quote(query)
    endpoint = f"/projects?search={encoded_query}"
    data = await make_gitlab_request(endpoint, ctx=ctx, token=token)
    
    if isinstance(data, dict) and "error" in data:
        return f"Error: {data['error']}"
    if not data:
        return "No projects found."
    
    projects = []
    for project in data[:10]:
        projects.append(f"• {project['name']} ({project['path_with_namespace']}) - ID: {project['id']}")
    return "\n".join(projects)

# Milestones
@mcp.tool()
async def get_project_milestones(project_id: int, state: str = "active", token: str = None, ctx=None) -> str:
    """Get project milestones.
    
    Args:
        project_id: GitLab project ID
        state: Milestone state (active, closed, all)
        token: GitLab Personal Access Token (optional)
        ctx: MCP context (automatically injected)
    """
    endpoint = f"/projects/{project_id}/milestones?state={state}"
    data = await make_gitlab_request(endpoint, ctx=ctx, token=token)
    
    if isinstance(data, dict) and "error" in data:
        return f"Error: {data['error']}"
    if not data:
        return f"No {state} milestones found."
    
    milestones = []
    for milestone in data:
        due_date = milestone.get('due_date', 'No due date')
        milestones.append(f"• {milestone['title']} - {milestone['state']} (Due: {due_date})")
    return "\n".join(milestones)

# Labels
@mcp.tool()
async def get_project_labels(project_id: int, token: str = None, ctx=None) -> str:
    """Get project labels.
    
    Args:
        project_id: GitLab project ID
        token: GitLab Personal Access Token (optional)
        ctx: MCP context (automatically injected)
    """
    data = await make_gitlab_request(f"/projects/{project_id}/labels", ctx=ctx, token=token)
    if isinstance(data, dict) and "error" in data:
        return f"Error: {data['error']}"
    if not data:
        return "No labels found."
    
    labels = []
    for label in data:
        labels.append(f"• {label['name']} ({label['color']})")
    return "\n".join(labels)

# Webhooks
@mcp.tool()
async def list_project_hooks(project_id: int, token: str = None, ctx=None) -> str:
    """List project webhooks.
    
    Args:
        project_id: GitLab project ID
        token: GitLab Personal Access Token (optional)
        ctx: MCP context (automatically injected)
    """
    data = await make_gitlab_request(f"/projects/{project_id}/hooks", ctx=ctx, token=token)
    if isinstance(data, dict) and "error" in data:
        return f"Error: {data['error']}"
    if not data:
        return "No webhooks found."
    
    hooks = []
    for hook in data:
        hooks.append(f"• {hook['url']} - ID: {hook['id']}")
    return "\n".join(hooks)

# Project Writing Operations
@mcp.tool()
async def update_project(project_id: int, name: str = None, description: str = None, visibility: str = None, token: str = None, ctx=None) -> str:
    """Update project settings.
    
    Args:
        project_id: GitLab project ID
        name: New project name (optional)
        description: New description (optional)
        visibility: New visibility (private, internal, public) (optional)
        token: GitLab Personal Access Token (optional)
        ctx: MCP context (automatically injected)
    """
    data = {}
    if name: data["name"] = name
    if description: data["description"] = description
    if visibility: data["visibility"] = visibility
    
    result = await make_gitlab_request(f"/projects/{project_id}", "PUT", data, ctx=ctx, token=token)
    
    if isinstance(result, dict) and "error" in result:
        return f"Error updating project: {result['error']}"
    
    return f"Project updated: {result['name']} (ID: {result['id']})"

@mcp.tool()
async def fork_project(project_id: int, namespace: str = None, token: str = None, ctx=None) -> str:
    """Fork a project.
    
    Args:
        project_id: GitLab project ID to fork
        namespace: Target namespace (optional)
        token: GitLab Personal Access Token (optional)
        ctx: MCP context (automatically injected)
    """
    data = {}
    if namespace: data["namespace"] = namespace
    
    result = await make_gitlab_request(f"/projects/{project_id}/fork", "POST", data, ctx=ctx, token=token)
    
    if isinstance(result, dict) and "error" in result:
        return f"Error forking project: {result['error']}"
    
    return f"Project forked: {result['name']} (ID: {result['id']})\nURL: {result['web_url']}"

@mcp.tool()
async def archive_project(project_id: int, token: str = None, ctx=None) -> str:
    """Archive a project.
    
    Args:
        project_id: GitLab project ID
        token: GitLab Personal Access Token (optional)
        ctx: MCP context (automatically injected)
    """
    result = await make_gitlab_request(f"/projects/{project_id}/archive", "POST", ctx=ctx, token=token)
    
    if isinstance(result, dict) and "error" in result:
        return f"Error archiving project: {result['error']}"
    
    return f"Project {project_id} archived successfully"

@mcp.tool()
async def unarchive_project(project_id: int, token: str = None, ctx=None) -> str:
    """Unarchive a project.
    
    Args:
        project_id: GitLab project ID
        token: GitLab Personal Access Token (optional)
        ctx: MCP context (automatically injected)
    """
    result = await make_gitlab_request(f"/projects/{project_id}/unarchive", "POST", ctx=ctx, token=token)
    
    if isinstance(result, dict) and "error" in result:
        return f"Error unarchiving project: {result['error']}"
    
    return f"Project {project_id} unarchived successfully"

# File Operations
@mcp.tool()
async def create_file(project_id: int, file_path: str, content: str, branch: str, commit_message: str, token: str = None, ctx=None) -> str:
    """Create a new file in repository.
    
    Args:
        project_id: GitLab project ID
        file_path: Path for the new file
        content: File content
        branch: Target branch
        commit_message: Commit message
        token: GitLab Personal Access Token (optional)
        ctx: MCP context (automatically injected)
    """
    import urllib.parse
    encoded_path = urllib.parse.quote(file_path, safe='')
    data = {
        "branch": branch,
        "content": content,
        "commit_message": commit_message
    }
    
    result = await make_gitlab_request(f"/projects/{project_id}/repository/files/{encoded_path}", "POST", data, ctx=ctx, token=token)
    
    if isinstance(result, dict) and "error" in result:
        return f"Error creating file: {result['error']}"
    
    return f"File created: {file_path} in branch {branch}"

@mcp.tool()
async def update_file(project_id: int, file_path: str, content: str, branch: str, commit_message: str, token: str = None, ctx=None) -> str:
    """Update an existing file in repository.
    
    Args:
        project_id: GitLab project ID
        file_path: Path to the file
        content: New file content
        branch: Target branch
        commit_message: Commit message
        token: GitLab Personal Access Token (optional)
        ctx: MCP context (automatically injected)
    """
    import urllib.parse
    encoded_path = urllib.parse.quote(file_path, safe='')
    data = {
        "branch": branch,
        "content": content,
        "commit_message": commit_message
    }
    
    result = await make_gitlab_request(f"/projects/{project_id}/repository/files/{encoded_path}", "PUT", data, ctx=ctx, token=token)
    
    if isinstance(result, dict) and "error" in result:
        return f"Error updating file: {result['error']}"
    
    return f"File updated: {file_path} in branch {branch}"

@mcp.tool()
async def delete_file(project_id: int, file_path: str, branch: str, commit_message: str, token: str = None, ctx=None) -> str:
    """Delete a file from repository.
    
    Args:
        project_id: GitLab project ID
        file_path: Path to the file
        branch: Target branch
        commit_message: Commit message
        token: GitLab Personal Access Token (optional)
        ctx: MCP context (automatically injected)
    """
    import urllib.parse
    encoded_path = urllib.parse.quote(file_path, safe='')
    data = {
        "branch": branch,
        "commit_message": commit_message
    }
    
    result = await make_gitlab_request(f"/projects/{project_id}/repository/files/{encoded_path}", "DELETE", data, ctx=ctx, token=token)
    
    if isinstance(result, dict) and "error" in result:
        return f"Error deleting file: {result['error']}"
    
    return f"File deleted: {file_path} from branch {branch}"

# Advanced Git Operations
@mcp.tool()
async def get_repository_tags(project_id: int, token: str = None, ctx=None) -> str:
    """Get repository tags.
    
    Args:
        project_id: GitLab project ID
        token: GitLab Personal Access Token (optional)
        ctx: MCP context (automatically injected)
    """
    data = await make_gitlab_request(f"/projects/{project_id}/repository/tags", ctx=ctx, token=token)
    
    if isinstance(data, dict) and "error" in data:
        return f"Error: {data['error']}"
    if not data:
        return "No tags found."
    
    tags = []
    for tag in data[:10]:
        tags.append(f"• {tag['name']} - {tag['commit']['short_id']} ({tag.get('message', 'No message')})")
    return "\n".join(tags)

@mcp.tool()
async def delete_tag(project_id: int, tag_name: str, token: str = None, ctx=None) -> str:
    """Delete a tag.
    
    Args:
        project_id: GitLab project ID
        tag_name: Tag name to delete
        token: GitLab Personal Access Token (optional)
        ctx: MCP context (automatically injected)
    """
    import urllib.parse
    encoded_tag = urllib.parse.quote(tag_name, safe='')
    result = await make_gitlab_request(f"/projects/{project_id}/repository/tags/{encoded_tag}", "DELETE", ctx=ctx, token=token)
    
    if isinstance(result, dict) and "error" in result:
        return f"Error deleting tag: {result['error']}"
    
    return f"Tag '{tag_name}' deleted successfully"

@mcp.tool()
async def compare_branches(project_id: int, from_branch: str, to_branch: str, token: str = None, ctx=None) -> str:
    """Compare two branches.
    
    Args:
        project_id: GitLab project ID
        from_branch: Source branch
        to_branch: Target branch
        token: GitLab Personal Access Token (optional)
        ctx: MCP context (automatically injected)
    """
    endpoint = f"/projects/{project_id}/repository/compare?from={from_branch}&to={to_branch}"
    data = await make_gitlab_request(endpoint, ctx=ctx, token=token)
    
    if isinstance(data, dict) and "error" in data:
        return f"Error: {data['error']}"
    
    commits = data.get('commits', [])
    diffs = data.get('diffs', [])
    
    result = f"Comparing {from_branch} to {to_branch}:\n"
    result += f"Commits: {len(commits)}\n"
    result += f"Files changed: {len(diffs)}\n\n"
    
    if commits:
        result += "Recent commits:\n"
        for commit in commits[:5]:
            result += f"• {commit['short_id']}: {commit['title']}\n"
    
    return result

@mcp.tool()
async def revert_commit(project_id: int, commit_sha: str, branch: str, token: str = None, ctx=None) -> str:
    """Revert a commit.
    
    Args:
        project_id: GitLab project ID
        commit_sha: Commit SHA to revert
        branch: Target branch for revert
        token: GitLab Personal Access Token (optional)
        ctx: MCP context (automatically injected)
    """
    data = {"branch": branch}
    result = await make_gitlab_request(f"/projects/{project_id}/repository/commits/{commit_sha}/revert", "POST", data, ctx=ctx, token=token)
    
    if isinstance(result, dict) and "error" in result:
        return f"Error reverting commit: {result['error']}"
    
    return f"Commit {commit_sha} reverted successfully: {result['short_id']}"

@mcp.tool()
async def cherry_pick_commit(project_id: int, commit_sha: str, branch: str, token: str = None, ctx=None) -> str:
    """Cherry-pick a commit.
    
    Args:
        project_id: GitLab project ID
        commit_sha: Commit SHA to cherry-pick
        branch: Target branch for cherry-pick
        token: GitLab Personal Access Token (optional)
        ctx: MCP context (automatically injected)
    """
    data = {"branch": branch}
    result = await make_gitlab_request(f"/projects/{project_id}/repository/commits/{commit_sha}/cherry_pick", "POST", data, ctx=ctx, token=token)
    
    if isinstance(result, dict) and "error" in result:
        return f"Error cherry-picking commit: {result['error']}"
    
    return f"Commit {commit_sha} cherry-picked successfully: {result['short_id']}"

# Issue Operations
@mcp.tool()
async def update_issue(project_id: int, issue_iid: int, title: str = None, description: str = None, state_event: str = None, token: str = None, ctx=None) -> str:
    """Update an issue.
    
    Args:
        project_id: GitLab project ID
        issue_iid: Issue IID
        title: New title (optional)
        description: New description (optional)
        state_event: State change (close, reopen) (optional)
        token: GitLab Personal Access Token (optional)
        ctx: MCP context (automatically injected)
    """
    data = {}
    if title: data["title"] = title
    if description: data["description"] = description
    if state_event: data["state_event"] = state_event
    
    result = await make_gitlab_request(f"/projects/{project_id}/issues/{issue_iid}", "PUT", data, ctx=ctx, token=token)
    
    if isinstance(result, dict) and "error" in result:
        return f"Error updating issue: {result['error']}"
    
    return f"Issue updated: #{result['iid']} - {result['title']} ({result['state']})"

@mcp.tool()
async def close_issue(project_id: int, issue_iid: int, token: str = None, ctx=None) -> str:
    """Close an issue.
    
    Args:
        project_id: GitLab project ID
        issue_iid: Issue IID
        token: GitLab Personal Access Token (optional)
        ctx: MCP context (automatically injected)
    """
    data = {"state_event": "close"}
    result = await make_gitlab_request(f"/projects/{project_id}/issues/{issue_iid}", "PUT", data, ctx=ctx, token=token)
    
    if isinstance(result, dict) and "error" in result:
        return f"Error closing issue: {result['error']}"
    
    return f"Issue closed: #{result['iid']} - {result['title']}"

# Clone Operations
@mcp.tool()
async def clone_repository(project_id: int, local_path: str = None, use_ssh: bool = False, token: str = None, ctx=None) -> str:
    """Clone a GitLab repository to local path.
    
    Args:
        project_id: GitLab project ID
        local_path: Local directory path (optional, defaults to project name)
        use_ssh: Use SSH URL instead of HTTPS (default: False)
        token: GitLab Personal Access Token (optional)
        ctx: MCP context (automatically injected)
    """
    import subprocess
    import os as os_module
    
    # Get project info
    project_data = await make_gitlab_request(f"/projects/{project_id}", ctx=ctx, token=token)
    
    if isinstance(project_data, dict) and "error" in project_data:
        return f"Error getting project info: {project_data['error']}"
    
    # Get clone URL
    clone_url = project_data['ssh_url_to_repo'] if use_ssh else project_data['http_url_to_repo']
    
    # If HTTPS and token available, add token to URL
    if not use_ssh:
        # Use the provided token or fall back to environment variable
        clone_token = token or os_module.getenv("GITLAB_TOKEN")
        if clone_token:
            # Replace https:// with https://gitlab-ci-token:TOKEN@
            clone_url = clone_url.replace("https://", f"https://gitlab-ci-token:{clone_token}@")
    
    # Set local path
    if not local_path:
        local_path = f"./{project_data['name']}"
    
    try:
        # Execute git clone
        result = subprocess.run(
            ["git", "clone", clone_url, local_path],
            capture_output=True,
            text=True,
            timeout=300  # 5 minute timeout
        )
        
        if result.returncode == 0:
            return f"Repository cloned successfully to: {local_path}\nProject: {project_data['name']} ({project_data['path_with_namespace']})"
        else:
            return f"Error cloning repository: {result.stderr}"
            
    except subprocess.TimeoutExpired:
        return "Error: Clone operation timed out (5 minutes)"
    except FileNotFoundError:
        return "Error: Git command not found. Please install Git."
    except Exception as e:
        return f"Error cloning repository: {str(e)}"

@mcp.tool()
async def clone_group_repositories(group_id: int, base_path: str = "./repos", token: str = None, ctx=None) -> str:
    """Clone all repositories from a GitLab group.
    
    Args:
        group_id: GitLab group ID
        base_path: Base directory for cloned repos (default: ./repos)
        token: GitLab Personal Access Token (optional)
        ctx: MCP context (automatically injected)
    """
    import subprocess
    import os as os_module
    
    # Get group projects
    projects_data = await make_gitlab_request(f"/groups/{group_id}/projects?per_page=100", ctx=ctx, token=token)
    
    if isinstance(projects_data, dict) and "error" in projects_data:
        return f"Error getting group projects: {projects_data['error']}"
    
    if not projects_data:
        return "No projects found in group"
    
    # Create base directory
    try:
        os_module.makedirs(base_path, exist_ok=True)
    except Exception as e:
        return f"Error creating base directory: {str(e)}"
    
    cloned = []
    failed = []
    # Use the provided token or fall back to environment variable
    clone_token = token or os_module.getenv("GITLAB_TOKEN")
    
    for project in projects_data:
        try:
            clone_url = project['http_url_to_repo']
            if clone_token:
                clone_url = clone_url.replace("https://", f"https://gitlab-ci-token:{clone_token}@")
            
            local_path = f"{base_path}/{project['name']}"
            
            result = subprocess.run(
                ["git", "clone", clone_url, local_path],
                capture_output=True,
                text=True,
                timeout=300
            )
            
            if result.returncode == 0:
                cloned.append(project['name'])
            else:
                failed.append(f"{project['name']}: {result.stderr.strip()}")
                
        except Exception as e:
            failed.append(f"{project['name']}: {str(e)}")
    
    result_msg = f"Cloned {len(cloned)} repositories to {base_path}\n"
    if cloned:
        result_msg += f"\nSuccessful: {', '.join(cloned)}"
    if failed:
        result_msg += f"\nFailed: {'; '.join(failed)}"
    
    return result_msg

# Additional Project Management Tools
@mcp.tool()
async def get_project(project_id: int, token: str = None, ctx=None) -> str:
    """Get detailed information about a specific project.
    
    Args:
        project_id: GitLab project ID
        token: GitLab Personal Access Token (optional)
        ctx: MCP context (automatically injected)
    """
    data = await make_gitlab_request(f"/projects/{project_id}", ctx=ctx, token=token)
    
    if isinstance(data, dict) and "error" in data:
        return f"Error: {data['error']}"
    
    result = f"Project: {data['name']} (ID: {data['id']})\n"
    result += f"Path: {data['path_with_namespace']}\n"
    result += f"Description: {data.get('description', 'No description')}\n"
    result += f"Visibility: {data['visibility']}\n"
    result += f"Default Branch: {data['default_branch']}\n"
    result += f"Created: {data['created_at']}\n"
    result += f"Last Activity: {data['last_activity_at']}\n"
    result += f"Stars: {data['star_count']} | Forks: {data['forks_count']}\n"
    result += f"Issues: {data['open_issues_count']} open\n"
    result += f"URL: {data['web_url']}"
    
    return result

@mcp.tool()
async def star_project(project_id: int, token: str = None, ctx=None) -> str:
    """Star a project.
    
    Args:
        project_id: GitLab project ID
        token: GitLab Personal Access Token (optional)
        ctx: MCP context (automatically injected)
    """
    result = await make_gitlab_request(f"/projects/{project_id}/star", "POST", ctx=ctx, token=token)
    
    if isinstance(result, dict) and "error" in result:
        return f"Error starring project: {result['error']}"
    
    return f"Project starred: {result['name']} (Stars: {result['star_count']})"

@mcp.tool()
async def unstar_project(project_id: int, token: str = None, ctx=None) -> str:
    """Unstar a project.
    
    Args:
        project_id: GitLab project ID
        token: GitLab Personal Access Token (optional)
        ctx: MCP context (automatically injected)
    """
    result = await make_gitlab_request(f"/projects/{project_id}/unstar", "POST", ctx=ctx, token=token)
    
    if isinstance(result, dict) and "error" in result:
        return f"Error unstarring project: {result['error']}"
    
    return f"Project unstarred: {result['name']} (Stars: {result['star_count']})"

@mcp.tool()
async def list_user_projects(user_id: int, token: str = None, ctx=None) -> str:
    """List projects owned by a specific user.
    
    Args:
        user_id: GitLab user ID
        token: GitLab Personal Access Token (optional)
        ctx: MCP context (automatically injected)
    """
    data = await make_gitlab_request(f"/users/{user_id}/projects", ctx=ctx, token=token)
    
    if isinstance(data, dict) and "error" in data:
        return f"Error: {data['error']}"
    
    if not data:
        return "No projects found for this user."
    
    projects = []
    for project in data[:10]:
        projects.append(f"• {project['name']} ({project['path_with_namespace']}) - ID: {project['id']}")
    
    return "\n".join(projects)

@mcp.tool()
async def list_starred_projects(user_id: int, token: str = None, ctx=None) -> str:
    """List projects starred by a specific user.
    
    Args:
        user_id: GitLab user ID
        token: GitLab Personal Access Token (optional)
        ctx: MCP context (automatically injected)
    """
    data = await make_gitlab_request(f"/users/{user_id}/starred_projects", ctx=ctx, token=token)
    
    if isinstance(data, dict) and "error" in data:
        return f"Error: {data['error']}"
    
    if not data:
        return "No starred projects found for this user."
    
    projects = []
    for project in data[:10]:
        projects.append(f"• {project['name']} ({project['path_with_namespace']}) - ID: {project['id']}")
    
    return "\n".join(projects)

@mcp.tool()
async def get_project_languages(project_id: int, token: str = None, ctx=None) -> str:
    """Get programming languages used in a project.
    
    Args:
        project_id: GitLab project ID
        token: GitLab Personal Access Token (optional)
        ctx: MCP context (automatically injected)
    """
    data = await make_gitlab_request(f"/projects/{project_id}/languages", ctx=ctx, token=token)
    
    if isinstance(data, dict) and "error" in data:
        return f"Error: {data['error']}"
    
    if not data:
        return "No language data available."
    
    languages = []
    for lang, percentage in data.items():
        languages.append(f"• {lang}: {percentage:.1f}%")
    
    return "\n".join(languages)

@mcp.tool()
async def get_project_forks(project_id: int, token: str = None, ctx=None) -> str:
    """List forks of a project.
    
    Args:
        project_id: GitLab project ID
        token: GitLab Personal Access Token (optional)
        ctx: MCP context (automatically injected)
    """
    data = await make_gitlab_request(f"/projects/{project_id}/forks", ctx=ctx, token=token)
    
    if isinstance(data, dict) and "error" in data:
        return f"Error: {data['error']}"
    
    if not data:
        return "No forks found."
    
    forks = []
    for fork in data[:10]:
        forks.append(f"• {fork['name']} by {fork['namespace']['name']} - ID: {fork['id']}")
    
    return "\n".join(forks)

@mcp.tool()
async def transfer_project(project_id: int, namespace: str, token: str = None, ctx=None) -> str:
    """Transfer a project to a new namespace.
    
    Args:
        project_id: GitLab project ID
        namespace: Target namespace (user or group)
        token: GitLab Personal Access Token (optional)
        ctx: MCP context (automatically injected)
    """
    data = {"namespace": namespace}
    result = await make_gitlab_request(f"/projects/{project_id}/transfer", "PUT", data, ctx=ctx, token=token)
    
    if isinstance(result, dict) and "error" in result:
        return f"Error transferring project: {result['error']}"
    
    return f"Project transferred: {result['name']} to {result['namespace']['full_path']}"

@mcp.tool()
async def get_project_users(project_id: int, token: str = None, ctx=None) -> str:
    """Get users with access to a project.
    
    Args:
        project_id: GitLab project ID
        token: GitLab Personal Access Token (optional)
        ctx: MCP context (automatically injected)
    """
    data = await make_gitlab_request(f"/projects/{project_id}/users", ctx=ctx, token=token)
    
    if isinstance(data, dict) and "error" in data:
        return f"Error: {data['error']}"
    
    if not data:
        return "No users found."
    
    users = []
    for user in data[:15]:
        users.append(f"• {user['name']} (@{user['username']}) - {user['state']}")
    
    return "\n".join(users)

@mcp.tool()
async def share_project_with_group(project_id: int, group_id: int, group_access: int, expires_at: str = None, token: str = None, ctx=None) -> str:
    """Share project with a group.
    
    Args:
        project_id: GitLab project ID
        group_id: Group ID to share with
        group_access: Access level (10=Guest, 20=Reporter, 30=Developer, 40=Maintainer, 50=Owner)
        expires_at: Expiration date (YYYY-MM-DD) (optional)
        token: GitLab Personal Access Token (optional)
        ctx: MCP context (automatically injected)
    """
    data = {
        "group_id": group_id,
        "group_access": group_access
    }
    if expires_at:
        data["expires_at"] = expires_at
    
    result = await make_gitlab_request(f"/projects/{project_id}/share", "POST", data, ctx=ctx, token=token)
    
    if isinstance(result, dict) and "error" in result:
        return f"Error sharing project: {result['error']}"
    
    return f"Project shared with group {group_id} (access level: {group_access})"

@mcp.tool()
async def unshare_project_with_group(project_id: int, group_id: int, token: str = None, ctx=None) -> str:
    """Remove project sharing with a group.
    
    Args:
        project_id: GitLab project ID
        group_id: Group ID to unshare from
        token: GitLab Personal Access Token (optional)
        ctx: MCP context (automatically injected)
    """
    result = await make_gitlab_request(f"/projects/{project_id}/share/{group_id}", "DELETE", ctx=ctx, token=token)
    
    if isinstance(result, dict) and "error" in result:
        return f"Error unsharing project: {result['error']}"
    
    return f"Project unshared from group {group_id}"

@mcp.tool()
async def list_group_projects(group_name: str, per_page: int = 50, token: str = None, ctx=None) -> str:
    """List projects in a group by group name.
    
    Args:
        group_name: GitLab group name or path
        per_page: Number of projects per page (max 100)
        token: GitLab Personal Access Token (optional)
        ctx: MCP context (automatically injected)
    """
    import urllib.parse
    encoded_name = urllib.parse.quote(group_name, safe='')
    per_page = min(per_page, 100)
    data = await make_gitlab_request(f"/groups/{encoded_name}/projects?per_page={per_page}", ctx=ctx, token=token)
    
    if isinstance(data, dict) and "error" in data:
        return f"Error: {data['error']}"
    
    if not data:
        return f"No projects found in group '{group_name}'."
    
    projects = []
    for project in data:
        projects.append(f"• {project['name']} ({project['path']}) - ID: {project['id']}")
    
    return f"Projects in group '{group_name}':\n" + "\n".join(projects)

def main():
    """Main entry point supporting all transports."""
    import argparse
    
    parser = argparse.ArgumentParser(description="GitLab MCP Server")
    parser.add_argument(
        "transport",
        choices=["stdio", "sse", "streamable-http"],
        default="stdio",
        nargs="?",
        help="Transport type (default: stdio)"
    )
    parser.add_argument(
        "--host",
        default="localhost",
        help="Host for HTTP transports (default: localhost)"
    )
    parser.add_argument(
        "--port",
        type=int,
        default=8000,
        help="Port for HTTP transports (default: 8000)"
    )
    
    args = parser.parse_args()
    
    # Run server with specified transport - GITLAB_TOKEN will be provided by the client
    if args.transport == "stdio":
        mcp.run(transport="stdio")
    elif args.transport == "sse":
        mcp.run(transport="sse")
    elif args.transport == "streamable-http":
        mcp.run(transport="streamable-http")

if __name__ == "__main__":
    main()