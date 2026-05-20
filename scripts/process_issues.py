#!/usr/bin/env python3
"""
Data processing script for classification and RAG corpus preparation.

Loads closed GitHub issues from JSONL, cleans text, maps labels to categories,
and creates train/val/test splits with temporal stratification.

Usage:
    python process_issues.py --input data/pandas_closed_issues.jsonl --output-dir data/
"""

import argparse
import json
import logging
import re
import sys
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


# ============================================================================
# CONFIGURATION
# ============================================================================

# Label mapping: pandas label -> class
# Customize this dictionary to map your labels to bug/feature/docs/question
# Priority (if multiple labels on same issue): bug > feature > docs > question
LABEL_MAP = {
    # Bug-related labels
    "Bug": "bug",
    "bug": "bug",
    "Defect": "bug",
    "defect": "bug",
    "Regression": "bug",
    "regression": "bug",
    "Performance": "bug",
    "performance": "bug",
    "Memory leak": "bug",
    "memory leak": "bug",
    "Crash": "bug",
    "crash": "bug",
    "Error": "bug",
    "error": "bug",
    "TypeError": "bug",
    "ValueError": "bug",
    "IndexError": "bug",
    "KeyError": "bug",
    # Feature-related labels
    "Enhancement": "feature",
    "enhancement": "feature",
    "Feature Request": "feature",
    "feature request": "feature",
    "New feature": "feature",
    "new feature": "feature",
    "API redesign": "feature",
    "api redesign": "feature",
    "Feature": "feature",
    "feature": "feature",
    "Request": "feature",
    "request": "feature",
    # Documentation-related labels
    "Docs": "docs",
    "docs": "docs",
    "Documentation": "docs",
    "documentation": "docs",
    "Website": "docs",
    "website": "docs",
    "Doc": "docs",
    "doc": "docs",
    # Question-related labels
    "Question": "question",
    "question": "question",
    "Help": "question",
    "help": "question",
    "User question": "question",
    "user question": "question",
    "Usage Question": "question",
    "usage question": "question",
    "Discussion": "question",
    "discussion": "question",
}

# Text cleaning configuration
REMOVE_CODE_BLOCKS = False  # Set to True to remove markdown code blocks
MIN_TEXT_LENGTH = 5  # Minimum cleaned text length to keep an issue

# Split ratios (70/15/15)
TRAIN_RATIO = 0.70
VAL_RATIO = 0.15
TEST_RATIO = 0.15


# ============================================================================
# LOGGING SETUP
# ============================================================================

def setup_logging(log_file: Path) -> None:
    """
    Configure logging to file and console.

    Args:
        log_file: Path to log file
    """
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(levelname)s - %(message)s",
        handlers=[
            logging.FileHandler(log_file),
            logging.StreamHandler(sys.stdout),
        ],
    )


# ============================================================================
# TEXT CLEANING
# ============================================================================

def remove_non_ascii(text: str) -> str:
    """
    Remove non-ASCII characters, replacing with space.

    Args:
        text: Input text

    Returns:
        Text with non-ASCII chars replaced by spaces
    """
    if not text:
        return ""
    return "".join(char if ord(char) < 128 else " " for char in text)


def remove_code_blocks(text: str) -> str:
    """
    Remove markdown code blocks (``` ... ```).

    Args:
        text: Input text

    Returns:
        Text with code blocks removed
    """
    if not text:
        return ""
    # Remove triple-backtick blocks
    text = re.sub(r"```[\s\S]*?```", " ", text)
    # Remove inline backticks
    text = re.sub(r"`[^`]*`", " ", text)
    return text


def remove_emails_and_mentions(text: str) -> str:
    """
    Remove email addresses and @mentions (but keep the word after @).

    Args:
        text: Input text

    Returns:
        Text with emails and mentions removed
    """
    if not text:
        return ""
    # Remove email addresses
    text = re.sub(r"\S+@\S+", " ", text)
    # Replace @mentions with just the word (remove the @)
    text = re.sub(r"@(\w+)", r"\1", text)
    return text


