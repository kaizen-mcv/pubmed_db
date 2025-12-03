#!/usr/bin/env python3
"""
Script para CRON - Actualización incremental de PubMed.

Ejecutar diariamente (recomendado: horas off-peak de NCBI):
    0 3 * * * cd /home/marc/db-projects/pubmed && ./venv/bin/python scripts/cron_update.py >> data/logs/cron.log 2>&1

Este script:
1. Descarga artículos nuevos desde la última ejecución (--incremental)
2. Actualiza la tabla de especialidades de autores para autores nuevos
3. Genera un resumen de la ejecución

Requisitos:
    - Variables de entorno: PUBMED_DB_PASSWORD
    - Configuración: config/pubmed_config.yaml con email

Uso:
    python scripts/cron_update.py                    # Actualización completa
    python scripts/cron_update.py --download-only   # Solo descargar artículos
    python scripts/cron_update.py --specialties-only # Solo actualizar especialidades
    python scripts/cron_update.py --dry-run          # Mostrar qué se haría
"""

import argparse
import sys
import os
import subprocess
from pathlib import Path
from datetime import datetime

# Añadir el directorio raíz al path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.database.connection import db


def log(message):
    """Log con timestamp."""
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    print(f"[{timestamp}] {message}")


def run_command(cmd, description, dry_run=False):
    """Ejecuta un comando y retorna si fue exitoso."""
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
            timeout=3600  # 1 hora máximo
        )

        if result.returncode == 0:
            log(f"  ✓ Completado")
            # Mostrar últimas líneas del output
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
    """Obtiene estadísticas antes de la actualización."""
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
    """Obtiene estadísticas después y calcula diferencias."""
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
        description='Actualización incremental de PubMed para CRON'
    )
    parser.add_argument(
        '--download-only',
        action='store_true',
        help='Solo descargar artículos nuevos'
    )
    parser.add_argument(
        '--specialties-only',
        action='store_true',
        help='Solo actualizar especialidades de autores'
    )
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Mostrar qué se haría sin ejecutar'
    )
    args = parser.parse_args()

    # Banner
    log("=" * 60)
    log("CRON UPDATE - PubMed España")
    log("=" * 60)

    # Verificar variables de entorno
    if not os.environ.get('PUBMED_DB_PASSWORD'):
        log("ERROR: Variable PUBMED_DB_PASSWORD no definida")
        sys.exit(1)

    # Estadísticas antes
    log("\n[Estadísticas iniciales]")
    stats_before = get_stats_before()
    log(f"  Artículos: {stats_before['articles']:,}")
    log(f"  Autores únicos: {stats_before['authors']:,}")
    log(f"  Especialidades asignadas: {stats_before['specialties']:,}")

    success = True
    python_cmd = str(PROJECT_ROOT / 'venv' / 'bin' / 'python')

    # Paso 1: Descargar artículos nuevos
    if not args.specialties_only:
        log("\n[Paso 1/2] Descargando artículos nuevos")
        cmd = [python_cmd, 'scripts/download_pubmed.py', '--incremental']
        if not run_command(cmd, "Descarga incremental", args.dry_run):
            log("  WARNING: La descarga tuvo problemas, continuando...")
            success = False

    # Paso 2: Actualizar especialidades de autores nuevos
    if not args.download_only:
        log("\n[Paso 2/2] Actualizando especialidades de autores")
        cmd = [python_cmd, 'scripts/populate_author_specialties.py', '--incremental']
        if not run_command(cmd, "Actualización de especialidades", args.dry_run):
            log("  WARNING: La actualización de especialidades tuvo problemas")
            success = False

    # Estadísticas después
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
