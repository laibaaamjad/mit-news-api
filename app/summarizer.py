"""
Summarization module: frequency-based extractive summarizer.

Pure Python with no model downloads, so the Docker image stays small and starts fast.
It scores each sentence by how many important (non-stopword) words it contains,
then returns the top-scoring sentences in their original order.
"""
import re
from collections import Counter

STOPWORDS = set("""
a about above after again against all also am an and any are aren't as at be because been
before being below between both but by can can't cannot could couldn't did didn't do does
doesn't doing don't down during each even few for from further get gets got had hadn't has
hasn't have haven't having he he'd he'll he's her here here's hers herself him himself his
how how's however i i'd i'll i'm i've if in into is isn't it it's its itself just let's like
made make many may me might more most much must mustn't my myself new no nor not now of off
on once one only or other ought our ours ourselves out over own really said same say says
she she'd she'll she's should shouldn't so some still such than that that's the their theirs
them themselves then there there's these they they'd they'll they're they've this those
through to too two under until up us very was wasn't we we'd we'll we're we've were weren't
what what's when when's where where's which while who who's whom why why's will with won't
would wouldn't year years you you'd you'll you're you've your yours yourself yourselves
""".split())

_SENT_SPLIT = re.compile(r"(?<=[.!?])[\"')\]]*\s+(?=[A-Z0-9\"'(\[])")
_WORD = re.compile(r"[a-zA-Z][a-zA-Z'-]+")


def split_sentences(text: str) -> list[str]:
    sentences = []
    for para in text.split("\n"):
        para = para.strip()
        if not para:
            continue
        sentences.extend(s.strip() for s in _SENT_SPLIT.split(para) if s.strip())
    return sentences


def summarize(text: str, max_sentences: int = 5) -> str:
    text = (text or "").strip()
    if not text:
        return ""

    sentences = split_sentences(text)
    if len(sentences) <= max_sentences:
        return " ".join(sentences)

    words = [w.lower() for w in _WORD.findall(text)]
    freq = Counter(w for w in words if w not in STOPWORDS and len(w) > 2)
    if not freq:
        return " ".join(sentences[:max_sentences])

    top = max(freq.values())
    weights = {w: c / top for w, c in freq.items()}

    scores = []
    for i, s in enumerate(sentences):
        tokens = [w.lower() for w in _WORD.findall(s)]
        if len(tokens) < 6:  # skip fragments, captions, bylines
            scores.append((0.0, i))
            continue
        score = sum(weights.get(t, 0) for t in tokens) / (len(tokens) ** 0.7)
        if i < 3:  # news articles front-load key facts
            score *= 1.25
        scores.append((score, i))

    best = sorted(scores, reverse=True)[:max_sentences]
    chosen = sorted(i for _, i in best)
    return " ".join(sentences[i] for i in chosen)