def normalize_whitespace(text: str) -> str:
    """
    Normalize whitespace: multiple spaces/newlines -> single space.

    Args:
        text: Input text

    Returns:
        Text with normalized whitespace
    """
    if not text:
        return ""
    # Replace multiple newlines/spaces with single space
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def clean_text(text: str) -> str:
    """
    Clean text comprehensively.

    Steps:
    1. Remove non-ASCII characters
    2. Optionally remove code blocks
    3. Remove email addresses and @mentions
    4. Normalize whitespace

    Args:
        text: Raw text to clean

    Returns:
        Cleaned text
    """
    if not text:
        return ""

    text = remove_non_ascii(text)
    if REMOVE_CODE_BLOCKS:
        text = remove_code_blocks(text)
    text = remove_emails_and_mentions(text)
    text = normalize_whitespace(text)

    return text


# ============================================================================
# ISSUE LOADING & FILTERING
# ============================================================================

def load_issues(jsonl_path: Path) -> List[Dict[str, Any]]:
    """
    Load issues from JSONL file, streaming to handle large files.

    Args:
        jsonl_path: Path to JSONL file

    Returns:
        List of issue dicts

    Raises:
        FileNotFoundError: If file doesn't exist
        IOError: If file can't be read
    """
    issues = []
    logging.info(f"Loading issues from {jsonl_path}...")

    if not jsonl_path.exists():
        logging.error(f"File not found: {jsonl_path}")
        raise FileNotFoundError(f"File not found: {jsonl_path}")

    try:
        with open(jsonl_path) as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    issue = json.loads(line)
                    issues.append(issue)
                except json.JSONDecodeError as e:
                    logging.warning(f"Skipping malformed JSON: {e}")

    except IOError as e:
        logging.error(f"Error reading file: {e}")
        raise

    logging.info(f"Loaded {len(issues)} total issues from file")
    return issues


def filter_prs_and_closed(
    issues: List[Dict[str, Any]],
) -> Tuple[List[Dict[str, Any]], int, int]:
    """
    Filter out pull requests and ensure all issues are closed.

    A PR is detected by the presence of the 'pull_request' key.

    Args:
        issues: List of issues

    Returns:
        Tuple of (filtered issues, num_prs_removed, num_open_removed)
    """
    filtered = []
    num_prs = 0
    num_open = 0

    for issue in issues:
        # Skip PRs: they have a 'pull_request' key in the API response
        if "pull_request" in issue:
            num_prs += 1
            continue

        # Double-check closed state
        if issue.get("state") != "closed":
            num_open += 1
            continue

        filtered.append(issue)

    logging.info(f"Filtered {num_prs} PRs and {num_open} open issues")
    return filtered, num_prs, num_open


# ============================================================================
# LABEL MAPPING
# ============================================================================

def map_issue_labels(issue: Dict[str, Any]) -> Optional[str]:
    """
    Map issue labels to one of: bug, feature, docs, question.

    Strategy:
    - If an issue has multiple labels, map all of them
    - If they map to different classes, use priority: bug > feature > docs > question
    - If no labels or none map, return None

    Args:
        issue: Issue dict with 'labels' key (list of label dicts)

    Returns:
        Mapped class string ('bug', 'feature', 'docs', 'question') or None if unmappable
    """
    labels = issue.get("labels", [])
    if not labels:
        return None

    # Collect all mapped classes from this issue's labels
    mapped_classes = set()
    for label in labels:
        label_name = label.get("name", "")
        if label_name in LABEL_MAP:
            mapped_classes.add(LABEL_MAP[label_name])

    if not mapped_classes:
        return None

    # Apply priority: bug > feature > docs > question
    priority_order = ["bug", "feature", "docs", "question"]
    for class_name in priority_order:
        if class_name in mapped_classes:
            return class_name

    # Fallback (shouldn't happen)
    return list(mapped_classes)[0]


