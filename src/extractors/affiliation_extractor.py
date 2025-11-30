"""
Extractor de afiliaciones institucionales.

Extrae texto de afiliación para cada autor.
"""

from typing import Any, Dict, Optional


class AffiliationExtractor:
    """
    Extrae afiliaciones institucionales de autores.
    """

    @staticmethod
    def extract_affiliation_text(author_data: Dict[str, Any]) -> Optional[str]:
        """
        Extrae el texto de afiliación de un autor.

        Maneja dos formatos de PubMed:
        1. AffiliationInfo (lista de afiliaciones)
        2. Affiliation (texto directo)

        Args:
            author_data: Diccionario con datos del autor (de AuthorList)

        Returns:
            Texto de afiliación o None
        """
        # Formato 1: AffiliationInfo (más común en artículos recientes)
        if 'AffiliationInfo' in author_data and author_data['AffiliationInfo']:
            affiliations = []
            for aff_info in author_data['AffiliationInfo']:
                if 'Affiliation' in aff_info:
                    affiliations.append(str(aff_info['Affiliation']))
            if affiliations:
                return '; '.join(affiliations)

        # Formato 2: Affiliation directa (artículos más antiguos)
        if 'Affiliation' in author_data:
            return str(author_data['Affiliation'])

        return None
