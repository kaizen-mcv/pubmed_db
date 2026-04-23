#!/usr/bin/env python3
"""CRON script for incremental PubMed updates.

Run daily (recommended: NCBI off-peak hours):
    0 3 * * * cd $PROJECT_DIR && ./venv/bin/python scripts/cron_update.py >> data/logs/cron.log 2>&1

This script:
1. Downloads new articles since the last run (--incremental).
2. Updates the author specialties table for new authors.
3. Generates an execution summary.

Requirements:
    - Environment variables: PUBMED_DB_PASSWORD
    - Configuration: config/pubmed_config.yaml with email

Usage:
    python scripts/cron_update.py                    # Full update
    python scripts/cron_update.py --download-only    # Only download articles
    python scripts/cron_update.py --specialties-only # Only update specialties
    python scripts/cron_update.py --dry-run          # Show what would be done
"""

import argparse
import sys
import os
import subprocess
from pathlib import Path
from datetime import datetime

# Add the root directory to the path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.database.connection import db


def log(message):
    """Log with timestamp."""
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    print(f"[{timestamp}] {message}")


def run_command(cmd, description, dry_run=False):
    """Runs a command and returns whether it succeeded."""
    log(f">>> {description}")

    if dry_run:
        log(f"  [DRY-RUN] Comando: {' '.join(cmd)}")
        return True

    try:
        result = subprocess.run(
            cmd,
            cwd=str(PROJECT_ROOT),
            capture_output=True,
            text=True,
            timeout=3600  # 1 hour maximum
        )

        if result.returncode == 0:
            log(f"  ✓ Completado")
            # Show the last lines of the output
            if result.stdout:
                for line in result.stdout.strip().split('\n')[-5:]:
                    if line.strip():
                        log(f"    {line}")
            return True
        else:
            log(f"  ✗ Error (código {result.returncode})")
            if result.stderr:
                for line in result.stderr.strip().split('\n')[-5:]:
                    log(f"    ERROR: {line}")
            return False

    except subprocess.TimeoutExpired:
        log(f"  ✗ Timeout (1 hora)")
        return False
    except Exception as e:
        log(f"  ✗ Excepción: {e}")
        return False


def get_stats_before():
    """Gets statistics before the update."""
    stats = {}
    try:
        with db.cursor_context() as cur:
            cur.execute("SELECT COUNT(*) FROM pubmed_articles")
            stats['articles'] = cur.fetchone()[0]

            cur.execute("SELECT COUNT(DISTINCT author_name) FROM pubmed_authors")
            stats['authors'] = cur.fetchone()[0]

            cur.execute("SELECT COUNT(*) FROM author_specialties")
            stats['specialties'] = cur.fetchone()[0]
    except Exception as e:
        log(f"  Warning: No se pudieron obtener estadísticas: {e}")
        stats = {'articles': 0, 'authors': 0, 'specialties': 0}

    return stats


def get_stats_after(stats_before):
    """Gets statistics after the update and computes differences."""
    stats_after = get_stats_before()

    diff = {
        'articles_new': stats_after['articles'] - stats_before['articles'],
        'authors_new': stats_after['authors'] - stats_before['authors'],
        'specialties_new': stats_after['specialties'] - stats_before['specialties'],
        'articles_total': stats_after['articles'],
        'authors_total': stats_after['authors'],
        'specialties_total': stats_after['specialties'],
    }

    return diff


def main():
    parser = argparse.ArgumentParser(
        description='Incremental PubMed update for CRON'
    )
    parser.add_argument(
        '--download-only',
        action='store_true',
        help='Only download new articles'
    )
    parser.add_argument(
        '--specialties-only',
        action='store_true',
        help='Only update author specialties'
    )
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Show what would be done without executing'
    )
    args = parser.parse_args()

    # Banner
    log("=" * 60)
    log("CRON UPDATE - PubMed España")
    log("=" * 60)

    # Verify environment variables
    if not os.environ.get('PUBMED_DB_PASSWORD'):
        log("ERROR: Variable PUBMED_DB_PASSWORD no definida")
        sys.exit(1)

    # Stats before
    log("\n[Estadísticas iniciales]")
    stats_before = get_stats_before()
    log(f"  Artículos: {stats_before['articles']:,}")
    log(f"  Autores únicos: {stats_before['authors']:,}")
    log(f"  Especialidades asignadas: {stats_before['specialties']:,}")

    success = True
    python_cmd = str(PROJECT_ROOT / 'venv' / 'bin' / 'python')

    # Step 1: Download new articles
    if not args.specialties_only:
        log("\n[Paso 1/2] Descargando artículos nuevos")
        cmd = [python_cmd, 'scripts/download_pubmed.py', '--incremental']
        if not run_command(cmd, "Descarga incremental", args.dry_run):
            log("  WARNING: La descarga tuvo problemas, continuando...")
            success = False

    # Step 2: Update specialties for new authors
    if not args.download_only:
        log("\n[Paso 2/2] Actualizando especialidades de autores")
        cmd = [python_cmd, 'scripts/populate_author_specialties.py', '--incremental']
        if not run_command(cmd, "Actualización de especialidades", args.dry_run):
            log("  WARNING: La actualización de especialidades tuvo problemas")
            success = False

    # Stats after
    if not args.dry_run:
        log("\n[Resumen de cambios]")
        diff = get_stats_after(stats_before)
        log(f"  Artículos nuevos: +{diff['articles_new']:,} (total: {diff['articles_total']:,})")
        log(f"  Autores nuevos: +{diff['authors_new']:,} (total: {diff['authors_total']:,})")
        log(f"  Especialidades nuevas: +{diff['specialties_new']:,} (total: {diff['specialties_total']:,})")

    # Final
    log("\n" + "=" * 60)
    if success:
        log("COMPLETADO - Actualización exitosa")
    else:
        log("COMPLETADO CON ADVERTENCIAS - Revisar logs")
    log("=" * 60)

    db.close()
    sys.exit(0 if success else 1)


if __name__ == '__main__':
    main()
