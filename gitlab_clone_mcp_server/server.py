from typing import Any, Optional
import httpx
from mcp.server.fastmcp import FastMCP
import os

# Initialize FastMCP server
mcp = FastMCP("gitlab")

async def make_gitlab_request(endpoint: str, method: str = "GET", data: dict = None) -> dict[str, Any] | None:
    """Make a request to GitLab API with proper error handling."""
    gitlab_url = os.getenv("GITLAB_URL", "https://gitlab.com")
    token = os.getenv("GITLAB_TOKEN")
    
    if not token:
        return {"error": "GITLAB_TOKEN environment variable not set"}
    
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
async def create_project(name: str, description: str = "", visibility: str = "private") -> str:
    """Create a new GitLab project.
    
    Args:
        name: Project name
        description: Project description (optional)
        visibility: Project visibility (private, internal, public)
    """
    data = {
        "name": name,
        "description": description,
        "visibility": visibility,
        "initialize_with_readme": True
    }
    
    result = await make_gitlab_request("/projects", "POST", data)
    
    if isinstance(result, dict) and "error" in result:
        return f"Error creating project: {result['error']}"
    
    return f"Project created: {result['name']} (ID: {result['id']})\nURL: {result['web_url']}"

@mcp.tool()
async def delete_project(project_id: int) -> str:
    """Delete a GitLab project.
    
    Args:
        project_id: GitLab project ID
    """
    result = await make_gitlab_request(f"/projects/{project_id}", "DELETE")
    
    if isinstance(result, dict) and "error" in result:
        return f"Error deleting project: {result['error']}"
    
    return f"Project {project_id} deleted successfully"

@mcp.tool()
async def list_projects(owned: bool = False) -> str:
    """List GitLab projects.
    
    Args:
        owned: If True, only show owned projects. If False, show all accessible projects.
    """
    endpoint = "/projects?membership=true&per_page=100" + ("&owned=true" if owned else "")
    data = await make_gitlab_request(endpoint)
    
    if isinstance(data, dict) and "error" in data:
        return f"Error: {data['error']}"
    
    if not data:
        return "No projects found."
    
    projects = []
    for project in data[:10]:  # Limit to 10 projects
        projects.append(f"• {project['name']} ({project['path_with_namespace']}) - ID: {project['id']}")
    
    return "\n".join(projects)

@mcp.tool()
async def get_project_issues(project_id: int, state: str = "opened") -> str:
    """Get issues for a GitLab project.
    
    Args:
        project_id: GitLab project ID
        state: Issue state (opened, closed, all)
    """
    endpoint = f"/projects/{project_id}/issues?state={state}"
    data = await make_gitlab_request(endpoint)
    
    if isinstance(data, dict) and "error" in data:
        return f"Error: {data['error']}"
    
    if not data:
        return f"No {state} issues found."
    
    issues = []
    for issue in data[:10]:  # Limit to 10 issues
        issues.append(f"#{issue['iid']}: {issue['title']} - {issue['state']} ({issue['author']['name']})")
    
    return "\n".join(issues)

@mcp.tool()
async def get_merge_requests(project_id: int, state: str = "opened") -> str:
    """Get merge requests for a GitLab project.
    
    Args:
        project_id: GitLab project ID
        state: MR state (opened, closed, merged, all)
    """
    endpoint = f"/projects/{project_id}/merge_requests?state={state}"
    data = await make_gitlab_request(endpoint)
    
    if isinstance(data, dict) and "error" in data:
        return f"Error: {data['error']}"
    
    if not data:
        return f"No {state} merge requests found."
    
    mrs = []
    for mr in data[:10]:  # Limit to 10 MRs
        mrs.append(f"!{mr['iid']}: {mr['title']} - {mr['state']} ({mr['author']['name']})")
    
    return "\n".join(mrs)

@mcp.tool()
async def create_issue(project_id: int, title: str, description: str = "") -> str:
    """Create a new issue in a GitLab project.
    
    Args:
        project_id: GitLab project ID
        title: Issue title
        description: Issue description (optional)
    """
    endpoint = f"/projects/{project_id}/issues"
    data = {
        "title": title,
        "description": description
    }
    
    result = await make_gitlab_request(endpoint, "POST", data)
    
    if isinstance(result, dict) and "error" in result:
        return f"Error creating issue: {result['error']}"
    
    return f"Issue created successfully: #{result['iid']} - {result['title']}"

