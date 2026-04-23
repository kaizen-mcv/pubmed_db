#!/usr/bin/env python3
"""Generates statistics for the PubMed database.

Exports results as JSON to the .stats/ folder.
"""

import json
import os
import sys
from collections import Counter
from datetime import datetime
from typing import Any

# Add the root directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src.database.connection import db


# Output directory
STATS_DIR = os.path.join(os.path.dirname(__file__), '..', '.stats')


def ensure_stats_dir():
    """Creates the .stats directory if it does not exist."""
    os.makedirs(STATS_DIR, exist_ok=True)


def save_json(filename: str, data: Any):
    """Saves data to a JSON file."""
    filepath = os.path.join(STATS_DIR, filename)
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2, default=str)
    print(f"  -> Guardado: {filepath}")


def get_author_names_stats() -> dict:
    """Statistics about author names."""
    print("\n[1/12] Analizando nombres de autores...")

    stats = {}

    with db.cursor_context() as cur:
        # Total of unique authors
        cur.execute("SELECT COUNT(DISTINCT author_name) FROM raw.pubmed_authors")
        stats['total_unique_authors'] = cur.fetchone()[0]

        # Names with hyphen (compound surnames)
        cur.execute("""
            SELECT COUNT(DISTINCT author_name)
            FROM raw.pubmed_authors
            WHERE author_name LIKE '%-%'
        """)
        stats['with_hyphen'] = cur.fetchone()[0]

        # Only initials in given name (e.g., "García, A M", "López, J")
        cur.execute("""
            SELECT COUNT(DISTINCT author_name)
            FROM raw.pubmed_authors
            WHERE author_name ~ ', [A-Z]( [A-Z])*$'
        """)
        stats['only_initials'] = cur.fetchone()[0]

        # Full name (without only initials)
        cur.execute("""
            SELECT COUNT(DISTINCT author_name)
            FROM raw.pubmed_authors
            WHERE author_name !~ ', [A-Z]( [A-Z])*$'
        """)
        stats['full_name'] = cur.fetchone()[0]

        # Surnames with Spanish particles
        cur.execute("""
            SELECT COUNT(DISTINCT author_name)
            FROM raw.pubmed_authors
            WHERE author_name ~* '( de la | del | de los | de las | de )'
        """)
        stats['with_spanish_particles'] = cur.fetchone()[0]

        # Special characters (ñ, accents)
        cur.execute("""
            SELECT COUNT(DISTINCT author_name)
            FROM raw.pubmed_authors
            WHERE author_name ~ '[áéíóúñÁÉÍÓÚÑüÜ]'
        """)
        stats['with_special_chars'] = cur.fetchone()[0]

        # Top 10 most common surnames
        cur.execute("""
            SELECT SPLIT_PART(author_name, ',', 1) as lastname, COUNT(*) as count
            FROM raw.pubmed_authors
            GROUP BY lastname
            ORDER BY count DESC
            LIMIT 20
        """)
        stats['top_20_lastnames'] = [
            {'lastname': row[0], 'count': row[1]} for row in cur.fetchall()
        ]

        # Examples of each category
        cur.execute("""
            SELECT DISTINCT author_name FROM raw.pubmed_authors
            WHERE author_name LIKE '%-%' LIMIT 5
        """)
        stats['examples_hyphen'] = [row[0] for row in cur.fetchall()]

        cur.execute("""
            SELECT DISTINCT author_name FROM raw.pubmed_authors
            WHERE author_name ~ ', [A-Z]( [A-Z])*$' LIMIT 5
        """)
        stats['examples_initials'] = [row[0] for row in cur.fetchall()]

        cur.execute("""
            SELECT DISTINCT author_name FROM raw.pubmed_authors
            WHERE author_name ~* '( de la | del | de los | de las | de )' LIMIT 5
        """)
        stats['examples_particles'] = [row[0] for row in cur.fetchall()]

    # Compute percentages
    total = stats['total_unique_authors']
    stats['percentages'] = {
        'with_hyphen': round(stats['with_hyphen'] / total * 100, 2),
        'only_initials': round(stats['only_initials'] / total * 100, 2),
        'full_name': round(stats['full_name'] / total * 100, 2),
        'with_spanish_particles': round(stats['with_spanish_particles'] / total * 100, 2),
        'with_special_chars': round(stats['with_special_chars'] / total * 100, 2),
    }

    return stats


