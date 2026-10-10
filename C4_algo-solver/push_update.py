#!/usr/bin/env python3
"""push_update.py — 通过 api.github.com 更新 C4_algo-solver 内容：
更新 README.md 并新增两个真题演示目录（demo_pat1009 / demo_range_sum）。
基于当前 main HEAD 追加一个 commit，不覆盖已有文件。"""
import base64
import json
import os
import sys
import urllib.request

REPO = "yihan110/yihan110"
BRANCH = "main"
LOCAL_ROOT = r"C:\Users\lucky\Doubao\chats\2026-10-08\new-chat\C4_algo-solver"
PREFIX = "C4_algo-solver"
API = "https://api.github.com"
token = os.environ.get("GH_STORED_PW", "").strip()
if not token:
    print("NO_TOKEN"); sys.exit(1)
HEADERS = {"Authorization": f"token {token}", "User-Agent": "doubao-agent",
           "Accept": "application/vnd.github+json"}

# 需要新增/更新的文件（相对 LOCAL_ROOT）
UPDATES = [
    "README.md",
    "demo_pat1009/solution.py",
    "demo_pat1009/tests/1.in", "demo_pat1009/tests/1.out",
    "demo_pat1009/tests/2.in", "demo_pat1009/tests/2.out",
    "demo_pat1009/tests/3.in", "demo_pat1009/tests/3.out",
    "demo_range_sum/solution.py",
    "demo_range_sum/tests/1.in", "demo_range_sum/tests/1.out",
    "demo_range_sum/tests/2.in", "demo_range_sum/tests/2.out",
    "demo_range_sum/tests/3.in", "demo_range_sum/tests/3.out",
]


def api(method, path, payload=None):
    url = API + path
    data = json.dumps(payload).encode("utf-8") if payload is not None else None
    req = urllib.request.Request(url, data=data, headers=HEADERS, method=method)
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            return json.loads(r.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        print(f"HTTP {e.code} {method} {path}: {e.read().decode('utf-8','replace')[:300]}")
        raise


def main():
    head = api("GET", f"/repos/{REPO}/branches/{BRANCH}")["commit"]["sha"]
    print("head:", head)
    tree_entries = []
    for rel in UPDATES:
        full = os.path.join(LOCAL_ROOT, rel)
        with open(full, "rb") as f:
            content = base64.b64encode(f.read()).decode("ascii")
        blob = api("POST", f"/repos/{REPO}/git/blobs",
                   {"content": content, "encoding": "base64"})
        tree_entries.append({"path": PREFIX + "/" + rel.replace(os.sep, "/"),
                             "mode": "100644", "type": "blob", "sha": blob["sha"]})
        print("blob ok:", rel)

    tree = api("POST", f"/repos/{REPO}/git/trees",
               {"base_tree": head, "tree": tree_entries})
    commit = api("POST", f"/repos/{REPO}/git/commits", {
        "message": "Add real PAT/range-sum verification demos and update README",
        "tree": tree["sha"], "parents": [head],
    })
    api("PATCH", f"/repos/{REPO}/git/refs/heads/{BRANCH}", {"sha": commit["sha"], "force": False})
    print("SUCCESS ->", commit["sha"])


if __name__ == "__main__":
    main()
