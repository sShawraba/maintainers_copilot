#!/usr/bin/env python3
"""
LLM baseline using Groq API (zero-shot) with subset sampling to avoid rate limits.
"""

import json
import time
import os
import random
from pathlib import Path
from dotenv import load_dotenv
from groq import Groq
from sklearn.metrics import accuracy_score, f1_score
import tiktoken

load_dotenv()

api_key = os.getenv("GROQ_API_KEY")
if not api_key:
    raise ValueError("GROQ_API_KEY not found in .env")
client = Groq(api_key=api_key)

def load_test_data(test_path, sample_size=None, random_seed=42):
    """Load test data, optionally take random sample."""
    items = []
    with open(test_path, 'r') as f:
        for line in f:
            item = json.loads(line)
            text = f"Title: {item['cleaned_title']}\nBody: {item['cleaned_body']}"
            items.append({
                "text": text,
                "true_label": item['class']
            })
    if sample_size and sample_size < len(items):
        random.seed(random_seed)
        items = random.sample(items, sample_size)
        print(f"Using random subset of {sample_size} samples (from {len(items)} total)")
    return items

def classify_zero_shot(text, retries=3):
    """With simple retry on rate limit."""
    prompt = f"""Classify the following GitHub issue into one of these categories: bug, feature, docs, question.
Return only the category name, nothing else.

Issue:
{text}

Category:"""
    
    for attempt in range(retries):
        try:
            response = client.chat.completions.create(
                model="qwen/qwen3-32b",
                messages=[{"role": "user", "content": prompt}],
                temperature=0,
                max_tokens=10
            )
            pred = response.choices[0].message.content.strip().lower()
            if pred in ["bug", "feature", "docs", "question"]:
                return pred
            return "question"
        except Exception as e:
            if "rate_limit" in str(e).lower() and attempt < retries - 1:
                # Wait for reset (error gives wait time)
                wait = 30  # fallback
                if "try again in" in str(e):
                    import re
                    match = re.search(r'in (\d+)m([\d.]+)s', str(e))
                    if match:
                        minutes = int(match.group(1))
                        seconds = float(match.group(2))
                        wait = minutes * 60 + seconds + 5
                print(f"Rate limit hit, waiting {wait:.0f}s...")
                time.sleep(wait)
                continue
            raise
    return "question"

def main():
    test_path = Path("data/classification/test.jsonl")
    if not test_path.exists():
        print(f"Error: Test data not found at {test_path}")
        return

    # Use a subset to avoid daily token limits (20 samples ~ 100k tokens)
    SAMPLE_SIZE = 10
    test_items = load_test_data(test_path, sample_size=SAMPLE_SIZE)
    
    print(f"Testing on {len(test_items)} samples using Groq (llama-3.3-70b-versatile)")

    y_true = []
    y_pred = []
    total_tokens = 0
    latencies = []

    encoder = tiktoken.get_encoding("cl100k_base")

    for i, item in enumerate(test_items):
        start = time.perf_counter()
        pred = classify_zero_shot(item["text"])
        latency = (time.perf_counter() - start) * 1000
        latencies.append(latency)

        input_tokens = len(encoder.encode(item["text"])) + 50
        output_tokens = 3
        total_tokens += input_tokens + output_tokens

        y_true.append(item["true_label"])
        y_pred.append(pred)

        print(f"Processed {i+1}/{len(test_items)} | Latency: {latency:.0f}ms")

    label_order = ["bug", "feature", "docs", "question"]
    y_true_idx = [label_order.index(l) for l in y_true]
    y_pred_idx = [label_order.index(p) if p in label_order else 3 for p in y_pred]

    acc = accuracy_score(y_true_idx, y_pred_idx)
    macro_f1 = f1_score(y_true_idx, y_pred_idx, average='macro')
    per_class_f1 = f1_score(y_true_idx, y_pred_idx, average=None, labels=[0,1,2,3])

    avg_latency = sum(latencies) / len(latencies)

    print("\n=== LLM Baseline (Groq API) Results ===")
    print(f"Model: llama-3.3-70b-versatile (free tier, {SAMPLE_SIZE} samples)")
    print(f"Accuracy:  {acc:.4f}")
    print(f"Macro F1:  {macro_f1:.4f}")
    for name, f1 in zip(label_order, per_class_f1):
        print(f"  {name}: {f1:.4f}")
    print(f"Avg latency: {avg_latency:.2f} ms per sample")

    report = {
        "model": "Groq llama-3.3-70b-versatile (zero-shot)",
        "samples_used": SAMPLE_SIZE,
        "accuracy": acc,
        "macro_f1": macro_f1,
        "per_class_f1": dict(zip(label_order, per_class_f1)),
        "latency_ms": avg_latency,
        "cost_usd": 0.0,
        "total_tokens": total_tokens
    }
    with open("llm_baseline_report_groq.json", "w") as f:
        json.dump(report, f, indent=2)
    print("\nReport saved to llm_baseline_report_groq.json")

if __name__ == "__main__":
    main()