import re

URL_RE = re.compile(r"https?://\S+|www\.\S+")
WHITESPACE_RE = re.compile(r"\s+")

QUOTE_MAP = str.maketrans({
    "\u2019": "'", "\u2018": "'",
    "\u201c": '"', "\u201d": '"',
    "\u2013": "-", "\u2014": "-",
})

def clean_review_text(text: str) -> str:
    if not text:
        return ""
    text = text.translate(QUOTE_MAP)
    text = text.lower()
    text = URL_RE.sub(" ", text)
    text = WHITESPACE_RE.sub(" ", text).strip()
    return text


if __name__ == "__main__":
    test_text = "Hello, world!    This is a test.    https://www.google.com"
    print("raw:    ", test_text)
    print("cleaned:", clean_review_text(test_text))