def get_productivity_stats() -> dict:
    """Author productivity statistics."""
    print("\n[2/12] Analizando productividad de autores...")

    stats = {}

    with db.cursor_context() as cur:
        # Top 20 most prolific authors
        cur.execute("""
            SELECT author_name, COUNT(DISTINCT pubmed_id) as articles
            FROM raw.pubmed_authors
            GROUP BY author_name
            ORDER BY articles DESC
            LIMIT 20
        """)
        stats['top_20_authors'] = [
            {'author': row[0], 'articles': row[1]} for row in cur.fetchall()
        ]

        # Distribution of publications per author
        cur.execute("""
            WITH author_counts AS (
                SELECT author_name, COUNT(DISTINCT pubmed_id) as articles
                FROM raw.pubmed_authors
                GROUP BY author_name
            )
            SELECT
                CASE
                    WHEN articles = 1 THEN '1'
                    WHEN articles BETWEEN 2 AND 5 THEN '2-5'
                    WHEN articles BETWEEN 6 AND 10 THEN '6-10'
                    WHEN articles BETWEEN 11 AND 20 THEN '11-20'
                    WHEN articles BETWEEN 21 AND 50 THEN '21-50'
                    ELSE '50+'
                END as range,
                COUNT(*) as authors
            FROM author_counts
            GROUP BY range
            ORDER BY MIN(articles)
        """)
        stats['distribution'] = [
            {'range': row[0], 'authors': row[1]} for row in cur.fetchall()
        ]

        # "One-hit wonder" authors (only 1 publication)
        cur.execute("""
            SELECT COUNT(*) FROM (
                SELECT author_name
                FROM raw.pubmed_authors
                GROUP BY author_name
                HAVING COUNT(DISTINCT pubmed_id) = 1
            ) t
        """)
        stats['one_pubmed_authors'] = cur.fetchone()[0]

        # Average articles per author
        cur.execute("""
            SELECT AVG(articles) FROM (
                SELECT COUNT(DISTINCT pubmed_id) as articles
                FROM raw.pubmed_authors
                GROUP BY author_name
            ) t
        """)
        stats['avg_articles_per_author'] = round(float(cur.fetchone()[0]), 2)

    return stats


def get_author_position_stats() -> dict:
    """Author position statistics."""
    print("\n[3/12] Analizando posición de autores...")

    stats = {}

    with db.cursor_context() as cur:
        # Distribution by position
        cur.execute("""
            SELECT
                CASE
                    WHEN author_position = 1 THEN 'Primer autor'
                    WHEN author_position = 2 THEN 'Segundo autor'
                    WHEN author_position = 3 THEN 'Tercer autor'
                    WHEN author_position BETWEEN 4 AND 5 THEN 'Posición 4-5'
                    WHEN author_position BETWEEN 6 AND 10 THEN 'Posición 6-10'
                    ELSE 'Posición 11+'
                END as position_range,
                COUNT(*) as count
            FROM raw.pubmed_authors
            WHERE author_position IS NOT NULL AND author_position > 0
            GROUP BY position_range
            ORDER BY MIN(author_position)
        """)
        stats['position_distribution'] = [
            {'position': row[0], 'count': row[1]} for row in cur.fetchall()
        ]

        # Total first Spanish authors
        cur.execute("""
            SELECT COUNT(*) FROM raw.pubmed_authors WHERE author_position = 1
        """)
        stats['first_authors'] = cur.fetchone()[0]

        # Total records with position
        cur.execute("""
            SELECT COUNT(*) FROM raw.pubmed_authors
            WHERE author_position IS NOT NULL AND author_position > 0
        """)
        stats['total_with_position'] = cur.fetchone()[0]

        # Percentage as first author
        if stats['total_with_position'] > 0:
            stats['first_author_percentage'] = round(
                stats['first_authors'] / stats['total_with_position'] * 100, 2
            )
        else:
            stats['first_author_percentage'] = 0

    return stats


