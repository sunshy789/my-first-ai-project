# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

A RAG (Retrieval-Augmented Generation) + Agent system built with FastAPI, Gradio, Qdrant, and Redis. The LLM backend is 火山豆包 (Doubao) via an OpenAI-compatible API at `https://ark.cn-beijing.volces.com/api/v3`.

## Services & Ports

| Service | Port | Entry |
|---------|------|-------|
| RAG Backend (FastAPI) | 8001 | `rag_backend/main.py` |
| Agent API (FastAPI) | 8002 | `agent/agent_api.py` |
| Gradio Frontend | 7860 | `gradio_frontend/gradio_app.py` |
| Qdrant (Docker) | 6333 | Required for RAG |
| Redis (Docker) | 6379 | Required for Agent session memory |

## Setup & Running

```bash
# Install dependencies (only dep file is in rag_backend/)
pip install -r rag_backend/requirements.txt

# Start Qdrant (Docker)
docker run -p 6333:6333 qdrant/qdrant

# Start Redis (Docker)
docker run -p 6379:6379 redis

# RAG Backend
cd rag_backend && uvicorn main:app --host 0.0.0.0 --port 8001 --reload

# Agent API — requires rag_backend/ on PYTHONPATH (imports llm_client)
cd agent && PYTHONPATH=.. uvicorn agent_api:app --host 0.0.0.0 --port 8002 --reload

# Gradio Frontend
cd gradio_frontend && python gradio_app.py
```

No `pyproject.toml`, `setup.py`, or root-level `requirements.txt` — only `rag_backend/requirements.txt`.

## Architecture

**RAG Pipeline** (`rag_backend/main.py`):
1. `/rag/upload` — Parse TXT/PDF → chunk (500 words, 50 overlap) → embed via `BAAI/bge-small-zh` (512-dim) → store in Qdrant collection `rag_docs`
2. `/rag/chat` — Query expansion (3 variants via LLM) → hybrid search (vector + BM25 + RRF fusion, k=60) → top-3 chunks → prompt → LLM answer
3. `/rag/chat/stream` — Same pipeline, streaming response via `StreamingResponse`

**Agent** (`agent/agent_with_rag.py`):
- Manual Function Calling loop: model returns JSON `{"function": ..., "arguments": {...}}`, code dispatches to tool, feeds result back for final answer
- Three tools: `get_weather` (mock), `calculator` (eval-based, unsafe), `retrieve_from_docs` (pure vector search in Qdrant, no doc_id filter)
- Session history persisted in Redis with 30-minute TTL (`agent/agent_api.py`)

**Frontend** (`gradio_frontend/gradio_app.py`):
- Currently wired to `chat_with_agent` (Agent mode). To switch to RAG-only, change the `fn` in `gr.ChatInterface` to `chat_with_rag`.
- RAG upload flow: select file → click upload button → stores `current_doc_id` globally → chat uses that doc_id
- Communicates with backends purely via HTTP (`requests` library), no Python imports from other services.

**Cross-service dependency:** `agent/agent_with_rag.py` imports `LLMClient` from `rag_backend/llm_client.py` and also uses `qdrant_client` + `sentence_transformers` directly for the `retrieve_from_docs` tool. The Agent service won't start without `rag_backend/` on PYTHONPATH.

## Key Dependencies

```
fastapi, uvicorn, gradio, requests, pdfplumber,
sentence-transformers, qdrant-client, rank-bm25,
redis, python-multipart, langchain-openai, pandas
```

Embedding model: `BAAI/bge-small-zh` (downloaded on first run from HuggingFace).

## Evaluation & Testing

Two RAGAS evaluation scripts (standalone, use hardcoded data, don't call running services):
- `eval_ragas.py` — multi-sample evaluation with faithfulness + answer relevancy metrics
- `eval_stable.py` — single-sample quick test with ground truth

Manual verification scripts in `test_all/`:
- `hybrid_search.py` — standalone hybrid search test
- `test_hybrid_vs_vector.py` — side-by-side comparison of hybrid vs pure vector retrieval
- `test_rerank.py` — CrossEncoder reranker experiment (not integrated into main pipeline)
- `gets_doc_ids.py` — list all doc_ids stored in Qdrant

Redis connectivity scripts in `redis/`:
- `test_redis.py` — ping check
- `redis_data_types.py` — exercises all five Redis data types

No pytest framework or automated test suite exists.

## Notable Issues

- **API keys are hardcoded** in `rag_backend/main.py`, `rag_backend/llm_client.py`, `agent/agent_with_rag.py`, and both eval scripts. Move to environment variables before any real deployment.
- `main.py` line 5 imports `sqlalchemy.result_tuple` which is unused.
- `file_utils.py` defines `chunk_text_by_chars` (character-based) but `main.py` uses its own `chunktext` (word-based). Only `parse_file_content` from `file_utils` is actually imported and used.
- `agent_with_rag.py` uses raw `eval()` in the calculator tool — unsafe for production.
