"""
Servicio de inferencia de especialidades médicas.

Combina múltiples fuentes para inferir especialidades SNOMED CT:
- MeSH terms del artículo
- ISSN/nombre de revista
- Palabras clave del autor
- Patrones en título/abstract
- Afiliación del autor
"""

from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from decimal import Decimal

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
    source: str  # 'mesh', 'journal', 'keyword', 'title', 'abstract', 'affiliation'
    detail: str  # Info adicional (ej: qué MeSH term matcheó)


class SpecialtyService:
    """
    Servicio para inferir especialidades médicas de artículos.

    Pesos por fuente (ajustables):
    - MeSH terms: 0.40 (más confiable, vocabulario controlado)
    - Journal: 0.25 (revistas especializadas)
    - Keywords: 0.15 (del autor)
    - Title: 0.10 (patrones en título)
    - Abstract: 0.05 (patrones en abstract)
    - Affiliation: 0.05 (departamento del autor)
    """

    # Pesos por fuente
    WEIGHTS = {
        'mesh': 0.40,
        'journal': 0.25,
        'keyword': 0.15,
        'title': 0.10,
        'abstract': 0.05,
        'affiliation': 0.05,
    }

    @classmethod
    def infer_article_specialties(
        cls,
        cur: cursor,
        pubmed_id: int,
        top_n: int = 5,
        min_confidence: float = 0.1
    ) -> List[Dict]:
        """
        Infiere las especialidades médicas de un artículo.

        Combina todas las fuentes disponibles y retorna las
        especialidades más probables con su score.

        Args:
            cur: Cursor de base de datos
            pubmed_id: ID del artículo PubMed
            top_n: Número máximo de especialidades a retornar
            min_confidence: Score mínimo para incluir

        Returns:
            Lista de dicts con snomed_code, name_en, name_es, score, sources
        """
        # 1. Obtener datos del artículo
        article = cls._get_article_data(cur, pubmed_id)
        if not article:
            return []

        # 2. Recolectar matches de todas las fuentes
        all_matches: List[SpecialtyMatch] = []

        # MeSH terms
        if article.get('mesh_terms'):
            all_matches.extend(
                cls._match_from_mesh(cur, article['mesh_terms'])
            )

        # Journal
        if article.get('journal_issn') or article.get('journal_name'):
            all_matches.extend(
                cls._match_from_journal(
                    cur,
                    article.get('journal_issn'),
                    article.get('journal_name')
                )
            )

        # Keywords
        if article.get('author_keywords'):
            all_matches.extend(
                cls._match_from_keywords(cur, article['author_keywords'])
            )

        # Title
        if article.get('article_title'):
            all_matches.extend(
                cls._match_from_title(cur, article['article_title'])
            )

        # Abstract
        if article.get('article_abstract'):
            all_matches.extend(
                cls._match_from_abstract(cur, article['article_abstract'])
            )

        # Affiliation (de autores del artículo)
        affiliations = cls._get_author_affiliations(cur, pubmed_id)
        for affiliation in affiliations:
            all_matches.extend(
                cls._match_from_affiliation(cur, affiliation)
            )

        # 3. Combinar y agregar scores
        combined = cls._combine_matches(all_matches)

        # 4. Filtrar y ordenar
        results = [
            r for r in combined
            if r['score'] >= min_confidence
        ]
        results.sort(key=lambda x: x['score'], reverse=True)

        return results[:top_n]

    @classmethod
    def _get_article_data(cls, cur: cursor, pubmed_id: int) -> Optional[Dict]:
        """Obtiene los datos del artículo necesarios para la inferencia."""
        cur.execute("""
            SELECT
                pubmed_id,
                article_title,
                article_abstract,
                journal_name,
                journal_issn,
                mesh_terms,
                author_keywords
            FROM pubmed_articles
            WHERE pubmed_id = %s
        """, (pubmed_id,))

        row = cur.fetchone()
        if not row:
            return None

        return {
            'pubmed_id': row[0],
            'article_title': row[1],
            'article_abstract': row[2],
            'journal_name': row[3],
            'journal_issn': row[4],
            'mesh_terms': row[5],
            'author_keywords': row[6],
        }

    @classmethod
    def _get_author_affiliations(cls, cur: cursor, pubmed_id: int) -> List[str]:
        """Obtiene las afiliaciones de los autores del artículo."""
        cur.execute("""
            SELECT DISTINCT affiliation
            FROM pubmed_authors
            WHERE pubmed_id = %s AND affiliation IS NOT NULL
        """, (pubmed_id,))

        return [row[0] for row in cur.fetchall()]

    @classmethod
    def _match_from_mesh(
        cls,
        cur: cursor,
        mesh_terms: str
    ) -> List[SpecialtyMatch]:
        """
        Encuentra especialidades desde MeSH terms.

        mesh_terms es un string con formato: "term1 [tree1]; term2 [tree2]"
        """
        matches = []

        # Parsear MeSH terms
        if not mesh_terms:
            return matches

        for term_block in mesh_terms.split(';'):
            term_block = term_block.strip()
            if '[' not in term_block:
                continue

            # Extraer tree numbers
            parts = term_block.split('[')
            if len(parts) < 2:
                continue

            term_name = parts[0].strip()
            tree_str = parts[1].rstrip(']').strip()

            # Pueden ser múltiples tree numbers separados por ','
            for tree_num in tree_str.split(','):
                tree_num = tree_num.strip()
                if not tree_num:
                    continue

                # Buscar en mesh_to_snomed
                cur.execute("""
                    SELECT
                        m.snomed_code,
                        s.name_en,
                        s.name_es,
                        m.confidence
                    FROM mesh_to_snomed m
                    JOIN snomed_specialties s ON m.snomed_code = s.snomed_code
                    WHERE %s LIKE m.mesh_tree_prefix || '%%'
                    ORDER BY LENGTH(m.mesh_tree_prefix) DESC
                    LIMIT 3
                """, (tree_num,))

                for row in cur.fetchall():
                    matches.append(SpecialtyMatch(
                        snomed_code=row[0],
                        name_en=row[1],
                        name_es=row[2],
                        confidence=float(row[3]) if row[3] else 0.8,
                        source='mesh',
                        detail=f"{term_name} [{tree_num}]"
                    ))

        return matches

    @classmethod
    def _match_from_journal(
        cls,
        cur: cursor,
        issn: Optional[str],
        name: Optional[str]
    ) -> List[SpecialtyMatch]:
        """Encuentra especialidades desde la revista."""
        matches = []

        if issn:
            cur.execute("""
                SELECT
                    j.snomed_code,
                    s.name_en,
                    s.name_es
                FROM journal_to_snomed j
                JOIN snomed_specialties s ON j.snomed_code = s.snomed_code
                WHERE j.journal_issn = %s
            """, (issn,))

            for row in cur.fetchall():
                matches.append(SpecialtyMatch(
                    snomed_code=row[0],
                    name_en=row[1],
                    name_es=row[2],
                    confidence=0.9,
                    source='journal',
                    detail=f"ISSN: {issn}"
                ))

        if name and not matches:
            cur.execute("""
                SELECT
                    j.snomed_code,
                    s.name_en,
                    s.name_es
                FROM journal_to_snomed j
                JOIN snomed_specialties s ON j.snomed_code = s.snomed_code
                WHERE j.journal_name ILIKE %s
            """, (name,))

            for row in cur.fetchall():
                matches.append(SpecialtyMatch(
                    snomed_code=row[0],
                    name_en=row[1],
                    name_es=row[2],
                    confidence=0.85,
                    source='journal',
                    detail=f"Journal: {name}"
                ))

        return matches

    @classmethod
    def _match_from_keywords(
        cls,
        cur: cursor,
        keywords: str
    ) -> List[SpecialtyMatch]:
        """Encuentra especialidades desde keywords del autor."""
        matches = []

        if not keywords:
            return matches

        for keyword in keywords.split(';'):
            keyword = keyword.strip().lower()
            if not keyword:
                continue

            cur.execute("""
                SELECT
                    k.snomed_code,
                    s.name_en,
                    s.name_es
                FROM keyword_to_snomed k
                JOIN snomed_specialties s ON k.snomed_code = s.snomed_code
                WHERE LOWER(k.keyword) = %s
            """, (keyword,))

            for row in cur.fetchall():
                matches.append(SpecialtyMatch(
                    snomed_code=row[0],
                    name_en=row[1],
                    name_es=row[2],
                    confidence=0.8,
                    source='keyword',
                    detail=keyword
                ))

        return matches

    @classmethod
    def _match_from_title(
        cls,
        cur: cursor,
        title: str
    ) -> List[SpecialtyMatch]:
        """Encuentra especialidades desde patrones en el título."""
        matches = []

        if not title:
            return matches

        cur.execute("""
            SELECT
                t.title_pattern,
                t.snomed_code,
                s.name_en,
                s.name_es
            FROM title_pattern_to_snomed t
            JOIN snomed_specialties s ON t.snomed_code = s.snomed_code
            WHERE %s ILIKE '%%' || t.title_pattern || '%%'
        """, (title,))

        for row in cur.fetchall():
            matches.append(SpecialtyMatch(
                snomed_code=row[1],
                name_en=row[2],
                name_es=row[3],
                confidence=0.7,
                source='title',
                detail=row[0]
            ))

        return matches

    @classmethod
    def _match_from_abstract(
        cls,
        cur: cursor,
        abstract: str
    ) -> List[SpecialtyMatch]:
        """Encuentra especialidades desde patrones en el abstract."""
        matches = []

        if not abstract:
            return matches

        cur.execute("""
            SELECT
                a.abstract_pattern,
                a.snomed_code,
                s.name_en,
                s.name_es
            FROM abstract_pattern_to_snomed a
            JOIN snomed_specialties s ON a.snomed_code = s.snomed_code
            WHERE %s ILIKE '%%' || a.abstract_pattern || '%%'
        """, (abstract,))

        for row in cur.fetchall():
            matches.append(SpecialtyMatch(
                snomed_code=row[1],
                name_en=row[2],
                name_es=row[3],
                confidence=0.6,
                source='abstract',
                detail=row[0]
            ))

        return matches

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
                s.name_en,
                s.name_es
            FROM affiliation_to_snomed a
            JOIN snomed_specialties s ON a.snomed_code = s.snomed_code
            WHERE %s ILIKE '%%' || a.affiliation_pattern || '%%'
        """, (affiliation,))

        for row in cur.fetchall():
            matches.append(SpecialtyMatch(
                snomed_code=row[1],
                name_en=row[2],
                name_es=row[3],
                confidence=0.75,
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

        Agrupa por snomed_code y combina:
        - Score = sum(weight[source] * confidence) para cada fuente única
        - Normalizado a 0-1
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
                    'raw_score': 0.0,
                    'sources': {},
                }

            # Acumular score por fuente (solo la mejor confidence por fuente)
            source = match.source
            weight = cls.WEIGHTS.get(source, 0.1)
            weighted_confidence = weight * match.confidence

            if source not in by_code[code]['sources']:
                by_code[code]['sources'][source] = {
                    'confidence': match.confidence,
                    'weighted': weighted_confidence,
                    'detail': match.detail
                }
            else:
                # Mantener el mejor match por fuente
                if match.confidence > by_code[code]['sources'][source]['confidence']:
                    by_code[code]['sources'][source] = {
                        'confidence': match.confidence,
                        'weighted': weighted_confidence,
                        'detail': match.detail
                    }

        # Calcular score final
        results = []
        max_possible_score = sum(cls.WEIGHTS.values())  # 1.0

        for code, data in by_code.items():
            raw_score = sum(
                s['weighted'] for s in data['sources'].values()
            )
            normalized_score = raw_score / max_possible_score

            results.append({
                'snomed_code': data['snomed_code'],
                'name_en': data['name_en'],
                'name_es': data['name_es'],
                'score': round(normalized_score, 3),
                'sources': list(data['sources'].keys()),
                'details': {
                    k: v['detail'] for k, v in data['sources'].items()
                }
            })

        return results

    @classmethod
    def get_specialty_stats(cls, cur: cursor) -> Dict:
        """
        Obtiene estadísticas de las tablas de mapeo.

        Returns:
            Dict con conteos de cada tabla de mapeo
        """
        stats = {}

        tables = [
            ('mesh_to_snomed', 'mesh_mappings'),
            ('journal_to_snomed', 'journal_mappings'),
            ('keyword_to_snomed', 'keyword_mappings'),
            ('title_pattern_to_snomed', 'title_mappings'),
            ('abstract_pattern_to_snomed', 'abstract_mappings'),
            ('affiliation_to_snomed', 'affiliation_mappings'),
        ]

        for table, key in tables:
            try:
                cur.execute(f"SELECT COUNT(*) FROM {table}")
                stats[key] = cur.fetchone()[0]
            except Exception:
                stats[key] = 0

        return stats
