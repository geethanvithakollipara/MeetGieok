# Member 2 — Hindsight Memory Engineer

Hindsight is the memory layer: every contact gets its own Hindsight **bank**
(`contact-<name>-<company>`), so memory is isolated by construction.

## Setup
```bash
pip install -r requirements.txt
cp .env.example .env
export OPENAI_API_KEY=sk-...          # Hindsight server needs an LLM key
docker compose up -d                  # API :8888, UI :9999
python demo.py                        # BEFORE -> STORE -> AFTER
python -m unittest discover -s tests -v                             # multi-meeting + isolation tests
```
No server? `MEMORY_BACKEND=local python demo.py` runs an offline fallback with the same interface.

## API
```python
retain_memory(contact, meeting) -> bank_id
recall_memory(contact, query=None, top_k=6) -> {category: [facts]}
```
**Stored:** role/company, topics, preferences, promises made, promises delivered
(undelivered are explicitly tagged), unresolved issues.
**Recalled (5 categories):** profile, preferences, commitments, unresolved, history.

## Notes
- Meetings are stored as natural-language sentences naming the person, which
  suits Hindsight's LLM fact extraction.
- `document_id` per meeting makes re-retaining the same meeting an update, not a duplicate.
- Hindsight client signatures (`retain`, `recall`, `create_bank`) were written from the
  documented API; verify against your installed `hindsight-client` version. Only
  `memory/backends.py` needs changing if they differ.
