#!/usr/bin/env python3
"""
Script para poblar las tablas de mapeo de especialidades SNOMED.
Analiza los datos existentes en pubmed_articles y pubmed_authors
y asigna códigos SNOMED basándose en coincidencias de texto.

Fidelidad:
- 'snomed' = el nombre oficial SNOMED aparece en el texto
- 'simplified' = el nombre simplificado (en/es) aparece en el texto
- '{synonym}' = el sinónimo específico que coincidió

Uso:
    python scripts/populate_specialty_mappings.py           # Dry-run
    python scripts/populate_specialty_mappings.py --apply   # Ejecutar
"""

import sys
import os
import argparse
import re

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src.database.connection import db
from src.utils.logger import get_logger

logger = get_logger(__name__)

# Sinónimos que requieren coincidencia de palabra completa (evitar substrings)
SHORT_SYNONYMS = {'ent', 'icu', 'uci', 'pet', 'orl', 'mir', 'eye'}


def is_word_match(text, term):
    """
    Verifica si el término aparece como palabra completa en el texto.
    Usa regex para detectar límites de palabra.
    """
    pattern = r'\b' + re.escape(term) + r'\b'
    return bool(re.search(pattern, text, re.IGNORECASE))


def get_specialties():
    """
    Obtiene todas las especialidades SNOMED con sus nombres y sinónimos.

    Returns:
        list: Lista de diccionarios con snomed_code, name_snomed, name_en, name_es, synonyms
    """
    with db.cursor_context() as cur:
        cur.execute("""
            SELECT snomed_code, name_snomed, name_en, name_es, synonyms
            FROM snomed_specialties
            ORDER BY name_en
        """)
        specialties = []
        for row in cur.fetchall():
            spec = {
                'snomed_code': row[0],
                'name_snomed': row[1].lower().replace('(qualifier value)', '').strip() if row[1] else None,
                'name_en': row[2].lower() if row[2] else None,
                'name_es': row[3].lower() if row[3] else None,
                'synonyms': [s.strip().lower() for s in row[4].split(';') if s.strip()] if row[4] else [],
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
    4. synonyms → el sinónimo que coincidió

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

        # 4. Sinónimos - guardar cuál sinónimo coincidió
        for synonym in spec['synonyms']:
            if len(synonym) >= 3:
                # Para sinónimos cortos, exigir coincidencia de palabra completa
                if synonym in SHORT_SYNONYMS:
                    if is_word_match(text_lower, synonym):
                        matches.append((code, synonym))
                        matched_codes.add(code)
                        break
                elif synonym in text_lower:
                    matches.append((code, synonym))
                    matched_codes.add(code)
                    break

    return matches


def populate_journal_mappings(specialties, apply=False):
    """Pobla la tabla journal_to_snomed."""
    logger.info("[1/5] Analizando journals...")

    with db.cursor_context() as cur:
        # Obtener journals únicos
        cur.execute("""
            SELECT DISTINCT journal_name, journal_issn
            FROM pubmed_articles
            WHERE journal_name IS NOT NULL
        """)
        journals = cur.fetchall()
        logger.info(f"   Journals únicos encontrados: {len(journals)}")

        # Contar matches
        stats = {'snomed': 0, 'simplified': 0, 'synonym': 0, 'total': 0}
        mappings = []

        for journal_name, journal_issn in journals:
            matches = check_matches(journal_name, specialties)
            for snomed_code, fidelity in matches:
                mappings.append((journal_name, journal_issn, snomed_code, fidelity))
                stats['total'] += 1
                if fidelity == 'snomed':
                    stats['snomed'] += 1
                elif fidelity == 'simplified':
                    stats['simplified'] += 1
                else:
                    stats['synonym'] += 1

        logger.info(f"   Mapeos encontrados: {stats['total']}")
        logger.info(f"     - Por nombre SNOMED: {stats['snomed']}")
        logger.info(f"     - Por nombre simplificado: {stats['simplified']}")
        logger.info(f"     - Por sinónimo: {stats['synonym']}")

        if apply:
            # Truncar tabla
            cur.execute("TRUNCATE TABLE journal_to_snomed CASCADE")

            # Insertar mappings
            for journal_name, journal_issn, snomed_code, fidelity in mappings:
                try:
                    cur.execute("""
                        INSERT INTO journal_to_snomed (journal_name, journal_issn, snomed_code, fidelity)
                        VALUES (%s, %s, %s, %s)
                        ON CONFLICT DO NOTHING
                    """, (journal_name, journal_issn, snomed_code, fidelity))
                except Exception:
                    pass

            db.commit()
            logger.info(f"   ✓ Insertados {stats['total']} mapeos")

    return stats


def populate_affiliation_mappings(specialties, apply=False):
    """Pobla la tabla affiliation_to_snomed."""
    logger.info("[2/5] Analizando afiliaciones...")

    with db.cursor_context() as cur:
        # Obtener afiliaciones únicas
        cur.execute("""
            SELECT DISTINCT affiliation
            FROM pubmed_authors
            WHERE affiliation IS NOT NULL
        """)
        affiliations = [row[0] for row in cur.fetchall()]
        logger.info(f"   Afiliaciones únicas encontradas: {len(affiliations)}")

        # Contar matches
        stats = {'snomed': 0, 'simplified': 0, 'synonym': 0, 'total': 0}
        mappings = []

        for affiliation in affiliations:
            matches = check_matches(affiliation, specialties)
            for snomed_code, fidelity in matches:
                pattern = affiliation[:500]  # Limitar longitud
                mappings.append((pattern, snomed_code, fidelity))
                stats['total'] += 1
                if fidelity == 'snomed':
                    stats['snomed'] += 1
                elif fidelity == 'simplified':
                    stats['simplified'] += 1
                else:
                    stats['synonym'] += 1

        logger.info(f"   Mapeos encontrados: {stats['total']}")
        logger.info(f"     - Por nombre SNOMED: {stats['snomed']}")
        logger.info(f"     - Por nombre simplificado: {stats['simplified']}")
        logger.info(f"     - Por sinónimo: {stats['synonym']}")

        if apply:
            cur.execute("TRUNCATE TABLE affiliation_to_snomed CASCADE")

            for pattern, snomed_code, fidelity in mappings:
                try:
                    cur.execute("""
                        INSERT INTO affiliation_to_snomed (affiliation_pattern, pattern_type, snomed_code, fidelity)
                        VALUES (%s, 'exact', %s, %s)
                        ON CONFLICT DO NOTHING
                    """, (pattern, snomed_code, fidelity))
                except Exception:
                    pass

            db.commit()
            logger.info(f"   ✓ Insertados {stats['total']} mapeos")

    return stats


def populate_keyword_mappings(specialties, apply=False):
    """Pobla la tabla keyword_to_snomed."""
    logger.info("[3/5] Analizando keywords...")

    with db.cursor_context() as cur:
        # Obtener keywords únicos
        cur.execute("""
            SELECT DISTINCT author_keywords
            FROM pubmed_articles
            WHERE author_keywords IS NOT NULL
        """)

        all_keywords = set()
        for row in cur.fetchall():
            # Keywords separados por coma o punto y coma
            keywords = [k.strip() for k in row[0].replace(';', ',').split(',')]
            all_keywords.update(k for k in keywords if len(k) >= 3)

        logger.info(f"   Keywords únicos encontrados: {len(all_keywords)}")

        # Contar matches
        stats = {'snomed': 0, 'simplified': 0, 'synonym': 0, 'total': 0}
        mappings = []

        for keyword in all_keywords:
            matches = check_matches(keyword, specialties)
            for snomed_code, fidelity in matches:
                mappings.append((keyword, snomed_code, fidelity))
                stats['total'] += 1
                if fidelity == 'snomed':
                    stats['snomed'] += 1
                elif fidelity == 'simplified':
                    stats['simplified'] += 1
                else:
                    stats['synonym'] += 1

        logger.info(f"   Mapeos encontrados: {stats['total']}")
        logger.info(f"     - Por nombre SNOMED: {stats['snomed']}")
        logger.info(f"     - Por nombre simplificado: {stats['simplified']}")
        logger.info(f"     - Por sinónimo: {stats['synonym']}")

        if apply:
            cur.execute("TRUNCATE TABLE keyword_to_snomed CASCADE")

            for keyword, snomed_code, fidelity in mappings:
                try:
                    cur.execute("""
                        INSERT INTO keyword_to_snomed (keyword, snomed_code, fidelity)
                        VALUES (%s, %s, %s)
                        ON CONFLICT DO NOTHING
                    """, (keyword, snomed_code, fidelity))
                except Exception:
                    pass

            db.commit()
            logger.info(f"   ✓ Insertados {stats['total']} mapeos")

    return stats


def populate_title_mappings(specialties, apply=False):
    """Pobla la tabla title_pattern_to_snomed."""
    logger.info("[4/5] Analizando títulos...")

    with db.cursor_context() as cur:
        # Obtener títulos únicos
        cur.execute("""
            SELECT DISTINCT article_title
            FROM pubmed_articles
            WHERE article_title IS NOT NULL
        """)
        titles = [row[0] for row in cur.fetchall()]
        logger.info(f"   Títulos únicos encontrados: {len(titles)}")

        # Contar matches
        stats = {'snomed': 0, 'simplified': 0, 'synonym': 0, 'total': 0}
        mappings = []

        for title in titles:
            matches = check_matches(title, specialties)
            for snomed_code, fidelity in matches:
                pattern = title[:500]
                mappings.append((pattern, snomed_code, fidelity))
                stats['total'] += 1
                if fidelity == 'snomed':
                    stats['snomed'] += 1
                elif fidelity == 'simplified':
                    stats['simplified'] += 1
                else:
                    stats['synonym'] += 1

        logger.info(f"   Mapeos encontrados: {stats['total']}")
        logger.info(f"     - Por nombre SNOMED: {stats['snomed']}")
        logger.info(f"     - Por nombre simplificado: {stats['simplified']}")
        logger.info(f"     - Por sinónimo: {stats['synonym']}")

        if apply:
            cur.execute("TRUNCATE TABLE title_pattern_to_snomed CASCADE")

            for pattern, snomed_code, fidelity in mappings:
                try:
                    cur.execute("""
                        INSERT INTO title_pattern_to_snomed (title_pattern, pattern_type, snomed_code, fidelity)
                        VALUES (%s, 'exact', %s, %s)
                        ON CONFLICT DO NOTHING
                    """, (pattern, snomed_code, fidelity))
                except Exception:
                    pass

            db.commit()
            logger.info(f"   ✓ Insertados {stats['total']} mapeos")

    return stats


def populate_abstract_mappings(specialties, apply=False):
    """Pobla la tabla abstract_pattern_to_snomed."""
    logger.info("[5/5] Analizando abstracts...")

    with db.cursor_context() as cur:
        # Obtener abstracts
        cur.execute("""
            SELECT pubmed_id, article_abstract
            FROM pubmed_articles
            WHERE article_abstract IS NOT NULL
        """)
        abstracts = cur.fetchall()
        logger.info(f"   Abstracts encontrados: {len(abstracts)}")

        # Contar matches
        stats = {'snomed': 0, 'simplified': 0, 'synonym': 0, 'total': 0}
        mappings = []
        patterns_seen = set()

        for pubmed_id, abstract in abstracts:
            matches = check_matches(abstract, specialties)
            for snomed_code, fidelity in matches:
                pattern = abstract[:500]
                pattern_key = (pattern, snomed_code)
                if pattern_key not in patterns_seen:
                    patterns_seen.add(pattern_key)
                    mappings.append((pattern, snomed_code, fidelity))
                    stats['total'] += 1
                    if fidelity == 'snomed':
                        stats['snomed'] += 1
                    elif fidelity == 'simplified':
                        stats['simplified'] += 1
                    else:
                        stats['synonym'] += 1

        logger.info(f"   Mapeos encontrados: {stats['total']}")
        logger.info(f"     - Por nombre SNOMED: {stats['snomed']}")
        logger.info(f"     - Por nombre simplificado: {stats['simplified']}")
        logger.info(f"     - Por sinónimo: {stats['synonym']}")

        if apply:
            cur.execute("TRUNCATE TABLE abstract_pattern_to_snomed CASCADE")

            for pattern, snomed_code, fidelity in mappings:
                try:
                    cur.execute("""
                        INSERT INTO abstract_pattern_to_snomed (abstract_pattern, pattern_type, snomed_code, fidelity)
                        VALUES (%s, 'exact', %s, %s)
                        ON CONFLICT DO NOTHING
                    """, (pattern, snomed_code, fidelity))
                except Exception:
                    pass

            db.commit()
            logger.info(f"   ✓ Insertados {stats['total']} mapeos")

    return stats


def show_stats():
    """Muestra estadísticas de las tablas de mapeo."""
    logger.info("")
    logger.info("=" * 60)
    logger.info("ESTADÍSTICAS DE MAPEOS")
    logger.info("=" * 60)

    with db.cursor_context() as cur:
        tables = [
            ('journal_to_snomed', 'journal_name'),
            ('affiliation_to_snomed', 'affiliation_pattern'),
            ('keyword_to_snomed', 'keyword'),
            ('title_pattern_to_snomed', 'title_pattern'),
            ('abstract_pattern_to_snomed', 'abstract_pattern')
        ]

        for table, col in tables:
            cur.execute(f"SELECT COUNT(*) FROM {table}")
            total = cur.fetchone()[0]

            cur.execute(f"SELECT COUNT(*) FROM {table} WHERE fidelity = 'snomed'")
            fidelity_snomed = cur.fetchone()[0]

            cur.execute(f"SELECT COUNT(*) FROM {table} WHERE fidelity = 'simplified'")
            fidelity_simplified = cur.fetchone()[0]

            cur.execute(f"SELECT COUNT(*) FROM {table} WHERE fidelity NOT IN ('snomed', 'simplified')")
            fidelity_synonym = cur.fetchone()[0]

            cur.execute(f"SELECT COUNT(DISTINCT snomed_code) FROM {table}")
            specialties = cur.fetchone()[0]

            logger.info(f"\n{table}:")
            logger.info(f"   Total: {total} mapeos")
            logger.info(f"   Por SNOMED: {fidelity_snomed}")
            logger.info(f"   Por simplificado: {fidelity_simplified}")
            logger.info(f"   Por sinónimo: {fidelity_synonym}")
            logger.info(f"   Especialidades distintas: {specialties}")


def main():
    parser = argparse.ArgumentParser(description='Pobla las tablas de mapeo SNOMED')
    parser.add_argument('--apply', action='store_true', help='Ejecutar cambios (sin esto es dry-run)')
    args = parser.parse_args()

    logger.info("=" * 60)
    logger.info("POBLANDO TABLAS DE MAPEO SNOMED")
    logger.info("=" * 60)

    if not args.apply:
        logger.info("MODO DRY-RUN: No se harán cambios. Usa --apply para ejecutar.")
    else:
        logger.info("MODO APLICAR: Se truncarán y repoblarán las tablas.")

    logger.info("")
    logger.info("Fidelidad:")
    logger.info("  'snomed' = nombre oficial SNOMED encontrado")
    logger.info("  'simplified' = nombre simplificado (en/es) encontrado")
    logger.info("  '{synonym}' = sinónimo específico que coincidió")
    logger.info("")

    try:
        # Obtener especialidades
        specialties = get_specialties()
        logger.info(f"Especialidades cargadas: {len(specialties)}")

        # Contar sinónimos totales
        total_synonyms = sum(len(s['synonyms']) for s in specialties)
        logger.info(f"Sinónimos totales: {total_synonyms}")
        logger.info("")

        # Poblar cada tabla
        populate_journal_mappings(specialties, apply=args.apply)
        populate_affiliation_mappings(specialties, apply=args.apply)
        populate_keyword_mappings(specialties, apply=args.apply)
        populate_title_mappings(specialties, apply=args.apply)
        populate_abstract_mappings(specialties, apply=args.apply)

        # Mostrar estadísticas si se aplicaron cambios
        if args.apply:
            show_stats()

        logger.info("")
        logger.info("=" * 60)
        if args.apply:
            logger.info("COMPLETADO - Tablas repobladas")
        else:
            logger.info("DRY-RUN COMPLETADO - Usa --apply para ejecutar")
        logger.info("=" * 60)

    finally:
        db.close()


if __name__ == '__main__':
    main()
