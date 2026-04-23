"""
Medical specialty inference service.

Infers SNOMED CT specialties based solely on the author's
affiliation, which is the only 100% reliable field to determine
the specialty of each individual author.
"""

from typing import Dict, List, Optional
from dataclasses import dataclass

from psycopg2.extensions import cursor

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))


@dataclass
class SpecialtyMatch:
    """Result of a specialty match."""
    snomed_code: str
    name_en: str
    name_es: Optional[str]
    confidence: float
    source: str  # 'affiliation'
    detail: str  # Additional info (pattern that matched)


class SpecialtyService:
    """
    Service to infer medical specialties of authors.

    Uses only the author's affiliation as inference source,
    since it is the only field that directly reflects the
    author's specialty (an article may have authors of multiple specialties).
    """

    @classmethod
    def infer_author_specialties(
        cls,
        cur: cursor,
        pubmed_id: int,
        min_confidence: float = 0.5
    ) -> List[Dict]:
        """
        Infer the specialties of the authors of an article.

        Analyzes author affiliations and searches for matches
        with SNOMED specialties in the mapping table.

        Args:
            cur: Database cursor
            pubmed_id: PubMed article ID
            min_confidence: Minimum score to include

        Returns:
            List of dicts with snomed_code, name_en, name_es, confidence, affiliation
        """
        # Get affiliations of article authors
        affiliations = cls._get_author_affiliations(cur, pubmed_id)

        if not affiliations:
            return []

        # Find matches for each affiliation
        all_matches: List[SpecialtyMatch] = []
        for affiliation in affiliations:
            matches = cls._match_from_affiliation(cur, affiliation)
            all_matches.extend(matches)

        # Combine and aggregate scores
        combined = cls._combine_matches(all_matches)

        # Filter by minimum confidence
        results = [
            r for r in combined
            if r['confidence'] >= min_confidence
        ]
        results.sort(key=lambda x: x['confidence'], reverse=True)

        return results

    @classmethod
    def _get_author_affiliations(cls, cur: cursor, pubmed_id: int) -> List[str]:
        """Get the affiliations of the article authors."""
        cur.execute("""
            SELECT DISTINCT affiliation
            FROM raw.pubmed_authors
            WHERE pubmed_id = %s AND affiliation IS NOT NULL
        """, (pubmed_id,))

        return [row[0] for row in cur.fetchall()]

    @classmethod
    def _match_from_affiliation(
        cls,
        cur: cursor,
        affiliation: str
    ) -> List[SpecialtyMatch]:
        """Find specialties from the affiliation."""
        matches = []

        if not affiliation:
            return matches

        cur.execute("""
            SELECT
                a.affiliation_pattern,
                a.snomed_code,
                a.fidelity,
                s.name_en,
                s.name_es
            FROM sm_maps.affiliation_to_snomed a
            JOIN vocab.snomed_specialties s ON a.snomed_code = s.snomed_code
            WHERE %s ILIKE '%%' || a.affiliation_pattern || '%%'
        """, (affiliation,))

        for row in cur.fetchall():
            # Fidelity: 'snomed' = 1.0, 'simplified' = 0.9
            confidence = 1.0 if row[2] == 'snomed' else 0.9

            matches.append(SpecialtyMatch(
                snomed_code=row[1],
                name_en=row[3],
                name_es=row[4],
                confidence=confidence,
                source='affiliation',
                detail=row[0]
            ))

        return matches

    @classmethod
    def _combine_matches(
        cls,
        matches: List[SpecialtyMatch]
    ) -> List[Dict]:
        """
        Combine multiple matches and compute final score.

        Groups by snomed_code and uses the best confidence found.
        """
        if not matches:
            return []

        # Group by snomed_code
        by_code: Dict[str, Dict] = {}

        for match in matches:
            code = match.snomed_code

            if code not in by_code:
                by_code[code] = {
                    'snomed_code': code,
                    'name_en': match.name_en,
                    'name_es': match.name_es,
                    'confidence': match.confidence,
                    'affiliations': [match.detail],
                }
            else:
                # Keep the best confidence
                if match.confidence > by_code[code]['confidence']:
                    by_code[code]['confidence'] = match.confidence
                # Add affiliation if different
                if match.detail not in by_code[code]['affiliations']:
                    by_code[code]['affiliations'].append(match.detail)

        # Convert to list
        results = []
        for code, data in by_code.items():
            results.append({
                'snomed_code': data['snomed_code'],
                'name_en': data['name_en'],
                'name_es': data['name_es'],
                'confidence': round(data['confidence'], 3),
                'affiliations': data['affiliations'],
            })

        return results

    @classmethod
    def get_specialty_stats(cls, cur: cursor) -> Dict:
        """
        Get statistics of the mapping table.

        Returns:
            Dict with counts from the mapping table
        """
        stats = {}

        try:
            cur.execute("SELECT COUNT(*) FROM sm_maps.affiliation_to_snomed")
            stats['affiliation_mappings'] = cur.fetchone()[0]

            cur.execute("SELECT COUNT(DISTINCT snomed_code) FROM sm_maps.affiliation_to_snomed")
            stats['specialties_mapped'] = cur.fetchone()[0]
        except Exception:
            stats['affiliation_mappings'] = 0
            stats['specialties_mapped'] = 0

        return stats
