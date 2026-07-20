# simplenote_mcp/server/search/

## Purpose

Advanced search: query tokenizing/parsing (`parser.py`), boolean expression evaluation (`engine.py`), fuzzy matching (`fuzzy.py`), and natural-language date resolution (`date_parser.py`). Used by `search_notes` and the cache's search indexing.

## Ownership

- `parser.py` — `QueryParser`/`QueryToken`: tokenizes `AND`/`OR`/`NOT`, quoted phrases, `tag:`/`from:`/`to:` filters, and parenthesized groups; inserts implicit `AND` between adjacent terms.
- `engine.py` — `SearchEngine`: recursive-descent evaluator (`_parse_or_expression` → `_parse_and_expression` → `_parse_not_expression` → `_parse_primary`, standard OR/AND/NOT precedence) plus tag/date filtering and relevance scoring.
- `fuzzy.py` — `FuzzyMatcher`, opt-in (`fuzzy: true`) `difflib.SequenceMatcher`-based approximate matching, default threshold 0.75.
- `date_parser.py` — `parse_natural_date`: resolves expressions like `last_week`, `yesterday`, `3_days_ago` to ISO dates.

## Local Contracts

- Search matching is **substring-based, not tokenized** — a word-index pre-filter requires terms ≥3 characters to be indexed; shorter terms fall back to full-content scan.
- Fuzzy matching only applies to terms ≥3 characters (`FuzzyMatcher`); shorter terms always use exact matching.
- Boolean operator precedence is fixed by the recursive-descent structure: `OR` binds loosest, then `AND`, then `NOT`, then grouped/primary expressions — do not reorder `_parse_*_expression` call chains without updating this doc.

## Work Guidance

- New query syntax (new filter prefix, new operator) needs changes in both `parser.py` (tokenizing) and `engine.py` (evaluation) — they are not independently extensible.

## Verification

- `make test-fast` (`tests/test_advanced_search.py`, `tests/test_date_parser.py`, and related search test files)

## Child DOX Index

None.
