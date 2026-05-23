#!/usr/bin/env python3
"""Full ingestion into rag_chunks using SentenceTransformer (processes all chunks)."""

import json
import sys
from pathlib import Path

from sentence_transformers import SentenceTransformer
from tqdm import tqdm
import psycopg2
from psycopg2.extras import execute_values

CHUNKS_FILE = Path("data/rag_corpus/chunks.jsonl")
EMBEDDING_MODEL = "all-MiniLM-L6-v2"  # 384 dims, matches your table
BATCH_SIZE = 64  # Adjust based on your RAM

def get_db_connection():
    return psycopg2.connect(
        host="localhost",
        port=5432,
        dbname="maintainers_copilot",
        user="postgres",
        password="postgres"
    )

def load_all_chunks():
    chunks = []
    with open(CHUNKS_FILE) as f:
        for line in f:
            if line.strip():
                chunks.append(json.loads(line))
    print(f"Loaded {len(chunks)} chunks from {CHUNKS_FILE}")
    return chunks

def main():
    chunks = load_all_chunks()
    if not chunks:
        print("No chunks found.")
        return 1

    texts = [c["text"] for c in chunks]
    print(f"Loading model {EMBEDDING_MODEL}...")
    model = SentenceTransformer(EMBEDDING_MODEL)

    # Generate embeddings in batches to show progress
    print("Generating embeddings...")
    embeddings = []
    for i in tqdm(range(0, len(texts), BATCH_SIZE), desc="Embedding batches"):
        batch = texts[i:i+BATCH_SIZE]
        batch_embeds = model.encode(batch, show_progress_bar=False)
        embeddings.extend(batch_embeds)

    # Prepare data for insertion
    data = []
    for chunk, emb in zip(chunks, embeddings):
        data.append((chunk["text"], json.dumps(chunk["metadata"]), emb.tolist()))

    # Insert into database
    print("Inserting into rag_chunks...")
    conn = get_db_connection()
    cur = conn.cursor()
    try:
        # Optional: clear existing table (comment if you want to keep previous test rows)
        cur.execute("TRUNCATE TABLE rag_chunks RESTART IDENTITY;")
        print("Truncated existing table.")

        execute_values(
            cur,
            "INSERT INTO rag_chunks (text, meta_data, embedding) VALUES %s",
            data,
            page_size=BATCH_SIZE
        )
        conn.commit()
        print(f"Successfully inserted {len(data)} rows.")
    except Exception as e:
        conn.rollback()
        print(f"Error during insertion: {e}")
        return 1
    finally:
        cur.close()
        conn.close()

    return 0

if __name__ == "__main__":
    sys.exit(main())