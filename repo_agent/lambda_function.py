"""AWS Lambda repository agent that proposes GitHub pull requests.

The function is intentionally PR-only. It reads a fixed repository, asks the
OpenAI Responses API for structured file edits, creates an agent branch, and
opens a pull request. It never executes repository code.
"""

from __future__ import annotations

import base64
import json
import os
import posixpath
import secrets
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from typing import Any


MAX_CONTEXT_BYTES = 220_000
MAX_FILE_BYTES = 50_000
MAX_EDIT_FILES = 12
MAX_EDIT_BYTES = 100_000

ALLOWED_SUFFIXES = {
    ".py", ".tf", ".tfvars.example", ".yml", ".yaml", ".json",
    ".md", ".txt", ".toml", ".ini", ".cfg", ".sh",
}
ALLOWED_NAMES = {
    "Dockerfile", "Makefile", ".gitignore", ".dockerignore",
    "requirements.txt",
}
EXCLUDED_PARTS = {
    ".git", ".terraform", "node_modules", "venv", ".venv",
    "__pycache__", "dist", "build",
}
SENSITIVE_NAME_PARTS = {
    ".env", "secret", "credential", "private_key", "id_rsa",
    "terraform.tfstate",
}


class AgentError(RuntimeError):
    """A safe, user-facing agent failure."""


def _http_json(
    method: str,
    url: str,
    *,
    headers: dict[str, str],
    payload: dict[str, Any] | None = None,
) -> dict[str, Any]:
    body = None if payload is None else json.dumps(payload).encode("utf-8")
    request = urllib.request.Request(url, data=body, headers=headers, method=method)
    try:
        with urllib.request.urlopen(request, timeout=45) as response:
            raw = response.read()
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")[:1_500]
        raise AgentError(f"HTTP {exc.code} from {url}: {detail}") from exc
    except urllib.error.URLError as exc:
        raise AgentError(f"Request failed for {url}: {exc.reason}") from exc

    if not raw:
        return {}
    return json.loads(raw.decode("utf-8"))


def _parse_event(event: dict[str, Any]) -> dict[str, Any]:
    if isinstance(event.get("body"), str):
        try:
            body = json.loads(event["body"])
        except json.JSONDecodeError as exc:
            raise AgentError("Request body must be valid JSON.") from exc
    else:
        body = event

    task = body.get("task")
    if not isinstance(task, str) or not task.strip():
        raise AgentError("Provide a non-empty 'task' string.")
    if len(task) > 4_000:
        raise AgentError("Task is too long; maximum length is 4,000 characters.")

    return {"task": task.strip(), "dry_run": bool(body.get("dry_run", False))}


def _load_secrets() -> dict[str, str]:
    import boto3

    secret_id = os.environ["SECRET_ID"]
    region = os.environ.get("AWS_REGION")
    client = boto3.client("secretsmanager", region_name=region)
    response = client.get_secret_value(SecretId=secret_id)
    values = json.loads(response["SecretString"])

    required = ("openai_api_key", "github_token")
    missing = [key for key in required if not values.get(key)]
    if missing:
        raise AgentError(f"Secret is missing required keys: {', '.join(missing)}")
    return values


def _github_headers(token: str) -> dict[str, str]:
    return {
        "Accept": "application/vnd.github+json",
        "Authorization": f"Bearer {token}",
        "X-GitHub-Api-Version": "2022-11-28",
        "Content-Type": "application/json",
        "User-Agent": "griffle-guard-repo-agent",
    }


def _github_request(
    method: str,
    repository: str,
    endpoint: str,
    token: str,
    payload: dict[str, Any] | None = None,
) -> dict[str, Any]:
    url = f"https://api.github.com/repos/{repository}{endpoint}"
    return _http_json(method, url, headers=_github_headers(token), payload=payload)


def _is_allowed_source(path: str, size: int) -> bool:
    if size <= 0 or size > MAX_FILE_BYTES:
        return False
    parts = set(path.split("/"))
    if parts & EXCLUDED_PARTS:
        return False
    lowered = path.lower()
    if any(fragment in lowered for fragment in SENSITIVE_NAME_PARTS):
        return False
    name = posixpath.basename(path)
    return name in ALLOWED_NAMES or any(lowered.endswith(s) for s in ALLOWED_SUFFIXES)


