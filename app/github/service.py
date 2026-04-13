import httpx
import os

GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")

async def get_pr_files(owner: str, repo: str, pull_number: int):
    url = f"https://api.github.com/repos/{owner}/{repo}/pulls/{pull_number}/files"
    headers = {
        "Authorization": f"Bearer {GITHUB_TOKEN}",
        "Accept": "application/vnd.github+json"
    }
    async with httpx.AsyncClient() as client:
        response = await client.get(url, headers=headers)
        response.raise_for_status()
        return response.json()


async def post_review(owner: str, repo: str, pull_number: int, head_sha: str, findings: list):
    url = f"https://api.github.com/repos/{owner}/{repo}/pulls/{pull_number}/reviews"
    headers = {
        "Authorization": f"Bearer {GITHUB_TOKEN}",
        "Accept": "application/vnd.github+json"
    }

    # Build inline comments from findings
    comments = []
    for f in findings:
        comments.append({
            "path": f["filename"],
            "position": f["position"],
            "body": f"**[{f['severity'].upper()}] {f['category'].capitalize()}**\n\n{f['message']}\n\n💡 **Suggestion:** {f['suggestion']}"
        })

    body = {
        "commit_id": head_sha,
        "body": build_summary(findings),
        "event": "COMMENT",
        "comments": comments
    }

    async with httpx.AsyncClient() as client:
        response = await client.post(url, headers=headers, json=body)
        response.raise_for_status()
        return response.json()


def build_summary(findings: list) -> str:
    if not findings:
        return "✅ No issues found in this PR."

    errors = [f for f in findings if f["severity"] == "error"]
    warnings = [f for f in findings if f["severity"] == "warning"]
    style = [f for f in findings if f["severity"] == "style"]

    summary = "## 🤖 AI Code Review Summary\n\n"
    summary += f"| Severity | Count |\n|---|---|\n"
    summary += f"| 🔴 Errors | {len(errors)} |\n"
    summary += f"| 🟡 Warnings | {len(warnings)} |\n"
    summary += f"| 🔵 Style | {len(style)} |\n"
    return summary