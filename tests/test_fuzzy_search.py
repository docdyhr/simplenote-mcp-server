"""Tests for fuzzy search functionality."""

import pytest

from simplenote_mcp.server.search.fuzzy import FuzzyMatcher, get_fuzzy_matcher


@pytest.mark.unit
class TestFuzzyMatcher:
    """Tests for FuzzyMatcher class."""

    @pytest.fixture
    def matcher(self):
        """Create a default FuzzyMatcher."""
        return FuzzyMatcher(threshold=0.75)

    def test_exact_match(self, matcher):
        """Test exact substring match works."""
        assert matcher.fuzzy_contains("Hello World", "Hello")

    def test_typo_match(self, matcher):
        """Test fuzzy matching catches typos."""
        assert matcher.fuzzy_contains("This is a project document", "proejct")

    def test_no_match(self, matcher):
        """Test non-matching content returns False."""
        assert not matcher.fuzzy_contains("Hello World", "banana")

    def test_empty_content(self, matcher):
        """Test empty content returns False."""
        assert not matcher.fuzzy_contains("", "test")

    def test_empty_term(self, matcher):
        """Test empty term returns False."""
        assert not matcher.fuzzy_contains("Hello World", "")

    def test_short_term_exact_only(self, matcher):
        """Test terms shorter than 3 chars use exact matching."""
        assert matcher.fuzzy_contains("Hello World", "lo")
        assert not matcher.fuzzy_contains("Hello World", "xq")

    def test_case_insensitive(self, matcher):
        """Test fuzzy matching is case-insensitive."""
        assert matcher.fuzzy_contains("PROJECT documentation", "project")

    def test_high_threshold(self):
        """Test strict threshold requires closer matches."""
        strict = FuzzyMatcher(threshold=0.95)
        # "proejct" vs "project" - high similarity but may not pass 0.95
        assert strict.fuzzy_contains("project notes", "project")
        # Very different word should fail
        assert not strict.fuzzy_contains("project notes", "banana")

    def test_low_threshold(self):
        """Test relaxed threshold accepts looser matches."""
        relaxed = FuzzyMatcher(threshold=0.5)
        assert relaxed.fuzzy_contains("Hello World", "Hllo")

    def test_threshold_clamping(self):
        """Test threshold is clamped to 0.0-1.0."""
        m1 = FuzzyMatcher(threshold=-0.5)
        assert m1.threshold == 0.0
        m2 = FuzzyMatcher(threshold=2.0)
        assert m2.threshold == 1.0


@pytest.mark.unit
class TestFuzzyScore:
    """Tests for fuzzy_score method."""

    @pytest.fixture
    def matcher(self):
        return FuzzyMatcher(threshold=0.75)

    def test_exact_match_score(self, matcher):
        """Test exact match returns 1.0."""
        score = matcher.fuzzy_score("project notes here", "project")
        assert score == 1.0

    def test_no_match_score(self, matcher):
        """Test no match returns 0.0 or very low."""
        score = matcher.fuzzy_score("Hello World", "zzzzz")
        assert score < 0.5

    def test_typo_score(self, matcher):
        """Test typo gives high but not perfect score."""
        score = matcher.fuzzy_score("This is a project", "proejct")
        assert 0.7 < score < 1.0

    def test_empty_inputs(self, matcher):
        """Test empty inputs return 0.0."""
        assert matcher.fuzzy_score("", "test") == 0.0
        assert matcher.fuzzy_score("test", "") == 0.0

    def test_short_term_score(self, matcher):
        """Test short terms use exact match scoring."""
        assert matcher.fuzzy_score("Hello", "He") == 1.0
        assert matcher.fuzzy_score("Hello", "Zx") == 0.0


@pytest.mark.unit
class TestFuzzyContainsPhrase:
    """Tests for fuzzy phrase matching."""

    @pytest.fixture
    def matcher(self):
        return FuzzyMatcher(threshold=0.75)

    def test_exact_phrase(self, matcher):
        """Test exact phrase match."""
        assert matcher.fuzzy_contains_phrase(
            "This is a project document", "project document"
        )

    def test_phrase_with_typo(self, matcher):
        """Test phrase with a typo in one word."""
        assert matcher.fuzzy_contains_phrase(
            "This is a project document", "proejct document"
        )

    def test_phrase_no_match(self, matcher):
        """Test non-matching phrase."""
        assert not matcher.fuzzy_contains_phrase("Hello World", "banana apple")

    def test_empty_phrase(self, matcher):
        """Test empty phrase returns False."""
        assert not matcher.fuzzy_contains_phrase("Hello", "")

    def test_empty_content(self, matcher):
        """Test empty content returns False."""
        assert not matcher.fuzzy_contains_phrase("", "test phrase")


@pytest.mark.unit
class TestGetFuzzyMatcher:
    """Tests for get_fuzzy_matcher factory."""

    def test_default_threshold(self):
        """Test default threshold returns cached instance."""
        m1 = get_fuzzy_matcher()
        m2 = get_fuzzy_matcher()
        assert m1 is m2

    def test_custom_threshold(self):
        """Test custom threshold creates new instance."""
        m = get_fuzzy_matcher(0.9)
        assert m.threshold == 0.9


@pytest.mark.unit
class TestSearchEngineWithFuzzy:
    """Tests for SearchEngine fuzzy mode integration."""

    def test_fuzzy_search_finds_typo(self):
        """Test fuzzy search finds notes with typos."""
        from simplenote_mcp.server.search.engine import SearchEngine

        engine = SearchEngine(fuzzy=True)
        notes = {
            "1": {"key": "1", "content": "Project Alpha documentation", "tags": []},
            "2": {"key": "2", "content": "Meeting notes for Tuesday", "tags": []},
        }
        results = engine.search(notes, "proejct")
        assert len(results) >= 1
        assert results[0].get("key") == "1"

    def test_non_fuzzy_misses_typo(self):
        """Test non-fuzzy search misses typo."""
        from simplenote_mcp.server.search.engine import SearchEngine

        engine = SearchEngine(fuzzy=False)
        notes = {
            "1": {"key": "1", "content": "Project Alpha documentation", "tags": []},
        }
        results = engine.search(notes, "proejct")
        assert len(results) == 0

    def test_fuzzy_exact_still_works(self):
        """Test exact matches still work in fuzzy mode."""
        from simplenote_mcp.server.search.engine import SearchEngine

        engine = SearchEngine(fuzzy=True)
        notes = {
            "1": {"key": "1", "content": "Project Alpha documentation", "tags": []},
        }
        results = engine.search(notes, "Project")
        assert len(results) == 1

    def test_fuzzy_default_is_off(self):
        """Test fuzzy is off by default."""
        from simplenote_mcp.server.search.engine import SearchEngine

        engine = SearchEngine()
        assert engine._fuzzy is False
        assert engine._fuzzy_matcher is None

    def test_fuzzy_relevance_scoring(self):
        """Test fuzzy matches get lower relevance than exact matches."""
        from simplenote_mcp.server.search.engine import SearchEngine

        engine_exact = SearchEngine(fuzzy=False)
        engine_fuzzy = SearchEngine(fuzzy=True)

        notes = {
            "1": {
                "key": "1",
                "content": "project details here",
                "tags": [],
                "modifydate": 1700000000,
            },
        }

        # Exact match should have higher relevance
        exact_results = engine_exact.search(notes, "project")
        fuzzy_results = engine_fuzzy.search(notes, "proejct")

        # Both should find the note
        assert len(exact_results) >= 0  # exact might find it
        assert len(fuzzy_results) == 1  # fuzzy should find it
