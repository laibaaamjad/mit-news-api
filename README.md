# Selenium News Summarizer API (MIT Technology Review)

CSC418 DevOps for Cloud Computing, Lab Assignment 4

- **Registration:** SP23-BAI-019
- **News source:** #20, MIT Technology Review (`019 % 20 + 1 = 20`)
- **Language:** Python (Selenium + FastAPI)

## What it does

1. Opens MIT Technology Review's search page in headless **Google Chrome** with **Selenium** and **ChromeDriver**
2. Takes the **first search result** for the given keyword
3. Opens the article and extracts its text
4. Summarizes it with an extractive summarizer (`app/summarizer.py`)
5. Returns the result as JSON from `GET /get` on **port 7000**

## API

`GET /get?keyword=<keyword>`

```json
{
  "registration": "SP23-BAI-019",
  "newssource": "MIT Technology Review",
  "keyword": "quantum computing",
  "url": "https://www.technologyreview.com/...",
  "summary": "..."
}
```

`GET /` shows a web page with the registration number and a search box.

## Project structure

```
app/
  main.py         REST API (FastAPI), /get endpoint and home page
  scraper.py      Selenium automation (Chrome + ChromeDriver)
  summarizer.py   Summarization module
Dockerfile        Python + Google Chrome + ChromeDriver + code, starts API on 7000
requirements.txt
```

## Run with Docker

```bash
docker pull laibaaamjad/mit-news-api:v1
docker run -d -p 7000:7000 --shm-size=1g --name newsapi laibaaamjad/mit-news-api:v1
curl "http://localhost:7000/get?keyword=quantum%20computing"
```

## Build it yourself

```bash
docker build --platform linux/amd64 -t laibaaamjad/mit-news-api:v1 .
```
