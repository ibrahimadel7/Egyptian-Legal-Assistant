# Egyptian Legal Assistant — FastAPI + Naive RAG

A local-first academic prototype for Arabic Egyptian legal information and guidance. It uses the supplied dataset, local dense embeddings, ChromaDB, and Groq-hosted `openai/gpt-oss-20b`.

> **Important legal/product boundary:** This is an experimental information assistant, not a lawyer or an authoritative legal service. The supplied dataset has no verified source URLs, issuing authority, publication dates, effective dates, or amendment history. The API must not claim that a provision is current or authoritative. It should abstain when the retrieved evidence is weak or insufficient.

## Stack

- Python 3.11+
- FastAPI
- Sentence Transformers: `mzahran1/arabic-english-e5-small-retrieval` (117.7M parameters, 384 dimensions, 256-token max input per the MTEB model registry)
- ChromaDB (persistent local collection, cosine distance)
- Groq API: `openai/gpt-oss-20b`
- SQLite for conversation history and plain-text summaries
- JSONL as the canonical working copy of the supplied Parquet data

## Dataset included

`data/source.parquet` preserves the original uploaded Parquet. `data/legal_dataset_decoded.jsonl` is the decoded JSONL working copy available in the project workspace. Each row has the following observed fields:

- `law_name` — dataset-provided record label; it is not guaranteed to be a formal law title.
- `categories` — category path.
- `text` — Arabic source text.
- `tokens` — source-provided token count.

The inspected working copy contains 2,434 records, 1,997 distinct `law_name` values, and 224 distinct category paths. Text length varies substantially (168 to 341,212 characters; median 3,445). There are 349 repeated text occurrences beyond the number of unique text values. Exact duplicates are preserved in the first baseline because their labels/categories may differ; deduplication should be an evaluated decision.

The data mixes legislation, court material, encyclopedic/commentary material, and other legal references. It is not safe to treat every record as a current statute. Ingestion preserves original record IDs and category paths.

## Quick start

### 1. Create an environment

```bash
python -m venv .venv
# Windows:
.venv\Scripts\activate
# macOS/Linux:
source .venv/bin/activate

pip install -r requirements.txt
```

### 2. Configure secrets

The project reads `.env` from the repository root.

```bash
# Edit .env and add:
GROQ_API_KEY=your_groq_api_key
```

The `.env` file is excluded from Git. Do not put keys in source code or commit them.

### 3. Build the vector index

```bash
python scripts/ingest.py
```

This downloads the embedding model weights on first run (roughly 449 MB in the MTEB registry), chunks the dataset, embeds each passage locally, and writes vectors to `./chroma_db`. The model is run locally; Groq is used only for LLM inference.

To rebuild the collection from scratch:

```bash
python scripts/ingest.py --reset
```

For a different source file:

```bash
python scripts/ingest.py --source path/to/dataset.parquet
```

Supported input formats: JSONL and Parquet. Parquet ingestion requires `pyarrow` (included in requirements). The included conversion utility is `scripts/convert_parquet_to_jsonl.py`.

### 4. Run the API

```bash
uvicorn app.main:app --reload
```

- API docs: http://127.0.0.1:8000/docs
- Health: http://127.0.0.1:8000/health
- Chat: `POST http://127.0.0.1:8000/api/v1/chat`

Example request:

```json
{
  "message": "أنا اتفصلت من شغلي، إيه المعلومات اللي محتاج تعرفها عشان تفهم موقفي؟"
}
```

Optional continuing conversation:

```json
{
  "conversation_id": "the-id-returned-by-the-first-request",
  "message": "كان عقدي محدد المدة."
}
```

## API response

The response includes:
- `conversation_id`
- `status`: `answered` or `needs_clarification`
- `answer`
- `sources`: source labels and exact retrieved excerpts, when used
- `retrieval_query`: the enriched query used for vector search (useful for development/debugging)

Source labels are dataset labels, not verified legal provenance. No article number, date, or amendment status is invented. Article references are included only when extracted from a structured legal segment.

## Retrieval and chunking behavior

