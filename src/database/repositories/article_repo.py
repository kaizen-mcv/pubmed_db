"""
Repositorio de artículos.

CRUD para la tabla articles (esquema simplificado).
"""

from typing import Optional

from psycopg2.extensions import cursor

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..'))

from src.models.article import Article


class ArticleRepository:
    """
    Repositorio para operaciones CRUD de artículos.
    """

    @staticmethod
    def insert_or_update(cur: cursor, article: Article) -> int:
        """
        Inserta un artículo o actualiza si ya existe.

        Args:
            cur: Cursor de base de datos
            article: Objeto Article a guardar

        Returns:
            pubmed_id del artículo
        """
        cur.execute("""
            INSERT INTO articles (
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
        Verifica si un artículo existe.

        Args:
            cur: Cursor de base de datos
            pubmed_id: ID del artículo en PubMed

        Returns:
            True si existe
        """
        cur.execute(
            "SELECT 1 FROM articles WHERE pubmed_id = %s",
            (pubmed_id,)
        )
        return cur.fetchone() is not None

    @staticmethod
    def count(cur: cursor) -> int:
        """
        Cuenta el total de artículos.

        Args:
            cur: Cursor de base de datos

        Returns:
            Número total de artículos
        """
        cur.execute("SELECT COUNT(*) FROM articles")
        return cur.fetchone()[0]
