#!/usr/bin/env python3
"""
RAG Corpus Builder: pandas docs + resolved issues → intelligent chunks (by header).

Intelligent chunking:
- For Markdown (.md): split by headings (##, ###, etc.).
- For reStructuredText (.rst): split by headings (=====, -----, ~~~~~, ^^^^^).
- Each heading + its content becomes a chunk (preserving hierarchy).
- Issues are single chunks (since they're atomic).
- Metadata includes source (doc/issue), path/issue number, and heading chain.

Output: JSONL file where each line is {"text": "...", "metadata": {...}}

Usage:
    python scripts/build_rag_corpus.py --issues-dir data/rag_corpus --output data/rag_corpus/chunks.jsonl
"""

import argparse
import json
import os
import re
import subprocess
import tempfile
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from urllib.parse import urlparse

import requests

# ----------------------------------------------------------------------------
# CONFIGURATION
# ----------------------------------------------------------------------------
PANDAS_DOCS_REPO = "https://github.com/pandas-dev/pandas.git"
PANDAS_DOCS_PATH_IN_REPO = "doc/source"  # relative to repo root
ALLOWED_DOC_EXTENSIONS = {".rst", ".md"}

# Headers in Markdown: lines starting with 1-6 #
MARKDOWN_HEADER_PATTERN = re.compile(r"^(#{1,6})\s+(.*)$")

# Headers in reStructuredText:
# Level 1: ===== above and below
# Level 2: -----
# Level 3: ~~~~~
# Level 4: ^^^^^
# We'll detect lines that are entirely =, -, ~, ^ of length >= 3 and the previous line is text.
RST_HEADER_PATTERN = re.compile(r"^(=+|-+|~+|\^+)$")


# ----------------------------------------------------------------------------
# DOCUMENTATION FETCHING
# ----------------------------------------------------------------------------
def fetch_pandas_docs(output_dir: Path, use_local_repo: Optional[Path] = None) -> Path:
    """
    Get pandas documentation source files.

    If use_local_repo is provided, copy from there. Otherwise, clone the repo into a temp dir.

    Args:
        output_dir: Directory to store the documentation (will be created).
        use_local_repo: Optional path to an existing pandas clone.

    Returns:
        Path to the directory containing documentation (doc/source/).
    """
    if use_local_repo and use_local_repo.exists():
        print(f"[DOCS] Using local repo at {use_local_repo}")
        src_docs = use_local_repo / PANDAS_DOCS_PATH_IN_REPO
        if not src_docs.exists():
            raise FileNotFoundError(f"Local repo does not have {PANDAS_DOCS_PATH_IN_REPO}")
        # Copy to output_dir
        output_docs_dir = output_dir / "pandas_docs"
        if output_docs_dir.exists():
            print(f"[DOCS] Removing existing {output_docs_dir}")
            subprocess.run(["rm", "-rf", str(output_docs_dir)], check=True)
        subprocess.run(["cp", "-r", str(src_docs), str(output_docs_dir)], check=True)
        return output_docs_dir
    else:
        # Clone into a temporary directory
        print("[DOCS] Cloning pandas repository (this may take a minute)...")
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)
            subprocess.run(
                ["git", "clone", "--depth", "1", "--filter=blob:none", PANDAS_DOCS_REPO, str(tmpdir_path)],
                check=True,
                capture_output=True,
            )
            src_docs = tmpdir_path / PANDAS_DOCS_PATH_IN_REPO
            # Copy to output_dir (persist)
            output_docs_dir = output_dir / "pandas_docs"
            if output_docs_dir.exists():
                subprocess.run(["rm", "-rf", str(output_docs_dir)], check=True)
            subprocess.run(["cp", "-r", str(src_docs), str(output_docs_dir)], check=True)
        return output_docs_dir


# ----------------------------------------------------------------------------
# PARSING & CHUNKING
# ----------------------------------------------------------------------------
def read_text_file(file_path: Path) -> str:
    """Read file as UTF-8 text, ignoring errors."""
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            return f.read()
    except UnicodeDecodeError:
        # Fallback to latin-1 if UTF-8 fails
        with open(file_path, "r", encoding="latin-1") as f:
            return f.read()


def chunk_markdown(content: str, source_path: str) -> List[Dict]:
    """
    Split Markdown content into chunks by headings.

    Returns list of dicts: {"text": chunk_text, "metadata": {"header_chain": [...], "source": ...}}
    """
    lines = content.split("\n")
    chunks = []
    current_header_chain = []
    current_content_lines = []

    for i, line in enumerate(lines):
        match = MARKDOWN_HEADER_PATTERN.match(line)
        if match:
            # Save previous chunk if any
            if current_content_lines:
                chunk_text = "\n".join(current_content_lines).strip()
                if chunk_text:
                    chunks.append({
                        "text": chunk_text,
                        "metadata": {
                            "source": source_path,
                            "header_chain": current_header_chain.copy(),
                            "type": "doc"
                        }
                    })
            # Start new chunk with this header
            level = len(match.group(1))
            header_text = match.group(2).strip()
            # Update header chain (trim deeper levels)
            current_header_chain = current_header_chain[:level-1] + [header_text]
            current_content_lines = [line]
        else:
            current_content_lines.append(line)

    # Final chunk
    if current_content_lines:
        chunk_text = "\n".join(current_content_lines).strip()
        if chunk_text:
            chunks.append({
                "text": chunk_text,
                "metadata": {
                    "source": source_path,
                    "header_chain": current_header_chain.copy(),
                    "type": "doc"
                }
            })
    return chunks


