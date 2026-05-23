    # app/model_loader.py
from sentence_transformers import SentenceTransformer, CrossEncoder
from transformers import pipeline
import os
from pathlib import Path

# These will be loaded once when the module is imported (at startup)
dense_model = SentenceTransformer("all-MiniLM-L6-v2")
reranker = CrossEncoder("cross-encoder/ms-marco-MiniLM-L-6-v2")

# ---------- Absolute path to classifier folder ----------
PROJECT_ROOT = Path(__file__).parent.parent  # goes from app/ to project root
CLASSIFIER_PATH = PROJECT_ROOT / "models" / "classifier"

if not CLASSIFIER_PATH.exists():
    raise FileNotFoundError(f"Classifier folder not found at {CLASSIFIER_PATH}")

print(f"[INFO] Loading classifier from {CLASSIFIER_PATH.absolute()}")
print(f"[INFO] Files in folder: {[f.name for f in CLASSIFIER_PATH.iterdir()]}")

# Load classifier from local folder (do NOT go to Hugging Face Hub)
classifier = pipeline(
    "text-classification",
    model=str(CLASSIFIER_PATH),
    tokenizer=str(CLASSIFIER_PATH),
    return_all_scores=False,
    device=-1,
    local_files_only=True   # Prevents any download attempt
)

# ---------- NER (lightweight, downloads from Hub once) ----------
print("[INFO] Loading NER model...")
ner = pipeline(
    "ner",
    model="dslim/bert-base-NER",
    aggregation_strategy="simple",
    device=-1
)

# ---------- Summarizer (using text2text-generation for older transformers) ----------
# print("[INFO] Loading summarizer model...")
# summarizer = pipeline(
#     "text2text-generation",
#     model="t5-small",
#     device=-1
# )

print("[INFO] All models loaded successfully.")