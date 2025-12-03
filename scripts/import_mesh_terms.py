#!/usr/bin/env python3
"""
Descarga e importa todos los términos MeSH a PostgreSQL.

Fuente: NLM MeSH ASCII files
URL: https://nlmpubs.nlm.nih.gov/projects/mesh/MESH_FILES/asciimesh/

Uso:
    python scripts/import_mesh_terms.py
    python scripts/import_mesh_terms.py --year 2024
"""

import argparse
import re
import sys
from pathlib import Path

import requests
import psycopg2

# Añadir el directorio raíz al path
sys.path.insert(0, str(Path(__file__).parent.parent))

from config.settings import settings


MESH_BASE_URL = "https://nlmpubs.nlm.nih.gov/projects/mesh/MESH_FILES/asciimesh"


def get_mesh_url(year: int = 2025) -> str:
    """Construye la URL del archivo MeSH para el año especificado."""
    return f"{MESH_BASE_URL}/d{year}.bin"


def download_mesh(year: int = 2025) -> str:
    """Descarga el archivo ASCII de descriptores MeSH."""
    url = get_mesh_url(year)
    print(f"Descargando MeSH {year} desde {url}...")

    response = requests.get(url, timeout=300)
    response.raise_for_status()

    # El archivo está en ISO-8859-1
    content = response.content.decode('utf-8', errors='replace')
    print(f"Descargado: {len(content):,} caracteres")

    return content


def parse_mesh_records(content: str) -> list:
    """
    Parsea el contenido ASCII de MeSH y extrae los registros.

    Formato ASCII MeSH:
    *NEWRECORD
    RECTYPE = D
    MH = Cardiovascular Diseases
    ...
    MN = C14
    MN = C14.280
    ...
    UI = D002318
    """
    records = []

    # Dividir por registros (separados por *NEWRECORD)
    raw_records = content.split('*NEWRECORD')

    for raw_record in raw_records[1:]:  # Saltar el primero (cabecera)
        record = parse_single_record(raw_record)
        if record and record.get('mesh_ui') and record.get('mesh_name'):
            records.append(record)

    return records


def parse_single_record(raw_record: str) -> dict:
    """Parsea un único registro MeSH."""
    # Extraer campos usando regex
    mesh_ui = re.search(r'^UI = (.+)$', raw_record, re.MULTILINE)
    mesh_name = re.search(r'^MH = (.+)$', raw_record, re.MULTILINE)
    tree_numbers = re.findall(r'^MN = (.+)$', raw_record, re.MULTILINE)
    year_intro = re.search(r'^DX = (\d{4})', raw_record, re.MULTILINE)

    if not mesh_ui or not mesh_name:
        return None

    # Determinar categoría padre del primer tree number
    parent_category = None
    if tree_numbers:
        parent_category = tree_numbers[0][0] if tree_numbers[0] else None

    return {
        'mesh_ui': mesh_ui.group(1).strip(),
        'mesh_name': mesh_name.group(1).strip(),
        'tree_numbers': ';'.join(tree_numbers) if tree_numbers else None,
        'parent_category': parent_category,
        'year_introduced': int(year_intro.group(1)) if year_intro else None
    }


def create_table(cursor):
    """Crea la tabla nlm_mesh_terms si no existe."""
    cursor.execute("""
        DROP TABLE IF EXISTS nlm_mesh_terms CASCADE;

        CREATE TABLE nlm_mesh_terms (
            id SERIAL PRIMARY KEY,
            mesh_ui VARCHAR(20) UNIQUE NOT NULL,
            mesh_name VARCHAR(500) NOT NULL,
            tree_numbers TEXT,
            parent_category CHAR(1),
            year_introduced INTEGER,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        CREATE INDEX idx_nlm_mesh_ui ON nlm_mesh_terms(mesh_ui);
        CREATE INDEX idx_nlm_mesh_name ON nlm_mesh_terms(mesh_name);
        CREATE INDEX idx_nlm_mesh_category ON nlm_mesh_terms(parent_category);

        COMMENT ON TABLE nlm_mesh_terms IS 'Términos MeSH de la National Library of Medicine (NLM)';
    """)


def import_to_db(records: list, db_config: dict):
    """Inserta los registros en PostgreSQL."""
    conn = psycopg2.connect(
        host=db_config['host'],
        port=db_config['port'],
        dbname=db_config['dbname'],
        user=db_config['user'],
        password=db_config['password']
    )

    try:
        cursor = conn.cursor()

        # Crear tabla
        print("Creando tabla nlm_mesh_terms...")
        create_table(cursor)
        conn.commit()

        # Insertar registros en lotes
        print(f"Insertando {len(records):,} registros...")
        batch_size = 1000
        inserted = 0

        for i in range(0, len(records), batch_size):
            batch = records[i:i + batch_size]

            for record in batch:
                cursor.execute("""
                    INSERT INTO nlm_mesh_terms (mesh_ui, mesh_name, tree_numbers, parent_category, year_introduced)
                    VALUES (%s, %s, %s, %s, %s)
                    ON CONFLICT (mesh_ui) DO NOTHING
                """, (
                    record['mesh_ui'],
                    record['mesh_name'],
                    record['tree_numbers'],
                    record['parent_category'],
                    record['year_introduced']
                ))

            conn.commit()
            inserted += len(batch)
            print(f"  Insertados: {inserted:,} / {len(records):,}")

        # Verificar
        cursor.execute("SELECT COUNT(*) FROM nlm_mesh_terms")
        total = cursor.fetchone()[0]
        print(f"\nTotal registros en nlm_mesh_terms: {total:,}")

        # Mostrar distribución por categoría
        cursor.execute("""
            SELECT parent_category, COUNT(*) as count
            FROM nlm_mesh_terms
            WHERE parent_category IS NOT NULL
            GROUP BY parent_category
            ORDER BY count DESC
        """)
        print("\nDistribución por categoría:")
        for row in cursor.fetchall():
            print(f"  {row[0]}: {row[1]:,}")

    finally:
        conn.close()


def main():
    parser = argparse.ArgumentParser(description='Importa términos MeSH a PostgreSQL')
    parser.add_argument('--year', type=int, default=2025, help='Año de MeSH a descargar (default: 2025)')
    args = parser.parse_args()

    # Cargar configuración de BD
    db_config = settings.get_db_connection_params()

    # Descargar MeSH
    content = download_mesh(args.year)

    # Parsear registros
    print("Parseando registros MeSH...")
    records = parse_mesh_records(content)
    print(f"Parseados: {len(records):,} registros")

    # Importar a BD
    import_to_db(records, db_config)

    print("\n¡Importación completada!")


if __name__ == '__main__':
    main()