def _decode_blob(blob: dict[str, Any]) -> str | None:
    if blob.get("encoding") != "base64":
        return None
    try:
        raw = base64.b64decode(blob["content"])
        if b"\x00" in raw:
            return None
        return raw.decode("utf-8")
    except (KeyError, ValueError, UnicodeDecodeError):
        return None


def _load_repository_context(
    repository: str, token: str
) -> tuple[str, str, str, dict[str, str]]:
    metadata = _github_request("GET", repository, "", token)
    default_branch = metadata.get("default_branch", "main")
    quoted_branch = urllib.parse.quote(default_branch, safe="")
    ref = _github_request(
        "GET", repository, f"/git/ref/heads/{quoted_branch}", token
    )
    base_sha = ref["object"]["sha"]
    commit = _github_request("GET", repository, f"/git/commits/{base_sha}", token)
    base_tree_sha = commit["tree"]["sha"]
    tree = _github_request(
        "GET", repository, f"/git/trees/{base_tree_sha}?recursive=1", token
    )
    if tree.get("truncated"):
        raise AgentError("Repository tree was truncated; narrow the agent scope first.")

    files: dict[str, str] = {}
    total = 0
    for item in sorted(tree.get("tree", []), key=lambda entry: entry["path"]):
        if item.get("type") != "blob":
            continue
        size = int(item.get("size", 0))
        path = item["path"]
        if not _is_allowed_source(path, size) or total + size > MAX_CONTEXT_BYTES:
            continue
        blob = _github_request("GET", repository, f"/git/blobs/{item['sha']}", token)
        content = _decode_blob(blob)
        if content is None:
            continue
        files[path] = content
        total += len(content.encode("utf-8"))

    if not files:
        raise AgentError("No eligible UTF-8 source files were found.")
    return default_branch, base_sha, base_tree_sha, files


def _response_output_text(response: dict[str, Any]) -> str:
    for item in response.get("output", []):
        if item.get("type") != "message":
            continue
        for content in item.get("content", []):
            if content.get("type") == "output_text" and content.get("text"):
                return content["text"]
    raise AgentError("OpenAI response did not contain structured output text.")


def _ask_openai(
    task: str, repository: str, files: dict[str, str], api_key: str
) -> dict[str, Any]:
    model = os.environ.get("OPENAI_MODEL", "gpt-6-astra")
    context = "\n\n".join(
        f"--- FILE: {path} ---\n{content}" for path, content in files.items()
    )
    schema = {
        "type": "object",
        "properties": {
            "title": {"type": "string"},
            "summary": {"type": "string"},
            "edits": {
                "type": "array",
                "maxItems": MAX_EDIT_FILES,
                "items": {
                    "type": "object",
                    "properties": {
                        "path": {"type": "string"},
                        "content": {"type": "string"},
                        "reason": {"type": "string"},
                    },
                    "required": ["path", "content", "reason"],
                    "additionalProperties": False,
                },
            },
        },
        "required": ["title", "summary", "edits"],
        "additionalProperties": False,
    }
    payload = {
        "model": model,
        "store": False,
        "max_output_tokens": 30_000,
        "instructions": (
            "You are a careful repository maintenance agent. Return the smallest "
            "complete patch that fulfills the task. Only edit text files. Never add "
            "credentials, tokens, generated state, binaries, or unrelated refactors. "
            "Do not delete files. Preserve existing behavior unless the task requires "
            "a change. The result will be committed to a new branch and reviewed by a "
            "human; never claim it has been merged or deployed."
        ),
        "input": (
            f"Repository: {repository}\nTask: {task}\n\n"
            f"Current eligible files:\n{context}"
        ),
        "text": {
            "format": {
                "type": "json_schema",
                "name": "repository_patch",
                "strict": True,
                "schema": schema,
            }
        },
    }
    response = _http_json(
        "POST",
        "https://api.openai.com/v1/responses",
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        payload=payload,
    )
    try:
        return json.loads(_response_output_text(response))
    except json.JSONDecodeError as exc:
        raise AgentError("OpenAI returned invalid structured JSON.") from exc


def _validate_edit_path(path: str) -> str:
    if not isinstance(path, str) or not path:
        raise AgentError("Every edit must have a non-empty path.")
    normalized = posixpath.normpath(path).lstrip("/")
    if normalized in {"", "."} or normalized.startswith("../"):
        raise AgentError(f"Unsafe edit path: {path}")
    lowered = normalized.lower()
    if any(part in EXCLUDED_PARTS for part in normalized.split("/")):
        raise AgentError(f"Excluded edit path: {path}")
    if any(fragment in lowered for fragment in SENSITIVE_NAME_PARTS):
        raise AgentError(f"Sensitive edit path rejected: {path}")
    return normalized


