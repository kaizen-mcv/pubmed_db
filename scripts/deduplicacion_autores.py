#!/usr/bin/env python3
"""
Script de deduplicación de autores.

Este script pobla las tablas sm_result.authors_orcid y sm_result.authors_norm
a partir de los datos en raw.pubmed_authors.

Proceso en 3 fases:
1. ORCID directo: Autores con ORCID (100% fiable)
2. Propagación de ORCID: Registros sin ORCID que coinciden en nombre+afiliación
3. Normalización: Resto de autores agrupados por nombre normalizado

Uso:
    python scripts/deduplicacion_autores.py [--dry-run] [--phase N]

Opciones:
    --dry-run       Solo mostrar estadísticas, no insertar datos
    --phase N       Ejecutar solo fase N (1, 2 o 3)
    --reset         Eliminar datos existentes antes de ejecutar

Documentación: docs/deduplicacion_autores.md
"""

import os
import sys
import argparse
from datetime import datetime
from collections import defaultdict
from typing import Dict, List, Tuple, Optional

import psycopg2
from psycopg2.extras import execute_values

# Añadir directorio raíz al path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config.settings import settings
from src.utils.name_normalizer import get_canonical_name, select_display_name


# =============================================================================
# CONFIGURACIÓN
# =============================================================================

BATCH_SIZE = 10000  # Registros por lote de inserción


def get_connection():
    """Obtiene conexión a la base de datos."""
    config = settings.get_db_connection_params()
    return psycopg2.connect(**config)


# =============================================================================
# FASE 1: AUTORES CON ORCID
# =============================================================================

def phase1_orcid_authors(conn, dry_run: bool = False) -> int:
    """
    Fase 1: Procesa autores con ORCID.

    Agrupa todos los registros por ORCID y crea un único autor por cada ORCID.

    Args:
        conn: Conexión a la base de datos
        dry_run: Si True, solo muestra estadísticas

    Returns:
        Número de autores insertados
    """
    print("\n" + "=" * 60)
    print("FASE 1: Autores con ORCID")
    print("=" * 60)

    with conn.cursor() as cur:
        # Obtener datos agrupados por ORCID
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

        # Preparar datos para inserción
        print("\nProcesando y normalizando nombres...")
        authors_data = []

        for orcid, name_variants, article_count, first_pub, last_pub in rows:
            # Obtener frecuencias de cada variante
            cur.execute("""
                SELECT author_name, COUNT(*) as cnt
                FROM raw.pubmed_authors
                WHERE author_orcid = %s
                GROUP BY author_name
            """, (orcid,))
            name_counts = {row[0]: row[1] for row in cur.fetchall()}

            # Seleccionar mejor nombre
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

        # Insertar en lotes
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
# FASE 2: PROPAGACIÓN DE ORCID
# =============================================================================

def phase2_propagate_orcid(conn, dry_run: bool = False) -> int:
    """
    Fase 2: Propaga ORCID a registros sin ORCID.

    Si un registro sin ORCID tiene el mismo nombre+afiliación que uno con ORCID,
    se asocia al mismo autor.

    Args:
        conn: Conexión a la base de datos
        dry_run: Si True, solo muestra estadísticas

    Returns:
        Número de registros propagados
    """
    print("\n" + "=" * 60)
    print("FASE 2: Propagación de ORCID")
    print("=" * 60)

    with conn.cursor() as cur:
        # Encontrar coincidencias exactas nombre+afiliación
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
            # Contar registros que se beneficiarían
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

        # Esta fase no modifica tablas, solo informa
        # La vinculación se hace en fase 3 al poblar authors_norm
        print(f"\n✓ Fase 2 completada: {len(matches):,} coincidencias identificadas")
        print("  (Se usarán en Fase 3 para vincular autores)")

        return len(matches)


# =============================================================================
# FASE 3: NORMALIZACIÓN DE NOMBRES
# =============================================================================

def phase3_normalize_names(conn, dry_run: bool = False) -> int:
    """
    Fase 3: Agrupa autores por nombre normalizado.

    Crea un autor único por cada nombre canónico, vinculando con ORCID si existe.

    Args:
        conn: Conexión a la base de datos
        dry_run: Si True, solo muestra estadísticas

    Returns:
        Número de autores insertados
    """
    print("\n" + "=" * 60)
    print("FASE 3: Normalización de nombres")
    print("=" * 60)

    with conn.cursor() as cur:
        # Crear tabla temporal con nombres normalizados
        print("\nCreando índice de nombres normalizados...")

        # Obtener todos los autores únicos con sus estadísticas
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

        # Agrupar por nombre canónico
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
            # Estadísticas adicionales
            with_orcid = sum(1 for g in canonical_groups.values() if g['orcids'])
            without_orcid = total_groups - with_orcid
            print(f"\n  Distribución:")
            print(f"    - Con ORCID vinculado: {with_orcid:,}")
            print(f"    - Sin ORCID: {without_orcid:,}")
            print("\n[DRY RUN] No se insertarán datos")
            return total_groups

        # Obtener mapeo ORCID -> sm_author_id de authors_orcid
        print("  Paso 3: Obteniendo mapeo de ORCIDs...")
        cur.execute("SELECT author_orcid, sm_author_id FROM sm_result.authors_orcid")
        orcid_to_id = {row[0]: row[1] for row in cur.fetchall()}

        # Preparar datos para inserción
        print("  Paso 4: Preparando datos para inserción...")
        authors_data = []

        for canonical_name, group in canonical_groups.items():
            name_variants = list(group['name_variants'])
            name_counts = dict(group['name_counts'])

            # Seleccionar mejor nombre para mostrar
            display_name = select_display_name(name_variants, name_counts)

            # Determinar ORCID (si hay múltiples, usar el primero)
            orcids = list(group['orcids'])
            author_orcid = orcids[0] if orcids else None
            orcid_author_id = orcid_to_id.get(author_orcid) if author_orcid else None

            # Confianza: 1.0 si tiene ORCID, 0.7 si no
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

        # Insertar en lotes
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
# FUNCIONES AUXILIARES
# =============================================================================

def reset_tables(conn):
    """Elimina datos de las tablas de autores."""
    print("\nEliminando datos existentes...")
    with conn.cursor() as cur:
        cur.execute("TRUNCATE sm_result.authors_norm CASCADE")
        cur.execute("TRUNCATE sm_result.authors_orcid CASCADE")
    conn.commit()
    print("  → Tablas vaciadas")


def show_statistics(conn):
    """Muestra estadísticas finales."""
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
        description='Deduplicación de autores de PubMed',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Ejemplos:
  python scripts/deduplicacion_autores.py --dry-run     # Ver estadísticas
  python scripts/deduplicacion_autores.py --reset       # Ejecutar todo desde cero
  python scripts/deduplicacion_autores.py --phase 1     # Solo fase 1
        """
    )
    parser.add_argument('--dry-run', action='store_true',
                        help='Solo mostrar estadísticas, no insertar')
    parser.add_argument('--phase', type=int, choices=[1, 2, 3],
                        help='Ejecutar solo una fase específica')
    parser.add_argument('--reset', action='store_true',
                        help='Eliminar datos existentes antes de ejecutar')

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
