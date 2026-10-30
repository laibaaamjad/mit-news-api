"""
Selenium scraper for MIT Technology Review (news source #20).

Flow: open the site's search page for a keyword -> take the FIRST search
result -> open the article -> extract its title and body text.
"""
import os
import re
import threading
import time
from urllib.parse import quote_plus

from selenium import webdriver
from selenium.common.exceptions import (
    StaleElementReferenceException,
    TimeoutException,
    WebDriverException,
)
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

NEWS_SOURCE = "MIT Technology Review"
BASE_URL = "https://www.technologyreview.com"

# Search page URLs to try, in order
SEARCH_URLS = [
    BASE_URL + "/search/?s={q}",
    BASE_URL + "/?s={q}",
]

# MIT TR article URLs look like: /2026/10/29/1234567/some-article-slug/
ARTICLE_RE = re.compile(
    r"^https?://(www\.)?technologyreview\.com/\d{4}/\d{2}/\d{2}/\d+/[^/?#]+"
)

# Selectors for the results list (most specific first). "main a" is only
# used as a fallback after a few seconds, once results have had time to render.
RESULT_SELECTORS = [
    "[class*='searchResult'] a",
    "[class*='SearchResult'] a",
    "[class*='search-result'] a",
    "[class*='results'] a",
]
GENERIC_SELECTOR = "main a"

# Article body selectors (most specific first)
BODY_SELECTORS = [
    "[class*='contentBody'] p",
    "[class*='articleBody'] p",
    "[class*='gutenbergContent'] p",
    "article p",
    "main p",
]

CHROMEDRIVER_PATH = os.getenv("CHROMEDRIVER_PATH", "/usr/local/bin/chromedriver")
USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36"
)

# At most 2 Chrome instances at once so the container doesn't run out of memory
_browser_slots = threading.Semaphore(2)


def make_driver() -> webdriver.Chrome:
    opts = webdriver.ChromeOptions()
    opts.add_argument("--headless=new")
    opts.add_argument("--no-sandbox")
    opts.add_argument("--disable-dev-shm-usage")
    opts.add_argument("--disable-gpu")
    opts.add_argument("--window-size=1366,900")
    opts.add_argument(f"--user-agent={USER_AGENT}")
    opts.page_load_strategy = "eager"  # don't wait for ads/trackers

    chrome_bin = os.getenv("CHROME_BIN")
    if chrome_bin:
        opts.binary_location = chrome_bin

    # In Docker we use the ChromeDriver baked into the image;
    # locally, Selenium Manager downloads a matching driver automatically.
    if os.path.exists(CHROMEDRIVER_PATH):
        service = Service(CHROMEDRIVER_PATH)
    else:
        service = Service()

    driver = webdriver.Chrome(service=service, options=opts)
    driver.set_page_load_timeout(45)
    return driver


def _article_links(driver, css: str) -> list[str]:
    links: list[str] = []
    for a in driver.find_elements(By.CSS_SELECTOR, css):
        try:
            href = (a.get_attribute("href") or "").split("?")[0].split("#")[0]
        except StaleElementReferenceException:
            continue
        if ARTICLE_RE.match(href) and href not in links:
            links.append(href)
    return links


def _wait_for_first_result(driver, timeout: int = 20) -> str | None:
    start = time.time()
    while time.time() - start < timeout:
        for css in RESULT_SELECTORS:
            links = _article_links(driver, css)
            if links:
                return links[0]
        if time.time() - start > 8:  # results container not found by class; fall back
            links = _article_links(driver, GENERIC_SELECTOR)
            if links:
                return links[0]
        time.sleep(1)
    return None


def find_first_result(driver, keyword: str) -> str | None:
    for template in SEARCH_URLS:
        url = template.format(q=quote_plus(keyword))
        try:
            driver.get(url)
        except TimeoutException:
            pass  # page may still be usable with eager loading
        link = _wait_for_first_result(driver)
        if link:
            return link
    return None


def extract_article(driver, url: str) -> dict:
    try:
        driver.get(url)
    except TimeoutException:
        pass
    try:
        WebDriverWait(driver, 15).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "p"))
        )
    except TimeoutException:
        pass

    titles = driver.find_elements(By.TAG_NAME, "h1")
    title = titles[0].text.strip() if titles and titles[0].text.strip() else driver.title

    paragraphs: list[str] = []
    for css in BODY_SELECTORS:
        texts = []
        for p in driver.find_elements(By.CSS_SELECTOR, css):
            try:
                t = p.text.strip()
            except StaleElementReferenceException:
                continue
            if len(t) > 40:
                texts.append(t)
        if sum(len(t) for t in texts) > 300:
            paragraphs = texts
            break

    text = "\n".join(paragraphs)

    # Last resort: the page's meta description
    if not text:
        metas = driver.find_elements(By.CSS_SELECTOR, "meta[name='description'], meta[property='og:description']")
        if metas:
            text = metas[0].get_attribute("content") or ""

    return {"url": url, "title": title, "text": text}


def scrape(keyword: str) -> dict | None:
    """Return {'url', 'title', 'text'} for the first search result, or None."""
    with _browser_slots:
        driver = make_driver()
        try:
            link = find_first_result(driver, keyword)
            if not link:
                return None
            return extract_article(driver, link)
        finally:
            try:
                driver.quit()
            except WebDriverException:
                pass