def filter_and_map_labels(
    issues: List[Dict[str, Any]],
) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]], int, int]:
    """
    Filter issues by label mapping and separate for classification vs RAG.

    - Classification: only keep issues with valid class labels (bug/feature/docs/question)
    - RAG corpus: keep ALL closed, non-PR issues (including those without labels)

    Args:
        issues: List of closed, non-PR issues

    Returns:
        Tuple of:
        - classification_issues (with 'class' field added)
        - rag_issues (all issues, even without labels)
        - num_no_labels (issues with empty labels list)
        - num_unmappable (issues with labels but unmappable to our 4 classes)
    """
    classification_issues = []
    rag_issues = []  # All issues (including no-label and unmappable)
    num_no_labels = 0
    num_unmappable = 0

    for issue in issues:
        # All closed issues go to RAG corpus
        rag_issues.append(issue)

        # Check label status
        labels = issue.get("labels", [])
        if not labels:
            num_no_labels += 1
            continue

        # Try to map labels to a class
        mapped_class = map_issue_labels(issue)
        if mapped_class is None:
            num_unmappable += 1
            continue

        # Add class label and include in classification dataset
        issue["class"] = mapped_class
        classification_issues.append(issue)

    logging.info(
        f"Classification dataset: {len(classification_issues)} issues | "
        f"RAG corpus: {len(rag_issues)} issues | "
        f"Skipped (no labels): {num_no_labels} | "
        f"Skipped (unmappable): {num_unmappable}"
    )
    return classification_issues, rag_issues, num_no_labels, num_unmappable


# ============================================================================
# TEXT CLEANING & ENRICHMENT
# ============================================================================