def get_identifiers_stats() -> dict:
    """Identifier statistics (ORCID, email, DOI)."""
    print("\n[4/12] Analizando identificadores...")

    stats = {}

    with db.cursor_context() as cur:
        # Authors with ORCID
        cur.execute("SELECT COUNT(*) FROM raw.pubmed_authors WHERE author_orcid IS NOT NULL")
        stats['authors_with_orcid'] = cur.fetchone()[0]

        cur.execute("SELECT COUNT(DISTINCT author_name) FROM raw.pubmed_authors WHERE author_orcid IS NOT NULL")
        stats['unique_authors_with_orcid'] = cur.fetchone()[0]

        # Authors with email
        cur.execute("SELECT COUNT(*) FROM raw.pubmed_authors WHERE author_email IS NOT NULL")
        stats['authors_with_email'] = cur.fetchone()[0]

        cur.execute("SELECT COUNT(DISTINCT author_name) FROM raw.pubmed_authors WHERE author_email IS NOT NULL")
        stats['unique_authors_with_email'] = cur.fetchone()[0]

        # Articles with DOI
        cur.execute("SELECT COUNT(*) FROM raw.pubmed_articles WHERE article_doi IS NOT NULL")
        stats['articles_with_doi'] = cur.fetchone()[0]

        cur.execute("SELECT COUNT(*) FROM raw.pubmed_articles")
        stats['total_articles'] = cur.fetchone()[0]

        cur.execute("SELECT COUNT(*) FROM raw.pubmed_authors")
        stats['total_author_records'] = cur.fetchone()[0]

        cur.execute("SELECT COUNT(DISTINCT author_name) FROM raw.pubmed_authors")
        stats['total_unique_authors'] = cur.fetchone()[0]

    # Percentages
    stats['percentages'] = {
        'orcid': round(stats['unique_authors_with_orcid'] / stats['total_unique_authors'] * 100, 2),
        'email': round(stats['unique_authors_with_email'] / stats['total_unique_authors'] * 100, 2),
        'doi': round(stats['articles_with_doi'] / stats['total_articles'] * 100, 2),
    }

    return stats


def get_affiliations_stats() -> dict:
    """Affiliation statistics."""
    print("\n[5/12] Analizando afiliaciones...")

    stats = {}

    with db.cursor_context() as cur:
        # Top institutions (simplified - first words)
        cur.execute("""
            SELECT affiliation, COUNT(*) as count
            FROM raw.pubmed_authors
            WHERE affiliation IS NOT NULL
            GROUP BY affiliation
            ORDER BY count DESC
            LIMIT 30
        """)
        stats['top_30_affiliations'] = [
            {'affiliation': row[0][:200], 'count': row[1]} for row in cur.fetchall()
        ]

        # Geographic distribution (Spanish cities)
        cities = ['Madrid', 'Barcelona', 'Valencia', 'Sevilla', 'Málaga', 'Bilbao',
                  'Zaragoza', 'Murcia', 'Salamanca', 'Granada', 'Alicante', 'Córdoba',
                  'Valladolid', 'Oviedo', 'Santander', 'Pamplona', 'San Sebastián',
                  'Santiago', 'La Coruña', 'Vigo']

        city_counts = []
        for city in cities:
            cur.execute("""
                SELECT COUNT(DISTINCT pubmed_id)
                FROM raw.pubmed_authors
                WHERE affiliation ILIKE %s
            """, (f'%{city}%',))
            count = cur.fetchone()[0]
            if count > 0:
                city_counts.append({'city': city, 'articles': count})

        stats['geographic_distribution'] = sorted(
            city_counts, key=lambda x: x['articles'], reverse=True
        )

        # CIBER (Centro de Investigación Biomédica en Red)
        cur.execute("""
            SELECT COUNT(DISTINCT pubmed_id)
            FROM raw.pubmed_authors
            WHERE affiliation ILIKE '%CIBER%'
        """)
        stats['ciber_articles'] = cur.fetchone()[0]

        # Universities
        cur.execute("""
            SELECT COUNT(DISTINCT pubmed_id)
            FROM raw.pubmed_authors
            WHERE affiliation ILIKE '%University%' OR affiliation ILIKE '%Universidad%'
                OR affiliation ILIKE '%Universitat%'
        """)
        stats['university_articles'] = cur.fetchone()[0]

        # Hospitals
        cur.execute("""
            SELECT COUNT(DISTINCT pubmed_id)
            FROM raw.pubmed_authors
            WHERE affiliation ILIKE '%Hospital%'
        """)
        stats['hospital_articles'] = cur.fetchone()[0]

        # Total articles
        cur.execute("SELECT COUNT(*) FROM raw.pubmed_articles")
        total = cur.fetchone()[0]

        stats['percentages'] = {
            'ciber': round(stats['ciber_articles'] / total * 100, 2),
            'university': round(stats['university_articles'] / total * 100, 2),
            'hospital': round(stats['hospital_articles'] / total * 100, 2),
        }

    return stats


