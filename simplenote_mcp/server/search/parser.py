"""Query parser for advanced search capabilities."""

import re
from enum import Enum, auto
from typing import List


class TokenType(Enum):
    """Token types for search query parsing."""

    TERM = auto()  # Regular search term
    PHRASE = auto()  # Quoted phrase
    AND = auto()  # Logical AND
    OR = auto()  # Logical OR
    NOT = auto()  # Logical NOT
    TAG = auto()  # Tag filter
    DATE_FROM = auto()  # Date range start
    DATE_TO = auto()  # Date range end
    GROUP_START = auto()  # Opening parenthesis
    GROUP_END = auto()  # Closing parenthesis


class QueryToken:
    """Represents a token in a parsed search query."""

    def __init__(self, token_type: TokenType, value: str):
        """Initialize a query token.

        Args:
            token_type: The type of token
            value: The value of the token

        """
        self.type = token_type
        self.value = value

    def __repr__(self) -> str:
        """Return string representation of the token."""
        return f"QueryToken({self.type}, '{self.value}')"


class QueryParser:
    """Parser for advanced search queries.

    Supports:
    - Boolean operators: AND, OR, NOT
    - Quoted phrases: "exact match"
    - Tag filters: tag:name
    - Date filters: from:2023-01-01, to:2023-12-31
    - Grouping with parentheses: (term1 AND term2) OR term3
    """

    def __init__(self, query_string: str):
        """Initialize a query parser.

        Args:
            query_string: The search query to parse

        """
        self.original_query = query_string
        self.tokens = self._tokenize(query_string)

    def _tokenize(self, query: str) -> List[QueryToken]:
        """Tokenize the query string into tokens.

        Args:
            query: The query string to tokenize

        Returns:
            List of QueryToken objects

        """
        if not query or not query.strip():
            return []

        # Normalize whitespace and case for operators
        query = re.sub(r"\s+", " ", query.strip())

        # Replace common operator aliases
        query = re.sub(r"\bAND\b", "AND", query, flags=re.IGNORECASE)
        query = re.sub(r"\bOR\b", "OR", query, flags=re.IGNORECASE)
        query = re.sub(r"\bNOT\b", "NOT", query, flags=re.IGNORECASE)

        # Extract quoted phrases
        phrases = []

        def replace_phrase(match):
            phrases.append(match.group(1))
            return f" __PHRASE_{len(phrases) - 1}__ "

        query = re.sub(r'"([^"]+)"', replace_phrase, query)

        # Extract date filters
        from_dates = []
        to_dates = []

        def replace_from_date(match):
            from_dates.append(match.group(1))
            return f" __FROM_{len(from_dates) - 1}__ "

        def replace_to_date(match):
            to_dates.append(match.group(1))
            return f" __TO_{len(to_dates) - 1}__ "

        query = re.sub(r"from:(\S+)", replace_from_date, query, flags=re.IGNORECASE)
        query = re.sub(r"to:(\S+)", replace_to_date, query, flags=re.IGNORECASE)

        # Extract tag filters
        tags = []

        def replace_tag(match):
            tags.append(match.group(1))
            return f" __TAG_{len(tags) - 1}__ "

        query = re.sub(r"tag:(\S+)", replace_tag, query, flags=re.IGNORECASE)

        # Split the query by spaces but keep operators and parentheses together
        tokens = []
        parts = query.split(" ")

        for part in parts:
            if not part:
                continue

            if part == "AND":
                tokens.append(QueryToken(TokenType.AND, "AND"))
            elif part == "OR":
                tokens.append(QueryToken(TokenType.OR, "OR"))
            elif part == "NOT":
                tokens.append(QueryToken(TokenType.NOT, "NOT"))
            elif part == "(":
                tokens.append(QueryToken(TokenType.GROUP_START, "("))
            elif part == ")":
                tokens.append(QueryToken(TokenType.GROUP_END, ")"))
            elif part.startswith("__PHRASE_"):
                idx = int(part.replace("__PHRASE_", "").replace("__", ""))
                tokens.append(QueryToken(TokenType.PHRASE, phrases[idx]))
            elif part.startswith("__FROM_"):
                idx = int(part.replace("__FROM_", "").replace("__", ""))
                tokens.append(QueryToken(TokenType.DATE_FROM, from_dates[idx]))
            elif part.startswith("__TO_"):
                idx = int(part.replace("__TO_", "").replace("__", ""))
                tokens.append(QueryToken(TokenType.DATE_TO, to_dates[idx]))
            elif part.startswith("__TAG_"):
                idx = int(part.replace("__TAG_", "").replace("__", ""))
                tokens.append(QueryToken(TokenType.TAG, tags[idx]))
            else:
                tokens.append(QueryToken(TokenType.TERM, part))

        # Handle implicit AND between terms
        expanded_tokens = []
        prev_token_requires_operator = False

        for token in tokens:
            if prev_token_requires_operator and token.type not in (
                TokenType.AND,
                TokenType.OR,
                TokenType.GROUP_END,
            ):
                # Insert implicit AND
                expanded_tokens.append(QueryToken(TokenType.AND, "AND"))

            expanded_tokens.append(token)

            # Check if the current token would require an operator next
            prev_token_requires_operator = token.type in (
                TokenType.TERM,
                TokenType.PHRASE,
                TokenType.GROUP_END,
            )

        return expanded_tokens
