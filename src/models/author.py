"""
Data model for article authors.

Fields extracted from PubMed.
"""

from dataclasses import dataclass
from typing import Optional


@dataclass
class Author:
    """
    Represents a scientific article author with a Spanish affiliation.

    PubMed attributes:
        author_lastname: Author's last name
        author_forename: Author's first name
        author_position: Position in the author list (1=first author)
        author_orcid: Author's ORCID (e.g. 0000-0001-2345-6789)
        author_email: Author's email (rare in PubMed)
        affiliation: Spanish affiliation text
    """

    # PubMed fields
    author_lastname: str
    author_forename: str = ""
    author_position: int = 0
    author_orcid: Optional[str] = None
    author_email: Optional[str] = None
    affiliation: Optional[str] = None

    def get_full_name(self) -> str:
        """Return the full name: 'Lastname, Forename'."""
        if self.author_forename:
            return f"{self.author_lastname}, {self.author_forename}"
        return self.author_lastname

    def __str__(self) -> str:
        return f"Author({self.get_full_name()})"

    def __repr__(self) -> str:
        return self.__str__()
