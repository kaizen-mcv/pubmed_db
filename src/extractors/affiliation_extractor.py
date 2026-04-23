"""
Institutional affiliation extractor.

Extracts affiliation text for each author.
"""

from typing import Any, Dict, Optional


class AffiliationExtractor:
    """
    Extracts institutional affiliations of authors.
    """

    @staticmethod
    def extract_affiliation_text(author_data: Dict[str, Any]) -> Optional[str]:
        """
        Extract the affiliation text of an author.

        Handles two PubMed formats:
        1. AffiliationInfo (list of affiliations)
        2. Affiliation (direct text)

        Args:
            author_data: Dictionary with author data (from AuthorList)

        Returns:
            Affiliation text or None
        """
        # Format 1: AffiliationInfo (more common in recent articles)
        if 'AffiliationInfo' in author_data and author_data['AffiliationInfo']:
            affiliations = []
            for aff_info in author_data['AffiliationInfo']:
                if 'Affiliation' in aff_info:
                    affiliations.append(str(aff_info['Affiliation']))
            if affiliations:
                return '; '.join(affiliations)

        # Format 2: Direct Affiliation (older articles)
        if 'Affiliation' in author_data:
            return str(author_data['Affiliation'])

        return None
