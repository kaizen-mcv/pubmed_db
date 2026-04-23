"""
Article authors repository.

CRUD for the pubmed_authors table.
"""

from typing import List

from psycopg2.extensions import cursor

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..'))

from src.models.author import Author


class ArticleAuthorRepository:
    """
    Repository for CRUD operations on article authors.
    """

    @staticmethod
    def insert(cur: cursor, pubmed_id: int, author: Author) -> int:
        """
        Insert an article author.

        Args:
            cur: Database cursor
            pubmed_id: Article ID in PubMed
            author: Author object to store

        Returns:
            ID of the inserted record
        """
        cur.execute("""
            INSERT INTO raw.pubmed_authors (
                pubmed_id,
                author_name,
                author_position,
                author_orcid,
                author_email,
                affiliation
            )
            VALUES (%s, %s, %s, %s, %s, %s)
            RETURNING sm_author_id
        """, (
            pubmed_id,
            author.get_full_name(),
            author.author_position,
            author.author_orcid,
            author.author_email,
            author.affiliation,
        ))

        return cur.fetchone()[0]

    @staticmethod
    def insert_batch(cur: cursor, pubmed_id: int, authors: List[Author]) -> int:
        """
        Insert multiple authors for an article.

        Args:
            cur: Database cursor
            pubmed_id: Article ID in PubMed
            authors: List of Author objects to store

        Returns:
            Number of authors inserted
        """
        count = 0
        for author in authors:
            ArticleAuthorRepository.insert(cur, pubmed_id, author)
            count += 1
        return count

    @staticmethod
    def delete_by_pubmed_id(cur: cursor, pubmed_id: int) -> int:
        """
        Delete all authors for an article.

        Args:
            cur: Database cursor
            pubmed_id: Article ID in PubMed

        Returns:
            Number of records deleted
        """
        cur.execute(
            "DELETE FROM raw.pubmed_authors WHERE pubmed_id = %s",
            (pubmed_id,)
        )
        return cur.rowcount

    @staticmethod
    def count(cur: cursor) -> int:
        """
        Count the total number of author records.

        Args:
            cur: Database cursor

        Returns:
            Total number of records
        """
        cur.execute("SELECT COUNT(*) FROM raw.pubmed_authors")
        return cur.fetchone()[0]
