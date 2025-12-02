#!/usr/bin/env python3
"""
Script para generar estadísticas de la base de datos PubMed.
Exporta resultados en JSON a la carpeta .stats/
"""

import json
import os
import sys
from collections import Counter
from datetime import datetime
from typing import Any

# Añadir el directorio raíz al path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src.database.connection import db


# Directorio de salida
STATS_DIR = os.path.join(os.path.dirname(__file__), '..', '.stats')


def ensure_stats_dir():
    """Crea el directorio .stats si no existe."""
    os.makedirs(STATS_DIR, exist_ok=True)


def save_json(filename: str, data: Any):
    """Guarda datos en un archivo JSON."""
    filepath = os.path.join(STATS_DIR, filename)
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2, default=str)
    print(f"  -> Guardado: {filepath}")


def get_author_names_stats() -> dict:
    """Estadísticas sobre nombres de autores."""
    print("\n[1/9] Analizando nombres de autores...")

    stats = {}

    with db.cursor_context() as cur:
        # Total de autores únicos
        cur.execute("SELECT COUNT(DISTINCT author_name) FROM pubmed_authors")
        stats['total_unique_authors'] = cur.fetchone()[0]

        # Nombres con guion (apellidos compuestos)
        cur.execute("""
            SELECT COUNT(DISTINCT author_name)
            FROM pubmed_authors
            WHERE author_name LIKE '%-%'
        """)
        stats['with_hyphen'] = cur.fetchone()[0]

        # Solo inicial en nombre (ej: "García, A M", "López, J")
        cur.execute("""
            SELECT COUNT(DISTINCT author_name)
            FROM pubmed_authors
            WHERE author_name ~ ', [A-Z]( [A-Z])*$'
        """)
        stats['only_initials'] = cur.fetchone()[0]

        # Nombre completo (sin solo iniciales)
        cur.execute("""
            SELECT COUNT(DISTINCT author_name)
            FROM pubmed_authors
            WHERE author_name !~ ', [A-Z]( [A-Z])*$'
        """)
        stats['full_name'] = cur.fetchone()[0]

        # Apellidos con partículas españolas
        cur.execute("""
            SELECT COUNT(DISTINCT author_name)
            FROM pubmed_authors
            WHERE author_name ~* '( de la | del | de los | de las | de )'
        """)
        stats['with_spanish_particles'] = cur.fetchone()[0]

        # Caracteres especiales (ñ, tildes)
        cur.execute("""
            SELECT COUNT(DISTINCT author_name)
            FROM pubmed_authors
            WHERE author_name ~ '[áéíóúñÁÉÍÓÚÑüÜ]'
        """)
        stats['with_special_chars'] = cur.fetchone()[0]

        # Top 10 apellidos más comunes
        cur.execute("""
            SELECT SPLIT_PART(author_name, ',', 1) as lastname, COUNT(*) as count
            FROM pubmed_authors
            GROUP BY lastname
            ORDER BY count DESC
            LIMIT 20
        """)
        stats['top_20_lastnames'] = [
            {'lastname': row[0], 'count': row[1]} for row in cur.fetchall()
        ]

        # Ejemplos de cada categoría
        cur.execute("""
            SELECT DISTINCT author_name FROM pubmed_authors
            WHERE author_name LIKE '%-%' LIMIT 5
        """)
        stats['examples_hyphen'] = [row[0] for row in cur.fetchall()]

        cur.execute("""
            SELECT DISTINCT author_name FROM pubmed_authors
            WHERE author_name ~ ', [A-Z]( [A-Z])*$' LIMIT 5
        """)
        stats['examples_initials'] = [row[0] for row in cur.fetchall()]

        cur.execute("""
            SELECT DISTINCT author_name FROM pubmed_authors
            WHERE author_name ~* '( de la | del | de los | de las | de )' LIMIT 5
        """)
        stats['examples_particles'] = [row[0] for row in cur.fetchall()]

    # Calcular porcentajes
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
    """Estadísticas de productividad de autores."""
    print("\n[2/9] Analizando productividad de autores...")

    stats = {}

    with db.cursor_context() as cur:
        # Top 20 autores más prolíficos
        cur.execute("""
            SELECT author_name, COUNT(DISTINCT pubmed_id) as articles
            FROM pubmed_authors
            GROUP BY author_name
            ORDER BY articles DESC
            LIMIT 20
        """)
        stats['top_20_authors'] = [
            {'author': row[0], 'articles': row[1]} for row in cur.fetchall()
        ]

        # Distribución de publicaciones por autor
        cur.execute("""
            WITH author_counts AS (
                SELECT author_name, COUNT(DISTINCT pubmed_id) as articles
                FROM pubmed_authors
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

        # Autores "one-hit wonder" (solo 1 publicación)
        cur.execute("""
            SELECT COUNT(*) FROM (
                SELECT author_name
                FROM pubmed_authors
                GROUP BY author_name
                HAVING COUNT(DISTINCT pubmed_id) = 1
            ) t
        """)
        stats['one_pubmed_authors'] = cur.fetchone()[0]

        # Promedio de artículos por autor
        cur.execute("""
            SELECT AVG(articles) FROM (
                SELECT COUNT(DISTINCT pubmed_id) as articles
                FROM pubmed_authors
                GROUP BY author_name
            ) t
        """)
        stats['avg_articles_per_author'] = round(float(cur.fetchone()[0]), 2)

    return stats


def get_author_position_stats() -> dict:
    """Estadísticas de posición de autores."""
    print("\n[3/9] Analizando posición de autores...")

    stats = {}

    with db.cursor_context() as cur:
        # Distribución por posición
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
            FROM pubmed_authors
            WHERE author_position IS NOT NULL AND author_position > 0
            GROUP BY position_range
            ORDER BY MIN(author_position)
        """)
        stats['position_distribution'] = [
            {'position': row[0], 'count': row[1]} for row in cur.fetchall()
        ]

        # Total de primeros autores españoles
        cur.execute("""
            SELECT COUNT(*) FROM pubmed_authors WHERE author_position = 1
        """)
        stats['first_authors'] = cur.fetchone()[0]

        # Total de registros con posición
        cur.execute("""
            SELECT COUNT(*) FROM pubmed_authors
            WHERE author_position IS NOT NULL AND author_position > 0
        """)
        stats['total_with_position'] = cur.fetchone()[0]

        # Porcentaje como primer autor
        if stats['total_with_position'] > 0:
            stats['first_author_percentage'] = round(
                stats['first_authors'] / stats['total_with_position'] * 100, 2
            )
        else:
            stats['first_author_percentage'] = 0

    return stats