def get_temporal_stats() -> dict:
    """Temporal statistics."""
    print("\n[6/12] Analizando distribución temporal...")

    stats = {}

    with db.cursor_context() as cur:
        # Articles per year
        cur.execute("""
            SELECT EXTRACT(YEAR FROM publication_date)::int as year, COUNT(*) as count
            FROM raw.pubmed_articles
            WHERE publication_date IS NOT NULL
            GROUP BY year
            ORDER BY year
        """)
        stats['by_year'] = [
            {'year': row[0], 'count': row[1]} for row in cur.fetchall()
        ]

        # Articles per month (aggregated over all years)
        cur.execute("""
            SELECT EXTRACT(MONTH FROM publication_date)::int as month, COUNT(*) as count
            FROM raw.pubmed_articles
            WHERE publication_date IS NOT NULL
            GROUP BY month
            ORDER BY month
        """)
        month_names = ['', 'Enero', 'Febrero', 'Marzo', 'Abril', 'Mayo', 'Junio',
                       'Julio', 'Agosto', 'Septiembre', 'Octubre', 'Noviembre', 'Diciembre']
        stats['by_month'] = [
            {'month': month_names[row[0]], 'count': row[1]} for row in cur.fetchall()
        ]

        # Date range
        cur.execute("""
            SELECT MIN(publication_date), MAX(publication_date)
            FROM raw.pubmed_articles
            WHERE publication_date IS NOT NULL
        """)
        row = cur.fetchone()
        stats['date_range'] = {
            'min': str(row[0]) if row[0] else None,
            'max': str(row[1]) if row[1] else None,
        }

        # Articles without date
        cur.execute("SELECT COUNT(*) FROM raw.pubmed_articles WHERE publication_date IS NULL")
        stats['without_date'] = cur.fetchone()[0]

    return stats


def get_journals_stats() -> dict:
    """Journal statistics."""
    print("\n[7/12] Analizando revistas...")

    stats = {}

    with db.cursor_context() as cur:
        # Top 30 journals
        cur.execute("""
            SELECT journal_name, COUNT(*) as count
            FROM raw.pubmed_articles
            WHERE journal_name IS NOT NULL
            GROUP BY journal_name
            ORDER BY count DESC
            LIMIT 30
        """)
        stats['top_30_journals'] = [
            {'journal': row[0], 'articles': row[1]} for row in cur.fetchall()
        ]

        # Total unique journals
        cur.execute("SELECT COUNT(DISTINCT journal_name) FROM raw.pubmed_articles WHERE journal_name IS NOT NULL")
        stats['unique_journals'] = cur.fetchone()[0]

        # Journals with ISSN vs without ISSN
        cur.execute("SELECT COUNT(*) FROM raw.pubmed_articles WHERE journal_issn IS NOT NULL")
        stats['with_issn'] = cur.fetchone()[0]

        cur.execute("SELECT COUNT(*) FROM raw.pubmed_articles WHERE journal_issn IS NULL")
        stats['without_issn'] = cur.fetchone()[0]

        # Distribution of articles per journal
        cur.execute("""
            WITH journal_counts AS (
                SELECT journal_name, COUNT(*) as articles
                FROM raw.pubmed_articles
                WHERE journal_name IS NOT NULL
                GROUP BY journal_name
            )
            SELECT
                CASE
                    WHEN articles = 1 THEN '1 artículo'
                    WHEN articles BETWEEN 2 AND 5 THEN '2-5 artículos'
                    WHEN articles BETWEEN 6 AND 20 THEN '6-20 artículos'
                    WHEN articles BETWEEN 21 AND 50 THEN '21-50 artículos'
                    ELSE '50+ artículos'
                END as range,
                COUNT(*) as journals
            FROM journal_counts
            GROUP BY range
            ORDER BY MIN(articles)
        """)
        stats['distribution'] = [
            {'range': row[0], 'journals': row[1]} for row in cur.fetchall()
        ]

    return stats


