#!/usr/bin/env python3
"""
Poblar la tabla author_specialties con especialidades inferidas.

Este script analiza todos los autores únicos y sus artículos para inferir
especialidades médicas basándose únicamente en las afiliaciones de los autores.

La afiliación es el único campo 100% fiable para determinar la especialidad
de cada autor individual (un artículo puede tener autores de múltiples
especialidades).

Uso:
    python scripts/populate_author_specialties.py           # Ejecutar
    python scripts/populate_author_specialties.py --limit 1000  # Solo 1000 autores
    python scripts/populate_author_specialties.py --incremental # Solo autores nuevos
"""

import argparse
import sys
from pathlib import Path
from collections import defaultdict
from datetime import datetime

# Añadir el directorio raíz al path
sys.path.insert(0, str(Path(__file__).parent.parent))

from config.settings import settings
from src.database.connection import db
from src.services.specialty_service import SpecialtyService


def get_unique_authors(cur, limit=None, incremental=False):
    """
    Obtiene la lista de autores únicos.

    Args:
        cur: Cursor de base de datos
        limit: Número máximo de autores a procesar
        incremental: Si True, solo procesa autores sin especialidades

    Returns:
        Lista de tuplas (author_name, author_orcid)
    """
    if incremental:
        # Solo autores que no tienen especialidades asignadas
        query = """
            SELECT DISTINCT pa.author_name, pa.author_orcid
            FROM raw.pubmed_authors pa
            LEFT JOIN sm_result.author_specialties asp ON pa.author_name = asp.author_name
            WHERE asp.sm_author_specialty_id IS NULL
        """
    else:
        query = """
            SELECT DISTINCT author_name, MAX(author_orcid) as author_orcid
            FROM raw.pubmed_authors
            GROUP BY author_name
        """

    if limit:
        query += f" LIMIT {limit}"

    cur.execute(query)
    return cur.fetchall()


def get_author_articles(cur, author_name):
    """
    Obtiene los artículos de un autor.

    Returns:
        Lista de pubmed_ids
    """
    cur.execute("""
        SELECT DISTINCT pubmed_id
        FROM raw.pubmed_authors
        WHERE author_name = %s
    """, (author_name,))
    return [row[0] for row in cur.fetchall()]


def infer_author_specialties(cur, author_name, article_ids):
    """
    Infiere las especialidades de un autor basándose en sus artículos.

    Combina las especialidades de todos los artículos (basadas en afiliaciones)
    y calcula un score agregado para cada especialidad.

    Returns:
        Dict de {snomed_code: {confidence, article_count, name_en, name_es}}
    """
    # Agregar especialidades de todos los artículos
    specialty_data = defaultdict(lambda: {
        'total_confidence': 0.0,
        'article_count': 0,
        'name_en': None,
        'name_es': None
    })

    for pubmed_id in article_ids:
        try:
            specialties = SpecialtyService.infer_author_specialties(
                cur, pubmed_id, min_confidence=0.5
            )

            for spec in specialties:
                code = spec['snomed_code']
                specialty_data[code]['total_confidence'] += spec['confidence']
                specialty_data[code]['article_count'] += 1
                specialty_data[code]['name_en'] = spec['name_en']
                specialty_data[code]['name_es'] = spec['name_es']

        except Exception:
            # Ignorar errores en artículos individuales
            continue

    # Calcular confianza promedio para cada especialidad
    results = {}
    for code, data in specialty_data.items():
        if data['article_count'] > 0:
            results[code] = {
                'confidence': data['total_confidence'] / data['article_count'],
                'article_count': data['article_count'],
                'name_en': data['name_en'],
                'name_es': data['name_es']
            }

    return results


def save_author_specialties(cur, author_name, author_orcid, specialties):
    """
    Guarda las especialidades de un autor en la BD.

    Usa INSERT ... ON CONFLICT para actualizar si ya existe.
    """
    for snomed_code, data in specialties.items():
        cur.execute("""
            INSERT INTO sm_result.author_specialties
                (author_name, author_orcid, snomed_code, confidence, article_count, last_updated)
            VALUES (%s, %s, %s, %s, %s, %s)
            ON CONFLICT (author_name, snomed_code)
            DO UPDATE SET
                author_orcid = EXCLUDED.author_orcid,
                confidence = EXCLUDED.confidence,
                article_count = EXCLUDED.article_count,
                last_updated = EXCLUDED.last_updated
        """, (
            author_name,
            author_orcid,
            snomed_code,
            round(data['confidence'], 3),
            data['article_count'],
            datetime.now()
        ))


def main():
    parser = argparse.ArgumentParser(
        description='Poblar tabla author_specialties con especialidades inferidas'
    )
    parser.add_argument(
        '--limit',
        type=int,
        help='Número máximo de autores a procesar'
    )
    parser.add_argument(
        '--incremental',
        action='store_true',
        help='Solo procesar autores sin especialidades asignadas'
    )
    parser.add_argument(
        '--commit-every',
        type=int,
        default=100,
        help='Hacer commit cada N autores (default: 100)'
    )
    args = parser.parse_args()

    print("=" * 60)
    print("POBLAR ESPECIALIDADES DE AUTORES")
    print("(basado únicamente en afiliaciones)")
    print("=" * 60)

    try:
        with db.cursor_context() as cur:
            # Obtener autores únicos
            print("\nObteniendo lista de autores...")
            authors = get_unique_authors(cur, args.limit, args.incremental)
            total_authors = len(authors)
            print(f"Autores a procesar: {total_authors:,}")

            if total_authors == 0:
                print("No hay autores para procesar.")
                return

            # Estadísticas
            processed = 0
            with_specialties = 0
            total_specialties = 0

            print("\nProcesando autores...")

            for i, (author_name, author_orcid) in enumerate(authors):
                # Obtener artículos del autor
                articles = get_author_articles(cur, author_name)

                if not articles:
                    processed += 1
                    continue

                # Inferir especialidades
                specialties = infer_author_specialties(cur, author_name, articles)

                if specialties:
                    # Guardar en BD
                    save_author_specialties(cur, author_name, author_orcid, specialties)
                    with_specialties += 1
                    total_specialties += len(specialties)

                processed += 1

                # Commit periódico
                if processed % args.commit_every == 0:
                    db.commit()
                    pct = processed / total_authors * 100
                    print(f"  Procesados: {processed:,}/{total_authors:,} ({pct:.1f}%) - "
                          f"Con especialidades: {with_specialties:,}")

            # Commit final
            db.commit()

            # Estadísticas finales
            print("\n" + "=" * 60)
            print("COMPLETADO")
            print("=" * 60)
            print(f"Autores procesados: {processed:,}")
            print(f"Autores con especialidades: {with_specialties:,} "
                  f"({with_specialties/processed*100:.1f}%)")
            print(f"Total especialidades asignadas: {total_specialties:,}")
            print(f"Promedio especialidades/autor: {total_specialties/max(with_specialties,1):.2f}")

            # Verificar en BD
            cur.execute("SELECT COUNT(*) FROM sm_result.author_specialties")
            total_in_db = cur.fetchone()[0]
            print(f"\nTotal registros en author_specialties: {total_in_db:,}")

    except Exception as e:
        print(f"\nError: {e}")
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == '__main__':
    main()