def _validate_plan(plan: dict[str, Any]) -> list[dict[str, str]]:
    edits = plan.get("edits")
    if not isinstance(edits, list) or not edits:
        raise AgentError("The agent proposed no file edits.")
    if len(edits) > MAX_EDIT_FILES:
        raise AgentError(f"The agent proposed more than {MAX_EDIT_FILES} files.")

    validated: list[dict[str, str]] = []
    seen: set[str] = set()
    for edit in edits:
        path = _validate_edit_path(edit.get("path"))
        content = edit.get("content")
        if not isinstance(content, str):
            raise AgentError(f"Edit content for {path} must be text.")
        if len(content.encode("utf-8")) > MAX_EDIT_BYTES:
            raise AgentError(f"Edit for {path} is larger than {MAX_EDIT_BYTES} bytes.")
        if path in seen:
            raise AgentError(f"Duplicate edit path: {path}")
        seen.add(path)
        validated.append({
            "path": path,
            "content": content,
            "reason": str(edit.get("reason", "")),
        })
    return validated


def _branch_name() -> str:
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    return f"agent/{timestamp}-{secrets.token_hex(3)}"


def _create_pull_request(
    repository: str,
    token: str,
    default_branch: str,
    base_sha: str,
    base_tree_sha: str,
    plan: dict[str, Any],
    edits: list[dict[str, str]],
) -> dict[str, Any]:
    branch = _branch_name()
    tree_entries = []
    for edit in edits:
        blob = _github_request(
            "POST", repository, "/git/blobs", token,
            {"content": edit["content"], "encoding": "utf-8"},
        )
        tree_entries.append({
            "path": edit["path"],
            "mode": "100644",
            "type": "blob",
            "sha": blob["sha"],
        })

    tree = _github_request(
        "POST", repository, "/git/trees", token,
        {"base_tree": base_tree_sha, "tree": tree_entries},
    )
    commit = _github_request(
        "POST", repository, "/git/commits", token,
        {
            "message": str(plan["title"])[:120],
            "tree": tree["sha"],
            "parents": [base_sha],
        },
    )
    _github_request(
        "POST", repository, "/git/refs", token,
        {"ref": f"refs/heads/{branch}", "sha": commit["sha"]},
    )

    changed = "\n".join(
        f"- `{edit['path']}` — {edit['reason']}" for edit in edits
    )
    body = (
        f"## Summary\n\n{plan['summary']}\n\n"
        f"## Files changed\n\n{changed}\n\n"
        "## Safety\n\n"
        "- Created by the Griffle-Guard AWS repository agent\n"
        "- Changes were proposed on a new branch; `main` was not modified\n"
        "- Repository code was not executed by the agent\n"
        "- Review CI results and the diff before merging\n"
    )
    return _github_request(
        "POST", repository, "/pulls", token,
        {
            "title": str(plan["title"])[:240],
            "head": branch,
            "base": default_branch,
            "body": body,
            "draft": True,
        },
    )


def lambda_handler(event: dict[str, Any], context: Any) -> dict[str, Any]:
    try:
        request = _parse_event(event or {})
        repository = os.environ["GITHUB_REPOSITORY"]
        credentials = _load_secrets()
        default_branch, base_sha, base_tree_sha, files = _load_repository_context(
            repository, credentials["github_token"]
        )
        plan = _ask_openai(
            request["task"], repository, files, credentials["openai_api_key"]
        )
        edits = _validate_plan(plan)

        if request["dry_run"]:
            result = {
                "dry_run": True,
                "title": plan["title"],
                "summary": plan["summary"],
                "files": [edit["path"] for edit in edits],
            }
        else:
            pull_request = _create_pull_request(
                repository,
                credentials["github_token"],
                default_branch,
                base_sha,
                base_tree_sha,
                plan,
                edits,
            )
            result = {
                "dry_run": False,
                "pull_request_number": pull_request["number"],
                "pull_request_url": pull_request["html_url"],
                "branch": pull_request["head"]["ref"],
            }
        return {"statusCode": 200, "body": json.dumps(result)}
    except (AgentError, KeyError, TypeError, ValueError) as exc:
        print(f"Repository agent failed: {exc}")
        return {"statusCode": 400, "body": json.dumps({"error": str(exc)})}