def get_scientific_content_stats() -> dict:
    """Scientific content statistics (MeSH, keywords, types)."""
    print("\n[8/12] Analizando contenido científico...")

    stats = {}

    with db.cursor_context() as cur:
        # Top MeSH terms
        cur.execute("""
            SELECT mesh_terms FROM raw.pubmed_articles WHERE mesh_terms IS NOT NULL
        """)
        mesh_counter = Counter()
        for row in cur.fetchall():
            terms = [t.strip() for t in row[0].split(',')]
            mesh_counter.update(terms)

        stats['top_50_mesh_terms'] = [
            {'term': term, 'count': count}
            for term, count in mesh_counter.most_common(50)
        ]

        # Publication types
        cur.execute("""
            SELECT publication_types FROM raw.pubmed_articles WHERE publication_types IS NOT NULL
        """)
        type_counter = Counter()
        for row in cur.fetchall():
            types = [t.strip() for t in row[0].split(';')]
            type_counter.update(types)

        stats['publication_types'] = [
            {'type': ptype, 'count': count}
            for ptype, count in type_counter.most_common(20)
        ]

        # Top author keywords
        cur.execute("""
            SELECT author_keywords FROM raw.pubmed_articles WHERE author_keywords IS NOT NULL
        """)
        keyword_counter = Counter()
        for row in cur.fetchall():
            keywords = [k.strip() for k in row[0].split(',')]
            keyword_counter.update(keywords)

        stats['top_50_author_keywords'] = [
            {'keyword': kw, 'count': count}
            for kw, count in keyword_counter.most_common(50)
        ]

        # Data completeness
        cur.execute("SELECT COUNT(*) FROM raw.pubmed_articles")
        total = cur.fetchone()[0]

        cur.execute("SELECT COUNT(*) FROM raw.pubmed_articles WHERE article_abstract IS NOT NULL")
        with_abstract = cur.fetchone()[0]

        cur.execute("SELECT COUNT(*) FROM raw.pubmed_articles WHERE mesh_terms IS NOT NULL")
        with_mesh = cur.fetchone()[0]

        cur.execute("SELECT COUNT(*) FROM raw.pubmed_articles WHERE author_keywords IS NOT NULL")
        with_keywords = cur.fetchone()[0]

        stats['data_completeness'] = {
            'total_articles': total,
            'with_abstract': with_abstract,
            'with_mesh_terms': with_mesh,
            'with_author_keywords': with_keywords,
            'percentages': {
                'abstract': round(with_abstract / total * 100, 2),
                'mesh_terms': round(with_mesh / total * 100, 2),
                'author_keywords': round(with_keywords / total * 100, 2),
            }
        }

    return stats


def get_summary_stats() -> dict:
    """General database summary."""
    print("\n[Resumen] Generando estadísticas generales...")

    stats = {}

    with db.cursor_context() as cur:
        cur.execute("SELECT COUNT(*) FROM raw.pubmed_articles")
        stats['total_articles'] = cur.fetchone()[0]

        cur.execute("SELECT COUNT(*) FROM raw.pubmed_authors")
        stats['total_author_records'] = cur.fetchone()[0]

        cur.execute("SELECT COUNT(DISTINCT author_name) FROM raw.pubmed_authors")
        stats['unique_authors'] = cur.fetchone()[0]

        cur.execute("SELECT COUNT(DISTINCT journal_name) FROM raw.pubmed_articles")
        stats['unique_journals'] = cur.fetchone()[0]

        cur.execute("SELECT MIN(publication_date), MAX(publication_date) FROM raw.pubmed_articles")
        row = cur.fetchone()
        stats['date_range'] = {
            'from': str(row[0]) if row[0] else None,
            'to': str(row[1]) if row[1] else None,
        }

        stats['generated_at'] = datetime.now().isoformat()

    return stats