def get_identifiers_stats() -> dict:
    """Estadísticas de identificadores (ORCID, email, DOI)."""
    print("\n[4/9] Analizando identificadores...")

    stats = {}

    with db.cursor_context() as cur:
        # Autores con ORCID
        cur.execute("SELECT COUNT(*) FROM pubmed_authors WHERE author_orcid IS NOT NULL")
        stats['authors_with_orcid'] = cur.fetchone()[0]

        cur.execute("SELECT COUNT(DISTINCT author_name) FROM pubmed_authors WHERE author_orcid IS NOT NULL")
        stats['unique_authors_with_orcid'] = cur.fetchone()[0]

        # Autores con email
        cur.execute("SELECT COUNT(*) FROM pubmed_authors WHERE author_email IS NOT NULL")
        stats['authors_with_email'] = cur.fetchone()[0]

        cur.execute("SELECT COUNT(DISTINCT author_name) FROM pubmed_authors WHERE author_email IS NOT NULL")
        stats['unique_authors_with_email'] = cur.fetchone()[0]

        # Artículos con DOI
        cur.execute("SELECT COUNT(*) FROM pubmed_articles WHERE article_doi IS NOT NULL")
        stats['articles_with_doi'] = cur.fetchone()[0]

        cur.execute("SELECT COUNT(*) FROM pubmed_articles")
        stats['total_articles'] = cur.fetchone()[0]

        cur.execute("SELECT COUNT(*) FROM pubmed_authors")
        stats['total_author_records'] = cur.fetchone()[0]

        cur.execute("SELECT COUNT(DISTINCT author_name) FROM pubmed_authors")
        stats['total_unique_authors'] = cur.fetchone()[0]

    # Porcentajes
    stats['percentages'] = {
        'orcid': round(stats['unique_authors_with_orcid'] / stats['total_unique_authors'] * 100, 2),
        'email': round(stats['unique_authors_with_email'] / stats['total_unique_authors'] * 100, 2),
        'doi': round(stats['articles_with_doi'] / stats['total_articles'] * 100, 2),
    }

    return stats


