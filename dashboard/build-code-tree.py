#!/usr/bin/env python3
"""dashboard/build-code-tree.py — embed repo text files into code.json.

The Code mode of the dashboard is offline-capable: it reads dashboard/code.json
which contains the path + full text content of every meaningful text file in
the repo. Excludes: gitignored content, mockup, PII-bearing data, binaries.

Run:
    python3 dashboard/build-code-tree.py
"""
from __future__ import annotations
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'dashboard' / 'code.json'

# Files / dirs to skip
SKIP_DIRS = {
    '.git', '.github', '__pycache__', '.venv', 'venv', 'node_modules',
    'data/raw', 'data/staging',     # gitignored regenerable / PII
    'dashboard/mockup',             # claude-design export, internal-ref only
    'reference-artifacts',          # internal-only (and was deleted)
    'examples', 'outputs',          # leftover from starter kit; not portfolio
    'sync', 'workflows', 'playbooks',  # starter-kit leftovers
    'skills/tier-b-news',           # uncommitted (CSE-blocked / pivoted to OSHA)
    'skills/tier-b-techstack',      # uncommitted (vendor-scrape yield-limited)
    'skills/account-research', 'skills/icp-scoring',          # starter-kit generic skills
    'skills/signal-to-sequence', 'skills/weekly-update',
    'skills/setup',
}
SKIP_FILES_EXTRA = {'ARTICLE.md'}  # generic starter-kit article

# Skip Tier-C LinkedIn scrape outputs from the public code.json (PII per CLAUDE.md)
SKIP_FILE_PREFIXES = (
    'documents/qso-briefs/auto/linkedin-',
    'documents/qso-briefs/auto/buying-committee-',
)
SKIP_FILE_PATTERNS = {
    '.DS_Store', '.gitkeep', '.env', '.env.example',
    'tam.csv', 'tam_scored.csv', 'tam.json',  # PII / large
    'data.json', 'code.json',                  # dashboard self-refs
    'source-map.tldraw.js', 'source-map.svg',   # binary-ish or huge
}
# Extensions we treat as embeddable text
TEXT_EXTS = {'.md', '.py', '.csv', '.html', '.yaml', '.yml', '.txt', '.gitignore', '.toml'}
# Hard cap per file to avoid blowing up payload (mandates.csv at ~7KB is fine; bigger CSVs skipped)
MAX_BYTES = 80_000

def should_skip_path(rel: Path) -> bool:
    parts = rel.parts
    for d in SKIP_DIRS:
        d_parts = tuple(d.split('/'))
        if len(parts) >= len(d_parts) and parts[:len(d_parts)] == d_parts:
            return True
    if rel.name in SKIP_FILE_PATTERNS or rel.name in SKIP_FILES_EXTRA:
        return True
    rel_str = str(rel).replace('\\', '/')
    if any(rel_str.startswith(p) for p in SKIP_FILE_PREFIXES):
        return True
    return False

def is_text_file(p: Path) -> bool:
    if p.suffix.lower() in TEXT_EXTS:
        return True
    if p.name in ('.gitignore', 'CLAUDE.md', 'RUNBOOK.md', 'README.md', 'Makefile'):
        return True
    return False

def collect_files() -> list[dict]:
    out = []
    for p in sorted(ROOT.rglob('*')):
        if not p.is_file():
            continue
        rel = p.relative_to(ROOT)
        if should_skip_path(rel):
            continue
        if not is_text_file(p):
            continue
        try:
            content = p.read_text(encoding='utf-8', errors='replace')
        except OSError:
            continue
        if len(content.encode('utf-8')) > MAX_BYTES:
            # truncate with a marker
            content = content[:MAX_BYTES // 2] + '\n\n... [truncated for dashboard payload — see GitHub for full file] ...\n'
        out.append({
            'path': str(rel).replace('\\', '/'),
            'size': len(content),
            'ext': p.suffix.lstrip('.').lower(),
            'content': content,
        })
    return out

def build_tree(files: list[dict]) -> dict:
    """Build a nested dict tree from file paths for sidebar rendering."""
    tree: dict = {'_dirs': {}, '_files': []}
    for f in files:
        parts = f['path'].split('/')
        cur = tree
        for part in parts[:-1]:
            cur = cur['_dirs'].setdefault(part, {'_dirs': {}, '_files': []})
        cur['_files'].append({'name': parts[-1], 'path': f['path'], 'ext': f['ext'], 'size': f['size']})
    return tree

def main():
    files = collect_files()
    tree = build_tree(files)
    payload = {
        'tree': tree,
        'files': {f['path']: f['content'] for f in files},
        'meta': {'count': len(files), 'total_bytes': sum(f['size'] for f in files)},
    }
    OUT.write_text(json.dumps(payload, separators=(',', ':')))
    kb = OUT.stat().st_size / 1024
    print(f'wrote {OUT.relative_to(ROOT)}  ({len(files)} files, {kb:,.0f} KB)')
    # show top files by size
    files_sorted = sorted(files, key=lambda f: -f['size'])
    print(f'  top 10 files by size:')
    for f in files_sorted[:10]:
        print(f"    {f['size']:>7} B  {f['path']}")

if __name__ == '__main__':
    main()
