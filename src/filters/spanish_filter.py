"""
(VL) Spanish affiliations filter.

This module contains project-LOCAL logic to identify whether
an affiliation belongs to a Spanish institution.

Uses the configuration in config/spanish_filters.yaml
"""

import re
from typing import List, Optional

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from config.settings import settings


class SpanishFilter:
    """
    (VL) Filter to identify Spanish affiliations.

    Strict criterion:
    - Must contain a Spanish marker (spain, españa, etc.)
    - Must NOT contain foreign countries (blacklist)
    """

    def __init__(self):
        """Initialize the filter with configuration from YAML."""
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
        (VL) Check whether an affiliation is EXCLUSIVELY Spanish.

        REJECTS affiliations that mention foreign countries.

        Args:
            affiliation_text: Affiliation text

        Returns:
            True if the affiliation is Spanish
        """
        if not affiliation_text:
            return False

        aff_lower = affiliation_text.lower()

        # BLACKLIST: if it mentions any foreign country -> REJECT
        for country in self.foreign_countries:
            if country in aff_lower:
                return False

        # WHITELIST: must contain a Spanish marker
        has_spanish_marker = any(
            marker in aff_lower for marker in self.spanish_markers
        )

        return has_spanish_marker

    def filter_spanish_parts(
        self,
        affiliation_text: str
    ) -> Optional[str]:
        """
        (VL) Filter and return only the Spanish parts of a multi-part affiliation.

        Splits by common separators and checks each part individually.

        Args:
            affiliation_text: Affiliation text (may contain multiple parts)

        Returns:
            Only the Spanish parts, or None if none is Spanish
        """
        if not affiliation_text:
            return None

        # Split by semicolon (most common separator)
        parts = []
        for segment in affiliation_text.split(';'):
            # Split each segment by period if followed by space and uppercase letter
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
        (VL) Filter a list of affiliations and return only the Spanish ones.

        Args:
            affiliations: List of affiliation texts

        Returns:
            List containing only Spanish affiliations
        """
        spanish = []

        for aff in affiliations:
            filtered = self.filter_spanish_parts(aff)
            if filtered:
                spanish.append(filtered)

        return spanish


# Global instance for convenient use
spanish_filter = SpanishFilter()
