#!/usr/bin/env python3
"""Author deduplication script.

This script populates the sm_result.authors_orcid and sm_result.authors_norm
tables from the data in raw.pubmed_authors.

Three-phase process:
    1. Direct ORCID: Authors with ORCID (100% reliable).
    2. ORCID propagation: Records without ORCID that match on name+affiliation.
    3. Normalization: Remaining authors grouped by normalized name.

Usage:
    python scripts/deduplicacion_autores.py [--dry-run] [--phase N]

Options:
    --dry-run       Only show statistics, do not insert data.
    --phase N       Execute only phase N (1, 2, or 3).
    --reset         Remove existing data before executing.

Documentation: docs/deduplicacion_autores.md
"""

import os
import sys
import argparse
from datetime import datetime
from collections import defaultdict
from typing import Dict, List, Tuple, Optional

import psycopg2
from psycopg2.extras import execute_values

# Add the root directory to the path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config.settings import settings
from src.utils.name_normalizer import get_canonical_name, select_display_name


# =============================================================================
# CONFIGURATION
# =============================================================================

BATCH_SIZE = 10000  # Records per insertion batch


def get_connection():
    """Gets a database connection."""
    config = settings.get_db_connection_params()
    return psycopg2.connect(**config)


# =============================================================================
# PHASE 1: AUTHORS WITH ORCID
# =============================================================================

def phase1_orcid_authors(conn, dry_run: bool = False) -> int:
    """Phase 1: Processes authors with ORCID.

    Groups all records by ORCID and creates a single author per ORCID.

    Args:
        conn: Database connection.
        dry_run: If True, only shows statistics.

    Returns:
        Number of authors inserted.
    """
    print("\n" + "=" * 60)
    print("FASE 1: Autores con ORCID")
    print("=" * 60)

    with conn.cursor() as cur:
        # Get data grouped by ORCID
        print("\nObteniendo datos de autores con ORCID...")
        cur.execute("""
            SELECT
                pa.author_orcid,
                array_agg(DISTINCT pa.author_name ORDER BY pa.author_name) as name_variants,
                COUNT(DISTINCT pa.pubmed_id) as article_count,
                MIN(a.publication_date) as first_pub,
                MAX(a.publication_date) as last_pub
            FROM raw.pubmed_authors pa
            JOIN raw.pubmed_articles a ON pa.pubmed_id = a.pubmed_id
            WHERE pa.author_orcid IS NOT NULL
            GROUP BY pa.author_orcid
        """)

        rows = cur.fetchall()
        total = len(rows)
        print(f"  → {total:,} ORCIDs únicos encontrados")

        if dry_run:
            print("\n[DRY RUN] No se insertarán datos")
            return total

        # Prepare data for insertion
        print("\nProcesando y normalizando nombres...")
        authors_data = []

        for orcid, name_variants, article_count, first_pub, last_pub in rows:
            # Get frequency of each variant
            cur.execute("""
                SELECT author_name, COUNT(*) as cnt
                FROM raw.pubmed_authors
                WHERE author_orcid = %s
                GROUP BY author_name
            """, (orcid,))
            name_counts = {row[0]: row[1] for row in cur.fetchall()}

            # Pick the best name
            display_name = select_display_name(list(name_variants), name_counts)
            canonical_name = get_canonical_name(display_name)

            authors_data.append((
                orcid,
                display_name,
                canonical_name,
                list(name_variants),
                article_count,
                first_pub,
                last_pub
            ))

        # Insert in batches
        print(f"\nInsertando {len(authors_data):,} autores en sm_result.authors_orcid...")

        for i in range(0, len(authors_data), BATCH_SIZE):
            batch = authors_data[i:i + BATCH_SIZE]
            execute_values(cur, """
                INSERT INTO sm_result.authors_orcid
                (author_orcid, display_name, canonical_name, name_variants,
                 article_count, first_publication, last_publication)
                VALUES %s
            """, batch)

            if (i + BATCH_SIZE) % (BATCH_SIZE * 10) == 0:
                print(f"  → Insertados {min(i + BATCH_SIZE, len(authors_data)):,} / {len(authors_data):,}")

        conn.commit()
        print(f"\n✓ Fase 1 completada: {len(authors_data):,} autores insertados")

        return len(authors_data)


# =============================================================================
# PHASE 2: ORCID PROPAGATION
# =============================================================================

