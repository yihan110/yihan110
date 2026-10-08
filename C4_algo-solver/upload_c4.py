#!/usr/bin/env python3
"""upload_c4.py — 通过 api.github.com (Git Data API) 把本地 C4_algo-solver 内容
以单次 commit 推送到公开仓库 yihan110/yihan110 的 C4_algo-solver/ 子目录。
不覆盖仓库已有文件。Token 从环境变量 GH_STORED_PW 读取。"""
import base64
import json
import os
import sys
import urllib.request

REPO = "yihan110/yihan110"
BRANCH = "main"
LOCAL_ROOT = r"C:\Users\lucky\Doubao\chats\2026-10-08\new-chat\C4_algo-solver"
PREFIX = "C4_algo-solver"          # 目标子目录
IGNORE = {".git"}

API = "https://api.github.com"
token = os.environ.get("GH_STORED_PW", "").strip()
if not token:
    print("NO_TOKEN"); sys.exit(1)
HEADERS = {"Authorization": f"token {token}", "User-Agent": "doubao-agent",
           "Accept": "application/vnd.github+json"}


def api(method, path, payload=None):
    url = API + path
    data = json.dumps(payload).encode("utf-8") if payload is not None else None
    req = urllib.request.Request(url, data=data, headers=HEADERS, method=method)
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            return json.loads(r.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", "replace")
        print(f"HTTP {e.code} {method} {path}: {body[:300]}")
        raise


def collect_files():
    files = []
    for root, dirs, names in os.walk(LOCAL_ROOT):
        dirs[:] = [d for d in dirs if d not in IGNORE]
        for n in sorted(names):
            full = os.path.join(root, n)
            rel = os.path.relpath(full, LOCAL_ROOT).replace(os.sep, "/")
            files.append((PREFIX + "/" + rel, full))
    return files


def main():
    head = api("GET", f"/repos/{REPO}/branches/{BRANCH}")["commit"]["sha"]
    print("head:", head)

    files = collect_files()
    print(f"files to upload: {len(files)}")

    # 1. create blobs
    tree_entries = []
    for path, full in files:
        with open(full, "rb") as f:
            content = base64.b64encode(f.read()).decode("ascii")
        blob = api("POST", f"/repos/{REPO}/git/blobs",
                   {"content": content, "encoding": "base64"})
        tree_entries.append({"path": path, "mode": "100644",
                             "type": "blob", "sha": blob["sha"]})
        print("blob ok:", path)

    # 2. create tree
    tree = api("POST", f"/repos/{REPO}/git/trees",
               {"base_tree": head, "tree": tree_entries})
    tree_sha = tree["sha"]

    # 3. create commit
    commit = api("POST", f"/repos/{REPO}/git/commits", {
        "message": "C4 skill sharing: algo-solver (verified algorithm problem solver) by Ruan Yihan",
        "tree": tree_sha,
        "parents": [head],
    })
    commit_sha = commit["sha"]
    print("commit:", commit_sha)

    # 4. update ref
    api("PATCH", f"/repos/{REPO}/git/refs/heads/{BRANCH}", {"sha": commit_sha, "force": False})
    print("SUCCESS -> branch updated to", commit_sha)


if __name__ == "__main__":
    main()
