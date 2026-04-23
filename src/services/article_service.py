"""
Article service.

Orchestrates the complete saving of an article with its authors.
Simplified schema: 2 tables (articles + article_authors).
"""

from typing import Any, Dict, Optional

from psycopg2.extensions import cursor

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from src.models.article import Article
from src.models.author import Author

from src.extractors.article_extractor import ArticleExtractor
from src.extractors.author_extractor import AuthorExtractor
from src.extractors.affiliation_extractor import AffiliationExtractor

from src.filters.spanish_filter import spanish_filter

from src.database.repositories.article_repo import ArticleRepository
from src.database.repositories.article_author_repo import ArticleAuthorRepository


class ArticleService:
    """
    Service that orchestrates the complete saving of articles.

    Simplified flow:
    1. Extract fields from PubMed XML
    2. Save article to DB
    3. Filter and save Spanish authors
    """

    @classmethod
    def process_and_save(
        cls,
        cur: cursor,
        article_data: Dict[str, Any]
    ) -> Optional[int]:
        """
        Process a PubMed article and save it to the DB.

        Args:
            cur: Database cursor
            article_data: Entrez article data

        Returns:
            pubmed_id of the saved article or None if it fails
        """
        try:
            # 1. Extract article data
            article = cls._extract_article(article_data)

            # 2. Save article
            pubmed_id = ArticleRepository.insert_or_update(cur, article)

            # 3. Process and save Spanish authors
            cls._process_authors(cur, article_data, pubmed_id)

            return pubmed_id

        except Exception as e:
            raise Exception(
                f"Error processing article: {e}"
            ) from e

    @classmethod
    def _extract_article(cls, article_data: Dict[str, Any]) -> Article:
        """Extract all fields of the article."""
        return Article(
            pubmed_id=ArticleExtractor.extract_pubmed_id(article_data),
            article_title=ArticleExtractor.extract_article_title(article_data),
            article_abstract=ArticleExtractor.extract_article_abstract(article_data),
            journal_name=ArticleExtractor.extract_journal_name(article_data),
            journal_issn=ArticleExtractor.extract_journal_issn(article_data),
            publication_date=ArticleExtractor.extract_publication_date(article_data),
            article_doi=ArticleExtractor.extract_article_doi(article_data),
            publication_types=ArticleExtractor.extract_publication_types(article_data),
            mesh_terms=ArticleExtractor.extract_mesh_terms(article_data),
            author_keywords=ArticleExtractor.extract_author_keywords(article_data),
        )

    @classmethod
    def _process_authors(
        cls,
        cur: cursor,
        article_data: Dict[str, Any],
        pubmed_id: int
    ) -> int:
        """
        Process and save authors with Spanish affiliation.

        Returns:
            Number of Spanish authors saved
        """
        article = article_data['MedlineCitation']['Article']
        author_list = article.get('AuthorList', [])

        spanish_authors_count = 0

        for position, author_data in enumerate(author_list, start=1):
            # Skip if it has no last name
            if 'LastName' not in author_data:
                continue

            # Extract affiliation as text
            affiliation_text = AffiliationExtractor.extract_affiliation_text(
                author_data
            )

            # Filter by Spain
            spanish_text = None
            if affiliation_text:
                spanish_text = spanish_filter.filter_spanish_parts(affiliation_text)

            # If there is no Spanish affiliation, skip
            if not spanish_text:
                continue

            spanish_authors_count += 1

            # Build Author object with all fields
            author = Author(
                author_lastname=author_data.get('LastName', ''),
                author_forename=author_data.get('ForeName', ''),
                author_position=position,
                author_orcid=AuthorExtractor.extract_author_orcid(author_data),
                author_email=AuthorExtractor.extract_author_email(author_data),
                affiliation=spanish_text,
            )

            # Save author
            ArticleAuthorRepository.insert(cur, pubmed_id, author)

        return spanish_authors_count

    @staticmethod
    def get_article_stats(cur: cursor) -> Dict[str, int]:
        """
        Get article statistics from the DB.

        Returns:
            Dict with counts of articles and Spanish authors
        """
        return {
            'total_articles': ArticleRepository.count(cur),
            'total_authors': ArticleAuthorRepository.count(cur),
        }
