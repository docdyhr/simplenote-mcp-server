"""Fuzzy string matching for search queries.

Provides approximate string matching using difflib.SequenceMatcher
to handle typos and near-matches in search terms.
"""

import re
from difflib import SequenceMatcher


class FuzzyMatcher:
    """Fuzzy string matcher using sequence similarity.

    Uses difflib.SequenceMatcher to find approximate matches between
    search terms and content words. Terms shorter than 3 characters
    use exact matching only.
    """

    def __init__(self, threshold: float = 0.75) -> None:
        """Initialize the fuzzy matcher.

        Args:
            threshold: Minimum similarity ratio (0.0-1.0) for a match.
                       Default 0.75 balances typo tolerance with precision.
        """
        self.threshold = max(0.0, min(1.0, threshold))

    def fuzzy_contains(self, content: str, term: str) -> bool:
        """Check if content contains a fuzzy match for the term.

        Args:
            content: The text to search within.
            term: The search term to match.

        Returns:
            True if any word in content matches the term above threshold.
        """
        if not content or not term:
            return False

        # Short terms (< 3 chars) require exact match — too many false positives
        if len(term) < 3:
            return term.lower() in content.lower()

        term_lower = term.lower()
        words = self._extract_words(content)

        for word in words:
            if len(word) < 2:
                continue
            ratio = SequenceMatcher(None, term_lower, word).ratio()
            if ratio >= self.threshold:
                return True

        return False

    def fuzzy_score(self, content: str, term: str) -> float:
        """Get the best fuzzy match score for a term in content.

        Args:
            content: The text to search within.
            term: The search term to score.

        Returns:
            Best similarity ratio found (0.0-1.0), or 0.0 if no match.
        """
        if not content or not term:
            return 0.0

        if len(term) < 3:
            return 1.0 if term.lower() in content.lower() else 0.0

        term_lower = term.lower()
        words = self._extract_words(content)
        best_ratio = 0.0

        for word in words:
            if len(word) < 2:
                continue
            ratio = SequenceMatcher(None, term_lower, word).ratio()
            if ratio > best_ratio:
                best_ratio = ratio
                if ratio >= 1.0:
                    break  # Perfect match, no need to continue

        return best_ratio

    def fuzzy_contains_phrase(self, content: str, phrase: str) -> bool:
        """Check if content contains a fuzzy match for a multi-word phrase.

        Each word in the phrase must fuzzy-match a word in the content.

        Args:
            content: The text to search within.
            phrase: The multi-word phrase to match.

        Returns:
            True if all words in the phrase have fuzzy matches in content.
        """
        if not content or not phrase:
            return False

        phrase_words = phrase.lower().split()
        if not phrase_words:
            return False

        return all(self.fuzzy_contains(content, word) for word in phrase_words)

    @staticmethod
    def _extract_words(text: str) -> list[str]:
        """Extract lowercase words from text.

        Args:
            text: The text to extract words from.

        Returns:
            List of lowercase words.
        """
        return re.findall(r"\b\w+\b", text.lower())


# Module-level default instance
_default_matcher: FuzzyMatcher | None = None


def get_fuzzy_matcher(threshold: float = 0.75) -> FuzzyMatcher:
    """Get a FuzzyMatcher instance with the given threshold.

    Reuses a cached instance if the threshold matches the default.

    Args:
        threshold: Similarity threshold.

    Returns:
        A FuzzyMatcher instance.
    """
    global _default_matcher
    if threshold == 0.75 and _default_matcher is not None:
        return _default_matcher
    matcher = FuzzyMatcher(threshold)
    if threshold == 0.75:
        _default_matcher = matcher
    return matcher
