# Apple Store Review Analysis API

## Quick start

```bash
# 1. Clone and enter
git clone https://github.com/Ostik24/OBRIO-test-task
cd OBRIO-test-task

# 2. Create venv and install
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# 3. (Optional) Set up Claude API key for LLM-generated recommendations
echo "ANTHROPIC_API_KEY=sk-ant-..." > .env

# 4. Run the API
python -m uvicorn app.api.main:app --reload

# 5. Open Swagger UI
open http://localhost:8000/docs
```

The API will warm up the embedding model on startup (~5 sec). If no `ANTHROPIC_API_KEY` is set, recommendations fall back to a templated version — the rest of the pipeline works fine without it.

---

## Try it

```bash
# Collect reviews for Tinder
curl -X POST http://localhost:8000/reviews/collect \
  -H "Content-Type: application/json" \
  -d '{"app_id": "547702041", "limit": 100}'

# Get metrics (avg rating, distributions)
curl http://localhost:8000/reviews/547702041/metrics

# Get insights (keywords, themes, recommendations)
curl http://localhost:8000/reviews/547702041/insights

# Download raw reviews (the first is JSON, the second is CSV formats)
curl http://localhost:8000/reviews/547702041/raw
curl "http://localhost:8000/reviews/547702041/raw?format=csv"
```

A pre-generated sample report is at [reports/tinder.md](reports/tinder.md).

---

## What this does

1. **Fetches reviews** from Apple's RSS customer reviews feed
2. **Cleans the text** - URLs, smart quotes, whitespace normalization
3. **Computes metrics** - avg rating, rating distribution, sentiment distribution
4. **Runs sentiment analysis** with VADER + a rating-based override for extreme mismatches
5. **Extracts keywords** from negative reviews using TF-IDF over lemmatized tokens
6. **Extracts bigrams** ("got banned", "fake profiles") for concrete complaint signals
7. **Classifies themes** using two parallel methods:
   - **Rule-based:** keyword matching against a hardcoded vocabulary (explainable baseline)
   - **Semantic:** sentence embeddings + cosine similarity (catches synonyms and paraphrases, and generally works better)
8. **Generates recommendations** with Claude Haiku, prompted with themes + bigrams

---

## Architecture diagram

![OBRIO Architecture](reports/obrio-architecture.drawio.svg)

---

## Design decisions

### Why Apple's RSS feed (and not the scraper libraries)

The original implementation used `app-store-scraper`, but that library hits Apple's `amp-api.apps.apple.com` endpoint, which now requires auth tokens it can't generate. Returns empty data silently.

The RSS feed (`itunes.apple.com/{country}/rss/customerreviews/...`) is older but still publicly accessible. It has its own problems (see "Known limitations" below), but still a solid solution.

### Why both rule-based AND semantic themes

**Rule-based** (`THEME_RULES` dict mapping themes to vocabulary):
- Pros: explainable, fast, deterministic, no model needed
- Cons: misses synonyms ("suspended" not in vocab -> moderation theme misses it)

**Semantic** (sentence embeddings + cosine similarity to theme descriptions):
- Pros: catches paraphrases, handles novel vocabulary, multi-assigns (one review can hit multiple themes)
- Cons: opaque ("0.412 cosine" is harder to defend than "matched 'banned'"), needs model

**Why ship both:** the report shows the same Tinder data through two lenses. Rule-based caught "ban" and "account" which are predictable. Semantic surfaced "suspended account", "kicked off platform", "shadow banned" which are paraphrases the rules would miss. Showing both demonstrates the engineering tradeoff rather than hiding it.

Per-theme cosine thresholds (`THEME_THRESHOLDS`) were hand-tuned by inspecting examples and adjusting until each bucket's top hits were genuinely on-topic.

### Why TF-IDF for keywords (not raw counts)

Raw frequency counts make common-but-uninformative words dominate. TF-IDF down-weights words that appear in many reviews (less distinctive) and up-weights words that appear often in fewer reviews (more characteristic).

Combined with lemmatization (`profiles` -> `profile`, `matches` -> `match`), top keywords surface the real complaints rather than the most-typed words.

### Why combine title + content for sentiment

VADER initially classified "Lack of Transparency" (a 1-star Tinder review) as **positive** because the body contained words like "trust", "believe", "deserve" which are all positive in isolation. The title carried the actual sentiment.

Combining `f"{r.title}. {r.content}"` for the VADER input fixed most of these mismatches without needing to upgrade to a transformer model.

### Why LLM-generated recommendations (and a fallback)

