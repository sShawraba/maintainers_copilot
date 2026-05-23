# Maintainer's Copilot

[![Python 3.11](https://img.shields.io/badge/python-3.11-blue.svg)](https://www.python.org/downloads/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115-green)](https://fastapi.tiangolo.com/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

**Maintainer's Copilot** is an AI‑powered assistant for open‑source maintainers to triage issues faster. It classifies issues, answers questions with advanced RAG, remembers user facts across conversations, and can be embedded as a lightweight widget into any host app.

---

## Features

- **Issue classification** – fine‑tuned RoBERTa (vs classical ML & LLM baseline) – accuracy 86% macro F1
- **Advanced RAG** – hybrid retrieval (dense + BM25), cross‑encoder reranking, HyDE query transformation
- **Chatbot with tools** – single LLM (Groq) that calls: `retrieve_docs`, `classify_issue`, `extract_entities`, `summarize`, `write_memory`, `recall_memory`
- **Memory** – short‑term (Redis TTL 1h) + long‑term (pgvector, episodic)
- **Authentication** – JWT (fastapi‑users), secrets in Vault (or env fallback)
- **Embeddable widget** – configuration stored in Postgres, allowed‑origins enforced, CSP header ready
- **Evaluation & CI** – golden sets (25 classification, 25 RAG triples), eval thresholds, redaction test
- **Observability** – tracing backend (Langfuse ready), redaction layer, structured exceptions

---

## Tech Stack

| Component          | Technology                                                                 |
|--------------------|----------------------------------------------------------------------------|
| API                | FastAPI, Uvicorn                                                           |
| Database           | PostgreSQL 16 + pgvector                                                   |
| Short‑term memory  | Redis                                                                      |
| Secrets            | HashiCorp Vault (or env var)                                               |
| Embedding model    | sentence‑transformers/all‑MiniLM‑L6‑v2                                     |
| Reranker           | cross‑encoder/ms‑marco‑MiniLM‑L‑6‑v2                                       |
| LLM                | Groq (llama‑3.3‑70b‑versatile)                                             |
| Frontend (admin)   | Streamlit                                                                  |
| Frontend (widget)  | React (Vite) – design completed                                            |
| Infrastructure     | Docker Compose                                                             |

---

---