@mcp.tool()
async def get_pipelines(project_id: int, status: str = "running") -> str:
    """Get CI/CD pipelines for a GitLab project.
    
    Args:
        project_id: GitLab project ID
        status: Pipeline status (running, pending, success, failed, canceled, skipped)
    """
    endpoint = f"/projects/{project_id}/pipelines?status={status}"
    data = await make_gitlab_request(endpoint)
    
    if isinstance(data, dict) and "error" in data:
        return f"Error: {data['error']}"
    
    if not data:
        return f"No {status} pipelines found."
    
    pipelines = []
    for pipeline in data[:10]:  # Limit to 10 pipelines
        pipelines.append(f"Pipeline #{pipeline['id']}: {pipeline['status']} - {pipeline['ref']} ({pipeline.get('user', {}).get('name', 'Unknown')})")
    
    return "\n".join(pipelines)

@mcp.tool()
async def get_project_branches(project_id: int) -> str:
    """Get branches for a GitLab project.
    
    Args:
        project_id: GitLab project ID
    """
    endpoint = f"/projects/{project_id}/repository/branches"
    data = await make_gitlab_request(endpoint)
    
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
async def list_groups() -> str:
    """List GitLab groups."""
    data = await make_gitlab_request("/groups")
    if isinstance(data, dict) and "error" in data:
        return f"Error: {data['error']}"
    if not data:
        return "No groups found."
    
    groups = []
    for group in data[:10]:
        groups.append(f"• {group['name']} ({group['path']}) - ID: {group['id']}")
    return "\n".join(groups)

@mcp.tool()
async def get_group_members(group_id: int) -> str:
    """Get members of a GitLab group.
    
    Args:
        group_id: GitLab group ID
    """
    data = await make_gitlab_request(f"/groups/{group_id}/members")
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
async def get_repository_files(project_id: int, path: str = "", ref: str = "main") -> str:
    """Get repository files and directories.
    
    Args:
        project_id: GitLab project ID
        path: Directory path (optional)
        ref: Branch/tag reference (default: main)
    """
    endpoint = f"/projects/{project_id}/repository/tree?path={path}&ref={ref}"
    data = await make_gitlab_request(endpoint)
    
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
async def get_file_content(project_id: int, file_path: str, ref: str = "main") -> str:
    """Get content of a repository file.
    
    Args:
        project_id: GitLab project ID
        file_path: Path to the file
        ref: Branch/tag reference (default: main)
    """
    import urllib.parse
    encoded_path = urllib.parse.quote(file_path, safe='')
    endpoint = f"/projects/{project_id}/repository/files/{encoded_path}?ref={ref}"
    data = await make_gitlab_request(endpoint)
    
    if isinstance(data, dict) and "error" in data:
        return f"Error: {data['error']}"
    
    import base64
    try:
        content = base64.b64decode(data['content']).decode('utf-8')
        return f"File: {file_path}\n\n{content[:2000]}{'...' if len(content) > 2000 else ''}"
    except:
        return "Unable to decode file content"

