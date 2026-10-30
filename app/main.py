import html
import logging
import os

from fastapi import FastAPI, Query
from fastapi.responses import HTMLResponse

from .scraper import NEWS_SOURCE, scrape
from .summarizer import summarize

REGISTRATION = os.getenv("REGISTRATION", "SP23-BAI-019")

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("news-api")

app = FastAPI(title=f"{NEWS_SOURCE} Selenium API", version="1.0")


def _response(keyword: str, url: str, summary: str) -> dict:
    return {
        "registration": REGISTRATION,
        "newssource": NEWS_SOURCE,
        "keyword": keyword,
        "url": url,
        "summary": summary,
    }


@app.get("/get")
def get_summary(keyword: str = Query(..., min_length=1, description="Search keyword")):
    keyword = keyword.strip()
    log.info("Request keyword=%r", keyword)
    try:
        article = scrape(keyword)
    except Exception as exc:  # keep the API answering even if a scrape fails
        log.exception("Scrape failed")
        return _response(keyword, "", f"Error while scraping: {type(exc).__name__}: {exc}")

    if not article:
        return _response(keyword, "", f"No search results found on {NEWS_SOURCE} for '{keyword}'.")

    summary = summarize(article["text"]) or article["title"]
    log.info("Done: %s", article["url"])
    return _response(keyword, article["url"], summary)


@app.get("/health")
def health():
    return {"status": "ok", "registration": REGISTRATION, "newssource": NEWS_SOURCE}


@app.get("/", response_class=HTMLResponse)
def home():
    reg = html.escape(REGISTRATION)
    src = html.escape(NEWS_SOURCE)
    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>News Summarizer API</title>
<style>
  body {{ font-family: system-ui, sans-serif; max-width: 760px; margin: 40px auto; padding: 0 16px; color: #1a1a1a; }}
  h1 {{ margin-bottom: 4px; }}
  .meta {{ background: #f3f4f6; border-radius: 8px; padding: 12px 16px; margin: 16px 0; }}
  .meta b {{ display: inline-block; width: 130px; }}
  form {{ display: flex; gap: 8px; }}
  input {{ flex: 1; padding: 10px; font-size: 16px; border: 1px solid #ccc; border-radius: 6px; }}
  button {{ padding: 10px 18px; font-size: 16px; border: 0; border-radius: 6px; background: #111; color: #fff; cursor: pointer; }}
  pre {{ background: #0f172a; color: #e2e8f0; padding: 16px; border-radius: 8px; white-space: pre-wrap; word-break: break-word; }}
  code {{ background: #f3f4f6; padding: 2px 6px; border-radius: 4px; }}
</style>
</head>
<body>
  <h1>Selenium News Summarizer</h1>
  <p>CSC418 DevOps for Cloud Computing, Lab Assignment 4</p>
  <div class="meta">
    <div><b>Registration:</b> {reg}</div>
    <div><b>News source:</b> {src}</div>
    <div><b>Endpoint:</b> <code>GET /get?keyword=&lt;keyword&gt;</code></div>
  </div>
  <form id="f">
    <input id="k" placeholder="Enter a keyword, e.g. quantum computing" required>
    <button>Search</button>
  </form>
  <pre id="out">Results will appear here (a search takes about 10 to 30 seconds).</pre>
<script>
  document.getElementById('f').addEventListener('submit', async (e) => {{
    e.preventDefault();
    const k = document.getElementById('k').value.trim();
    const out = document.getElementById('out');
    out.textContent = 'Searching ' + {src!r} + ' for "' + k + '"...';
    try {{
      const r = await fetch('/get?keyword=' + encodeURIComponent(k));
      out.textContent = JSON.stringify(await r.json(), null, 2);
    }} catch (err) {{
      out.textContent = 'Request failed: ' + err;
    }}
  }});
</script>
</body>
</html>"""
