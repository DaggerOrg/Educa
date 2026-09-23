"""Checks that a specialist's `evidence_quote` really appears in the chapter.

Models paraphrase when asked to quote, and a citation that isn't in the book
is worse than none. Extracted PDF text also has line breaks mid-word,
hyphenation, and ligatures (`ﬁ`), so both sides are reduced to bare
lowercase letters and digits before comparing -- strict enough to catch a
paraphrase, loose enough not to reject a correct quote over layout noise.
"""

import re
import unicodedata

MIN_QUOTE_CHARS = 12  # shorter than this matches almost anything
_NON_ALNUM = re.compile(r"[\W_]+")


def _squash(text: str) -> str:
    return _NON_ALNUM.sub("", unicodedata.normalize("NFKC", text).casefold())


def is_grounded(quote: str, source_text: str) -> bool:
    squashed = _squash(quote)
    return len(squashed) >= MIN_QUOTE_CHARS and squashed in _squash(source_text)