def get_affiliations_stats() -> dict:
    """Estadísticas de afiliaciones."""
    print("\n[5/9] Analizando afiliaciones...")

    stats = {}

    with db.cursor_context() as cur:
        # Top instituciones (simplificado - primeras palabras)
        cur.execute("""
            SELECT affiliation, COUNT(*) as count
            FROM pubmed_authors
            WHERE affiliation IS NOT NULL
            GROUP BY affiliation
            ORDER BY count DESC
            LIMIT 30
        """)
        stats['top_30_affiliations'] = [
            {'affiliation': row[0][:200], 'count': row[1]} for row in cur.fetchall()
        ]

        # Distribución geográfica (ciudades españolas)
        cities = ['Madrid', 'Barcelona', 'Valencia', 'Sevilla', 'Málaga', 'Bilbao',
                  'Zaragoza', 'Murcia', 'Salamanca', 'Granada', 'Alicante', 'Córdoba',
                  'Valladolid', 'Oviedo', 'Santander', 'Pamplona', 'San Sebastián',
                  'Santiago', 'La Coruña', 'Vigo']

        city_counts = []
        for city in cities:
            cur.execute("""
                SELECT COUNT(DISTINCT pubmed_id)
                FROM pubmed_authors
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
            FROM pubmed_authors
            WHERE affiliation ILIKE '%CIBER%'
        """)
        stats['ciber_articles'] = cur.fetchone()[0]

        # Universidades
        cur.execute("""
            SELECT COUNT(DISTINCT pubmed_id)
            FROM pubmed_authors
            WHERE affiliation ILIKE '%University%' OR affiliation ILIKE '%Universidad%'
                OR affiliation ILIKE '%Universitat%'
        """)
        stats['university_articles'] = cur.fetchone()[0]

        # Hospitales
        cur.execute("""
            SELECT COUNT(DISTINCT pubmed_id)
            FROM pubmed_authors
            WHERE affiliation ILIKE '%Hospital%'
        """)
        stats['hospital_articles'] = cur.fetchone()[0]

        # Total de artículos
        cur.execute("SELECT COUNT(*) FROM pubmed_articles")
        total = cur.fetchone()[0]

        stats['percentages'] = {
            'ciber': round(stats['ciber_articles'] / total * 100, 2),
            'university': round(stats['university_articles'] / total * 100, 2),
            'hospital': round(stats['hospital_articles'] / total * 100, 2),
        }

    return stats


def get_temporal_stats() -> dict:
    """Estadísticas temporales."""
    print("\n[6/9] Analizando distribución temporal...")

    stats = {}

    with db.cursor_context() as cur:
        # Artículos por año
        cur.execute("""
            SELECT EXTRACT(YEAR FROM publication_date)::int as year, COUNT(*) as count
            FROM pubmed_articles
            WHERE publication_date IS NOT NULL
            GROUP BY year
            ORDER BY year
        """)
        stats['by_year'] = [
            {'year': row[0], 'count': row[1]} for row in cur.fetchall()
        ]

        # Artículos por mes (agregado de todos los años)
        cur.execute("""
            SELECT EXTRACT(MONTH FROM publication_date)::int as month, COUNT(*) as count
            FROM pubmed_articles
            WHERE publication_date IS NOT NULL
            GROUP BY month
            ORDER BY month
        """)
        month_names = ['', 'Enero', 'Febrero', 'Marzo', 'Abril', 'Mayo', 'Junio',
                       'Julio', 'Agosto', 'Septiembre', 'Octubre', 'Noviembre', 'Diciembre']
        stats['by_month'] = [
            {'month': month_names[row[0]], 'count': row[1]} for row in cur.fetchall()
        ]

        # Rango de fechas
        cur.execute("""
            SELECT MIN(publication_date), MAX(publication_date)
            FROM pubmed_articles
            WHERE publication_date IS NOT NULL
        """)
        row = cur.fetchone()
        stats['date_range'] = {
            'min': str(row[0]) if row[0] else None,
            'max': str(row[1]) if row[1] else None,
        }

        # Artículos sin fecha
        cur.execute("SELECT COUNT(*) FROM pubmed_articles WHERE publication_date IS NULL")
        stats['without_date'] = cur.fetchone()[0]

    return stats


