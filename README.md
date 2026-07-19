# AI PR Reviewer

An AI-powered GitHub App that automatically reviews pull requests using Google's Gemini API. It listens for PR events via GitHub Webhooks, fetches the diff, grounds its feedback in the repository's own existing code style, and posts the review as a PR comment.

## What it does

1. Receives a GitHub webhook when a pull request is opened, verified via HMAC signature.
2. Fetches the PR's diff and list of changed files.
3. Retrieves the most stylistically similar existing files from the repo to use as style-grounding examples (see "RAG upgrade" below).
4. Sends the diff + style examples to Gemini (`gemini-2.5-flash`) with a prompt instructing it to review against the team's actual conventions, not generic best practices.
5. Posts the generated review as a comment on the PR.

## Tech stack

- **Python / FastAPI** — webhook server
- **Google Gemini API** — review generation (`gemini-2.5-flash`) and embeddings (`gemini-embedding-001`)
- **GitHub Apps API + Webhooks** — PR events, diff/content fetching, posting comments
- **ChromaDB** — vector database for embedding-based retrieval

## The RAG upgrade

**Problem:** the first version selected style-reference files with `candidates[:2]` — the first two repo files matching the changed file's extension, in whatever order the GitHub API happened to return them. This had no signal for whether those files were actually similar in style or purpose to the code being reviewed.

**Fix:** replaced that with a proper retrieval pipeline:
- On first PR review for a repo, existing files are embedded using Gemini's embedding model (`RETRIEVAL_DOCUMENT` task type) and stored in a per-repo ChromaDB collection (cosine similarity), persisted to disk so re-indexing only happens once per repo.
- At review time, the PR's diff is embedded using the same model (`CODE_RETRIEVAL_QUERY` task type) and used to query Chroma for the top-k most similar stored files.
- Those retrieved files replace the old hardcoded slice as the style-grounding context injected into the Gemini prompt.

**Evidence it works:** tested against a small fixture repo with two Flask-style route handlers (with try/except error handling) and one unrelated math utility file. Given a diff adding another route handler:

| File | Similarity distance |
|------|---------------------|
| `orders.py` (route handler) | 0.194 |
| `users.py` (route handler) | 0.209 |
| `math_helpers.py` (unrelated utility) | 0.426 |

The two stylistically relevant files were ranked clearly ahead of the unrelated one — roughly 2x the distance gap — confirming the retrieval is discriminating on actual content similarity, not just returning results in insertion order.

Validated end-to-end on a live PR against a real test repo: the retrieved reference file (`utils.py`) was correctly used to ground the review, which called out a missing-docstring inconsistency and quoted the exact docstring convention from the reference file as the standard to follow.

## Setup

1. Clone the repo and create a virtual environment:
   ```bash
   python -m venv venv
   .\venv\Scripts\activate   # Windows
   pip install -r requirements.txt
   ```
2. Create a `.env` file with:
   ```
   GEMINI_API_KEY=your_gemini_api_key
   GITHUB_TOKEN=your_github_token
   WEBHOOK_SECRET=your_webhook_secret
   ```
3. Register a GitHub App with the **Pull requests** webhook event enabled, and set its webhook URL to a local tunnel (e.g. [smee.io](https://smee.io) or ngrok) pointing at `/webhook`.
4. Run the server:
   ```bash
   uvicorn main:app --reload --port 8000
   ```
5. Forward webhooks (if using smee):
   ```bash
   smee -u https://smee.io/your-channel-id -t http://localhost:8000/webhook
   ```

## Project structure

```
main.py              # FastAPI app, webhook handler, review orchestration
app/
  embeddings.py       # Gemini embedding wrapper (Chroma-compatible)
  indexer.py          # Per-repo Chroma collection creation + indexing
  retriever.py        # Similarity search: diff -> top-k reference files
test_embeddings.py    # Sanity check for the embedding wrapper
test_rag.py           # Isolated indexing + retrieval test with fixture data
```

## Known limitations / next steps

- **Indexing only happens once per repo** (triggered by an empty Chroma collection). It doesn't currently re-index on new commits, so the reference set can go stale over time. Next step: trigger re-indexing on `push` webhook events for the default branch.
- **Diffs are embedded as raw unified-diff text** (including `+`/`-` markers and hunk headers), which is noisier than plain code. Stripping this down before embedding would likely improve retrieval precision.
- **No error handling around GitHub API failures** (rate limits, large repos, missing files) — a production version would need graceful fallbacks instead of letting these propagate as unhandled exceptions.
- **Whole files are embedded rather than chunks.** Fine for small-to-medium files; large files would benefit from function/class-level chunking so retrieval matches the relevant section rather than a diluted whole-file average.
- **Not yet deployed** — currently runs locally via webhook tunneling (smee/ngrok). Deploying to a persistent host would allow the GitHub App to be installed and demoed without a local server running.