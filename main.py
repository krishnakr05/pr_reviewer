from fastapi import FastAPI, Request, HTTPException
from google import genai
from dotenv import load_dotenv
import hmac, hashlib, os
import httpx

load_dotenv()

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
WEBHOOK_SECRET = os.getenv("WEBHOOK_SECRET")

gemini_client = genai.Client(api_key=GEMINI_API_KEY)

app = FastAPI()

def verify_signature(payload: bytes, signature: str) -> bool:
    expected = "sha256=" + hmac.new(
        WEBHOOK_SECRET.encode(),
        payload,
        hashlib.sha256
    ).hexdigest()
    return hmac.compare_digest(expected, signature)

@app.post("/webhook")
async def webhook(request: Request):
    payload = await request.body()
    sig = request.headers.get("X-Hub-Signature-256", "")

    if not verify_signature(payload, sig):
        raise HTTPException(status_code=401, detail="Invalid signature")

    data = await request.json()
    event = request.headers.get("X-GitHub-Event")

    if event == "pull_request" and data["action"] == "opened":
        pr_title = data["pull_request"]["title"]
        diff_url = data["pull_request"]["url"]
        comments_url = data["pull_request"]["comments_url"]
        review = await review_pr(diff_url, pr_title)
        print(f"Review generated:\n{review}")

        await post_comment(comments_url, review)

async def review_pr(diff_url: str, pr_title: str):
    async with httpx.AsyncClient() as client:
        diff_response = await client.get(diff_url, headers={
            "Accept": "application/vnd.github.v3.diff",
            "Authorization": f"token {GITHUB_TOKEN}"
        })
        diff = diff_response.text

    response = gemini_client.models.generate_content(
        model="gemini-2.5-flash",
        contents=f"Review this PR titled '{pr_title}'.\n\nCode diff:\n{diff}\n\nGive specific, actionable feedback on bugs, code quality, and improvements."
    )
    return response.text

async def post_comment(comments_url: str, review_text: str):
    async with httpx.AsyncClient() as client:
        await client.post(
            comments_url,
            headers={
                "Authorization": f"token {GITHUB_TOKEN}",
                "Accept": "application/vnd.github.v3+json"
            },
            json={"body": review_text}
        )