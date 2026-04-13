# AI Code Review Agent

> Automated pull request reviewer that catches security vulnerabilities, logic errors, and performance issues before they merge — powered by LLM analysis and a production-grade async pipeline.

---

## How It Works

When a pull request is opened or updated on GitHub, a webhook fires and triggers a fully async review pipeline:

1. **Webhook intake** — FastAPI receives the GitHub event, verifies the HMAC signature, and immediately queues a job
2. **Diff fetching** — the Celery worker fetches changed files from the GitHub API
3. **Chunking** — each file's patch is parsed into structured chunks with a position map tracking exact diff offsets
4. **LLM review** — each chunk is sent to the LLM with a structured prompt constraining findings to valid line numbers only
5. **Aggregation** — findings are validated, deduplicated, and ranked by severity
6. **Comment posting** — inline comments are posted directly on the PR, mapped to the exact changed lines

The webhook returns `200` immediately — all processing happens asynchronously in the background.

---

## Architecture

```
GitHub PR event
      │
      ▼
FastAPI Webhook ──► Signature verification
      │
      ▼
Redis Queue (Celery)
      │
      ▼
Worker Pipeline
  ├── Fetch diff (GitHub API)
  ├── Parse & chunk diff
  ├── LLM review per chunk (OpenRouter)
  ├── Validate findings (line numbers, JSON)
  ├── Aggregate & rank
  └── Post inline comments (GitHub API)
      │
      ▼
PostgreSQL
  ├── reviews   (status, tokens, cost)
  └── findings  (file, line, severity, message)
      │
      ▼
Dashboard (/dashboard)
```

---

## Features

- **Async pipeline** — webhook returns instantly; review runs in the background via Celery + Redis
- **Structured LLM output** — findings constrained to valid diff line numbers, parsed and validated before posting
- **Inline GitHub comments** — comments posted on exact changed lines, not just at PR level
- **Idempotency** — each commit SHA is reviewed at most once, even if the webhook fires multiple times
- **Auto-retry** — failed jobs retry up to 3 times with exponential backoff
- **Webhook signature verification** — `X-Hub-Signature-256` verified on every request
- **Audit logging** — every review persisted to PostgreSQL with token usage and cost tracking
- **Dashboard** — live view of reviews, findings by severity/category, token usage, and estimated cost

---

## Tech Stack

| Component | Technology | Why |
|-----------|------------|-----|
| API | FastAPI | Async-first, fast webhook intake |
| Queue | Celery + Redis | Reliable async job processing |
| Database | PostgreSQL | Structured review history and audit trail |
| LLM | OpenRouter API | Model-agnostic; swap models without changing the pipeline |
| GitHub | REST API + Webhooks | Diff fetching and inline comment posting |
| Infrastructure | Docker Compose | Redis and PostgreSQL containerized |

---

## Hard Problems Solved

### Diff Position Mapping

GitHub's inline comment API doesn't accept line numbers — it requires a *position offset* within the diff itself. The chunker builds a position map from the raw patch format, tracking every added line's offset. Findings with unmapped positions are filtered out rather than failing silently.

### LLM Output Validation

LLMs hallucinate line numbers that don't exist in the diff. The prompt explicitly passes the list of valid line numbers, and the validator cross-checks every finding against the position map before it reaches the GitHub API.

### Idempotency

GitHub retries webhook deliveries on timeout. Without idempotency, the same commit gets reviewed multiple times and the PR gets flooded with duplicate comments. Each processed SHA is stored in Redis with a 7-day TTL — duplicate deliveries are detected and skipped in O(1).

### Crash Recovery

The idempotency key is only written after successful completion. If the pipeline crashes midway, the job retries cleanly from the beginning rather than being silently skipped.

---

## Project Structure

```
app/
├── webhook/
│   └── router.py          # GitHub webhook intake + signature verification
├── github/
│   └── service.py         # Diff fetching, inline comment posting
├── review/
│   ├── chunker.py         # Diff parser, position map builder
│   └── pipeline.py        # Review orchestration
├── llm/
│   └── service.py         # OpenRouter API, structured output, token tracking
├── worker/
│   └── tasks.py           # Celery task definition, DB persistence
├── db/
│   ├── database.py        # SQLAlchemy engine, session
│   ├── models.py          # Review + Finding models
│   └── init_db.py         # Table creation
├── dashboard/
│   └── router.py          # Live review dashboard
└── main.py                # FastAPI app, router registration
```

---

## Running Locally

**Prerequisites:** Docker, Python 3.11+, ngrok

### 1. Clone and install

```bash
git clone https://github.com/youssef667-y/code-review-agent
cd code-review-agent
python -m venv venv
venv\Scripts\activate  # Windows: use `source venv/bin/activate` on macOS/Linux
pip install -r requirements.txt
```

### 2. Configure environment

```bash
cp .env.example .env
# Fill in: GITHUB_TOKEN, GITHUB_WEBHOOK_SECRET, OPENROUTER_API_KEY, DATABASE_URL
```

### 3. Start infrastructure

```bash
docker-compose up -d
python -m app.db.init_db
```

### 4. Start the API server

```bash
uvicorn app.main:app --reload --port 3000
```

### 5. Start the worker

```bash
celery -A app.worker.tasks worker --loglevel=info -P solo
```

### 6. Expose via ngrok

```bash
ngrok http 3000
```

Then add the ngrok URL as a webhook on your GitHub repo:
- **Payload URL:** `https://your-ngrok-url/webhook/github`
- **Content type:** `application/json`
- **Events:** Pull requests only

Open a PR on your connected repo and watch the review appear automatically.

---

## Dashboard

Visit `http://localhost:3000/dashboard` to see:

- Total reviews and findings
- Findings breakdown by severity (`error` / `warning` / `style`)
- Findings breakdown by category (`security` / `logic` / `performance` / `style`)
- Token usage and estimated cost per session
- Full review history table

---

## Example Review Output

The agent posts a summary comment and inline comments for each finding:

```
[ERROR] Security — Line 23
SQL query concatenates user input directly, leading to SQL injection.
Suggestion: Use parameterized queries → cursor.execute("SELECT * FROM users WHERE name = ?", (name,))

[ERROR] Security — Line 51
Deserializing untrusted data with pickle can lead to remote code execution.
Suggestion: Use json.loads() for safe deserialization of untrusted input.
```

---

## Environment Variables

| Variable | Description |
|----------|-------------|
| `GITHUB_TOKEN` | GitHub Personal Access Token with `repo` scope |
| `GITHUB_WEBHOOK_SECRET` | Secret used to verify webhook signatures |
| `OPENROUTER_API_KEY` | OpenRouter API key for LLM access |
| `OPENROUTER_MODEL` | Model string, e.g. `openai/gpt-4o` |
| `DATABASE_URL` | PostgreSQL connection string |
| `REDIS_URL` | Redis connection string |
