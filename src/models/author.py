"""
Modelo de datos para autores de artículos.

Campos extraídos de PubMed.
"""

from dataclasses import dataclass
from typing import Optional


@dataclass
class Author:
    """
    Representa un autor de artículo científico con afiliación española.

    Atributos de PubMed:
        author_lastname: Apellido del autor
        author_forename: Nombre del autor
        author_position: Posición en la lista de autores (1=primer autor)
        author_orcid: ORCID del autor (ej: 0000-0001-2345-6789)
        author_email: Email del autor (raro en PubMed)
        affiliation: Texto de afiliación española
    """

    # Campos de PubMed
    author_lastname: str
    author_forename: str = ""
    author_position: int = 0
    author_orcid: Optional[str] = None
    author_email: Optional[str] = None
    affiliation: Optional[str] = None

    def get_full_name(self) -> str:
        """Retorna nombre completo: 'Apellido, Nombre'."""
        if self.author_forename:
            return f"{self.author_lastname}, {self.author_forename}"
        return self.author_lastname

    def __str__(self) -> str:
        return f"Author({self.get_full_name()})"

    def __repr__(self) -> str:
        return self.__str__()
