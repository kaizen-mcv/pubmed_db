"""
Extractor de información de autores.

Extrae: author_lastname, author_forename, author_position, author_orcid, author_email
"""

from typing import Any, Dict, List, Optional

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from src.models.author import Author


class AuthorExtractor:
    """
    Extrae información de autores de un artículo de PubMed.
    """

    @staticmethod
    def extract_author_orcid(author_data: Dict[str, Any]) -> Optional[str]:
        """
        Extrae el ORCID del autor si existe.

        Args:
            author_data: Diccionario con datos del autor (de AuthorList)

        Returns:
            ORCID del autor (ej: "0000-0001-2345-6789") o None
        """
        if 'Identifier' not in author_data:
            return None

        identifiers = author_data['Identifier']

        # Si es lista de identificadores
        if isinstance(identifiers, list):
            for identifier in identifiers:
                if hasattr(identifier, 'attributes'):
                    if identifier.attributes.get('Source') == 'ORCID':
                        return str(identifier)
        # Si es un único identificador
        elif hasattr(identifiers, 'attributes'):
            if identifiers.attributes.get('Source') == 'ORCID':
                return str(identifiers)

        return None

    @staticmethod
    def extract_author_email(author_data: Dict[str, Any]) -> Optional[str]:
        """
        Extrae el email del autor si está disponible.

        NOTA: Muy pocos autores proporcionan email en PubMed.
        Este campo rara vez estará disponible.

        Args:
            author_data: Diccionario con datos del autor

        Returns:
            Email del autor o None (casi siempre None)
        """
        return author_data.get('Email', None)

    @staticmethod
    def extract_authors(article_data: Dict[str, Any]) -> List[Author]:
        """
        Extrae la lista completa de autores del artículo.

        Args:
            article_data: Diccionario con datos del artículo

        Returns:
            Lista de objetos Author con lastname, forename, position, orcid y email
        """
        article = article_data['MedlineCitation']['Article']
        author_list = article.get('AuthorList', [])

        authors = []

        for position, author_data in enumerate(author_list, start=1):
            # Algunos "autores" son colectivos sin LastName
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
        Extrae un autor específico por su posición.

        Args:
            article_data: Diccionario con datos del artículo
            position: Posición del autor (1-indexed)

        Returns:
            Objeto Author o None si no existe

        Raises:
            IndexError: Si la posición no existe
        """
        authors = AuthorExtractor.extract_authors(article_data)

        for author in authors:
            if author.author_position == position:
                return author

        raise IndexError(f"No existe autor en posición {position}")

    @staticmethod
    def get_first_author(article_data: Dict[str, Any]) -> Author:
        """
        Extrae el primer autor del artículo.

        Args:
            article_data: Diccionario con datos del artículo

        Returns:
            Primer autor o None
        """
        return AuthorExtractor.extract_author_at_position(article_data, 1)

    @staticmethod
    def get_last_author(article_data: Dict[str, Any]) -> Author:
        """
        Extrae el último autor del artículo (senior author).

        Args:
            article_data: Diccionario con datos del artículo

        Returns:
            Último autor o None
        """
        authors = AuthorExtractor.extract_authors(article_data)
        if authors:
            return authors[-1]
        return None