@mcp.tool()
async def get_commits(project_id: int, ref_name: str = "main") -> str:
    """Get recent commits for a project.
    
    Args:
        project_id: GitLab project ID
        ref_name: Branch name (default: main)
    """
    endpoint = f"/projects/{project_id}/repository/commits?ref_name={ref_name}"
    data = await make_gitlab_request(endpoint)
    
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
async def create_commit(project_id: int, branch: str, commit_message: str, file_path: str, file_content: str, action: str = "create") -> str:
    """Create a commit with file changes.
    
    Args:
        project_id: GitLab project ID
        branch: Target branch
        commit_message: Commit message
        file_path: Path to the file
        file_content: File content
        action: Action (create, update, delete)
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
    
    result = await make_gitlab_request(f"/projects/{project_id}/repository/commits", "POST", data)
    
    if isinstance(result, dict) and "error" in result:
        return f"Error creating commit: {result['error']}"
    
    return f"Commit created: {result['short_id']} - {result['title']}"

@mcp.tool()
async def create_branch(project_id: int, branch_name: str, ref: str = "main") -> str:
    """Create a new branch.
    
    Args:
        project_id: GitLab project ID
        branch_name: New branch name
        ref: Source branch/commit (default: main)
    """
    data = {
        "branch": branch_name,
        "ref": ref
    }
    
    result = await make_gitlab_request(f"/projects/{project_id}/repository/branches", "POST", data)
    
    if isinstance(result, dict) and "error" in result:
        return f"Error creating branch: {result['error']}"
    
    return f"Branch created: {result['name']} from {ref}"

@mcp.tool()
async def delete_branch(project_id: int, branch_name: str) -> str:
    """Delete a branch.
    
    Args:
        project_id: GitLab project ID
        branch_name: Branch name to delete
    """
    import urllib.parse
    encoded_branch = urllib.parse.quote(branch_name, safe='')
    result = await make_gitlab_request(f"/projects/{project_id}/repository/branches/{encoded_branch}", "DELETE")
    
    if isinstance(result, dict) and "error" in result:
        return f"Error deleting branch: {result['error']}"
    
    return f"Branch '{branch_name}' deleted successfully"

@mcp.tool()
async def create_merge_request(project_id: int, source_branch: str, target_branch: str, title: str, description: str = "") -> str:
    """Create a merge request.
    
    Args:
        project_id: GitLab project ID
        source_branch: Source branch
        target_branch: Target branch
        title: MR title
        description: MR description (optional)
    """
    data = {
        "source_branch": source_branch,
        "target_branch": target_branch,
        "title": title,
        "description": description
    }
    
    result = await make_gitlab_request(f"/projects/{project_id}/merge_requests", "POST", data)
    
    if isinstance(result, dict) and "error" in result:
        return f"Error creating merge request: {result['error']}"
    
    return f"Merge request created: !{result['iid']} - {result['title']}\nURL: {result['web_url']}"

@mcp.tool()
async def merge_merge_request(project_id: int, merge_request_iid: int, merge_commit_message: str = "") -> str:
    """Merge a merge request.
    
    Args:
        project_id: GitLab project ID
        merge_request_iid: Merge request IID
        merge_commit_message: Custom merge commit message (optional)
    """
    data = {}
    if merge_commit_message:
        data["merge_commit_message"] = merge_commit_message
    
    result = await make_gitlab_request(f"/projects/{project_id}/merge_requests/{merge_request_iid}/merge", "PUT", data)
    
    if isinstance(result, dict) and "error" in result:
        return f"Error merging MR: {result['error']}"
    
    return f"Merge request !{merge_request_iid} merged successfully"

@mcp.tool()
async def create_tag(project_id: int, tag_name: str, ref: str, message: str = "") -> str:
    """Create a new tag.
    
    Args:
        project_id: GitLab project ID
        tag_name: Tag name
        ref: Source branch/commit
        message: Tag message (optional)
    """
    data = {
        "tag_name": tag_name,
        "ref": ref,
        "message": message
    }
    
    result = await make_gitlab_request(f"/projects/{project_id}/repository/tags", "POST", data)
    
    if isinstance(result, dict) and "error" in result:
        return f"Error creating tag: {result['error']}"
    
    return f"Tag created: {result['name']} at {result['commit']['short_id']}"

# CI/CD
@mcp.tool()
async def get_pipeline_jobs(project_id: int, pipeline_id: int) -> str:
    """Get jobs for a specific pipeline.
    
    Args:
        project_id: GitLab project ID
        pipeline_id: Pipeline ID
    """
    endpoint = f"/projects/{project_id}/pipelines/{pipeline_id}/jobs"
    data = await make_gitlab_request(endpoint)
    
    if isinstance(data, dict) and "error" in data:
        return f"Error: {data['error']}"
    if not data:
        return "No jobs found."
    
    jobs = []
    for job in data:
        jobs.append(f"• {job['name']}: {job['status']} (Stage: {job['stage']})")
    return "\n".join(jobs)

@mcp.tool()
async def trigger_pipeline(project_id: int, ref: str = "main") -> str:
    """Trigger a new pipeline.
    
    Args:
        project_id: GitLab project ID
        ref: Branch/tag to run pipeline on (default: main)
    """
    endpoint = f"/projects/{project_id}/pipeline"
    data = {"ref": ref}
    result = await make_gitlab_request(endpoint, "POST", data)
    
    if isinstance(result, dict) and "error" in result:
        return f"Error triggering pipeline: {result['error']}"
    
    return f"Pipeline triggered successfully: #{result['id']} on {ref}"

# Users
@mcp.tool()
async def get_current_user() -> str:
    """Get current user information."""
    data = await make_gitlab_request("/user")
    if isinstance(data, dict) and "error" in data:
        return f"Error: {data['error']}"
    
    return f"User: {data['name']} (@{data['username']})\nEmail: {data['email']}\nID: {data['id']}"

@mcp.tool()
async def search_projects(query: str) -> str:
    """Search for projects.
    
    Args:
        query: Search query
    """
    import urllib.parse
    encoded_query = urllib.parse.quote(query)
    endpoint = f"/projects?search={encoded_query}"
    data = await make_gitlab_request(endpoint)
    
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
async def get_project_milestones(project_id: int, state: str = "active") -> str:
    """Get project milestones.
    
    Args:
        project_id: GitLab project ID
        state: Milestone state (active, closed, all)
    """
    endpoint = f"/projects/{project_id}/milestones?state={state}"
    data = await make_gitlab_request(endpoint)
    
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
async def get_project_labels(project_id: int) -> str:
    """Get project labels.
    
    Args:
        project_id: GitLab project ID
    """
    data = await make_gitlab_request(f"/projects/{project_id}/labels")
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
async def list_project_hooks(project_id: int) -> str:
    """List project webhooks.
    
    Args:
        project_id: GitLab project ID
    """
    data = await make_gitlab_request(f"/projects/{project_id}/hooks")
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
async def update_project(project_id: int, name: str = None, description: str = None, visibility: str = None) -> str:
    """Update project settings.
    
    Args:
        project_id: GitLab project ID
        name: New project name (optional)
        description: New description (optional)
        visibility: New visibility (private, internal, public) (optional)
    """
    data = {}
    if name: data["name"] = name
    if description: data["description"] = description
    if visibility: data["visibility"] = visibility
    
    result = await make_gitlab_request(f"/projects/{project_id}", "PUT", data)
    
    if isinstance(result, dict) and "error" in result:
        return f"Error updating project: {result['error']}"
    
    return f"Project updated: {result['name']} (ID: {result['id']})"

@mcp.tool()
async def fork_project(project_id: int, namespace: str = None) -> str:
    """Fork a project.
    
    Args:
        project_id: GitLab project ID to fork
        namespace: Target namespace (optional)
    """
    data = {}
    if namespace: data["namespace"] = namespace
    
    result = await make_gitlab_request(f"/projects/{project_id}/fork", "POST", data)
    
    if isinstance(result, dict) and "error" in result:
        return f"Error forking project: {result['error']}"
    
    return f"Project forked: {result['name']} (ID: {result['id']})\nURL: {result['web_url']}"

@mcp.tool()
async def archive_project(project_id: int) -> str:
    """Archive a project.
    
    Args:
        project_id: GitLab project ID
    """
    result = await make_gitlab_request(f"/projects/{project_id}/archive", "POST")
    
    if isinstance(result, dict) and "error" in result:
        return f"Error archiving project: {result['error']}"
    
    return f"Project {project_id} archived successfully"

@mcp.tool()
async def unarchive_project(project_id: int) -> str:
    """Unarchive a project.
    
    Args:
        project_id: GitLab project ID
    """
    result = await make_gitlab_request(f"/projects/{project_id}/unarchive", "POST")
    
    if isinstance(result, dict) and "error" in result:
        return f"Error unarchiving project: {result['error']}"
    
    return f"Project {project_id} unarchived successfully"

# File Operations
@mcp.tool()
async def create_file(project_id: int, file_path: str, content: str, branch: str, commit_message: str) -> str:
    """Create a new file in repository.
    
    Args:
        project_id: GitLab project ID
        file_path: Path for the new file
        content: File content
        branch: Target branch
        commit_message: Commit message
    """
    import urllib.parse
    encoded_path = urllib.parse.quote(file_path, safe='')
    data = {
        "branch": branch,
        "content": content,
        "commit_message": commit_message
    }
    
    result = await make_gitlab_request(f"/projects/{project_id}/repository/files/{encoded_path}", "POST", data)
    
    if isinstance(result, dict) and "error" in result:
        return f"Error creating file: {result['error']}"
    
    return f"File created: {file_path} in branch {branch}"

@mcp.tool()
async def update_file(project_id: int, file_path: str, content: str, branch: str, commit_message: str) -> str:
    """Update an existing file in repository.
    
    Args:
        project_id: GitLab project ID
        file_path: Path to the file
        content: New file content
        branch: Target branch
        commit_message: Commit message
    """
    import urllib.parse
    encoded_path = urllib.parse.quote(file_path, safe='')
    data = {
        "branch": branch,
        "content": content,
        "commit_message": commit_message
    }
    
    result = await make_gitlab_request(f"/projects/{project_id}/repository/files/{encoded_path}", "PUT", data)
    
    if isinstance(result, dict) and "error" in result:
        return f"Error updating file: {result['error']}"
    
    return f"File updated: {file_path} in branch {branch}"

@mcp.tool()
async def delete_file(project_id: int, file_path: str, branch: str, commit_message: str) -> str:
    """Delete a file from repository.
    
    Args:
        project_id: GitLab project ID
        file_path: Path to the file
        branch: Target branch
        commit_message: Commit message
    """
    import urllib.parse
    encoded_path = urllib.parse.quote(file_path, safe='')
    data = {
        "branch": branch,
        "commit_message": commit_message
    }
    
    result = await make_gitlab_request(f"/projects/{project_id}/repository/files/{encoded_path}", "DELETE", data)
    
    if isinstance(result, dict) and "error" in result:
        return f"Error deleting file: {result['error']}"
    
    return f"File deleted: {file_path} from branch {branch}"

# Advanced Git Operations
@mcp.tool()
async def get_repository_tags(project_id: int) -> str:
    """Get repository tags.
    
    Args:
        project_id: GitLab project ID
    """
    data = await make_gitlab_request(f"/projects/{project_id}/repository/tags")
    
    if isinstance(data, dict) and "error" in data:
        return f"Error: {data['error']}"
    if not data:
        return "No tags found."
    
    tags = []
    for tag in data[:10]:
        tags.append(f"• {tag['name']} - {tag['commit']['short_id']} ({tag.get('message', 'No message')})")
    return "\n".join(tags)

@mcp.tool()
async def delete_tag(project_id: int, tag_name: str) -> str:
    """Delete a tag.
    
    Args:
        project_id: GitLab project ID
        tag_name: Tag name to delete
    """
    import urllib.parse
    encoded_tag = urllib.parse.quote(tag_name, safe='')
    result = await make_gitlab_request(f"/projects/{project_id}/repository/tags/{encoded_tag}", "DELETE")
    
    if isinstance(result, dict) and "error" in result:
        return f"Error deleting tag: {result['error']}"
    
    return f"Tag '{tag_name}' deleted successfully"

@mcp.tool()
async def compare_branches(project_id: int, from_branch: str, to_branch: str) -> str:
    """Compare two branches.
    
    Args:
        project_id: GitLab project ID
        from_branch: Source branch
        to_branch: Target branch
    """
    endpoint = f"/projects/{project_id}/repository/compare?from={from_branch}&to={to_branch}"
    data = await make_gitlab_request(endpoint)
    
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
async def revert_commit(project_id: int, commit_sha: str, branch: str) -> str:
    """Revert a commit.
    
    Args:
        project_id: GitLab project ID
        commit_sha: Commit SHA to revert
        branch: Target branch for revert
    """
    data = {"branch": branch}
    result = await make_gitlab_request(f"/projects/{project_id}/repository/commits/{commit_sha}/revert", "POST", data)
    
    if isinstance(result, dict) and "error" in result:
        return f"Error reverting commit: {result['error']}"
    
    return f"Commit {commit_sha} reverted successfully: {result['short_id']}"

@mcp.tool()
async def cherry_pick_commit(project_id: int, commit_sha: str, branch: str) -> str:
    """Cherry-pick a commit.
    
    Args:
        project_id: GitLab project ID
        commit_sha: Commit SHA to cherry-pick
        branch: Target branch for cherry-pick
    """
    data = {"branch": branch}
    result = await make_gitlab_request(f"/projects/{project_id}/repository/commits/{commit_sha}/cherry_pick", "POST", data)
    
    if isinstance(result, dict) and "error" in result:
        return f"Error cherry-picking commit: {result['error']}"
    
    return f"Commit {commit_sha} cherry-picked successfully: {result['short_id']}"

# Issue Operations
@mcp.tool()
async def update_issue(project_id: int, issue_iid: int, title: str = None, description: str = None, state_event: str = None) -> str:
    """Update an issue.
    
    Args:
        project_id: GitLab project ID
        issue_iid: Issue IID
        title: New title (optional)
        description: New description (optional)
        state_event: State change (close, reopen) (optional)
    """
    data = {}
    if title: data["title"] = title
    if description: data["description"] = description
    if state_event: data["state_event"] = state_event
    
    result = await make_gitlab_request(f"/projects/{project_id}/issues/{issue_iid}", "PUT", data)
    
    if isinstance(result, dict) and "error" in result:
        return f"Error updating issue: {result['error']}"
    
    return f"Issue updated: #{result['iid']} - {result['title']} ({result['state']})"

@mcp.tool()
async def close_issue(project_id: int, issue_iid: int) -> str:
    """Close an issue.
    
    Args:
        project_id: GitLab project ID
        issue_iid: Issue IID
    """
    data = {"state_event": "close"}
    result = await make_gitlab_request(f"/projects/{project_id}/issues/{issue_iid}", "PUT", data)
    
    if isinstance(result, dict) and "error" in result:
        return f"Error closing issue: {result['error']}"
    
    return f"Issue closed: #{result['iid']} - {result['title']}"

# Clone Operations
@mcp.tool()
async def clone_repository(project_id: int, local_path: str = None, use_ssh: bool = False) -> str:
    """Clone a GitLab repository to local path.
    
    Args:
        project_id: GitLab project ID
        local_path: Local directory path (optional, defaults to project name)
        use_ssh: Use SSH URL instead of HTTPS (default: False)
    """
    import subprocess
    import os as os_module
    
    # Get project info
    project_data = await make_gitlab_request(f"/projects/{project_id}")
    
    if isinstance(project_data, dict) and "error" in project_data:
        return f"Error getting project info: {project_data['error']}"
    
    # Get clone URL
    clone_url = project_data['ssh_url_to_repo'] if use_ssh else project_data['http_url_to_repo']
    
    # If HTTPS and token available, add token to URL
    if not use_ssh:
        token = os_module.getenv("GITLAB_TOKEN")
        if token:
            # Replace https:// with https://gitlab-ci-token:TOKEN@
            clone_url = clone_url.replace("https://", f"https://gitlab-ci-token:{token}@")
    
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
async def clone_group_repositories(group_id: int, base_path: str = "./repos") -> str:
    """Clone all repositories from a GitLab group.
    
    Args:
        group_id: GitLab group ID
        base_path: Base directory for cloned repos (default: ./repos)
    """
    import subprocess
    import os as os_module
    
    # Get group projects
    projects_data = await make_gitlab_request(f"/groups/{group_id}/projects?per_page=100")
    
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
    token = os_module.getenv("GITLAB_TOKEN")
    
    for project in projects_data:
        try:
            clone_url = project['http_url_to_repo']
            if token:
                clone_url = clone_url.replace("https://", f"https://gitlab-ci-token:{token}@")
            
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

def main():
    """Main entry point for uvx."""
    mcp.run(transport='stdio')

if __name__ == "__main__":
    main()