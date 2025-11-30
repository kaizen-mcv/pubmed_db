"""
Modelo de datos para artículos de PubMed.

Campos extraídos directamente de PubMed (sin marca).
"""

from dataclasses import dataclass, field
from datetime import date
from typing import List, Optional

from .author import Author


@dataclass
class Article:
    """
    Representa un artículo científico de PubMed.

    Atributos de PubMed:
        pubmed_id: ID único del artículo en PubMed
        article_title: Título completo del artículo
        article_abstract: Resumen/Abstract del artículo
        journal_name: Nombre de la revista científica
        journal_issn: ISSN de la revista
        publication_date: Fecha de publicación
        article_doi: Digital Object Identifier
        publication_types: Tipos de publicación (ej: "Journal Article; Review")
        mesh_terms: Términos MeSH (vocabulario médico controlado)
        author_keywords: Palabras clave definidas por el autor
        authors: Lista de autores del artículo
    """

    # Identificador
    pubmed_id: int

    # Contenido principal
    article_title: str = ""
    article_abstract: Optional[str] = None

    # Información de la revista
    journal_name: Optional[str] = None
    journal_issn: Optional[str] = None

    # Identificador adicional
    article_doi: Optional[str] = None

    # Fecha
    publication_date: Optional[date] = None

    # Tipo de publicación
    publication_types: Optional[str] = None

    # Metadatos
    mesh_terms: Optional[str] = None
    author_keywords: Optional[str] = None

    # Autores
    authors: List[Author] = field(default_factory=list)

    def __str__(self) -> str:
        title_preview = self.article_title[:50] if self.article_title else ""
        return f"Article(pubmed_id={self.pubmed_id}, title='{title_preview}...')"

    def __repr__(self) -> str:
        return self.__str__()
