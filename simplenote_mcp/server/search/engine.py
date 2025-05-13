"""Search engine implementation for advanced search capabilities."""

import asyncio
import re
from datetime import datetime
from typing import Any, Dict, List, Optional, Set, Tuple

from ..logging import logger
from .parser import QueryParser, QueryToken, TokenType


class SearchEngine:
    """Implementation of advanced search capabilities for Simplenote notes.

    Supports:
    - Boolean operators (AND, OR, NOT)
    - Phrase matching
    - Tag filtering
    - Date range filtering
    """

    def __init__(self):
        """Initialize the search engine."""
        self._lock = asyncio.Lock()

    def search(
        self,
        notes: Dict[str, Dict[str, Any]],
        query: str,
        tag_filters: Optional[List[str]] = None,
        date_range: Optional[Tuple[Optional[datetime], Optional[datetime]]] = None,
    ) -> List[Dict[str, Any]]:
        """Search notes using advanced query capabilities.

        Args:
            notes: Dictionary of notes to search through (key -> note)
            query: The search query (supports boolean operators)
            tag_filters: Optional list of tags to filter by
            date_range: Optional tuple of (from_date, to_date)

        Returns:
            List of matching notes sorted by relevance. Pagination should be handled
            by the caller.

        """
        logger.debug(f"Performing advanced search with query: '{query}'")

        # Parse the query into tokens
        parser = QueryParser(query)
        tokens = parser.tokens

        # Extract standalone special tokens (tags, dates) that should be applied globally
        global_tag_filters = set(tag_filters) if tag_filters else set()
        global_from_date = None
        global_to_date = None

        if date_range:
            global_from_date, global_to_date = date_range

        # Find and process special tokens
        remaining_tokens = []

        for token in tokens:
            if token.type == TokenType.TAG:
                global_tag_filters.add(token.value)
            elif token.type == TokenType.DATE_FROM:
                try:
                    global_from_date = datetime.fromisoformat(token.value)
                except ValueError:
                    logger.warning(f"Invalid from date format: {token.value}")
            elif token.type == TokenType.DATE_TO:
                try:
                    global_to_date = datetime.fromisoformat(token.value)
                except ValueError:
                    logger.warning(f"Invalid to date format: {token.value}")
            else:
                remaining_tokens.append(token)

        # Update date_range with parsed dates from the query
        date_range = (global_from_date, global_to_date)

        # If no query text and we have filters, we should still return filtered results
        if not query and (
            global_tag_filters or date_range[0] is not None or date_range[1] is not None
        ):
            logger.debug(
                f"Processing empty query with filters: tags={global_tag_filters}, date_range={date_range}"
            )

            # Collect results with scores
            results = []

            for _, note in notes.items():
                # Apply tag filters
                if global_tag_filters and not self._matches_tags(
                    note, global_tag_filters
                ):
                    continue

                # Apply date range filters
                if (
                    date_range[0] is not None or date_range[1] is not None
                ) and not self._is_in_date_range(note, date_range):
                    continue

                # Add matching note to results with a default score of 1
                results.append((note, 1))

            # Sort by modification date (most recent first) as a default
            results.sort(key=lambda x: self._get_modify_date(x[0]), reverse=True)

            # Return just the notes, not the scores
            return [note for note, _ in results]

        # For regular searches with actual query tokens
        elif tokens:
            # Collect results with scores
            results = []

            for _, note in notes.items():
                # Apply tag filters
                if global_tag_filters and not self._matches_tags(
                    note, global_tag_filters
                ):
                    continue

                # Apply date range filters
                if (
                    date_range[0] is not None or date_range[1] is not None
                ) and not self._is_in_date_range(note, date_range):
                    continue

                # Evaluate the boolean expression
                if remaining_tokens and not self._evaluate_expression(
                    note, remaining_tokens
                ):
                    continue

                # Calculate relevance score
                score = self._calculate_relevance(note, query)

                # Add matching note to results
                results.append((note, score))

            # Sort by relevance score (descending)
            results.sort(key=lambda x: x[1], reverse=True)

            # Return just the notes, not the scores
            return [note for note, _ in results]

        # Empty query with no filters returns empty result
        else:
            return []

    def _matches_tags(self, note: Dict[str, Any], tags: Set[str]) -> bool:
        """Check if a note matches the specified tags.

        Args:
            note: The note to check
            tags: Set of tags to match

        Returns:
            True if note has all the specified tags, False otherwise

        """
        note_tags = set(note.get("tags", []))
        logger.debug(f"Checking if tags {tags} are in note tags {note_tags}")
        return tags.issubset(note_tags)

    def _is_in_date_range(
        self,
        note: Dict[str, Any],
        date_range: Tuple[Optional[datetime], Optional[datetime]],
    ) -> bool:
        """Check if a note's modification date is within the specified range.

        Args:
            note: The note to check
            date_range: Tuple of (from_date, to_date), either may be None

        Returns:
            True if note is in the date range, False otherwise

        """
        from_date, to_date = date_range

        # If no date range specified, note is in range
        if not from_date and not to_date:
            return True

        # Get note modification date
        modify_date = note.get("modifydate", 0)

        if not modify_date:
            return False

        # Parse date if it's a string
        if isinstance(modify_date, str):
            try:
                note_date = datetime.fromisoformat(modify_date)
            except ValueError:
                logger.warning(f"Invalid note modification date format: {modify_date}")
                return False
        else:
            # Assume it's a timestamp
            try:
                note_date = datetime.fromtimestamp(modify_date)
            except (ValueError, TypeError):
                logger.warning(f"Invalid note modification timestamp: {modify_date}")
                return False

        # Check if note date is in range
        if from_date and note_date < from_date:
            return False

        return not (to_date and note_date > to_date)

    def _evaluate_expression(
        self, note: Dict[str, Any], tokens: List[QueryToken]
    ) -> bool:
        """Evaluate a boolean expression against a note.

        Uses a simple recursive descent parser to evaluate the expression.

        Args:
            note: The note to evaluate against
            tokens: List of query tokens

        Returns:
            True if note matches the expression, False otherwise

        """
        if not tokens:
            return True

        # Create a parser state with current position
        pos = [0]

        # Parse the boolean expression
        result = self._parse_or_expression(note, tokens, pos)

        return result

    def _parse_or_expression(
        self, note: Dict[str, Any], tokens: List[QueryToken], pos: List[int]
    ) -> bool:
        """Parse an OR expression (term OR term OR ...).

        Args:
            note: The note to check
            tokens: List of query tokens
            pos: Current position in the token list

        Returns:
            Result of evaluating the expression

        """
        # Parse the first term
        result = self._parse_and_expression(note, tokens, pos)

        # Continue parsing OR terms
        while pos[0] < len(tokens) and tokens[pos[0]].type == TokenType.OR:
            # Skip the OR token
            pos[0] += 1

            # Parse the next term
            next_result = self._parse_and_expression(note, tokens, pos)

            # Combine with OR
            result = result or next_result

        return result

    def _parse_and_expression(
        self, note: Dict[str, Any], tokens: List[QueryToken], pos: List[int]
    ) -> bool:
        """Parse an AND expression (term AND term AND ...).

        Args:
            note: The note to check
            tokens: List of query tokens
            pos: Current position in the token list

        Returns:
            Result of evaluating the expression

        """
        # Parse the first term
        result = self._parse_not_expression(note, tokens, pos)

        # Continue parsing AND terms
        while pos[0] < len(tokens) and tokens[pos[0]].type == TokenType.AND:
            # Skip the AND token
            pos[0] += 1

            # Parse the next term
            next_result = self._parse_not_expression(note, tokens, pos)

            # Combine with AND
            result = result and next_result

        return result

    def _parse_not_expression(
        self, note: Dict[str, Any], tokens: List[QueryToken], pos: List[int]
    ) -> bool:
        """Parse a NOT expression (NOT term).

        Args:
            note: The note to check
            tokens: List of query tokens
            pos: Current position in the token list

        Returns:
            Result of evaluating the expression

        """
        # Check for NOT operator
        if pos[0] < len(tokens) and tokens[pos[0]].type == TokenType.NOT:
            # Skip the NOT token
            pos[0] += 1

            # Parse the term and negate it
            result = not self._parse_primary(note, tokens, pos)
        else:
            # Parse a regular term
            result = self._parse_primary(note, tokens, pos)

        return result

    def _parse_primary(
        self, note: Dict[str, Any], tokens: List[QueryToken], pos: List[int]
    ) -> bool:
        """Parse a primary expression (term, phrase, or grouped expression).

        Args:
            note: The note to check
            tokens: List of query tokens
            pos: Current position in the token list

        Returns:
            Result of evaluating the expression

        """
        if pos[0] >= len(tokens):
            # End of input
            return False

        token = tokens[pos[0]]

        if token.type == TokenType.GROUP_START:
            # Parse a grouped expression (...)
            pos[0] += 1

            # Parse the expression inside the group
            result = self._parse_or_expression(note, tokens, pos)

            # Ensure we have a closing parenthesis
            if pos[0] < len(tokens) and tokens[pos[0]].type == TokenType.GROUP_END:
                pos[0] += 1
            else:
                logger.warning("Missing closing parenthesis in search query")

            return result

        elif token.type == TokenType.TERM:
            # Check if the term matches the note content
            pos[0] += 1
            return self._content_contains(note, token.value)

        elif token.type == TokenType.PHRASE:
            # Check if the phrase matches the note content
            pos[0] += 1
            return self._content_contains(note, token.value, exact=True)

        else:
            # Skip unexpected tokens
            pos[0] += 1
            return False

    def _content_contains(
        self, note: Dict[str, Any], search_term: str, exact: bool = False
    ) -> bool:
        """Check if note content contains the search term.

        Args:
            note: The note to check
            search_term: The term to search for
            exact: Whether to perform exact matching (case sensitive)

        Returns:
            True if note contains the term, False otherwise

        """
        content = note.get("content", "")

        if not content:
            return False

        if exact:
            # For exact phrase matching, we need to check for the exact sequence of words
            # This requires whole word matching, not just substring matching

            # Convert search term and content to lowercase for case-insensitive matching
            search_lower = search_term.lower()
            content_lower = content.lower()

            # Split into words and join with a word boundary pattern
            search_words = search_lower.split()
            if len(search_words) <= 1:
                # Single word or empty - just do direct matching
                return search_lower in content_lower

            # For multiple words, use a regex pattern that matches the exact sequence
            # with word boundaries
            import re

            # Escape regex special characters
            escaped_words = [re.escape(word) for word in search_words]
            # Join with whitespace pattern
            pattern = r"\b" + r"\s+".join(escaped_words) + r"\b"

            # Check if the pattern matches
            return bool(re.search(pattern, content_lower))
        else:
            # Case-insensitive match for regular terms
            return search_term.lower() in content.lower()

    def _get_modify_date(self, note: Dict[str, Any]) -> datetime:
        """Extract the modification date from a note.

        Args:
            note: The note to extract date from

        Returns:
            A datetime object representing the modification date,
            or epoch start if not available

        """
        modify_date = note.get("modifydate", 0)

        if not modify_date:
            return datetime.fromtimestamp(0)

        try:
            # Parse date if it's a string
            if isinstance(modify_date, str):
                return datetime.fromisoformat(modify_date)
            else:
                # Assume it's a timestamp
                return datetime.fromtimestamp(modify_date)
        except (ValueError, TypeError):
            logger.warning(f"Invalid note modification date format: {modify_date}")
            return datetime.fromtimestamp(0)

    def _calculate_relevance(self, note: Dict[str, Any], query: str) -> int:
        """Calculate relevance score for a note.

        Args:
            note: The note to score
            query: The original search query

        Returns:
            Relevance score (higher is more relevant)

        """
        content = note.get("content", "").lower()
        title_line = content.split("\n", 1)[0].lower() if content else ""

        # Get all search terms (excluding operators)
        search_terms = re.findall(r"\b\w+\b", query.lower())
        search_terms = [
            term for term in search_terms if term not in ("and", "or", "not")
        ]

        if not search_terms:
            return 0

        # Calculate base score from term occurrences
        score = 0

        for term in search_terms:
            # Count occurrences in content
            term_score = content.count(term)

            # Bonus for title matches
            if term in title_line:
                term_score += 10

            score += term_score

        # Bonus for tags matching the search terms
        note_tags = [tag.lower() for tag in note.get("tags", [])]
        for term in search_terms:
            if term in note_tags:
                score += 5

        # Bonus for recency
        try:
            modify_date = note.get("modifydate", 0)
            if modify_date:
                # Simple recency bonus: 0-5 points based on age
                # (more recent notes get higher scores)
                if isinstance(modify_date, str):
                    # Parse ISO format date
                    note_date = datetime.fromisoformat(modify_date)
                else:
                    # Unix timestamp
                    note_date = datetime.fromtimestamp(modify_date)

                days_old = (datetime.now() - note_date).days
                recency_bonus = max(0, 5 - min(5, days_old // 30))
                score += recency_bonus
        except (ValueError, TypeError):
            # Ignore date parsing errors
            pass

        return score
