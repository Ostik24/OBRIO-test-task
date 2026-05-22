from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity
from app.models.review import Review

_model = SentenceTransformer("all-MiniLM-L6-v2")

THEME_THRESHOLDS = {
    "billing":     0.35,
    "matching":    0.40,
    "performance": 0.30,
    "moderation":  0.40,
    "ads":         0.35,
    "ui_ux":       0.40,
    "support":     0.35,
}

THEME_DESCRIPTIONS = {
    "billing":     "complaints about money, subscriptions, refunds, charges, payments, scams",
    "matching": "complaints about not getting matches, fake profiles, bots, swipes left/right, distance filters",
    "performance": "complaints about crashes, bugs, slowness, loading, freezing",
    "moderation":  "complaints about being banned, suspended, blocked, locked out, account issues",
    "ads":         "complaints about advertisements, premium features, paywalls",
    "ui_ux":       "complaints about confusing interface, design, navigation",
    "support":     "complaints about customer service, no response, ignored",
}

_theme_vecs = _model.encode(list(THEME_DESCRIPTIONS.values()))
_theme_names = list(THEME_DESCRIPTIONS.keys())


def classify_review_themes(reviews: list[Review]) -> dict:
    negatives = [r for r in reviews if r.sentiment == "negative" or r.rating <= 2]
    if not negatives:
        return {}

    texts = [
        f"{r.title}. {r.cleaned_content}".strip(". ")
        for r in negatives
        if r.cleaned_content or r.title
    ]

    if not texts:
        return {}

    review_vecs = _model.encode(texts)
    similarities = cosine_similarity(review_vecs, _theme_vecs)

    theme_hits = {name: [] for name in _theme_names}
    for review_text, sim_row in zip(texts, similarities):
        for idx, score in enumerate(sim_row):
            theme = _theme_names[idx]
            if score >= THEME_THRESHOLDS.get(theme, 0.35):
                theme_hits[theme].append({
                    "review": review_text[:120],
                    "score": round(float(score), 3),
                })

    return {
        name: {
            "count": len(hits),
            "examples": sorted(hits, key=lambda x: -x["score"])[:3],
        }
        for name, hits in theme_hits.items()
        if hits
    }
