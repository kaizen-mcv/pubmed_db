"""
(VL) Filtro de afiliaciones españolas.

Este módulo contiene lógica LOCAL del proyecto para identificar
si una afiliación pertenece a una institución española.

Usa la configuración de config/spanish_filters.yaml
"""

import re
from typing import List, Optional

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from config.settings import settings


class SpanishFilter:
    """
    (VL) Filtro para identificar afiliaciones españolas.

    Criterio estricto:
    - Debe contener un marcador español (spain, españa, etc.)
    - NO debe contener países extranjeros (lista negra)
    """

    def __init__(self):
        """Inicializa el filtro con configuración de YAML."""
        self.spanish_markers = [
            m.lower() for m in settings.get_spanish_markers()
        ]
        self.spanish_cities = [
            c.lower() for c in settings.get_spanish_cities()
        ]
        self.foreign_countries = [
            c.lower() for c in settings.get_foreign_countries()
        ]

    def is_spanish_affiliation(self, affiliation_text: str) -> bool:
        """
        (VL) Verifica si una afiliación es EXCLUSIVAMENTE española.

        RECHAZA afiliaciones que mencionen países extranjeros.

        Args:
            affiliation_text: Texto de la afiliación

        Returns:
            True si la afiliación es española
        """
        if not affiliation_text:
            return False

        aff_lower = affiliation_text.lower()

        # LISTA NEGRA: Si menciona cualquier país extranjero → RECHAZAR
        for country in self.foreign_countries:
            if country in aff_lower:
                return False

        # LISTA BLANCA: Debe contener marcador español
        has_spanish_marker = any(
            marker in aff_lower for marker in self.spanish_markers
        )

        return has_spanish_marker

    def filter_spanish_parts(
        self,
        affiliation_text: str
    ) -> Optional[str]:
        """
        (VL) Filtra y retorna solo las partes españolas de una afiliación múltiple.

        Divide por separadores comunes y verifica cada parte individualmente.

        Args:
            affiliation_text: Texto de afiliación (puede tener múltiples)

        Returns:
            Solo las partes españolas o None si ninguna es española
        """
        if not affiliation_text:
            return None

        # Separar por punto y coma (separador más común)
        parts = []
        for segment in affiliation_text.split(';'):
            # Separar cada segmento por punto si está seguido de espacio y mayúscula
            subsegments = re.split(r'\.\s+(?=[A-Z])', segment)
            parts.extend(subsegments)

        spanish_parts = []

        for part in parts:
            part = part.strip()
            if part and self.is_spanish_affiliation(part):
                spanish_parts.append(part)

        return '; '.join(spanish_parts) if spanish_parts else None

    def get_spanish_affiliations(
        self,
        affiliations: List[str]
    ) -> List[str]:
        """
        (VL) Filtra una lista de afiliaciones y retorna solo las españolas.

        Args:
            affiliations: Lista de textos de afiliación

        Returns:
            Lista con solo afiliaciones españolas
        """
        spanish = []

        for aff in affiliations:
            filtered = self.filter_spanish_parts(aff)
            if filtered:
                spanish.append(filtered)

        return spanish


# Instancia global para uso conveniente
spanish_filter = SpanishFilter()
