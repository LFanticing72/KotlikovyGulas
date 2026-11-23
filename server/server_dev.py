import os
import json
import base64
import requests
from flask import Flask, request, jsonify
from flask_cors import CORS
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
CORS(app)

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

MODEL        = os.getenv("OPENAI_MODEL", "gpt-5.4")
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
REPO         = os.getenv("GITHUB_REPO", "LFanticing72/helf")
BRANCH       = os.getenv("GITHUB_BRANCH", "main")

SYSTEM_PROMPT = "Perform well, do not overcomplicate things."
MAX_HISTORY   = 20

BASE_DIR      = os.path.dirname(os.path.abspath(__file__))
CHAT_HISTORY  = os.path.join(BASE_DIR, "conversation.json")
COUNTER_FILE  = os.path.join(BASE_DIR, "counter.txt")


# ── history (local JSON) ──────────────────────────────────────────────────────

def load_history() -> list:
    if not os.path.exists(CHAT_HISTORY):
        return []
    with open(CHAT_HISTORY, encoding="utf-8") as f:
        return json.load(f).get("messages", [])

def save_history(messages: list):
    with open(CHAT_HISTORY, "w", encoding="utf-8") as f:
        json.dump({"messages": messages}, f, indent=2, ensure_ascii=False)

def api_messages(full: list) -> list:
    system = [m for m in full if m["role"] == "system"]
    rest   = [m for m in full if m["role"] != "system"]
    return system + rest[-MAX_HISTORY:]


# ── GitHub ────────────────────────────────────────────────────────────────────

def get_next_number() -> int:
    if not os.path.exists(COUNTER_FILE):
        with open(COUNTER_FILE, "w") as f:
            f.write("1")
        return 1
    with open(COUNTER_FILE) as f:
        num = int(f.read().strip())
    with open(COUNTER_FILE, "w") as f:
        f.write(str(num + 1))
    return num

def upload_to_github(content: str, github_path: str):
    encoded = base64.b64encode(content.encode()).decode()
    url  = f"https://api.github.com/repos/{REPO}/contents/{github_path}"
    resp = requests.put(
        url,
        json={"message": f"Add {github_path}", "content": encoded, "branch": BRANCH},
        headers={"Authorization": f"token {GITHUB_TOKEN}", "Accept": "application/vnd.github+json"},
    )
    return resp.status_code, resp.json()


# ── routes ────────────────────────────────────────────────────────────────────

@app.route("/chat", methods=["POST"])
def chat():
    prompt = request.get_json().get("prompt", "")

    full = load_history()
    if not full:
        full.append({"role": "system", "content": SYSTEM_PROMPT})

    to_send  = api_messages(full) + [{"role": "user", "content": prompt}]
    response = client.chat.completions.create(model=MODEL, messages=to_send)
    reply    = response.choices[0].message.content

    full.append({"role": "user",      "content": prompt})
    full.append({"role": "assistant", "content": reply})
    save_history(full)

    return jsonify({"response": reply})


@app.route("/upload-image", methods=["POST"])
def upload_image():
    if not request.files:
        return jsonify({"error": "No file uploaded"}), 400

    img      = next(iter(request.files.values()))
    img_b64  = base64.b64encode(img.read()).decode()
    ext      = os.path.splitext(img.filename or "")[1].lower()
    mime     = {".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".png": "image/png",
                ".gif": "image/gif",  ".webp": "image/webp"}.get(ext, "image/jpeg")

    try:
        resp = client.chat.completions.create(
            model=MODEL,
            messages=[{"role": "user", "content": [
                {"type": "text", "text": (
                    "Extract all text from this image. "
                    "Restore diacritics, fix spacing and formatting, "
                    "and rebuild the document structure without changing meaning."
                )},
                {"type": "image_url", "image_url": {"url": f"data:{mime};base64,{img_b64}"}},
            ]}],
        )
        cleaned_text = resp.choices[0].message.content
    except Exception as e:
        return jsonify({"error": f"GPT vision failed: {e}"}), 500

    count = get_next_number()
    gh_status, gh_resp = upload_to_github(cleaned_text, f"image{count}_cleaned.txt")

    full = load_history()
    if not full:
        full.append({"role": "system", "content": SYSTEM_PROMPT})
    full.append({"role": "user", "content": f"[OCR image{count}]\n{cleaned_text}"})
    save_history(full)

    return jsonify({
        "status": "ok",
        "saved_as": f"image{count}",
        "cleaned_text": cleaned_text,
        "github_status": gh_status,
        "github_response": gh_resp,
    })


@app.route("/health")
def health():
    return jsonify({"status": "ok"})


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5002, debug=True)
