import os
import requests
from flask import Flask, jsonify, request
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

GITHUB_API = "https://api.github.com"
TOKEN = os.getenv("GITHUB_TOKEN", "")

def gh_headers():
    h = {"Accept": "application/vnd.github+json"}
    if TOKEN:
        h["Authorization"] = f"Bearer {TOKEN}"
    return h

def gh_get(path, params=None):
    r = requests.get(f"{GITHUB_API}{path}", headers=gh_headers(), params=params, timeout=10)
    if r.status_code == 404:
        return None, "Repository not found"
    if r.status_code == 403:
        return None, "GitHub rate limit exceeded. Set GITHUB_TOKEN."
    if not r.ok:
        return None, f"GitHub API error {r.status_code}"
    return r.json(), None

def repo_param():
    repo = request.args.get("repo", "").strip()
    if not repo or len(repo.split("/")) != 2:
        return None, "Missing or invalid ?repo=owner/repo"
    return repo, None

@app.route("/api/repo/info")
def repo_info():
    repo, err = repo_param()
    if err: return jsonify({"error": err}), 400
    data, err = gh_get(f"/repos/{repo}")
    if err: return jsonify({"error": err}), 404
    return jsonify({
        "name": data["full_name"],
        "description": data.get("description", ""),
        "stars": data["stargazers_count"],
        "forks": data["forks_count"],
        "open_issues": data["open_issues_count"],
        "language": data.get("language"),
        "license": data["license"]["spdx_id"] if data.get("license") else None,
        "default_branch": data["default_branch"],
        "created_at": data["created_at"],
        "updated_at": data["updated_at"],
        "html_url": data["html_url"],
    })

@app.route("/api/repo/commits")
def repo_commits():
    repo, err = repo_param()
    if err: return jsonify({"error": err}), 400
    data, err = gh_get(f"/repos/{repo}/commits", params={"per_page": 30})
    if err: return jsonify({"error": err}), 404
    commits = []
    for c in data:
        commit_info = c.get("commit", {})
        author_info = commit_info.get("author", {})
        commits.append({
            "sha": c["sha"],
            "message": commit_info.get("message", ""),
            "author": author_info.get("name", "unknown"),
            "date": author_info.get("date", ""),
        })
    return jsonify(commits)

@app.route("/api/repo/branches")
def repo_branches():
    repo, err = repo_param()
    if err: return jsonify({"error": err}), 400
    data, err = gh_get(f"/repos/{repo}/branches", params={"per_page": 50})
    if err: return jsonify({"error": err}), 404
    return jsonify([{"name": b["name"]} for b in data])

@app.route("/api/repo/contributors")
def repo_contributors():
    repo, err = repo_param()
    if err: return jsonify({"error": err}), 400
    data, err = gh_get(f"/repos/{repo}/contributors", params={"per_page": 20})
    if err: return jsonify({"error": err}), 404
    return jsonify([{
        "login": c["login"],
        "avatar": c["avatar_url"],
        "contributions": c["contributions"],
        "profile": c["html_url"],
    } for c in data])

@app.route("/api/repo/tree")
def repo_tree():
    repo, err = repo_param()
    if err: return jsonify({"error": err}), 400

    # Get default branch
    info, err = gh_get(f"/repos/{repo}")
    if err: return jsonify({"error": err}), 404
    branch = info["default_branch"]

    # Get full recursive tree
    data, err = gh_get(f"/repos/{repo}/git/trees/{branch}", params={"recursive": "1"})
    if err: return jsonify({"error": err}), 404

    tree = data.get("tree", [])
    # Limit to 300 nodes to keep graph usable
    items = [{"path": item["path"], "type": item["type"], "size": item.get("size", 0)}
             for item in tree[:300]]
    return jsonify({"tree": items, "truncated": data.get("truncated", False)})

@app.route("/health")
def health():
    return jsonify({"status": "ok"})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=False)