def get_journals_stats() -> dict:
    """Estadísticas de revistas."""
    print("\n[7/9] Analizando revistas...")

    stats = {}

    with db.cursor_context() as cur:
        # Top 30 revistas
        cur.execute("""
            SELECT journal_name, COUNT(*) as count
            FROM pubmed_articles
            WHERE journal_name IS NOT NULL
            GROUP BY journal_name
            ORDER BY count DESC
            LIMIT 30
        """)
        stats['top_30_journals'] = [
            {'journal': row[0], 'articles': row[1]} for row in cur.fetchall()
        ]

        # Total de revistas únicas
        cur.execute("SELECT COUNT(DISTINCT journal_name) FROM pubmed_articles WHERE journal_name IS NOT NULL")
        stats['unique_journals'] = cur.fetchone()[0]

        # Revistas con ISSN vs sin ISSN
        cur.execute("SELECT COUNT(*) FROM pubmed_articles WHERE journal_issn IS NOT NULL")
        stats['with_issn'] = cur.fetchone()[0]

        cur.execute("SELECT COUNT(*) FROM pubmed_articles WHERE journal_issn IS NULL")
        stats['without_issn'] = cur.fetchone()[0]

        # Distribución de artículos por revista
        cur.execute("""
            WITH journal_counts AS (
                SELECT journal_name, COUNT(*) as articles
                FROM pubmed_articles
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
    """Estadísticas de contenido científico (MeSH, keywords, tipos)."""
    print("\n[8/9] Analizando contenido científico...")

    stats = {}

    with db.cursor_context() as cur:
        # Top MeSH terms
        cur.execute("""
            SELECT mesh_terms FROM pubmed_articles WHERE mesh_terms IS NOT NULL
        """)
        mesh_counter = Counter()
        for row in cur.fetchall():
            terms = [t.strip() for t in row[0].split(',')]
            mesh_counter.update(terms)

        stats['top_50_mesh_terms'] = [
            {'term': term, 'count': count}
            for term, count in mesh_counter.most_common(50)
        ]

        # Tipos de publicación
        cur.execute("""
            SELECT publication_types FROM pubmed_articles WHERE publication_types IS NOT NULL
        """)
        type_counter = Counter()
        for row in cur.fetchall():
            types = [t.strip() for t in row[0].split(';')]
            type_counter.update(types)

        stats['publication_types'] = [
            {'type': ptype, 'count': count}
            for ptype, count in type_counter.most_common(20)
        ]

        # Top keywords de autor
        cur.execute("""
            SELECT author_keywords FROM pubmed_articles WHERE author_keywords IS NOT NULL
        """)
        keyword_counter = Counter()
        for row in cur.fetchall():
            keywords = [k.strip() for k in row[0].split(',')]
            keyword_counter.update(keywords)

        stats['top_50_author_keywords'] = [
            {'keyword': kw, 'count': count}
            for kw, count in keyword_counter.most_common(50)
        ]

        # Completitud de datos
        cur.execute("SELECT COUNT(*) FROM pubmed_articles")
        total = cur.fetchone()[0]

        cur.execute("SELECT COUNT(*) FROM pubmed_articles WHERE article_abstract IS NOT NULL")
        with_abstract = cur.fetchone()[0]

        cur.execute("SELECT COUNT(*) FROM pubmed_articles WHERE mesh_terms IS NOT NULL")
        with_mesh = cur.fetchone()[0]

        cur.execute("SELECT COUNT(*) FROM pubmed_articles WHERE author_keywords IS NOT NULL")
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
    """Resumen general de la base de datos."""
    print("\n[Resumen] Generando estadísticas generales...")

    stats = {}

    with db.cursor_context() as cur:
        cur.execute("SELECT COUNT(*) FROM pubmed_articles")
        stats['total_articles'] = cur.fetchone()[0]

        cur.execute("SELECT COUNT(*) FROM pubmed_authors")
        stats['total_author_records'] = cur.fetchone()[0]

        cur.execute("SELECT COUNT(DISTINCT author_name) FROM pubmed_authors")
        stats['unique_authors'] = cur.fetchone()[0]

        cur.execute("SELECT COUNT(DISTINCT journal_name) FROM pubmed_articles")
        stats['unique_journals'] = cur.fetchone()[0]

        cur.execute("SELECT MIN(publication_date), MAX(publication_date) FROM pubmed_articles")
        row = cur.fetchone()
        stats['date_range'] = {
            'from': str(row[0]) if row[0] else None,
            'to': str(row[1]) if row[1] else None,
        }

        stats['generated_at'] = datetime.now().isoformat()

    return stats


def get_data_completeness_stats() -> dict:
    """Estadísticas de completitud de datos por columna."""
    print("\n[9/9] Analizando completitud de datos...")

    stats = {
        'pubmed_articles': {},
        'pubmed_authors': {}
    }

    with db.cursor_context() as cur:
        # Total de artículos
        cur.execute("SELECT COUNT(*) FROM pubmed_articles")
        total_articles = cur.fetchone()[0]

        # Columnas de la tabla pubmed_articles
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

        # Columnas de texto vs otras
        text_columns = ['article_title', 'article_abstract', 'journal_name', 'journal_issn',
                        'article_doi', 'publication_types', 'mesh_terms', 'author_keywords']

        for col in articles_columns:
            # Para pubmed_id (PK), siempre está presente
            if col == 'pubmed_id':
                count = total_articles
            elif col in text_columns:
                cur.execute(f"SELECT COUNT(*) FROM pubmed_articles WHERE {col} IS NOT NULL AND {col} != ''")
                count = cur.fetchone()[0]
            else:
                # Para DATE y otros tipos no-texto
                cur.execute(f"SELECT COUNT(*) FROM pubmed_articles WHERE {col} IS NOT NULL")
                count = cur.fetchone()[0]

            stats['pubmed_articles'][col] = {
                'count': count,
                'total': total_articles,
                'percentage': round(count / total_articles * 100, 2) if total_articles > 0 else 0
            }

        # Total de registros de autores
        cur.execute("SELECT COUNT(*) FROM pubmed_authors")
        total_authors = cur.fetchone()[0]

        # Columnas de la tabla pubmed_authors
        authors_columns = [
            'pubmed_id',
            'author_name',
            'author_position',
            'author_orcid',
            'author_email',
            'affiliation'
        ]

        for col in authors_columns:
            # Para pubmed_id y author_name, verificar NOT NULL
            if col in ['pubmed_id', 'author_name']:
                cur.execute(f"SELECT COUNT(*) FROM pubmed_authors WHERE {col} IS NOT NULL")
            elif col == 'author_position':
                cur.execute(f"SELECT COUNT(*) FROM pubmed_authors WHERE {col} IS NOT NULL AND {col} > 0")
            else:
                cur.execute(f"SELECT COUNT(*) FROM pubmed_authors WHERE {col} IS NOT NULL AND {col} != ''")
            count = cur.fetchone()[0]

            stats['pubmed_authors'][col] = {
                'count': count,
                'total': total_authors,
                'percentage': round(count / total_authors * 100, 2) if total_authors > 0 else 0
            }

    return stats


def main():
    """Genera todas las estadísticas y las guarda en .stats/"""
    print("=" * 60)
    print("GENERADOR DE ESTADÍSTICAS - PubMed España")
    print("=" * 60)

    ensure_stats_dir()

    try:
        # Generar todas las estadísticas
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

        print("\n" + "=" * 60)
        print("COMPLETADO - Estadísticas guardadas en .stats/")
        print("=" * 60)

    finally:
        db.close()


if __name__ == '__main__':
    main()
