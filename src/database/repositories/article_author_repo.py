"""
Repositorio de autores de artículos.

CRUD para la tabla article_authors.
"""

from typing import List

from psycopg2.extensions import cursor

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..'))

from src.models.author import Author


class ArticleAuthorRepository:
    """
    Repositorio para operaciones CRUD de autores de artículos.
    """

    @staticmethod
    def insert(cur: cursor, pubmed_id: int, author: Author) -> int:
        """
        Inserta un autor de artículo.

        Args:
            cur: Cursor de base de datos
            pubmed_id: ID del artículo en PubMed
            author: Objeto Author a guardar

        Returns:
            ID del registro insertado
        """
        cur.execute("""
            INSERT INTO article_authors (
                pubmed_id,
                author_name,
                author_position,
                author_orcid,
                author_email,
                affiliation
            )
            VALUES (%s, %s, %s, %s, %s, %s)
            RETURNING id
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
        Inserta múltiples autores de un artículo.

        Args:
            cur: Cursor de base de datos
            pubmed_id: ID del artículo en PubMed
            authors: Lista de objetos Author a guardar

        Returns:
            Número de autores insertados
        """
        count = 0
        for author in authors:
            ArticleAuthorRepository.insert(cur, pubmed_id, author)
            count += 1
        return count

    @staticmethod
    def delete_by_pubmed_id(cur: cursor, pubmed_id: int) -> int:
        """
        Elimina todos los autores de un artículo.

        Args:
            cur: Cursor de base de datos
            pubmed_id: ID del artículo en PubMed

        Returns:
            Número de registros eliminados
        """
        cur.execute(
            "DELETE FROM article_authors WHERE pubmed_id = %s",
            (pubmed_id,)
        )
        return cur.rowcount

    @staticmethod
    def count(cur: cursor) -> int:
        """
        Cuenta el total de registros de autores.

        Args:
            cur: Cursor de base de datos

        Returns:
            Número total de registros
        """
        cur.execute("SELECT COUNT(*) FROM article_authors")
        return cur.fetchone()[0]
