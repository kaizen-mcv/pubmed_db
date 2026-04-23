#!/usr/bin/env python3
"""Script to synchronize SNOMED CT specialties from the FHIR API.

Usage:
    python sync_snomed_specialties.py           # Report differences only
    python sync_snomed_specialties.py --apply   # Apply changes to the DB

Source: HL7 FHIR ValueSet c80-practice-codes
https://www.hl7.org/fhir/valueset-c80-practice-codes.html
"""

import argparse
import sys
from datetime import date
from pathlib import Path
from typing import Dict, List, Set, Tuple

import requests

# Add project path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.database.connection import db


# FHIR API URL for medical specialties
FHIR_VALUESET_URL = (
    "https://tx.fhir.org/r4/ValueSet/$expand"
    "?url=http://hl7.org/fhir/ValueSet/c80-practice-codes"
)


def fetch_fhir_specialties() -> Dict[str, str]:
    """Fetches specialties from the FHIR API.

    Returns:
        Dict[snomed_code, name_en].
    """
    print("Consultando API FHIR...")

    try:
        headers = {"Accept": "application/fhir+json"}
        response = requests.get(FHIR_VALUESET_URL, headers=headers, timeout=30)
        response.raise_for_status()
        data = response.json()

        specialties = {}

        # Extract codes from the expanded ValueSet
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
    """Fetches specialties from the local DB.

    Returns:
        Dict[snomed_code, (name_en, name_snomed, name_es, is_mir_spain)].
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
    """Compares FHIR specialties with local ones.

    Returns:
        (new, removed, modified_name_en, missing_name_snomed).
    """
    fhir_codes = set(fhir.keys())
    local_codes = set(local.keys())

    # New in FHIR (not in local)
    new_codes = fhir_codes - local_codes
    nuevas = [(code, fhir[code]) for code in sorted(new_codes)]

    # Removed from FHIR (in local but not in FHIR)
    removed_codes = local_codes - fhir_codes
    eliminadas = [(code, local[code][0]) for code in sorted(removed_codes)]

    # Detect those that do not have name_snomed populated
    # We do NOT modify name_en - that is our simplified name
    common_codes = fhir_codes & local_codes
    modificadas = []  # Only if there are real future changes in the standard
    sin_name_snomed = []

    for code in sorted(common_codes):
        fhir_name = fhir[code]
        name_en, name_snomed, name_es, is_mir = local[code]

        # If it does not have name_snomed, add to the list to populate
        if name_snomed is None:
            sin_name_snomed.append((code, fhir_name))
        # If it has name_snomed but differs from the current FHIR (change in standard)
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
    """Prints the differences report."""
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
        for code, name in sin_name_snomed[:10]:  # Show only the first 10
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
    """Applies the changes to the DB."""
    print("\nAplicando cambios a la BD...")

    with db.transaction() as cur:
        # Insert new ones (with name_snomed = official FHIR name)
        for code, name in nuevas:
            # Simplify name (remove "(qualifier value)", etc.)
            simple_name = simplify_snomed_name(name)
            cur.execute("""
                INSERT INTO snomed_specialties (snomed_code, name_en, name_snomed, is_mir_spain, last_checked)
                VALUES (%s, %s, %s, FALSE, %s)
            """, (code, simple_name, name, date.today()))
            print(f"  + Insertada: {code} - {simple_name}")

        # Update modified ones
        for code, old_name, new_name in modificadas:
            cur.execute("""
                UPDATE snomed_specialties
                SET name_en = %s, last_checked = %s
                WHERE snomed_code = %s
            """, (new_name, date.today(), code))
            print(f"  ~ Actualizada: {code} - {new_name}")

        # Populate name_snomed where missing
        for code, fhir_name in sin_name_snomed:
            cur.execute("""
                UPDATE snomed_specialties
                SET name_snomed = %s, last_checked = %s
                WHERE snomed_code = %s
            """, (fhir_name, date.today(), code))

        if sin_name_snomed:
            print(f" Poblado name_snomed para {len(sin_name_snomed)} especialidades")

        # Update last_checked date for all
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
    """Simplifies the official SNOMED name by removing suffixes such as "(qualifier value)".

    Args:
        name: Official SNOMED name.

    Returns:
        Simplified name.
    """
    # Remove "(qualifier value)" and similar
    import re
    simplified = re.sub(r'\s*\([^)]*\)\s*$', '', name)
    return simplified.strip()


def main():
    parser = argparse.ArgumentParser(
        description="Synchronize SNOMED CT specialties from the FHIR API"
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Apply changes to the DB (by default only reports)"
    )

    args = parser.parse_args()

    # Fetch data
    fhir_specialties = fetch_fhir_specialties()
    local_specialties = fetch_local_specialties()

    # Compare
    nuevas, eliminadas, modificadas, sin_name_snomed = compare_specialties(
        fhir_specialties, local_specialties
    )

    # Report
    print_report(
        nuevas, eliminadas, modificadas, sin_name_snomed,
        len(fhir_specialties), len(local_specialties)
    )

    # Apply if requested
    if args.apply and (nuevas or modificadas or sin_name_snomed):
        apply_changes(nuevas, modificadas, sin_name_snomed)
    elif args.apply:
        print("No hay cambios que aplicar.")


if __name__ == "__main__":
    main()