1. The user question is rewritten into one standalone retrieval query using the conversation summary and last two messages.
2. The query is embedded using the same model used for passages, with the E5-style `query:` prefix.
3. ChromaDB returns the top 5 chunks by cosine distance.
4. A configurable cosine-distance gate rejects clearly weak matches. `MAX_COSINE_DISTANCE` is an initial uncalibrated setting, not a validated relevance threshold.
5. Neighboring chunks are added only from the same parent record and same detected unit (article/judgment/record).
6. Evidence is assembled under a token budget. `tiktoken` is used as a practical estimate; it is not the exact tokenizer for GPT-OSS.
7. GPT-OSS assesses whether the evidence supports the requested answer and generates a grounded answer in one call. It may ask a clarifying question or abstain.
8. The application validates returned source IDs against the actual retrieved chunks before returning citations.

### Chunking

- Records categorized under court-of-cassation/administrative-court material are segmented by `الطعن رقم` when multiple case headings are present.
- Other legal records are segmented by article markers (`مادة` / `المادة`) when multiple boundaries are detected.
- Oversized units are packed at sentence/paragraph boundaries up to `CHUNK_MAX_TOKENS` (default 220), below the embedding model's 256-token input limit.
- Unstructured records fall back to sentence-aware packing.
- Every chunk retains `record_id`, `unit_id`, `law_name`, categories, unit label, article/case reference when detected, and chunk order.
- The original source text is not normalized or rewritten. Minimal Arabic normalization is applied only in a separate helper for future lexical work; this Naive RAG baseline embeds original text.

## Conversation memory

- The full conversation is stored in SQLite.
- A plain-text summary is updated when at least 10 unsummarized messages exist, before the next user message is processed.
- During summarization, the newest two previous messages are retained outside the summary.
- The LLM receives the summary, last two messages, and current user message.
- Multiple legal topics remain in the same conversation summary.
- The summary is conversational context, never legal evidence.

## Configuration

See `.env.example`. Important values:

| Variable | Default | Purpose |
|---|---:|---|
| `GROQ_MODEL` | `openai/gpt-oss-20b` | Generation model |
| `EMBEDDING_MODEL` | `mzahran1/arabic-english-e5-small-retrieval` | Local embedding model |
| `TOP_K` | `5` | Initial retrieval count |
| `MAX_COSINE_DISTANCE` | `0.65` | Uncalibrated distance gate |
| `CHUNK_MAX_TOKENS` | `220` | Chunk target |
| `MAX_CONTEXT_TOKENS` | `6000` | Estimated context budget |
| `CONTEXT_NEIGHBORS` | `1` | Neighbor chunks per retrieved chunk |

## Important limitations and next engineering tasks

1. **Currentness/provenance:** the dataset does not expose enough metadata to verify legislation status or amendments. Do not present the corpus as comprehensive or current.
2. **Chunking QA:** inspect sampled chunk boundaries by document category. Automated article detection is heuristic, not a legal parser.
3. **Embedding evaluation:** the chosen model is a baseline. Build an Egyptian legal query set and manually label relevant records before claiming retrieval quality.
4. **Threshold calibration:** tune `MAX_COSINE_DISTANCE` against labeled queries; cosine distance alone is not proof of answerability.
5. **LLM answer quality:** model-based answers and evidence assessment are fallible. Test answer quality and grounding.
6. **Prompt injection:** retrieved text is treated as untrusted evidence, not instructions.
7. **Security:** add authentication, rate limiting, retention controls, and production CORS rules before any public deployment.

## Tests

```bash
pytest -q
```

Tests cover deterministic text segmentation and metadata preservation. They do not require downloading the embedding model.


### Parquet / JSONL parity note

The original uploaded Parquet is included unchanged as `data/source.parquet`. The JSONL working copy was already available in the project workspace from earlier work and was used for the included dataset profile and default ingestion. The build environment had no Parquet engine installed and no package-network access, so exact row-for-row parity between the uploaded Parquet and that pre-existing JSONL could not be independently verified here. To guarantee that the working JSONL is generated from the included Parquet, run the conversion utility and then ingest the regenerated JSONL.


## Frontend integration

The React/Vite frontend calls `POST /api/v1/chat` through the Vite development proxy. Start the API on `127.0.0.1:8000` and the frontend on `127.0.0.1:5173`; the browser sends requests to the same Vite origin, which proxies `/api` to FastAPI. For a separately hosted frontend, set `VITE_API_BASE_URL` to the backend API base URL (for example `https://api.example.com/api/v1`) and configure `CORS_ORIGINS` on the backend accordingly.

The frontend stores the backend-issued `conversation_id` and sends it with follow-up questions. It renders only source records returned by the API; it does not invent source cards when retrieval abstains. Set `GROQ_API_KEY` in `.env` and run ingestion before expecting successful answers.
