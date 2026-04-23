#!/usr/bin/env python3
"""
Script para poblar la tabla de mapeo de afiliaciones a especialidades SNOMED.
Analiza las afiliaciones de autores y asigna códigos SNOMED basándose en
coincidencias de texto con nombres de especialidades.

Fidelidad:
- 'snomed' = el nombre oficial SNOMED aparece en el texto
- 'simplified' = el nombre simplificado (en/es) aparece en el texto

Uso:
    python scripts/populate_specialty_mappings.py           # Dry-run
    python scripts/populate_specialty_mappings.py --apply   # Ejecutar
"""

import sys
import os
import argparse

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src.database.connection import db
from src.utils.logger import get_logger

logger = get_logger(__name__)


def get_specialties():
    """
    Obtiene todas las especialidades SNOMED con sus nombres.

    Returns:
        list: Lista de diccionarios con snomed_code, name_snomed, name_en, name_es
    """
    with db.cursor_context() as cur:
        cur.execute("""
            SELECT snomed_code, name_snomed, name_en, name_es
            FROM vocab.snomed_specialties
            ORDER BY name_en
        """)
        specialties = []
        for row in cur.fetchall():
            spec = {
                'snomed_code': row[0],
                'name_snomed': row[1].lower().replace('(qualifier value)', '').strip() if row[1] else None,
                'name_en': row[2].lower() if row[2] else None,
                'name_es': row[3].lower() if row[3] else None,
            }
            specialties.append(spec)
        return specialties


def check_matches(text, specialties):
    """
    Busca todas las especialidades que coinciden con el texto.

    Orden de prioridad:
    1. name_snomed → 'snomed'
    2. name_en → 'simplified'
    3. name_es → 'simplified'

    Args:
        text: Texto donde buscar coincidencias
        specialties: Lista de especialidades de get_specialties()

    Returns:
        list: Lista de tuplas (snomed_code, fidelity)
    """
    if not text:
        return []

    text_lower = text.lower()
    matches = []
    matched_codes = set()

    for spec in specialties:
        code = spec['snomed_code']

        # Ya encontrado por fuente de mayor prioridad
        if code in matched_codes:
            continue

        # 1. Nombre SNOMED (sin "qualifier value")
        if spec['name_snomed'] and spec['name_snomed'] in text_lower:
            matches.append((code, 'snomed'))
            matched_codes.add(code)
            continue

        # 2. Nombre inglés
        if spec['name_en'] and spec['name_en'] in text_lower:
            matches.append((code, 'simplified'))
            matched_codes.add(code)
            continue

        # 3. Nombre español
        if spec['name_es'] and spec['name_es'] in text_lower:
            matches.append((code, 'simplified'))
            matched_codes.add(code)
            continue

    return matches


def populate_affiliation_mappings(specialties, apply=False):
    """Pobla la tabla affiliation_to_snomed."""
    logger.info("Analizando afiliaciones...")

    with db.cursor_context() as cur:
        # Obtener afiliaciones únicas
        cur.execute("""
            SELECT DISTINCT affiliation
            FROM raw.pubmed_authors
            WHERE affiliation IS NOT NULL
        """)
        affiliations = [row[0] for row in cur.fetchall()]
        logger.info(f"   Afiliaciones únicas encontradas: {len(affiliations)}")

        # Contar matches
        stats = {'snomed': 0, 'simplified': 0, 'total': 0}
        mappings = []

        for affiliation in affiliations:
            matches = check_matches(affiliation, specialties)
            for snomed_code, fidelity in matches:
                pattern = affiliation[:500]  # Limitar longitud
                mappings.append((pattern, snomed_code, fidelity))
                stats['total'] += 1
                if fidelity == 'snomed':
                    stats['snomed'] += 1
                else:
                    stats['simplified'] += 1

        logger.info(f"   Mapeos encontrados: {stats['total']}")
        logger.info(f"     - Por nombre SNOMED: {stats['snomed']}")
        logger.info(f"     - Por nombre simplificado: {stats['simplified']}")

        if apply:
            cur.execute("TRUNCATE TABLE sm_maps.affiliation_to_snomed CASCADE")

            for pattern, snomed_code, fidelity in mappings:
                try:
                    cur.execute("""
                        INSERT INTO sm_maps.affiliation_to_snomed (affiliation_pattern, pattern_type, snomed_code, fidelity)
                        VALUES (%s, 'exact', %s, %s)
                        ON CONFLICT DO NOTHING
                    """, (pattern, snomed_code, fidelity))
                except Exception:
                    pass

            db.commit()
            logger.info(f"   ✓ Insertados {stats['total']} mapeos")

    return stats


def show_stats():
    """Muestra estadísticas de la tabla de mapeo."""
    logger.info("")
    logger.info("=" * 60)
    logger.info("ESTADÍSTICAS DE MAPEOS")
    logger.info("=" * 60)

    with db.cursor_context() as cur:
        cur.execute("SELECT COUNT(*) FROM sm_maps.affiliation_to_snomed")
        total = cur.fetchone()[0]

        cur.execute("SELECT COUNT(*) FROM sm_maps.affiliation_to_snomed WHERE fidelity = 'snomed'")
        fidelity_snomed = cur.fetchone()[0]

        cur.execute("SELECT COUNT(*) FROM sm_maps.affiliation_to_snomed WHERE fidelity = 'simplified'")
        fidelity_simplified = cur.fetchone()[0]

        cur.execute("SELECT COUNT(DISTINCT snomed_code) FROM sm_maps.affiliation_to_snomed")
        specialties = cur.fetchone()[0]

        logger.info(f"\nsm_maps.affiliation_to_snomed:")
        logger.info(f"   Total: {total} mapeos")
        logger.info(f"   Por SNOMED: {fidelity_snomed}")
        logger.info(f"   Por simplificado: {fidelity_simplified}")
        logger.info(f"   Especialidades distintas: {specialties}")


def main():
    parser = argparse.ArgumentParser(description='Pobla la tabla de mapeo afiliación → SNOMED')
    parser.add_argument('--apply', action='store_true', help='Ejecutar cambios (sin esto es dry-run)')
    args = parser.parse_args()

    logger.info("=" * 60)
    logger.info("POBLANDO TABLA DE MAPEO AFILIACIÓN → SNOMED")
    logger.info("=" * 60)

    if not args.apply:
        logger.info("MODO DRY-RUN: No se harán cambios. Usa --apply para ejecutar.")
    else:
        logger.info("MODO APLICAR: Se truncará y repoblará la tabla.")

    logger.info("")
    logger.info("Fidelidad:")
    logger.info("  'snomed' = nombre oficial SNOMED encontrado")
    logger.info("  'simplified' = nombre simplificado (en/es) encontrado")
    logger.info("")

    try:
        # Obtener especialidades
        specialties = get_specialties()
        logger.info(f"Especialidades cargadas: {len(specialties)}")
        logger.info("")

        # Poblar tabla de afiliaciones
        populate_affiliation_mappings(specialties, apply=args.apply)

        # Mostrar estadísticas si se aplicaron cambios
        if args.apply:
            show_stats()

        logger.info("")
        logger.info("=" * 60)
        if args.apply:
            logger.info("COMPLETADO - Tabla repoblada")
        else:
            logger.info("DRY-RUN COMPLETADO - Usa --apply para ejecutar")
        logger.info("=" * 60)

    finally:
        db.close()


if __name__ == '__main__':
    main()
