#!/usr/bin/env python3
"""push_docs.py — 更新仓库中的 skill说明 与 AI日志（追加真实真题验证）。"""
import base64, json, os, sys, urllib.request

REPO = "yihan110/yihan110"
LOCAL_ROOT = r"C:\Users\lucky\Doubao\chats\2026-10-08\new-chat\C4_algo-solver"
PREFIX = "C4_algo-solver"
API = "https://api.github.com"
token = os.environ.get("GH_STORED_PW", "").strip()
if not token:
    print("NO_TOKEN"); sys.exit(1)
HEADERS = {"Authorization": f"token {token}", "User-Agent": "doubao-agent",
           "Accept": "application/vnd.github+json"}
UPDATES = ["阮依涵_C4_skill说明.md", "阮依涵_C4_AI日志.md"]


def api(method, path, payload=None):
    data = json.dumps(payload).encode("utf-8") if payload is not None else None
    req = urllib.request.Request(API + path, data=data, headers=HEADERS, method=method)
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            return json.loads(r.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        print(f"HTTP {e.code}: {e.read().decode('utf-8','replace')[:300]}")
        raise


def main():
    head = api("GET", f"/repos/{REPO}/branches/main")["commit"]["sha"]
    entries = []
    for rel in UPDATES:
        with open(os.path.join(LOCAL_ROOT, rel), "rb") as f:
            b64 = base64.b64encode(f.read()).decode("ascii")
        blob = api("POST", f"/repos/{REPO}/git/blobs", {"content": b64, "encoding": "base64"})
        entries.append({"path": PREFIX + "/" + rel, "mode": "100644",
                        "type": "blob", "sha": blob["sha"]})
        print("blob ok:", rel)
    tree = api("POST", f"/repos/{REPO}/git/trees", {"base_tree": head, "tree": entries})
    commit = api("POST", f"/repos/{REPO}/git/commits", {
        "message": "Append real PAT/range-sum verification to skill doc and AI log",
        "tree": tree["sha"], "parents": [head]})
    api("PATCH", f"/repos/{REPO}/git/refs/heads/main", {"sha": commit["sha"], "force": False})
    print("SUCCESS ->", commit["sha"])


if __name__ == "__main__":
    main()
