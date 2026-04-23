"""
Articles repository.

CRUD for the pubmed_articles table (simplified schema).
"""

from typing import Optional

from psycopg2.extensions import cursor

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..'))

from src.models.article import Article


class ArticleRepository:
    """
    Repository for CRUD operations on articles.
    """

    @staticmethod
    def insert_or_update(cur: cursor, article: Article) -> int:
        """
        Insert an article or update it if it already exists.

        Args:
            cur: Database cursor
            article: Article object to store

        Returns:
            pubmed_id of the article
        """
        cur.execute("""
            INSERT INTO raw.pubmed_articles (
                pubmed_id,
                article_title,
                article_abstract,
                journal_name,
                journal_issn,
                publication_date,
                article_doi,
                publication_types,
                mesh_terms,
                author_keywords
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (pubmed_id) DO UPDATE SET
                article_title = EXCLUDED.article_title,
                article_abstract = EXCLUDED.article_abstract,
                journal_name = EXCLUDED.journal_name,
                journal_issn = EXCLUDED.journal_issn,
                publication_date = EXCLUDED.publication_date,
                article_doi = EXCLUDED.article_doi,
                publication_types = EXCLUDED.publication_types,
                mesh_terms = EXCLUDED.mesh_terms,
                author_keywords = EXCLUDED.author_keywords
            RETURNING pubmed_id
        """, (
            article.pubmed_id,
            article.article_title,
            article.article_abstract,
            article.journal_name,
            article.journal_issn,
            article.publication_date,
            article.article_doi,
            article.publication_types,
            article.mesh_terms,
            article.author_keywords,
        ))

        return cur.fetchone()[0]

    @staticmethod
    def exists(cur: cursor, pubmed_id: int) -> bool:
        """
        Check whether an article exists.

        Args:
            cur: Database cursor
            pubmed_id: Article ID in PubMed

        Returns:
            True if it exists
        """
        cur.execute(
            "SELECT 1 FROM raw.pubmed_articles WHERE pubmed_id = %s",
            (pubmed_id,)
        )
        return cur.fetchone() is not None

    @staticmethod
    def count(cur: cursor) -> int:
        """
        Count the total number of articles.

        Args:
            cur: Database cursor

        Returns:
            Total number of articles
        """
        cur.execute("SELECT COUNT(*) FROM raw.pubmed_articles")
        return cur.fetchone()[0]
