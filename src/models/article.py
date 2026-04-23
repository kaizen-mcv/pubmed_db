"""
Data model for PubMed articles.

Fields extracted directly from PubMed (unbranded).
"""

from dataclasses import dataclass, field
from datetime import date
from typing import List, Optional

from .author import Author


@dataclass
class Article:
    """
    Represents a PubMed scientific article.

    PubMed attributes:
        pubmed_id: Unique article ID in PubMed
        article_title: Full article title
        article_abstract: Article abstract/summary
        journal_name: Scientific journal name
        journal_issn: Journal ISSN
        publication_date: Publication date
        article_doi: Digital Object Identifier
        publication_types: Publication types (e.g. "Journal Article; Review")
        mesh_terms: MeSH terms (controlled medical vocabulary)
        author_keywords: Keywords defined by the author
        authors: List of article authors
    """

    # Identifier
    pubmed_id: int

    # Main content
    article_title: str = ""
    article_abstract: Optional[str] = None

    # Journal information
    journal_name: Optional[str] = None
    journal_issn: Optional[str] = None

    # Additional identifier
    article_doi: Optional[str] = None

    # Date
    publication_date: Optional[date] = None

    # Publication type
    publication_types: Optional[str] = None

    # Metadata
    mesh_terms: Optional[str] = None
    author_keywords: Optional[str] = None

    # Authors
    authors: List[Author] = field(default_factory=list)

    def __str__(self) -> str:
        title_preview = self.article_title[:50] if self.article_title else ""
        return f"Article(pubmed_id={self.pubmed_id}, title='{title_preview}...')"

    def __repr__(self) -> str:
        return self.__str__()