def enrich_and_clean_issues(issues: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Clean text fields for all issues.

    Adds new fields: cleaned_title, cleaned_body.

    Args:
        issues: List of issues

    Returns:
        Issues with added cleaned_title and cleaned_body fields
    """
    for issue in issues:
        title = issue.get("title", "")
        body = issue.get("body")

        issue["cleaned_title"] = clean_text(title)
        issue["cleaned_body"] = clean_text(body) if body else ""

    return issues


# ============================================================================
# TEMPORAL SPLIT
# ============================================================================

def temporal_split(
    issues: List[Dict[str, Any]],
) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]], List[Dict[str, Any]]]:
    """
    Stratified temporal split into train/val/test (70/15/15).

    CRITICAL: Maintains BOTH:
    1. Temporal ordering: test > val > train (strictly by closed_at date)
    2. Class stratification: each split has similar class proportions to overall

    Strategy:
    - Group issues by class
    - For each class, sort by time and split into 70/15/15
    - Concatenate splits across classes

    This ensures realistic evaluation (newer test data) while maintaining class balance.

    Args:
        issues: List of issues (should all have 'closed_at' field and 'class')

    Returns:
        Tuple of (train_issues, val_issues, test_issues)
    """
    # Group issues by class
    issues_by_class = defaultdict(list)
    for issue in issues:
        class_label = issue.get("class", "unknown")
        issues_by_class[class_label].append(issue)

    train = []
    val = []
    test = []

    # For each class, do temporal split and collect
    for class_label, class_issues in issues_by_class.items():
        # Sort by closed_at within this class
        sorted_class_issues = sorted(class_issues, key=lambda x: x.get("closed_at", ""))

        n = len(sorted_class_issues)
        train_split = int(n * TRAIN_RATIO)
        val_split = int(n * (TRAIN_RATIO + VAL_RATIO))

        train.extend(sorted_class_issues[:train_split])
        val.extend(sorted_class_issues[train_split:val_split])
        test.extend(sorted_class_issues[val_split:])

        logging.info(
            f"Class '{class_label}': train={train_split}, val={val_split - train_split}, test={n - val_split}"
        )

    logging.info(
        f"Stratified temporal split: train={len(train)}, val={len(val)}, test={len(test)}"
    )

    # Log class distribution per split
    for split_name, split_data in [("train", train), ("val", val), ("test", test)]:
        class_counts = defaultdict(int)
        for issue in split_data:
            class_counts[issue.get("class", "unknown")] += 1
        logging.info(f"{split_name.upper()} class distribution: {dict(class_counts)}")

    # Log date ranges to verify temporal ordering
    if train:
        train_dates = sorted([x.get("closed_at", "") for x in train])
        logging.info(f"Train dates: {train_dates[0]} to {train_dates[-1]}")

    if val:
        val_dates = sorted([x.get("closed_at", "") for x in val])
        logging.info(f"Val dates: {val_dates[0]} to {val_dates[-1]}")

    if test:
        test_dates = sorted([x.get("closed_at", "") for x in test])
        logging.info(f"Test dates: {test_dates[0]} to {test_dates[-1]}")

    return train, val, test


# ============================================================================
# FILE OPERATIONS
# ============================================================================

def save_jsonl(issues: List[Dict[str, Any]], output_path: Path) -> None:
    """
    Save issues to JSONL file (one JSON object per line).

    Args:
        issues: List of issues
        output_path: Path to output file
    """
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with open(output_path, "w") as f:
        for issue in issues:
            f.write(json.dumps(issue) + "\n")

    logging.info(f"Saved {len(issues)} issues to {output_path}")


def analyze_labels(all_issues: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Analyze label frequencies and class distribution.

    Args:
        all_issues: All closed, non-PR issues

    Returns:
        Analysis dict with:
        - unique_labels: dict of label_name -> count
        - class_distribution: dict of class -> count (only for classified issues)
        - label_names: sorted list of all unique label names
    """
    label_counts = defaultdict(int)
    class_counts = defaultdict(int)

    for issue in all_issues:
        # Count label frequencies
        labels = issue.get("labels", [])
        for label in labels:
            label_name = label.get("name", "")
            if label_name:
                label_counts[label_name] += 1

        # Count mapped classes
        if "class" in issue:
            class_counts[issue["class"]] += 1

    return {
        "unique_labels": dict(label_counts),
        "class_distribution": dict(class_counts),
        "label_names": sorted(label_counts.keys()),
    }


def save_label_analysis(
    analysis: Dict[str, Any],
    all_issues: List[Dict[str, Any]],
    classification_issues: List[Dict[str, Any]],
    rag_issues: List[Dict[str, Any]],
    num_no_labels: int,
    num_unmappable: int,
    num_prs: int,
    output_path: Path,
) -> None:
    """
    Save comprehensive label analysis report.

    Args:
        analysis: Analysis dict from analyze_labels()
        all_issues: All closed, non-PR issues
        classification_issues: Issues with valid class labels
        rag_issues: All resolved issues
        num_no_labels: Count of issues with no labels
        num_unmappable: Count of issues with unmappable labels
        num_prs: Count of PRs filtered out
        output_path: Path to output JSON file
    """
    report = {
        "timestamp": datetime.now().isoformat(),
        "summary": {
            "total_prs_filtered": num_prs,
            "total_closed_issues": len(all_issues),
            "issues_with_no_labels": num_no_labels,
            "issues_with_unmappable_labels": num_unmappable,
            "issues_for_classification": len(classification_issues),
            "issues_for_rag_corpus": len(rag_issues),
        },
        "label_analysis": analysis,
    }

    output_path.parent.mkdir(parents=True, exist_ok=True)

    with open(output_path, "w") as f:
        json.dump(report, f, indent=2)

    logging.info(f"Saved label analysis to {output_path}")


# ============================================================================
# MAIN ENTRY POINT
# ============================================================================

def main() -> int:
    """
    Main entry point.

    Orchestrates the full pipeline:
    1. Load issues from JSONL
    2. Filter PRs and open issues
    3. Optionally filter by date
    4. Separate for classification (with labels) vs RAG (all)
    5. Clean text fields
    6. Temporal split for classification
    7. Save all outputs
    8. Generate label analysis
    9. Print summary

    Returns:
        0 on success, 1 on error
    """
    parser = argparse.ArgumentParser(
        description="Process GitHub issues for classification and RAG corpus."
    )
    parser.add_argument(
        "--input",
        type=Path,
        default=Path("data/pandas_closed_issues.jsonl"),
        help="Path to input JSONL file (default: data/pandas_closed_issues.jsonl)",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("data"),
        help="Output directory (default: data/)",
    )
    parser.add_argument(
        "--min-date",
        type=str,
        default=None,
        help="Optional minimum date filter (YYYY-MM-DD)",
    )

    args = parser.parse_args()

    # Setup logging
    log_file = args.output_dir / "processing.log"
    args.output_dir.mkdir(parents=True, exist_ok=True)
    setup_logging(log_file)

    logging.info("=" * 70)
    logging.info("Starting issue processing pipeline")
    logging.info("=" * 70)

    # Step 1: Load issues
    try:
        all_raw_issues = load_issues(args.input)
    except (FileNotFoundError, IOError) as e:
        logging.error(f"Failed to load issues: {e}")
        return 1

    # Step 2: Filter PRs and closed state
    all_closed_issues, num_prs, num_open = filter_prs_and_closed(all_raw_issues)

    # Step 3: Apply date filter if provided
    if args.min_date:
        try:
            min_datetime = datetime.fromisoformat(args.min_date)
            original_count = len(all_closed_issues)
            all_closed_issues = [
                issue
                for issue in all_closed_issues
                if datetime.fromisoformat(issue.get("closed_at", "")) >= min_datetime
            ]
            logging.info(
                f"Date filter applied: {original_count - len(all_closed_issues)} issues removed"
            )
        except ValueError as e:
            logging.error(f"Invalid date format: {e}")
            return 1

    # Step 4: Save all closed, non-PR issues (baseline for RAG corpus)
    all_closed_path = args.output_dir / "all_closed_non_pr_issues.jsonl"
    save_jsonl(all_closed_issues, all_closed_path)

    # Step 5: Map labels and separate for classification vs RAG
    classification_issues, rag_issues, num_no_labels, num_unmappable = filter_and_map_labels(
        all_closed_issues
    )

    # Step 6: Clean text for all issues
    enriched_classification = enrich_and_clean_issues(classification_issues)
    enriched_rag = enrich_and_clean_issues(rag_issues)

    # Step 7: Temporal split for classification dataset (only)
    train_issues, val_issues, test_issues = temporal_split(enriched_classification)

    # Step 8: Save classification dataset and splits
    classification_dir = args.output_dir / "classification"
    classification_dir.mkdir(parents=True, exist_ok=True)

    save_jsonl(enriched_classification, classification_dir / "classification_ready.jsonl")
    save_jsonl(train_issues, classification_dir / "train.jsonl")
    save_jsonl(val_issues, classification_dir / "val.jsonl")
    save_jsonl(test_issues, classification_dir / "test.jsonl")

    # Step 9: Save RAG corpus
    rag_dir = args.output_dir / "rag_corpus"
    rag_dir.mkdir(parents=True, exist_ok=True)
    save_jsonl(enriched_rag, rag_dir / "issues.jsonl")

    # Step 10: Analyze labels
    analysis = analyze_labels(all_closed_issues)

    # Step 11: Save label analysis report
    label_report_path = args.output_dir / "label_analysis.json"
    save_label_analysis(
        analysis,
        all_closed_issues,
        enriched_classification,
        enriched_rag,
        num_no_labels,
        num_unmappable,
        num_prs,
        label_report_path,
    )

    # Step 12: Print summary to console
    print("\n" + "=" * 70)
    print("PROCESSING SUMMARY")
    print("=" * 70)
    print(f"Total issues read:              {len(all_raw_issues)}")
    print(f"PRs filtered out:               {num_prs}")
    print(f"Open issues filtered out:       {num_open}")
    print(f"Closed, non-PR issues:          {len(all_closed_issues)}")
    print()
    print(f"Issues with no labels:          {num_no_labels}")
    print(f"Issues with unmappable labels:  {num_unmappable}")
    print()
    print(f"Classification dataset:         {len(enriched_classification)}")
    print(f"  - Train:                      {len(train_issues)}")
    print(f"  - Val:                        {len(val_issues)}")
    print(f"  - Test:                       {len(test_issues)}")
    print()
    print(f"RAG corpus:                     {len(enriched_rag)}")
    print()

    # Class distribution in classification set
    class_dist = defaultdict(int)
    for issue in enriched_classification:
        class_dist[issue.get("class", "unknown")] += 1

    print("Class distribution (classification):")
    for class_name in ["bug", "feature", "docs", "question"]:
        count = class_dist.get(class_name, 0)
        pct = (count / len(enriched_classification) * 100) if enriched_classification else 0
        print(f"  - {class_name:12s}: {count:5d} ({pct:5.1f}%)")

    print()
    print(f"Label analysis saved to:        {label_report_path}")
    print(f"Classification data saved to:   {classification_dir}/")
    print(f"RAG corpus saved to:            {rag_dir}/")
    print()
    print("=" * 70)
    print("Next: Run `scripts/prepare_rag_corpus.py` to combine issues with docs.")
    print("=" * 70)

    return 0


if __name__ == "__main__":
    sys.exit(main())