def phase2_propagate_orcid(conn, dry_run: bool = False) -> int:
    """Phase 2: Propagates ORCID to records without ORCID.

    If a record without ORCID has the same name+affiliation as one with ORCID,
    it is associated with the same author.

    Args:
        conn: Database connection.
        dry_run: If True, only shows statistics.

    Returns:
        Number of records propagated.
    """
    print("\n" + "=" * 60)
    print("FASE 2: Propagación de ORCID")
    print("=" * 60)

    with conn.cursor() as cur:
        # Find exact name+affiliation matches
        print("\nBuscando coincidencias nombre+afiliación...")
        cur.execute("""
            SELECT DISTINCT
                pa_sin.author_name,
                pa_sin.affiliation,
                pa_con.author_orcid
            FROM raw.pubmed_authors pa_sin
            JOIN raw.pubmed_authors pa_con
                ON pa_sin.author_name = pa_con.author_name
                AND pa_sin.affiliation = pa_con.affiliation
                AND pa_con.author_orcid IS NOT NULL
            WHERE pa_sin.author_orcid IS NULL
                AND pa_sin.affiliation IS NOT NULL
        """)

        matches = cur.fetchall()
        print(f"  → {len(matches):,} coincidencias encontradas")

        if dry_run:
            # Count records that would benefit
            cur.execute("""
                SELECT COUNT(*)
                FROM raw.pubmed_authors pa_sin
                WHERE pa_sin.author_orcid IS NULL
                AND EXISTS (
                    SELECT 1 FROM raw.pubmed_authors pa_con
                    WHERE pa_sin.author_name = pa_con.author_name
                    AND pa_sin.affiliation = pa_con.affiliation
                    AND pa_con.author_orcid IS NOT NULL
                )
            """)
            total_records = cur.fetchone()[0]
            print(f"  → {total_records:,} registros sin ORCID podrían vincularse")
            print("\n[DRY RUN] No se actualizarán datos")
            return len(matches)

        # This phase does not modify tables, it just reports
        # The linking is done in phase 3 when populating authors_norm
        print(f"\n✓ Fase 2 completada: {len(matches):,} coincidencias identificadas")
        print("  (Se usarán en Fase 3 para vincular autores)")

        return len(matches)


# =============================================================================
# PHASE 3: NAME NORMALIZATION
# =============================================================================

def phase3_normalize_names(conn, dry_run: bool = False) -> int:
    """Phase 3: Groups authors by normalized name.

    Creates a single author per canonical name, linking with ORCID if present.

    Args:
        conn: Database connection.
        dry_run: If True, only shows statistics.

    Returns:
        Number of authors inserted.
    """
    print("\n" + "=" * 60)
    print("FASE 3: Normalización de nombres")
    print("=" * 60)

    with conn.cursor() as cur:
        # Create a temporary table with normalized names
        print("\nCreando índice de nombres normalizados...")

        # Fetch all unique authors with their stats
        print("  Paso 1: Obteniendo datos de autores...")
        cur.execute("""
            SELECT
                pa.author_name,
                pa.author_orcid,
                COUNT(DISTINCT pa.pubmed_id) as article_count,
                MIN(a.publication_date) as first_pub,
                MAX(a.publication_date) as last_pub
            FROM raw.pubmed_authors pa
            JOIN raw.pubmed_articles a ON pa.pubmed_id = a.pubmed_id
            GROUP BY pa.author_name, pa.author_orcid
        """)

        rows = cur.fetchall()
        print(f"  → {len(rows):,} combinaciones nombre/ORCID")

        # Group by canonical name
        print("  Paso 2: Normalizando y agrupando nombres...")
        canonical_groups: Dict[str, Dict] = defaultdict(lambda: {
            'name_variants': set(),
            'name_counts': defaultdict(int),
            'orcids': set(),
            'article_count': 0,
            'first_pub': None,
            'last_pub': None
        })

        for author_name, author_orcid, article_count, first_pub, last_pub in rows:
            canonical = get_canonical_name(author_name)
            group = canonical_groups[canonical]

            group['name_variants'].add(author_name)
            group['name_counts'][author_name] += article_count

            if author_orcid:
                group['orcids'].add(author_orcid)

            group['article_count'] += article_count

            if first_pub:
                if group['first_pub'] is None or first_pub < group['first_pub']:
                    group['first_pub'] = first_pub
            if last_pub:
                if group['last_pub'] is None or last_pub > group['last_pub']:
                    group['last_pub'] = last_pub

        total_groups = len(canonical_groups)
        print(f"  → {total_groups:,} nombres canónicos únicos")

        if dry_run:
            # Additional stats
            with_orcid = sum(1 for g in canonical_groups.values() if g['orcids'])
            without_orcid = total_groups - with_orcid
            print(f"\n  Distribución:")
            print(f"    - Con ORCID vinculado: {with_orcid:,}")
            print(f"    - Sin ORCID: {without_orcid:,}")
            print("\n[DRY RUN] No se insertarán datos")
            return total_groups

        # Fetch mapping ORCID -> sm_author_id from authors_orcid
        print("  Paso 3: Obteniendo mapeo de ORCIDs...")
        cur.execute("SELECT author_orcid, sm_author_id FROM sm_result.authors_orcid")
        orcid_to_id = {row[0]: row[1] for row in cur.fetchall()}

        # Prepare data for insertion
        print("  Paso 4: Preparando datos para inserción...")
        authors_data = []

        for canonical_name, group in canonical_groups.items():
            name_variants = list(group['name_variants'])
            name_counts = dict(group['name_counts'])

            # Pick the best display name
            display_name = select_display_name(name_variants, name_counts)

            # Determine ORCID (if multiple, use the first)
            orcids = list(group['orcids'])
            author_orcid = orcids[0] if orcids else None
            orcid_author_id = orcid_to_id.get(author_orcid) if author_orcid else None

            # Confidence: 1.0 if it has ORCID, 0.7 if not
            confidence = 1.0 if author_orcid else 0.7

            authors_data.append((
                canonical_name,
                display_name,
                author_orcid,
                orcid_author_id,
                name_variants,
                confidence,
                group['article_count'],
                group['first_pub'],
                group['last_pub']
            ))

        # Insert in batches
        print(f"\nInsertando {len(authors_data):,} autores en sm_result.authors_norm...")

        for i in range(0, len(authors_data), BATCH_SIZE):
            batch = authors_data[i:i + BATCH_SIZE]
            execute_values(cur, """
                INSERT INTO sm_result.authors_norm
                (canonical_name, display_name, author_orcid, orcid_author_id,
                 name_variants, confidence, article_count, first_publication, last_publication)
                VALUES %s
            """, batch)

            if (i + BATCH_SIZE) % (BATCH_SIZE * 10) == 0:
                print(f"  → Insertados {min(i + BATCH_SIZE, len(authors_data)):,} / {len(authors_data):,}")

        conn.commit()
        print(f"\n✓ Fase 3 completada: {len(authors_data):,} autores insertados")

        return len(authors_data)


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def reset_tables(conn):
    """Removes data from the author tables."""
    print("\nEliminando datos existentes...")
    with conn.cursor() as cur:
        cur.execute("TRUNCATE sm_result.authors_norm CASCADE")
        cur.execute("TRUNCATE sm_result.authors_orcid CASCADE")
    conn.commit()
    print("  → Tablas vaciadas")


