"""
Servicio de artículos.

Orquesta el guardado completo de un artículo con sus autores.
Esquema simplificado: 2 tablas (articles + article_authors).
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
    Servicio que orquesta el guardado completo de artículos.

    Flujo simplificado:
    1. Extraer campos del XML de PubMed
    2. Guardar artículo en BD
    3. Filtrar y guardar autores españoles
    """

    @classmethod
    def process_and_save(
        cls,
        cur: cursor,
        article_data: Dict[str, Any]
    ) -> Optional[int]:
        """
        Procesa un artículo de PubMed y lo guarda en la BD.

        Args:
            cur: Cursor de base de datos
            article_data: Datos del artículo de Entrez

        Returns:
            pubmed_id del artículo guardado o None si falla
        """
        try:
            # 1. Extraer datos del artículo
            article = cls._extract_article(article_data)

            # 2. Guardar artículo
            pubmed_id = ArticleRepository.insert_or_update(cur, article)

            # 3. Procesar y guardar autores españoles
            cls._process_authors(cur, article_data, pubmed_id)

            return pubmed_id

        except Exception as e:
            raise Exception(
                f"Error procesando artículo: {e}"
            ) from e

    @classmethod
    def _extract_article(cls, article_data: Dict[str, Any]) -> Article:
        """Extrae todos los campos del artículo."""
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
        Procesa y guarda los autores con afiliación española.

        Returns:
            Número de autores españoles guardados
        """
        article = article_data['MedlineCitation']['Article']
        author_list = article.get('AuthorList', [])

        spanish_authors_count = 0

        for position, author_data in enumerate(author_list, start=1):
            # Saltar si no tiene apellido
            if 'LastName' not in author_data:
                continue

            # Extraer afiliación como texto
            affiliation_text = AffiliationExtractor.extract_affiliation_text(
                author_data
            )

            # Filtrar por España
            spanish_text = None
            if affiliation_text:
                spanish_text = spanish_filter.filter_spanish_parts(affiliation_text)

            # Si no hay afiliación española, saltar
            if not spanish_text:
                continue

            spanish_authors_count += 1

            # Crear objeto Author con todos los campos
            author = Author(
                author_lastname=author_data.get('LastName', ''),
                author_forename=author_data.get('ForeName', ''),
                author_position=position,
                author_orcid=AuthorExtractor.extract_author_orcid(author_data),
                author_email=AuthorExtractor.extract_author_email(author_data),
                affiliation=spanish_text,
            )

            # Guardar autor
            ArticleAuthorRepository.insert(cur, pubmed_id, author)

        return spanish_authors_count

    @staticmethod
    def get_article_stats(cur: cursor) -> Dict[str, int]:
        """
        Obtiene estadísticas de artículos en la BD.

        Returns:
            Dict con conteos de artículos y autores españoles
        """
        return {
            'total_articles': ArticleRepository.count(cur),
            'total_authors': ArticleAuthorRepository.count(cur),
        }
