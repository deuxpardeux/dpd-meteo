#!/usr/bin/env python3
"""Flag AI calls that bypass LiteLLM (Zac t3907u, 2026-11-14). Standard library only,
so the same file runs in every repo's CI.

Every API-key AI call in our code must go through the LiteLLM gateway, so spend,
caps and the ledger see it. This lint finds direct provider SDK imports and direct
provider HTTP endpoints. It does not flag:
- billing / usage / admin reads (they are not model calls): ``usage_report``,
  ``/organization/costs``, ``/organization/usage``, ``/v1/key``, ``/credits``,
  ``/user/balance``, ``management-api``, ``/v1/user/subscription`` ...
- the gateway itself (``cloud/litellm/``) and tests/fixtures
- a file that points the SDK at the gateway (``LITELLM`` base URL in the same file)
- lines with ``# litellm-bypass-ok: <reason>`` and paths in ``.ai-bypass-allow``
  (one ``path  # reason`` per line)

Subscription apps (ChatGPT, Claude, Grok Bot, Cursor, Perplexity, Higgsfield,
ElevenLabs) are not API-key calls; they stay on admin APIs or browser reads.

Exit code: 0 in --warn mode; in --max N mode, 1 when more than N bypasses remain
(a ratchet: lower N as files move to the gateway).
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
from pathlib import Path

EXTS = {".py", ".js", ".mjs", ".cjs", ".ts", ".tsx", ".sh", ".gs", ".ps1"}
SKIP_DIRS = {".git", "node_modules", "dist", "build", ".venv", "venv", "__pycache__", ".next",
             "vendor", "site-packages", "reports", "qa"}
SKIP_PATH_RE = re.compile(r"(^|/)(tests?|__tests__|fixtures|cloud/litellm)(/|$)|(^|/)test_[^/]+$|\.test\.[jt]sx?$|\.spec\.[jt]sx?$")
SDK_RES = [
    ("openai-sdk", re.compile(r"^\s*(?:from\s+openai\b|import\s+openai\b)|require\(['\"]openai['\"]\)|from\s+['\"]openai['\"]")),
    ("anthropic-sdk", re.compile(r"^\s*(?:from\s+anthropic\b|import\s+anthropic\b)|require\(['\"]@anthropic-ai/sdk['\"]\)|from\s+['\"]@anthropic-ai/sdk['\"]")),
    ("gemini-sdk", re.compile(r"^\s*(?:from\s+google\s+import\s+genai|import\s+google\.generativeai|from\s+google\.genai|from\s+google\.generativeai)|['\"]@google/(?:genai|generative-ai)['\"]")),
    ("mistral-sdk", re.compile(r"^\s*(?:from\s+mistralai\b|import\s+mistralai\b)|['\"]@mistralai/mistralai['\"]")),
    ("xai-sdk", re.compile(r"^\s*(?:from\s+xai_sdk\b|import\s+xai_sdk\b)")),
    ("groq-sdk", re.compile(r"^\s*(?:from\s+groq\b|import\s+groq\b)")),
]
HTTP_RE = re.compile(
    r"https?://(?:api\.openai\.com|api\.anthropic\.com|api\.x\.ai|generativelanguage\.googleapis\.com|"
    r"api\.mistral\.ai|openrouter\.ai/api|api\.deepseek\.com|api\.moonshot\.(?:ai|cn)|api\.perplexity\.ai|"
    r"dashscope(?:-intl)?\.aliyuncs\.com|api\.groq\.com|api\.together\.xyz|api\.fireworks\.ai)[^\s'\"`)]*")
NON_MODEL = re.compile(
    r"usage_report|/organizations?/(?:costs|usage|users|me|api_keys|invites|workspaces)|/v1/organization/|"
    r"/v1/key\b|/credits\b|/user/balance|users/me/balance|management-api|/v1/models\b|/v1/user/subscription|"
    r"/v1/dashboard|/auth/|/v1/files\b|/billing|cost_report|/models(?:\?|$|['\"])|language-models|image-generation-models|/v1beta/models\?")
GATEWAY_HINT = re.compile(r"LITELLM|dpd-litellm|litellm_proxy|LITELLM_BASE_URL|LITELLM_URL")
OK_COMMENT = re.compile(r"litellm-bypass-ok:\s*\S")


def _allow(root: Path) -> set[str]:
    path = root / ".ai-bypass-allow"
    if not path.exists():
        return set()
    out = set()
    for line in path.read_text(encoding="utf-8").splitlines():
        entry = line.split("#", 1)[0].strip()
        if entry:
            out.add(entry)
    return out


def scan(root: Path) -> list[dict]:
    root = root.resolve()
    allow = _allow(root)
    found = []
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS and not d.startswith(".")]
        for name in filenames:
            path = Path(dirpath) / name
            if path.suffix not in EXTS:
                continue
            rel = path.relative_to(root).as_posix()
            if SKIP_PATH_RE.search(rel) or rel in allow or any(rel.startswith(a.rstrip("/") + "/") for a in allow if a.endswith("/")):
                continue
            try:
                text = path.read_text(encoding="utf-8", errors="replace")
            except OSError:
                continue
            if len(text) > 2_000_000:
                continue
            via_gateway = bool(GATEWAY_HINT.search(text))
            for number, line in enumerate(text.splitlines(), 1):
                if OK_COMMENT.search(line):
                    continue
                for kind, rx in SDK_RES:
                    if rx.search(line) and not via_gateway:
                        found.append({"path": rel, "line": number, "kind": kind, "text": line.strip()[:160]})
                for match in HTTP_RE.finditer(line):
                    if NON_MODEL.search(match.group(0)) or NON_MODEL.search(line):
                        continue
                    if via_gateway and "base_url" in line.lower():
                        continue
                    found.append({"path": rel, "line": number, "kind": "provider-http", "text": match.group(0)[:160]})
    return found


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("root", nargs="?", default=".")
    parser.add_argument("--warn", action="store_true", help="print GitHub warnings, never fail")
    parser.add_argument("--max", type=int, default=None, help="fail when more than this many remain")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)
    found = scan(Path(args.root))
    files = sorted({f["path"] for f in found})
    if args.json:
        print(json.dumps({"bypasses": len(found), "files": len(files), "items": found}, indent=1))
    else:
        for item in found:
            prefix = "::warning " if args.warn or os.environ.get("GITHUB_ACTIONS") else ""
            print(f"{prefix}file={item['path']},line={item['line']}::LiteLLM bypass ({item['kind']}): {item['text']}"
                  if prefix else f"{item['path']}:{item['line']}: {item['kind']}: {item['text']}")
        print(f"LiteLLM bypasses: {len(found)} in {len(files)} files")
    if args.max is not None and len(found) > args.max:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
