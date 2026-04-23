"""
Author information extractor.

Extracts: author_lastname, author_forename, author_position, author_orcid, author_email
"""

from typing import Any, Dict, List, Optional

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from src.models.author import Author


class AuthorExtractor:
    """
    Extracts author information from a PubMed article.
    """

    @staticmethod
    def extract_author_orcid(author_data: Dict[str, Any]) -> Optional[str]:
        """
        Extract the author's ORCID if it exists.

        Args:
            author_data: Dictionary with author data (from AuthorList)

        Returns:
            Author ORCID (e.g. "0000-0001-2345-6789") or None
        """
        if 'Identifier' not in author_data:
            return None

        identifiers = author_data['Identifier']

        # If it is a list of identifiers
        if isinstance(identifiers, list):
            for identifier in identifiers:
                if hasattr(identifier, 'attributes'):
                    if identifier.attributes.get('Source') == 'ORCID':
                        return str(identifier)
        # If it is a single identifier
        elif hasattr(identifiers, 'attributes'):
            if identifiers.attributes.get('Source') == 'ORCID':
                return str(identifiers)

        return None

    @staticmethod
    def extract_author_email(author_data: Dict[str, Any]) -> Optional[str]:
        """
        Extract the author's email if available.

        NOTE: Very few authors provide email in PubMed.
        This field will rarely be available.

        Args:
            author_data: Dictionary with author data

        Returns:
            Author email or None (almost always None)
        """
        return author_data.get('Email', None)

    @staticmethod
    def extract_authors(article_data: Dict[str, Any]) -> List[Author]:
        """
        Extract the full list of authors of the article.

        Args:
            article_data: Dictionary with article data

        Returns:
            List of Author objects with lastname, forename, position, orcid and email
        """
        article = article_data['MedlineCitation']['Article']
        author_list = article.get('AuthorList', [])

        authors = []

        for position, author_data in enumerate(author_list, start=1):
            # Some "authors" are collective entries without LastName
            if 'LastName' not in author_data:
                continue

            author = Author(
                author_lastname=author_data.get('LastName', ''),
                author_forename=author_data.get('ForeName', ''),
                author_position=position,
                author_orcid=AuthorExtractor.extract_author_orcid(author_data),
                author_email=AuthorExtractor.extract_author_email(author_data)
            )

            authors.append(author)

        return authors

    @staticmethod
    def extract_author_at_position(
        article_data: Dict[str, Any],
        position: int
    ) -> Author:
        """
        Extract a specific author by their position.

        Args:
            article_data: Dictionary with article data
            position: Author position (1-indexed)

        Returns:
            Author object or None if it does not exist

        Raises:
            IndexError: If the position does not exist
        """
        authors = AuthorExtractor.extract_authors(article_data)

        for author in authors:
            if author.author_position == position:
                return author

        raise IndexError(f"No author at position {position}")

    @staticmethod
    def get_first_author(article_data: Dict[str, Any]) -> Author:
        """
        Extract the first author of the article.

        Args:
            article_data: Dictionary with article data

        Returns:
            First author or None
        """
        return AuthorExtractor.extract_author_at_position(article_data, 1)

    @staticmethod
    def get_last_author(article_data: Dict[str, Any]) -> Author:
        """
        Extract the last author of the article (senior author).

        Args:
            article_data: Dictionary with article data

        Returns:
            Last author or None
        """
        authors = AuthorExtractor.extract_authors(article_data)
        if authors:
            return authors[-1]
        return None