def get_attr_tables_stats() -> dict:
    """Statistics for the normalized attribute tables (sm_attr)."""
    print("\n[10/12] Analizando tablas de atributos normalizados...")

    stats = {}

    with db.cursor_context() as cur:
        # sm_attr.journals
        cur.execute("SELECT COUNT(*) FROM sm_attr.journals")
        stats['journals'] = {
            'total': cur.fetchone()[0],
        }
        cur.execute("SELECT journal_name, article_count FROM sm_attr.journals ORDER BY article_count DESC LIMIT 10")
        stats['journals']['top_10'] = [
            {'journal': row[0], 'articles': row[1]} for row in cur.fetchall()
        ]

        # sm_attr.keywords
        cur.execute("SELECT COUNT(*) FROM sm_attr.keywords")
        stats['keywords'] = {
            'total': cur.fetchone()[0],
        }
        cur.execute("SELECT keyword_text, article_count FROM sm_attr.keywords ORDER BY article_count DESC LIMIT 20")
        stats['keywords']['top_20'] = [
            {'keyword': row[0], 'articles': row[1]} for row in cur.fetchall()
        ]

        # sm_attr.affiliations
        cur.execute("SELECT COUNT(*) FROM sm_attr.affiliations")
        stats['affiliations'] = {
            'total': cur.fetchone()[0],
        }
        cur.execute("SELECT LEFT(affiliation_text, 150), author_count FROM sm_attr.affiliations ORDER BY author_count DESC LIMIT 10")
        stats['affiliations']['top_10'] = [
            {'affiliation': row[0], 'authors': row[1]} for row in cur.fetchall()
        ]

        # sm_attr.mesh_terms_articles
        cur.execute("SELECT COUNT(*) FROM sm_attr.mesh_terms_articles")
        stats['mesh_terms_articles'] = {
            'total': cur.fetchone()[0],
        }
        cur.execute("SELECT mesh_term_text, article_count FROM sm_attr.mesh_terms_articles ORDER BY article_count DESC LIMIT 20")
        stats['mesh_terms_articles']['top_20'] = [
            {'mesh_term': row[0], 'articles': row[1]} for row in cur.fetchall()
        ]

    return stats


def get_specialty_detection_stats() -> dict:
    """Statistics for SNOMED specialty detection in affiliations."""
    print("\n[12/12] Analizando especialidades SNOMED en afiliaciones...")

    stats = {}

    with db.cursor_context() as cur:
        # Totals
        cur.execute("SELECT COUNT(*) FROM raw.pubmed_authors")
        total_records = cur.fetchone()[0]

        cur.execute("SELECT COUNT(DISTINCT author_name) FROM raw.pubmed_authors")
        total_unique = cur.fetchone()[0]

        stats['total_author_records'] = total_records
        stats['total_unique_authors'] = total_unique

        # Fetch real SNOMED specialties (only name_en and name_es)
        cur.execute("""
            SELECT snomed_code, name_en, name_es
            FROM vocab.snomed_specialties
            WHERE name_en IS NOT NULL
            ORDER BY name_en
        """)
        snomed_specialties = cur.fetchall()

        # Build conditions using only the official SNOMED names
        conditions = []
        for code, name_en, name_es in snomed_specialties:
            if name_en:
                conditions.append(f"LOWER(affiliation) LIKE '%{name_en.lower()}%'")
            if name_es:
                conditions.append(f"LOWER(affiliation) LIKE '%{name_es.lower()}%'")

        where_clause = " OR ".join(conditions)

        # Count records with SNOMED specialty
        cur.execute(f"""
            SELECT COUNT(*) FROM raw.pubmed_authors
            WHERE affiliation IS NOT NULL AND ({where_clause})
        """)
        records_with_specialty = cur.fetchone()[0]

        # Count unique authors with SNOMED specialty
        cur.execute(f"""
            SELECT COUNT(DISTINCT author_name) FROM raw.pubmed_authors
            WHERE affiliation IS NOT NULL AND ({where_clause})
        """)
        unique_with_specialty = cur.fetchone()[0]

        stats['records_with_specialty'] = records_with_specialty
        stats['unique_authors_with_specialty'] = unique_with_specialty

        stats['percentages'] = {
            'records': round(records_with_specialty / total_records * 100, 2) if total_records > 0 else 0,
            'unique_authors': round(unique_with_specialty / total_unique * 100, 2) if total_unique > 0 else 0,
        }

        # Breakdown by SNOMED specialty
        specialty_counts = []
        for code, name_en, name_es in snomed_specialties:
            pattern_conditions = []
            if name_en:
                pattern_conditions.append(f"LOWER(affiliation) LIKE '%{name_en.lower()}%'")
            if name_es:
                pattern_conditions.append(f"LOWER(affiliation) LIKE '%{name_es.lower()}%'")

            if not pattern_conditions:
                continue

            pattern_where = " OR ".join(pattern_conditions)

            cur.execute(f"""
                SELECT COUNT(DISTINCT author_name)
                FROM raw.pubmed_authors
                WHERE affiliation IS NOT NULL AND ({pattern_where})
            """)
            count = cur.fetchone()[0]
            if count > 0:
                specialty_counts.append({
                    'snomed_code': code,
                    'specialty_en': name_en,
                    'specialty_es': name_es,
                    'unique_authors': count,
                    'percentage': round(count / total_unique * 100, 2)
                })

        stats['by_specialty'] = sorted(
            specialty_counts, key=lambda x: x['unique_authors'], reverse=True
        )

        stats['snomed_specialties_total'] = len(snomed_specialties)
        stats['snomed_specialties_detected'] = len(specialty_counts)

    return stats


