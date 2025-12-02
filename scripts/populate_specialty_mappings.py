#!/usr/bin/env python3
"""
Script para poblar las tablas de mapeo de especialidades SNOMED.
Analiza los datos existentes en pubmed_articles y pubmed_authors
y asigna códigos SNOMED basándose en coincidencias de texto.

Fidelidad:
- 'V' = Verdadero: el nombre de la especialidad aparece exactamente en el texto
- 'F' = Falso: es una inferencia/relación indirecta
"""

import sys
import os
import re

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src.database.connection import db


def get_specialties():
    """Obtiene todas las especialidades SNOMED."""
    with db.cursor_context() as cur:
        cur.execute("""
            SELECT snomed_code, name_en, name_es
            FROM snomed_specialties
            ORDER BY name_en
        """)
        specialties = []
        for row in cur.fetchall():
            spec = {
                'snomed_code': row[0],
                'name_en': row[1].lower() if row[1] else None,
                'name_es': row[2].lower() if row[2] else None,
            }
            specialties.append(spec)
        return specialties


def check_exact_match(text, specialties):
    """
    Verifica si el texto contiene el nombre exacto de alguna especialidad.
    Retorna (snomed_code, fidelity) o (None, None)
    """
    if not text:
        return None, None

    text_lower = text.lower()

    # Buscar coincidencia exacta (nombre completo de la especialidad en el texto)
    for spec in specialties:
        # Verificar nombre en inglés
        if spec['name_en'] and spec['name_en'] in text_lower:
            return spec['snomed_code'], 'V'
        # Verificar nombre en español
        if spec['name_es'] and spec['name_es'] in text_lower:
            return spec['snomed_code'], 'V'

    return None, None


def populate_journal_mappings(specialties):
    """Pobla la tabla journal_to_snomed."""
    print("\n[1/5] Poblando journal_to_snomed...")

    with db.cursor_context() as cur:
        # Obtener journals únicos
        cur.execute("""
            SELECT DISTINCT journal_name, journal_issn
            FROM pubmed_articles
            WHERE journal_name IS NOT NULL
        """)
        journals = cur.fetchall()

        inserted_v = 0
        inserted_f = 0

        for journal_name, journal_issn in journals:
            snomed_code, fidelity = check_exact_match(journal_name, specialties)

            if snomed_code:
                try:
                    cur.execute("""
                        INSERT INTO journal_to_snomed (journal_name, journal_issn, snomed_code, fidelity)
                        VALUES (%s, %s, %s, %s)
                        ON CONFLICT DO NOTHING
                    """, (journal_name, journal_issn, snomed_code, fidelity))
                    if cur.rowcount > 0:
                        if fidelity == 'V':
                            inserted_v += 1
                        else:
                            inserted_f += 1
                except Exception as e:
                    pass

        db.commit()
        print(f"   Insertados: {inserted_v} con fidelidad V, {inserted_f} con fidelidad F")
        print(f"   Total: {inserted_v + inserted_f} de {len(journals)} journals analizados")


def populate_affiliation_mappings(specialties):
    """Pobla la tabla affiliation_to_snomed."""
    print("\n[2/5] Poblando affiliation_to_snomed...")

    with db.cursor_context() as cur:
        # Obtener afiliaciones únicas (limitar para no sobrecargar)
        cur.execute("""
            SELECT DISTINCT affiliation
            FROM pubmed_authors
            WHERE affiliation IS NOT NULL
        """)
        affiliations = [row[0] for row in cur.fetchall()]

        inserted_v = 0
        inserted_f = 0
        patterns_added = set()

        for affiliation in affiliations:
            snomed_code, fidelity = check_exact_match(affiliation, specialties)

            if snomed_code:
                # Usar la afiliación como patrón
                pattern = affiliation[:500]  # Limitar longitud
                pattern_key = (pattern, snomed_code)

                if pattern_key not in patterns_added:
                    try:
                        cur.execute("""
                            INSERT INTO affiliation_to_snomed (affiliation_pattern, pattern_type, snomed_code, fidelity)
                            VALUES (%s, 'exact', %s, %s)
                            ON CONFLICT DO NOTHING
                        """, (pattern, snomed_code, fidelity))
                        if cur.rowcount > 0:
                            patterns_added.add(pattern_key)
                            if fidelity == 'V':
                                inserted_v += 1
                            else:
                                inserted_f += 1
                    except Exception as e:
                        pass

        db.commit()
        print(f"   Insertados: {inserted_v} con fidelidad V, {inserted_f} con fidelidad F")
        print(f"   Total: {inserted_v + inserted_f} patrones de {len(affiliations)} afiliaciones")


def populate_keyword_mappings(specialties):
    """Pobla la tabla keyword_to_snomed."""
    print("\n[3/5] Poblando keyword_to_snomed...")

    with db.cursor_context() as cur:
        # Obtener keywords únicos
        cur.execute("""
            SELECT DISTINCT author_keywords
            FROM pubmed_articles
            WHERE author_keywords IS NOT NULL
        """)

        all_keywords = set()
        for row in cur.fetchall():
            keywords = [k.strip() for k in row[0].split(',')]
            all_keywords.update(keywords)

        inserted_v = 0
        inserted_f = 0

        for keyword in all_keywords:
            if len(keyword) < 3:
                continue

            snomed_code, fidelity = check_exact_match(keyword, specialties)

            if snomed_code:
                try:
                    cur.execute("""
                        INSERT INTO keyword_to_snomed (keyword, snomed_code, fidelity)
                        VALUES (%s, %s, %s)
                        ON CONFLICT DO NOTHING
                    """, (keyword, snomed_code, fidelity))
                    if cur.rowcount > 0:
                        if fidelity == 'V':
                            inserted_v += 1
                        else:
                            inserted_f += 1
                except Exception as e:
                    pass

        db.commit()
        print(f"   Insertados: {inserted_v} con fidelidad V, {inserted_f} con fidelidad F")
        print(f"   Total: {inserted_v + inserted_f} de {len(all_keywords)} keywords únicos")


