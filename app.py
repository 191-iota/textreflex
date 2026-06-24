import os
import json
import re
import time
from flask import Flask, render_template, request, jsonify
import requests

app = Flask(__name__)

# textreflex is deliberately keyless: no API keys, no sign-ups, no per-user
# config. It runs on free, no-auth AI endpoints. Robustness comes from retrying
# with backoff (the free tiers rate-limit), not from paid fallbacks.
HTTP_TIMEOUT = int(os.environ.get("AI_TIMEOUT", "90"))
RETRIES = int(os.environ.get("AI_RETRIES", "3"))
MAX_LOG_LENGTH = 500

ANALYSIS_PROMPT = """Analyze the following text for emotional-manipulation strategies:
- Identify each strategy (fear, urgency, scapegoating, polarization, tone).
- Rate each on scale <none/low/mid/high/very high: why>.
- Provide the exact character or sentence ranges for each rating.
- Call out any false or misleading ("BS") claims with brief reasoning and ranges.
- List the top three most manipulative passages under "top_passages".
Be ultra-concise. Output ONLY valid JSON matching this schema exactly:

{
  "ratings": { /* strategy: "level: short label" */ },
  "passages": { /* strategy: "start-end" */ },
  "bs_callout": "yes/no",
  "bs_passage": "start-end",
  "top_passages": ["start-end", ...],
  "conclusion": "cold logic meta analysis about the ulterior manipulative motive OF THE TEXT what does the text as a whole try to achieve here? how does it try to change the perception of the reader? should be meta motive analysis not a rhethorical analysis"
}"""

SYSTEM_PROMPT = (
    "You must output ONLY valid JSON. Do not include markdown code fences or any "
    "explanatory text, just the raw JSON object."
)


def _models(env_var, defaults):
    """Model candidates: a comma-separated env override, else the defaults."""
    override = os.environ.get(env_var)
    source = override.split(",") if override else defaults
    return [m.strip() for m in source if m.strip()]


# Keyless providers, tried in order. All speak the OpenAI chat-completions format.
# Only Pollinations offers a genuinely keyless, high-quality endpoint today; the
# list is kept open so another keyless source can drop in as a single entry.
# An optional POLLINATIONS_TOKEN only raises rate limits — it is never required.
PROVIDERS = [
    {
        "name": "pollinations",
        "url": "https://text.pollinations.ai/openai",
        "token_env": "POLLINATIONS_TOKEN",
        "models": lambda: _models("POLLINATIONS_MODEL", ["openai-fast", "openai"]),
    },
]

# Errors worth retrying after a short wait (rate limits, transient server faults).
RETRY_STATUS = {429, 500, 502, 503, 504}


def call_provider(p, model, messages):
    """One OpenAI-compatible chat-completions call. Returns the requests.Response."""
    headers = {"Content-Type": "application/json"}
    token = os.environ.get(p.get("token_env", "")) if p.get("token_env") else None
    if token:
        headers["Authorization"] = f"Bearer {token}"
    payload = {"model": model, "messages": messages, "temperature": 0.3, "max_tokens": 4096}
    # The keyless model is a GPT-OSS reasoning model; without this it spends the
    # whole token budget "thinking" and never emits the JSON.
    if "gpt-oss" in model.lower() or "openai" in model.lower() or p["name"] == "pollinations":
        payload["reasoning_effort"] = "low"
    return requests.post(p["url"], headers=headers, json=payload, timeout=HTTP_TIMEOUT)


def extract_content(resp):
    """Pull the assistant text out of an OpenAI-style (or plain-text) response."""
    try:
        data = resp.json()
    except ValueError:
        return resp.text.strip()
    if isinstance(data, dict):
        choices = data.get("choices")
        if choices:
            msg = choices[0].get("message", {}) or {}
            if msg.get("content"):
                return msg["content"].strip()
            for k in ("reasoning_content", "reasoning"):
                if msg.get(k):
                    return str(msg[k])
        if data.get("content"):
            return str(data["content"])
    return resp.text.strip()


def parse_result(content):
    """Turn a model's text into the analysis dict, or None if it isn't usable JSON."""
    if not content:
        return None
    s = content.strip()
    s = re.sub(r"^```(?:json)?\s*", "", s).strip()
    s = re.sub(r"\s*```$", "", s).strip()

    obj = None
    try:
        obj = json.loads(s)
    except json.JSONDecodeError:
        start, end = s.find("{"), s.rfind("}")
        if start != -1 and end != -1 and end > start:
            try:
                obj = json.loads(s[start:end + 1])
            except json.JSONDecodeError:
                return None
    if not isinstance(obj, dict):
        return None
    if not any(k in obj for k in ("ratings", "passages", "conclusion")):
        return None

    obj.setdefault("ratings", {})
    obj.setdefault("passages", {})
    obj.setdefault("conclusion", "N/A")
    obj.setdefault("bs_callout", "no")
    obj.setdefault("bs_passage", "")
    obj.setdefault("top_passages", [])
    return obj


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/analyze", methods=["POST"])
def analyze():
    data = request.get_json(silent=True)
    if not data or "text" not in data:
        return jsonify({"error": "No text provided"}), 400
    text = data["text"].strip()
    if not text:
        return jsonify({"error": "Empty text provided"}), 400
    if len(text) > 5000:
        return jsonify({"error": "Text exceeds 5000 character limit"}), 400

    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": f"{ANALYSIS_PROMPT}\n\nText to analyze:\n{text}"},
    ]

    attempts = []
    for p in PROVIDERS:
        for model in p["models"]():
            label = f"{p['name']}/{model}"
            resp = None
            for attempt in range(max(1, RETRIES)):
                try:
                    r = call_provider(p, model, messages)
                except requests.RequestException as e:
                    attempts.append(f"{label}: {type(e).__name__} (try {attempt + 1})")
                    time.sleep(1.5 * (attempt + 1))
                    continue
                if r.status_code in RETRY_STATUS:
                    attempts.append(f"{label}: HTTP {r.status_code} (try {attempt + 1})")
                    app.logger.warning(f"{label} -> {r.status_code}, retrying")
                    time.sleep(1.5 * (attempt + 1))
                    continue
                resp = r
                break

            if resp is None:
                continue
            if resp.status_code != 200:
                attempts.append(f"{label}: HTTP {resp.status_code}")
                app.logger.warning(f"{label} -> {resp.status_code}: {resp.text[:MAX_LOG_LENGTH]}")
                continue

            result = parse_result(extract_content(resp))
            if result is not None:
                app.logger.info(f"analysis served by {label}")
                return jsonify(result)
            attempts.append(f"{label}: unparseable output")

    return jsonify({
        "error": "The free AI service is busy right now. Please try again in a few seconds.",
        "attempts": attempts[:12],
    }), 502


if __name__ == "__main__":
    debug_mode = os.environ.get("FLASK_DEBUG", "False").lower() in ("true", "1", "yes")
    port = int(os.environ.get("PORT", "5000"))
    app.run(debug=debug_mode, host="0.0.0.0", port=port)