def get_data_completeness_stats() -> dict:
    """Data completeness statistics per column."""
    print("\n[9/12] Analizando completitud de datos...")

    stats = {
        'pubmed_articles': {},
        'pubmed_authors': {}
    }

    with db.cursor_context() as cur:
        # Total articles
        cur.execute("SELECT COUNT(*) FROM raw.pubmed_articles")
        total_articles = cur.fetchone()[0]

        # Columns of the pubmed_articles table
        articles_columns = [
            'pubmed_id',
            'article_title',
            'article_abstract',
            'journal_name',
            'journal_issn',
            'publication_date',
            'article_doi',
            'publication_types',
            'mesh_terms',
            'author_keywords'
        ]

        # Text columns vs others
        text_columns = ['article_title', 'article_abstract', 'journal_name', 'journal_issn',
                        'article_doi', 'publication_types', 'mesh_terms', 'author_keywords']

        for col in articles_columns:
            # For pubmed_id (PK), always present
            if col == 'pubmed_id':
                count = total_articles
            elif col in text_columns:
                cur.execute(f"SELECT COUNT(*) FROM raw.pubmed_articles WHERE {col} IS NOT NULL AND {col} != ''")
                count = cur.fetchone()[0]
            else:
                # For DATE and other non-text types
                cur.execute(f"SELECT COUNT(*) FROM raw.pubmed_articles WHERE {col} IS NOT NULL")
                count = cur.fetchone()[0]

            stats['pubmed_articles'][col] = {
                'count': count,
                'total': total_articles,
                'percentage': round(count / total_articles * 100, 2) if total_articles > 0 else 0
            }

        # Total author records
        cur.execute("SELECT COUNT(*) FROM raw.pubmed_authors")
        total_authors = cur.fetchone()[0]

        # Columns of the pubmed_authors table
        authors_columns = [
            'pubmed_id',
            'author_name',
            'author_position',
            'author_orcid',
            'author_email',
            'affiliation'
        ]

        for col in authors_columns:
            # For pubmed_id and author_name, check NOT NULL
            if col in ['pubmed_id', 'author_name']:
                cur.execute(f"SELECT COUNT(*) FROM raw.pubmed_authors WHERE {col} IS NOT NULL")
            elif col == 'author_position':
                cur.execute(f"SELECT COUNT(*) FROM raw.pubmed_authors WHERE {col} IS NOT NULL AND {col} > 0")
            else:
                cur.execute(f"SELECT COUNT(*) FROM raw.pubmed_authors WHERE {col} IS NOT NULL AND {col} != ''")
            count = cur.fetchone()[0]

            stats['pubmed_authors'][col] = {
                'count': count,
                'total': total_authors,
                'percentage': round(count / total_authors * 100, 2) if total_authors > 0 else 0
            }

    return stats


def main():
    """Generates all statistics and saves them to .stats/."""
    print("=" * 60)
    print("GENERADOR DE ESTADÍSTICAS - PubMed España")
    print("=" * 60)

    ensure_stats_dir()

    try:
        # Generate all statistics
        save_json('summary.json', get_summary_stats())
        save_json('author_names.json', get_author_names_stats())
        save_json('productivity.json', get_productivity_stats())
        save_json('author_position.json', get_author_position_stats())
        save_json('identifiers.json', get_identifiers_stats())
        save_json('affiliations.json', get_affiliations_stats())
        save_json('temporal.json', get_temporal_stats())
        save_json('journals.json', get_journals_stats())
        save_json('scientific_content.json', get_scientific_content_stats())
        save_json('data_completeness.json', get_data_completeness_stats())
        save_json('attr_tables.json', get_attr_tables_stats())
        save_json('specialty_detection.json', get_specialty_detection_stats())

        print("\n" + "=" * 60)
        print("COMPLETADO - Estadísticas guardadas en .stats/")
        print("=" * 60)

    finally:
        db.close()


if __name__ == '__main__':
    main()