def populate_title_mappings(specialties):
    """Pobla la tabla title_pattern_to_snomed."""
    print("\n[4/5] Poblando title_pattern_to_snomed...")

    with db.cursor_context() as cur:
        # Obtener títulos únicos
        cur.execute("""
            SELECT DISTINCT article_title
            FROM pubmed_articles
            WHERE article_title IS NOT NULL
        """)
        titles = [row[0] for row in cur.fetchall()]

        inserted_v = 0
        inserted_f = 0
        patterns_added = set()

        for title in titles:
            snomed_code, fidelity = check_exact_match(title, specialties)

            if snomed_code:
                pattern = title[:500]
                pattern_key = (pattern, snomed_code)

                if pattern_key not in patterns_added:
                    try:
                        cur.execute("""
                            INSERT INTO title_pattern_to_snomed (title_pattern, pattern_type, snomed_code, fidelity)
                            VALUES (%s, 'exact', %s, %s)
                            ON CONFLICT DO NOTHING
                        """, (pattern, snomed_code, fidelity))
                        if cur.rowcount > 0:
                            patterns_added.add(pattern_key)
                            if fidelity == 'V':
                                inserted_v += 1
                            else:
                                inserted_f += 1
                    except Exception as e:
                        pass

        db.commit()
        print(f"   Insertados: {inserted_v} con fidelidad V, {inserted_f} con fidelidad F")
        print(f"   Total: {inserted_v + inserted_f} patrones de {len(titles)} títulos")


def populate_abstract_mappings(specialties):
    """Pobla la tabla abstract_pattern_to_snomed."""
    print("\n[5/5] Poblando abstract_pattern_to_snomed...")

    with db.cursor_context() as cur:
        # Obtener abstracts (muchos, procesamos en lotes)
        cur.execute("""
            SELECT pubmed_id, article_abstract
            FROM pubmed_articles
            WHERE article_abstract IS NOT NULL
        """)
        abstracts = cur.fetchall()

        inserted_v = 0
        inserted_f = 0
        patterns_added = set()

        for pubmed_id, abstract in abstracts:
            snomed_code, fidelity = check_exact_match(abstract, specialties)

            if snomed_code:
                # Usar los primeros 500 caracteres como patrón identificador
                pattern = abstract[:500]
                pattern_key = (pattern, snomed_code)

                if pattern_key not in patterns_added:
                    try:
                        cur.execute("""
                            INSERT INTO abstract_pattern_to_snomed (abstract_pattern, pattern_type, snomed_code, fidelity)
                            VALUES (%s, 'exact', %s, %s)
                            ON CONFLICT DO NOTHING
                        """, (pattern, snomed_code, fidelity))
                        if cur.rowcount > 0:
                            patterns_added.add(pattern_key)
                            if fidelity == 'V':
                                inserted_v += 1
                            else:
                                inserted_f += 1
                    except Exception as e:
                        pass

        db.commit()
        print(f"   Insertados: {inserted_v} con fidelidad V, {inserted_f} con fidelidad F")
        print(f"   Total: {inserted_v + inserted_f} patrones de {len(abstracts)} abstracts")


def show_stats():
    """Muestra estadísticas de las tablas de mapeo."""
    print("\n" + "=" * 60)
    print("ESTADÍSTICAS DE MAPEOS")
    print("=" * 60)

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

            cur.execute(f"SELECT COUNT(*) FROM {table} WHERE fidelity = 'V'")
            fidelity_v = cur.fetchone()[0]

            cur.execute(f"SELECT COUNT(*) FROM {table} WHERE fidelity = 'F'")
            fidelity_f = cur.fetchone()[0]

            cur.execute(f"SELECT COUNT(DISTINCT snomed_code) FROM {table}")
            specialties = cur.fetchone()[0]

            print(f"\n{table}:")
            print(f"   Total: {total} mapeos")
            print(f"   Fidelidad V (exacto): {fidelity_v}")
            print(f"   Fidelidad F (inferido): {fidelity_f}")
            print(f"   Especialidades distintas: {specialties}")


def main():
    print("=" * 60)
    print("POBLANDO TABLAS DE MAPEO SNOMED")
    print("=" * 60)
    print("\nFidelidad:")
    print("  'V' = Verdadero: nombre exacto de especialidad encontrado")
    print("  'F' = Falso: relación inferida")

    try:
        # Obtener especialidades
        specialties = get_specialties()
        print(f"\nEspecialidades cargadas: {len(specialties)}")

        # Poblar cada tabla
        populate_journal_mappings(specialties)
        populate_affiliation_mappings(specialties)
        populate_keyword_mappings(specialties)
        populate_title_mappings(specialties)
        populate_abstract_mappings(specialties)

        # Mostrar estadísticas
        show_stats()

        print("\n" + "=" * 60)
        print("COMPLETADO")
        print("=" * 60)

    finally:
        db.close()


if __name__ == '__main__':
    main()
