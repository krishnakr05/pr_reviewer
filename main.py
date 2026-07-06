from fastapi import FastAPI, Request, HTTPException
from google import genai
from dotenv import load_dotenv
import hmac, hashlib, os
import httpx
import base64

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
        changed_files = await get_changed_filenames(diff_url)
        print(f"Changed files: {changed_files}")
        repo_full_name = data["pull_request"]["base"]["repo"]["full_name"]
        default_branch = data["pull_request"]["base"]["repo"]["default_branch"]

        reference_files = await get_reference_files(repo_full_name, default_branch, changed_files)
        print(f"Reference files: {[f['path'] for f in reference_files]}")
        comments_url = data["pull_request"]["comments_url"]
        review = await review_pr(diff_url, pr_title, reference_files)
        print(f"Review generated:\n{review}")

        await post_comment(comments_url, review)

async def review_pr(diff_url: str, pr_title: str, reference_files: list[dict]):
    # Fetch the diff (same as before)
    async with httpx.AsyncClient() as client:
        diff_response = await client.get(diff_url, headers={
            "Accept": "application/vnd.github.v3.diff",
            "Authorization": f"token {GITHUB_TOKEN}"
        })
        diff = diff_response.text

    # Build the style examples block from reference files
    if reference_files:
        examples = "\n\n".join(
            f"File: {f['path']}\n{f['content']}"
            for f in reference_files
        )
        style_section = (
            "Here are some existing files from this repository.\n"
            "Study them to understand how this team writes code — "
            "their naming style, docstring format, and structure.\n"
            "Use this as your standard when reviewing, not generic best practices.\n\n"
            f"{examples}\n\n"
            "---\n\n"
        )
    else:
        style_section = ""  # no examples found, skip this section

    # Send to Gemini
    prompt = (
        f"{style_section}"
        f"Now review this PR titled '{pr_title}'.\n\n"
        f"Code diff:\n{diff}\n\n"
        "Give specific, actionable feedback. "
        "Where relevant, point out deviations from the style shown above."
    )

    response = gemini_client.models.generate_content(
        model="gemini-2.5-flash",
        contents=prompt
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

async def get_changed_filenames(pr_url: str) -> list[str]:
    async with httpx.AsyncClient() as client:
        resp = await client.get(
            f"{pr_url}/files",           
            headers={
                "Authorization": f"token {GITHUB_TOKEN}",
                "Accept": "application/vnd.github.v3+json"
            }
        )
    files = resp.json()                  
    return [f["filename"] for f in files]  


async def get_reference_files(repo_full_name: str, default_branch: str,
                               changed_files: list[str]) -> list[dict]:

    async with httpx.AsyncClient() as client:
        headers = {
            "Authorization": f"token {GITHUB_TOKEN}",
            "Accept": "application/vnd.github.v3+json"
        }

        # 1. Get every file path in the repo (one API call)
        tree_resp = await client.get(
            f"https://api.github.com/repos/{repo_full_name}/git/trees/{default_branch}",
            headers=headers,
            params={"recursive": "1"}
        )
        tree = tree_resp.json().get("tree", [])

        # 2. Find which extensions the changed files use (e.g. "py")
        extensions = {f.split(".")[-1] for f in changed_files if "." in f}

        # 3. Filter the repo's files: same extension, not in the PR, not too big
        candidates = [
            item["path"] for item in tree
            if item["type"] == "blob"                          # only files, not folders
            and item["path"].split(".")[-1] in extensions      # same extension
            and item["path"] not in changed_files              # not already in this PR
            and item.get("size", 0) < 20_000                  # skip very large files
        ]

        # 4. Pick the first 2 and fetch their contents
        reference_files = []
        for path in candidates[:2]:
            content_resp = await client.get(
                f"https://api.github.com/repos/{repo_full_name}/contents/{path}",
                headers=headers,
                params={"ref": default_branch}
            )
            content_data = content_resp.json()

            if "content" in content_data:
                decoded = base64.b64decode(content_data["content"]).decode("utf-8", errors="ignore")
                reference_files.append({
                    "path": path,
                    "content": decoded[:3000]   # cap length so we don't waste tokens
                })

    return reference_files