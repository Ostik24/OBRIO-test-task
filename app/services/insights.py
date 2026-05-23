from app.models.review import Review
import nltk
from nltk.corpus import stopwords
from sklearn.feature_extraction.text import CountVectorizer, TfidfVectorizer

nltk.download("wordnet", quiet=True)
nltk.download("omw-1.4", quiet=True)
nltk.download("stopwords", quiet=True)
from nltk.stem import WordNetLemmatizer
_lemmatizer = WordNetLemmatizer()


THEME_RULES = {
    "billing": {"refund", "charge", "subscription", "money", "paid", "cancel", "scam"},
    "matching": {"match", "swipe", "people", "bot", "fake"},
    "performance": {"crash", "bug", "buggy", "slow", "freeze", "loading"},
    "moderation": {"ban", "shadowban", "report", "blocked", "account"},
    "ads": {"ad", "advertising", "premium", "paywall"},
}


STOPWORDS = set(stopwords.words("english")) | {"app", "apps", "would", "really", "tinder", "people", "get", "even", "never", "see", "like", "use", "don", "dont", "im", "ive", "youre"}


def top_keywords(reviews: list[Review], n: int = 15) -> list[tuple[str, float]]:
    negatives = [r for r in reviews if r.sentiment == "negative" or r.rating <= 2]
    if not negatives:
        return []
    
    texts = []
    for r in negatives:
        tokens = []
        for tok in r.cleaned_content.split():
            tok = tok.strip(".,!?\"'()[]")
            if len(tok) > 2 and tok not in STOPWORDS:
                tok = _lemmatizer.lemmatize(tok)
                if tok not in STOPWORDS:
                    tokens.append(tok)
        texts.append(" ".join(tokens))
    
    vec = TfidfVectorizer(max_features=50, min_df=2)
    matrix = vec.fit_transform(texts)
    scores = matrix.sum(axis=0).A1  # total TF-IDF score per term
    pairs = list(zip(vec.get_feature_names_out(), scores.tolist()))
    return sorted(pairs, key=lambda x: -x[1])[:n]

def top_bigrams(reviews: list[Review], n: int = 15) -> list[tuple[str, int]]:
    negatives = [r for r in reviews if r.sentiment == "negative" or r.rating <= 2]
    if not negatives:
        return []
    texts = [r.cleaned_content for r in negatives]
    vec = CountVectorizer(
        ngram_range=(2, 2),
        stop_words=list(STOPWORDS),
        min_df=2,
    )
    matrix = vec.fit_transform(texts)
    counts = matrix.sum(axis=0).A1
    pairs = list(zip(vec.get_feature_names_out(), counts.tolist()))
    return sorted(pairs, key=lambda x: -x[1])[:n]

def themes(keywords: list[tuple[str, int]]) -> list[dict]:
    kw_dict = dict(keywords)
    results = []
    for theme, vocab in THEME_RULES.items():
        hits = {w: kw_dict[w] for w in vocab if w in kw_dict}
        if hits:
            results.append({
                "theme": theme,
                "weight": sum(hits.values()),
                "evidence": sorted(hits.items(), key=lambda x: -x[1]),
            })
    return sorted(results, key=lambda t: -t["weight"])


def generate_recommendations(reviews: list[Review]) -> list[str]:
    kws = top_keywords(reviews, n=30)
    th = themes(kws)
    out = []
    for t in th[:5]:
        out.append(f"Address concerns around theme {t['theme']} and top mentions are {', '.join(w for w,_ in t['evidence'][:5])}.")
    return out


def compute_insights(reviews: list[Review]) -> dict:
    from app.services.embeddings import classify_review_themes
    semantic_themes = classify_review_themes(reviews)
    bigrams = top_bigrams(reviews, n=15)

    try:
        from app.services.recommendations import generate_llm_recommendations
        recs = generate_llm_recommendations(semantic_themes, bigrams)
        if not recs:
            recs = generate_recommendations(reviews)
    except Exception as e:
        print(f"[warn] LLM recommendations failed, using templated fallback: {e}")
        recs = generate_recommendations(reviews)

    return {
        "negative_keywords": top_keywords(reviews, n=15),
        "negative_bigrams":  bigrams,
        "themes_rule_based": themes(top_keywords(reviews, n=100)),
        "themes_semantic":   semantic_themes,
        "recommendations":   recs,
    }



if __name__ == "__main__":
    from app.services.apple_reviews import fetch_reviews
    from app.services.sentiment import annotate
    reviews_test = fetch_reviews("547702041", limit=100)
    annotate(reviews_test)
    from pprint import pprint
    pprint(compute_insights(reviews_test))
