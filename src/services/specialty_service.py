"""
Servicio de inferencia de especialidades médicas.

Infiere especialidades SNOMED CT basándose únicamente en la afiliación
del autor, que es el único campo 100% fiable para determinar la
especialidad de cada autor individual.
"""

from typing import Dict, List, Optional
from dataclasses import dataclass

from psycopg2.extensions import cursor

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))


@dataclass
class SpecialtyMatch:
    """Resultado de un match de especialidad."""
    snomed_code: str
    name_en: str
    name_es: Optional[str]
    confidence: float
    source: str  # 'affiliation'
    detail: str  # Info adicional (patrón que matcheó)


class SpecialtyService:
    """
    Servicio para inferir especialidades médicas de autores.

    Usa únicamente la afiliación del autor como fuente de inferencia,
    ya que es el único campo que refleja directamente la especialidad
    del autor (un artículo puede tener autores de múltiples especialidades).
    """

    @classmethod
    def infer_author_specialties(
        cls,
        cur: cursor,
        pubmed_id: int,
        min_confidence: float = 0.5
    ) -> List[Dict]:
        """
        Infiere las especialidades de los autores de un artículo.

        Analiza las afiliaciones de los autores y busca coincidencias
        con especialidades SNOMED en la tabla de mapeo.

        Args:
            cur: Cursor de base de datos
            pubmed_id: ID del artículo PubMed
            min_confidence: Score mínimo para incluir

        Returns:
            Lista de dicts con snomed_code, name_en, name_es, confidence, affiliation
        """
        # Obtener afiliaciones de autores del artículo
        affiliations = cls._get_author_affiliations(cur, pubmed_id)

        if not affiliations:
            return []

        # Buscar matches para cada afiliación
        all_matches: List[SpecialtyMatch] = []
        for affiliation in affiliations:
            matches = cls._match_from_affiliation(cur, affiliation)
            all_matches.extend(matches)

        # Combinar y agregar scores
        combined = cls._combine_matches(all_matches)

        # Filtrar por confianza mínima
        results = [
            r for r in combined
            if r['confidence'] >= min_confidence
        ]
        results.sort(key=lambda x: x['confidence'], reverse=True)

        return results

    @classmethod
    def _get_author_affiliations(cls, cur: cursor, pubmed_id: int) -> List[str]:
        """Obtiene las afiliaciones de los autores del artículo."""
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
        """Encuentra especialidades desde la afiliación."""
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
            # Fidelidad: 'snomed' = 1.0, 'simplified' = 0.9
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
        Combina múltiples matches y calcula score final.

        Agrupa por snomed_code y usa la mejor confidence encontrada.
        """
        if not matches:
            return []

        # Agrupar por snomed_code
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
                # Mantener la mejor confidence
                if match.confidence > by_code[code]['confidence']:
                    by_code[code]['confidence'] = match.confidence
                # Agregar afiliación si es diferente
                if match.detail not in by_code[code]['affiliations']:
                    by_code[code]['affiliations'].append(match.detail)

        # Convertir a lista
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
        Obtiene estadísticas de la tabla de mapeo.

        Returns:
            Dict con conteos de la tabla de mapeo
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
