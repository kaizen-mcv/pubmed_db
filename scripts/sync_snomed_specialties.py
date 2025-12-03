#!/usr/bin/env python3
"""
Script para sincronizar especialidades SNOMED CT desde API FHIR.

Uso:
    python sync_snomed_specialties.py           # Solo reportar diferencias
    python sync_snomed_specialties.py --apply   # Aplicar cambios a BD

Fuente: HL7 FHIR ValueSet c80-practice-codes
https://www.hl7.org/fhir/valueset-c80-practice-codes.html
"""

import argparse
import sys
from datetime import date
from pathlib import Path
from typing import Dict, List, Set, Tuple

import requests

# Añadir path del proyecto
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.database.connection import db


# URL de la API FHIR para especialidades médicas
FHIR_VALUESET_URL = (
    "https://tx.fhir.org/r4/ValueSet/$expand"
    "?url=http://hl7.org/fhir/ValueSet/c80-practice-codes"
)


def fetch_fhir_specialties() -> Dict[str, str]:
    """
    Obtiene las especialidades desde la API FHIR.

    Returns:
        Dict[snomed_code, name_en]
    """
    print("Consultando API FHIR...")

    try:
        headers = {"Accept": "application/fhir+json"}
        response = requests.get(FHIR_VALUESET_URL, headers=headers, timeout=30)
        response.raise_for_status()
        data = response.json()

        specialties = {}

        # Extraer códigos del ValueSet expandido
        if 'expansion' in data and 'contains' in data['expansion']:
            for item in data['expansion']['contains']:
                code = item.get('code')
                display = item.get('display')
                if code and display:
                    specialties[code] = display

        print(f"  Encontradas {len(specialties)} especialidades en FHIR")
        return specialties

    except requests.RequestException as e:
        print(f"Error consultando API FHIR: {e}")
        sys.exit(1)


def fetch_local_specialties() -> Dict[str, Tuple[str, str, str, bool]]:
    """
    Obtiene las especialidades desde la BD local.

    Returns:
        Dict[snomed_code, (name_en, name_snomed, name_es, is_mir_spain)]
    """
    print("Consultando BD local...")

    with db.cursor_context() as cur:
        cur.execute("""
            SELECT snomed_code, name_en, name_snomed, name_es, is_mir_spain
            FROM snomed_specialties
        """)

        specialties = {}
        for row in cur.fetchall():
            code, name_en, name_snomed, name_es, is_mir = row
            specialties[code] = (name_en, name_snomed, name_es, is_mir)

        print(f"  Encontradas {len(specialties)} especialidades en BD local")
        return specialties


def compare_specialties(
    fhir: Dict[str, str],
    local: Dict[str, Tuple[str, str, str, bool]]
) -> Tuple[List, List, List, List]:
    """
    Compara especialidades FHIR con locales.

    Returns:
        (nuevas, eliminadas, modificadas_name_en, sin_name_snomed)
    """
    fhir_codes = set(fhir.keys())
    local_codes = set(local.keys())

    # Nuevas en FHIR (no están en local)
    new_codes = fhir_codes - local_codes
    nuevas = [(code, fhir[code]) for code in sorted(new_codes)]

    # Eliminadas de FHIR (están en local pero no en FHIR)
    removed_codes = local_codes - fhir_codes
    eliminadas = [(code, local[code][0]) for code in sorted(removed_codes)]

    # Detectar las que no tienen name_snomed poblado
    # NO modificamos name_en - ese es nuestro nombre simplificado
    common_codes = fhir_codes & local_codes
    modificadas = []  # Solo si hay cambios reales futuros en el estándar
    sin_name_snomed = []

    for code in sorted(common_codes):
        fhir_name = fhir[code]
        name_en, name_snomed, name_es, is_mir = local[code]

        # Si no tiene name_snomed, añadir a la lista para poblar
        if name_snomed is None:
            sin_name_snomed.append((code, fhir_name))
        # Si tiene name_snomed pero difiere del FHIR actual (cambio en estándar)
        elif name_snomed != fhir_name:
            modificadas.append((code, name_snomed, fhir_name))

    return nuevas, eliminadas, modificadas, sin_name_snomed


