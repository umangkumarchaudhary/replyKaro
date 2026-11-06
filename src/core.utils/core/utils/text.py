# -*- coding: utf-8 -*-

"""

    Module :mod:`core.utils.text`

    Text helpers for simple keyword search.

"""

# ----------- START: Native Imports ---------- #
import re
# ----------- END: Native Imports ---------- #

__all__ = ["tokens"]

_WORD = re.compile(r"\w+")

# Filler words in English and Hinglish that carry no search meaning
STOPWORDS = frozenset(
    "the a an is are was of for to in on at and or what which how much many me my i you your "
    "price prices cost rate please tell "
    "kya hai hain ka ki ke ko me mein se aur kitna kitne kitni bata batao batado".split()
)


def tokens(text: str) -> set[str]:
    return {t for t in _WORD.findall(text.lower()) if len(t) > 1 and t not in STOPWORDS}
