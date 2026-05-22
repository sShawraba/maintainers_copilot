#!/usr/bin/env python3
"""
Classical ML baseline for issue classification.
Uses TF-IDF + LogisticRegression, with hyperparameter tuning on validation set.
Reports accuracy, macro F1, per-class F1, latency, cost ($0).
"""

import json
import time
from pathlib import Path
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, f1_score, classification_report
import numpy as np

def load_data(split_path):
    texts, labels = [], []
    label_map = {'bug': 0, 'feature': 1, 'docs': 2, 'question': 3}
    with open(split_path, 'r') as f:
        for line in f:
            item = json.loads(line)
            text = f"Title: {item['cleaned_title']}\nBody: {item['cleaned_body']}"
            texts.append(text)
            labels.append(label_map[item['class']])
    return texts, labels

def main():
    data_dir = Path("data/classification")
    train_texts, train_labels = load_data(data_dir / "train.jsonl")
    val_texts, val_labels = load_data(data_dir / "val.jsonl")
    test_texts, test_labels = load_data(data_dir / "test.jsonl")

    print(f"Train: {len(train_texts)}, Val: {len(val_texts)}, Test: {len(test_texts)}")

    # TF-IDF vectorizer
    vectorizer = TfidfVectorizer(max_features=20000, ngram_range=(1,2), sublinear_tf=True)
    X_train = vectorizer.fit_transform(train_texts)
    X_val = vectorizer.transform(val_texts)
    X_test = vectorizer.transform(test_texts)

    # Hyperparameter tuning on validation set
    best_c = 1.0
    best_f1 = 0
    for C in [0.1, 0.5, 1.0, 2.0, 5.0]:
        clf = LogisticRegression(C=C, max_iter=1000, solver='lbfgs')  # removed multi_class
        clf.fit(X_train, train_labels)
        y_val_pred = clf.predict(X_val)
        f1 = f1_score(val_labels, y_val_pred, average='macro')
        if f1 > best_f1:
            best_f1 = f1
            best_c = C
    print(f"Best C on validation: {best_c} (macro F1={best_f1:.4f})")

    # Final model on full training set
    clf = LogisticRegression(C=best_c, max_iter=1000, solver='lbfgs')
    clf.fit(X_train, train_labels)

    # Measure inference latency
    start = time.perf_counter()
    y_pred = clf.predict(X_test)
    latency = (time.perf_counter() - start) / len(test_texts) * 1000  # ms per sample

    acc = accuracy_score(test_labels, y_pred)
    macro_f1 = f1_score(test_labels, y_pred, average='macro')
    per_class_f1 = f1_score(test_labels, y_pred, average=None, labels=[0,1,2,3])
    class_names = ['bug', 'feature', 'docs', 'question']

    print("\n=== Classical ML Baseline Results ===")
    print(f"Accuracy:  {acc:.4f}")
    print(f"Macro F1:  {macro_f1:.4f}")
    for name, f1 in zip(class_names, per_class_f1):
        print(f"  {name}: {f1:.4f}")
    print(f"Inference latency: {latency:.2f} ms per sample")
    print(f"Cost: $0 (no API calls)")

    # Save report
    report = {
        "model": "TF-IDF + LogisticRegression",
        "accuracy": acc,
        "macro_f1": macro_f1,
        "per_class_f1": dict(zip(class_names, per_class_f1)),
        "latency_ms": latency,
        "cost_usd": 0.0
    }
    with open("classical_baseline_report.json", "w") as f:
        json.dump(report, f, indent=2)
    print("\nReport saved to classical_baseline_report.json")

if __name__ == "__main__":
    main()