def print_report(
    nuevas: List,
    eliminadas: List,
    modificadas: List,
    sin_name_snomed: List,
    fhir_count: int,
    local_count: int
):
    """Imprime el reporte de diferencias."""
    print("\n" + "=" * 70)
    print("REPORTE DE SINCRONIZACIÓN SNOMED CT")
    print("=" * 70)
    print(f"Especialidades en FHIR:  {fhir_count}")
    print(f"Especialidades en BD:    {local_count}")
    print("=" * 70)

    if not nuevas and not eliminadas and not modificadas and not sin_name_snomed:
        print("\n✓ La BD está sincronizada con FHIR. No hay cambios.")
        return

    if nuevas:
        print(f"\n NUEVAS ESPECIALIDADES ({len(nuevas)}):")
        print("-" * 50)
        for code, name in nuevas:
            print(f"  {code}: {name}")

    if eliminadas:
        print(f"\n ESPECIALIDADES ELIMINADAS DE FHIR ({len(eliminadas)}):")
        print("-" * 50)
        for code, name in eliminadas:
            print(f"  {code}: {name}")
        print("  (Nota: No se eliminan automáticamente por seguridad)")

    if modificadas:
        print(f"\n NOMBRES MODIFICADOS ({len(modificadas)}):")
        print("-" * 50)
        for code, old_name, new_name in modificadas:
            print(f"  {code}:")
            print(f"    Antes: {old_name}")
            print(f"    Ahora: {new_name}")

    if sin_name_snomed:
        print(f"\n SIN NAME_SNOMED (se poblará) ({len(sin_name_snomed)}):")
        print("-" * 50)
        for code, name in sin_name_snomed[:10]:  # Solo mostrar primeros 10
            print(f"  {code}: {name}")
        if len(sin_name_snomed) > 10:
            print(f"  ... y {len(sin_name_snomed) - 10} más")

    print("\n" + "=" * 70)
    total_changes = len(nuevas) + len(modificadas) + len(sin_name_snomed)
    print(f"Total cambios aplicables: {total_changes}")
    if total_changes > 0:
        print("Usa --apply para aplicar los cambios a la BD")
    print("=" * 70 + "\n")


def apply_changes(
    nuevas: List,
    modificadas: List,
    sin_name_snomed: List
):
    """Aplica los cambios a la BD."""
    print("\nAplicando cambios a la BD...")

    with db.transaction() as cur:
        # Insertar nuevas (con name_snomed = nombre oficial FHIR)
        for code, name in nuevas:
            # Simplificar nombre (quitar "(qualifier value)" etc.)
            simple_name = simplify_snomed_name(name)
            cur.execute("""
                INSERT INTO snomed_specialties (snomed_code, name_en, name_snomed, is_mir_spain, last_checked)
                VALUES (%s, %s, %s, FALSE, %s)
            """, (code, simple_name, name, date.today()))
            print(f"  + Insertada: {code} - {simple_name}")

        # Actualizar modificadas
        for code, old_name, new_name in modificadas:
            cur.execute("""
                UPDATE snomed_specialties
                SET name_en = %s, last_checked = %s
                WHERE snomed_code = %s
            """, (new_name, date.today(), code))
            print(f"  ~ Actualizada: {code} - {new_name}")

        # Poblar name_snomed donde falta
        for code, fhir_name in sin_name_snomed:
            cur.execute("""
                UPDATE snomed_specialties
                SET name_snomed = %s, last_checked = %s
                WHERE snomed_code = %s
            """, (fhir_name, date.today(), code))

        if sin_name_snomed:
            print(f" Poblado name_snomed para {len(sin_name_snomed)} especialidades")

        # Actualizar fecha de comprobación para todas
        cur.execute("""
            UPDATE snomed_specialties
            SET last_checked = %s
            WHERE last_checked IS NULL OR last_checked < %s
        """, (date.today(), date.today()))

    print(f"\n✓ Cambios aplicados exitosamente")
    print(f"  - {len(nuevas)} nuevas especialidades")
    print(f"  - {len(modificadas)} nombres actualizados")
    print(f"  - {len(sin_name_snomed)} name_snomed poblados")


def simplify_snomed_name(name: str) -> str:
    """
    Simplifica el nombre oficial SNOMED quitando sufijos como "(qualifier value)".

    Args:
        name: Nombre oficial SNOMED

    Returns:
        Nombre simplificado
    """
    # Quitar "(qualifier value)" y similares
    import re
    simplified = re.sub(r'\s*\([^)]*\)\s*$', '', name)
    return simplified.strip()


def main():
    parser = argparse.ArgumentParser(
        description="Sincroniza especialidades SNOMED CT desde API FHIR"
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Aplicar cambios a la BD (por defecto solo reporta)"
    )

    args = parser.parse_args()

    # Obtener datos
    fhir_specialties = fetch_fhir_specialties()
    local_specialties = fetch_local_specialties()

    # Comparar
    nuevas, eliminadas, modificadas, sin_name_snomed = compare_specialties(
        fhir_specialties, local_specialties
    )

    # Reportar
    print_report(
        nuevas, eliminadas, modificadas, sin_name_snomed,
        len(fhir_specialties), len(local_specialties)
    )

    # Aplicar si se pidió
    if args.apply and (nuevas or modificadas or sin_name_snomed):
        apply_changes(nuevas, modificadas, sin_name_snomed)
    elif args.apply:
        print("No hay cambios que aplicar.")


if __name__ == "__main__":
    main()