def chunk_rst(content: str, source_path: str) -> List[Dict]:
    """
    Split reStructuredText content into chunks by headings.

    RST headings: a line of text, then a line of =, -, ~, ^ (or the same above and below).
    We detect both styles.
    """
    lines = content.split("\n")
    chunks = []
    current_header_chain = []
    current_content_lines = []
    i = 0
    n = len(lines)

    while i < n:
        line = lines[i]
        # Check if line is a heading underline (or overline+underline)
        if RST_HEADER_PATTERN.match(line):
            # This could be an underline; previous line is the heading text
            if i > 0:
                heading_text = lines[i-1].strip()
                if heading_text:  # valid heading
                    # Save previous chunk
                    if current_content_lines:
                        chunk_text = "\n".join(current_content_lines).strip()
                        if chunk_text:
                            chunks.append({
                                "text": chunk_text,
                                "metadata": {
                                    "source": source_path,
                                    "header_chain": current_header_chain.copy(),
                                    "type": "doc"
                                }
                            })
                    # Determine level based on character
                    char = line[0]
                    level = {"=": 1, "-": 2, "~": 3, "^": 4}.get(char, 5)
                    # Update header chain
                    current_header_chain = current_header_chain[:level-1] + [heading_text]
                    current_content_lines = [heading_text, line]  # start new chunk
                    i += 1
                    continue
        # Regular line
        current_content_lines.append(line)
        i += 1

    # Final chunk
    if current_content_lines:
        chunk_text = "\n".join(current_content_lines).strip()
        if chunk_text:
            chunks.append({
                "text": chunk_text,
                "metadata": {
                    "source": source_path,
                    "header_chain": current_header_chain.copy(),
                    "type": "doc"
                }
            })
    return chunks


def process_docs_directory(docs_dir: Path) -> List[Dict]:
    """Recursively walk docs_dir, parse all .rst/.md files, and return chunks."""
    all_chunks = []
    for file_path in docs_dir.rglob("*"):
        if file_path.suffix in ALLOWED_DOC_EXTENSIONS:
            rel_path = str(file_path.relative_to(docs_dir.parent))
            content = read_text_file(file_path)
            if file_path.suffix == ".md":
                chunks = chunk_markdown(content, rel_path)
            else:  # .rst
                chunks = chunk_rst(content, rel_path)
            all_chunks.extend(chunks)
    return all_chunks


def process_issues(issues_jsonl_path: Path) -> List[Dict]:
    """Load issues from JSONL, each issue becomes one chunk."""
    chunks = []
    with open(issues_jsonl_path, "r") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            issue = json.loads(line)
            # Combine cleaned title and body
            text = f"Title: {issue.get('cleaned_title', '')}\n\nBody: {issue.get('cleaned_body', '')}"
            text = text.strip()
            if not text:
                continue
            chunks.append({
                "text": text,
                "metadata": {
                    "source": f"issue_{issue.get('number', 'unknown')}",
                    "issue_number": issue.get("number"),
                    "html_url": issue.get("html_url"),
                    "type": "issue",
                    "labels": [lbl["name"] for lbl in issue.get("labels", [])],
                    "class": issue.get("class"),  # may be None
                }
            })
    return chunks


# ----------------------------------------------------------------------------
# MAIN
# ----------------------------------------------------------------------------
def main():
    parser = argparse.ArgumentParser(description="Build RAG corpus from pandas docs and resolved issues.")
    parser.add_argument("--issues-dir", type=Path, required=True,
                        help="Directory containing rag_corpus/issues.jsonl (from process_issues.py)")
    parser.add_argument("--output", type=Path, required=True,
                        help="Output JSONL file path (e.g., data/rag_corpus/chunks.jsonl)")
    parser.add_argument("--docs-dir", type=Path, default=None,
                        help="Optional: Path to an existing pandas repo clone (to avoid cloning).")
    args = parser.parse_args()

    issues_file = args.issues_dir / "issues.jsonl"
    if not issues_file.exists():
        print(f"ERROR: Issues file not found at {issues_file}")
        return 1

    # Create output directory
    args.output.parent.mkdir(parents=True, exist_ok=True)

    # Fetch or copy docs
    temp_docs_parent = Path(tempfile.mkdtemp(prefix="pandas_docs_"))
    docs_source_dir = fetch_pandas_docs(temp_docs_parent, use_local_repo=args.docs_dir)
    print(f"[DOCS] Documentation source ready at {docs_source_dir}")

    # Process docs
    print("[CHUNKING] Processing documentation...")
    doc_chunks = process_docs_directory(docs_source_dir)
    print(f"[DOCS] Generated {len(doc_chunks)} doc chunks")

    # Process issues
    print("[CHUNKING] Processing issues...")
    issue_chunks = process_issues(issues_file)
    print(f"[ISSUES] Generated {len(issue_chunks)} issue chunks")

    # Combine and write
    all_chunks = doc_chunks + issue_chunks
    with open(args.output, "w") as f:
        for chunk in all_chunks:
            f.write(json.dumps(chunk) + "\n")

    print(f"\n[DONE] Wrote {len(all_chunks)} total chunks to {args.output}")
    print(f"  - Doc chunks: {len(doc_chunks)}")
    print(f"  - Issue chunks: {len(issue_chunks)}")

    # Clean up temporary docs copy (optional, but we created it)
    subprocess.run(["rm", "-rf", str(temp_docs_parent)], check=False)

    return 0


if __name__ == "__main__":
    exit(main())