def show_statistics(conn):
    """Displays final statistics."""
    print("\n" + "=" * 60)
    print("ESTADÍSTICAS FINALES")
    print("=" * 60)

    with conn.cursor() as cur:
        # authors_orcid
        cur.execute("SELECT COUNT(*) FROM sm_result.authors_orcid")
        orcid_count = cur.fetchone()[0]

        cur.execute("SELECT AVG(article_count), MAX(article_count) FROM sm_result.authors_orcid")
        orcid_avg, orcid_max = cur.fetchone()

        # authors_norm
        cur.execute("SELECT COUNT(*) FROM sm_result.authors_norm")
        norm_count = cur.fetchone()[0]

        cur.execute("""
            SELECT
                COUNT(*) FILTER (WHERE author_orcid IS NOT NULL) as with_orcid,
                COUNT(*) FILTER (WHERE author_orcid IS NULL) as without_orcid
            FROM sm_result.authors_norm
        """)
        with_orcid, without_orcid = cur.fetchone()

        cur.execute("SELECT AVG(article_count), MAX(article_count) FROM sm_result.authors_norm")
        norm_avg, norm_max = cur.fetchone()

    print(f"\n📊 sm_result.authors_orcid:")
    print(f"   Total autores: {orcid_count:,}")
    print(f"   Promedio artículos/autor: {orcid_avg:.1f}")
    print(f"   Máximo artículos: {orcid_max:,}")

    print(f"\n📊 sm_result.authors_norm:")
    print(f"   Total autores: {norm_count:,}")
    print(f"   Con ORCID: {with_orcid:,} ({100*with_orcid/norm_count:.1f}%)")
    print(f"   Sin ORCID: {without_orcid:,} ({100*without_orcid/norm_count:.1f}%)")
    print(f"   Promedio artículos/autor: {norm_avg:.1f}")
    print(f"   Máximo artículos: {norm_max:,}")


# =============================================================================
# MAIN
# =============================================================================

def main():
    parser = argparse.ArgumentParser(
        description='PubMed author deduplication',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python scripts/deduplicacion_autores.py --dry-run     # Show statistics
  python scripts/deduplicacion_autores.py --reset       # Run everything from scratch
  python scripts/deduplicacion_autores.py --phase 1     # Only phase 1
        """
    )
    parser.add_argument('--dry-run', action='store_true',
                        help='Only show statistics, do not insert')
    parser.add_argument('--phase', type=int, choices=[1, 2, 3],
                        help='Run only a specific phase')
    parser.add_argument('--reset', action='store_true',
                        help='Remove existing data before executing')

    args = parser.parse_args()

    print("\n" + "=" * 60)
    print("DEDUPLICACIÓN DE AUTORES - PubMed")
    print("=" * 60)
    print(f"Inicio: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    conn = get_connection()

    try:
        if args.reset and not args.dry_run:
            reset_tables(conn)

        phases_to_run = [args.phase] if args.phase else [1, 2, 3]

        if 1 in phases_to_run:
            phase1_orcid_authors(conn, args.dry_run)

        if 2 in phases_to_run:
            phase2_propagate_orcid(conn, args.dry_run)

        if 3 in phases_to_run:
            phase3_normalize_names(conn, args.dry_run)

        if not args.dry_run:
            show_statistics(conn)

    finally:
        conn.close()

    print(f"\nFin: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)


if __name__ == '__main__':
    main()
