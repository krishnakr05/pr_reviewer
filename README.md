# AI PR Reviewer

A GitHub App that automatically reviews pull requests using an LLM (Gemini).

## How it works
1. GitHub sends a webhook when a PR is opened
2. The server verifies the webhook signature
3. It fetches the PR diff and sends it to Gemini for review
4. The AI-generated review is posted back as a PR comment

## Stack
- FastAPI (Python)
- Google Gemini API
- GitHub Apps + Webhooks

## Status
MVP complete. Next: style-aware reviews using embeddings.