The templated version (`"Address concerns around theme X"`) was good but useless. Claude Haiku, given the same themes + bigrams, generates concrete PM-shippable tickets, for example:

> *"Implement a transparent ban appeal process with specific violation reasons and evidence shown to users, directly addressing the 36 moderation complaints..."*

---

## NLP methodology details

| Step | Method | Library |
|---|---|---|
| Text cleaning | URL strip, smart quote normalization, whitespace collapse | regex + `str.maketrans` |
| Sentiment | Lexicon-based polarity scoring on title+content | `vaderSentiment` |
| Sentiment override | Hard override on rating==1 (positive→negative) and rating==5 (negative→positive) | custom |
| Keywords | TF-IDF over lemmatized tokens, top by sum-of-scores | `sklearn.TfidfVectorizer`, `nltk.WordNetLemmatizer` |
| Bigrams | Bag-of-words with `min_df=2`, stopwords from NLTK + domain set | `sklearn.CountVectorizer`, `nltk.stopwords` |
| Themes (rule-based) | Vocabulary lookup against hardcoded `THEME_RULES` | custom |
| Themes (semantic) | Sentence embeddings + cosine similarity, multi-assign with per-theme thresholds | `sentence-transformers` (`all-MiniLM-L6-v2`), `sklearn.cosine_similarity` |
| Recommendations | Themes + bigrams → prompt → Claude Haiku 4.5 | `anthropic` |

---

## Known limitations

### Apple's RSS feed is genuinely unreliable

The feed has been on minimal maintenance since ~2020 and exhibits several failure modes:

- **Empty `entry` arrays during cache regeneration.** Apple caches each (app, country, page, sort) tuple separately. When a cache expires, the next request returns an empty array (not 404, not 429, just empty) while the regeneration job runs. Can last seconds to minutes.
- **Per-page inconsistency.** On a given fetch, pages 1, 7, 8, 9 may have data while pages 2-6 are empty.

**Handling:** `fetch_reviews` iterates all 10 pages (up to 50 reviews per page, so it is up to 500 reviews overall), skipping empty ones via `continue`, and stops early once `limit` is hit.

### Theme rules are domain-specific

`THEME_RULES` and `THEME_DESCRIPTIONS` are tuned for dating/subscription apps. Running on a calculator app would surface mostly empty themes. 

### Sentiment can show 0% neutral

For polarized review sets (like Tinder's 84% 1-star, 8% 5-star for the data of 100 reviews), VADER's narrow neutral band (`compound in [-0.05, +0.05]`) is rarely hit. Most multi-sentence reviews contain some polarity word. This isn't a bug, it reflects real-world reviewer self-selection bias (people leave reviews when they have strong feelings).

---

## What I tried that didn't work (or improvments I have made so far)

### Attempted: hardcoded `THEME_RULES` only

Initial themes were keyword-based. Worked but missed obvious synonyms ("suspended" not matching "moderation"). **Added semantic theme classification via sentence embeddings as a parallel method, kept both for comparison.**

### Attempted: VADER on content only

Missed strong signals from titles. **Combined `f"{r.title}. {r.content}"` for VADER input** was fixed most rating/sentiment mismatches.

---

## API reference

Open `http://localhost:8000/docs` for interactive Swagger UI. Summary:

### `POST /reviews/collect`

Fetch and cache reviews for an app.

**Body:**
```json
{
  "app_id": "547702041",     // required, numeric
  "country": "us",           // optional, 2-letter, default "us"
  "limit": 100               // optional, default 100
}
```

**Returns:** `{"app_id": ..., "country": ..., "fetched": ..., "cached": true}`

**Errors:**
- `422` — invalid input (non-numeric app_id, bad country code, etc.)
- `404` — app exists but no reviews available
- `502` — Apple's RSS feed returned an error

### `GET /reviews/{app_id}/metrics`

Returns rating + sentiment distributions for cached reviews.

### `GET /reviews/{app_id}/insights`

Returns keywords, bigrams, themes (both methods), and recommendations.

### `GET /reviews/{app_id}/raw`

Returns the raw cached reviews.

**Query params:**
- `format=json` (default) — JSON array
- `format=csv` — CSV download with `Content-Disposition` header

### `GET /health`

Returns `{"status": "ok"}`

---

## Running tests

```bash
pytest -v
```

Covers:
- `tests/test_metrics.py` — pure function tests for averages, distributions
- `tests/test_api.py` — endpoint smoke tests with mocked `fetch_reviews`
