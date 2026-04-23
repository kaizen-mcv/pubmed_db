"""
Módulo de normalización de nombres de autores.

Este módulo proporciona funciones para normalizar nombres de autores,
permitiendo identificar variaciones del mismo nombre como una única entidad.

Documentación: docs/deduplicacion_autores.md
"""

import re
import unicodedata
from typing import List, Dict, Optional, Tuple


# Variantes de "María" que deben normalizarse
MARIA_VARIANTS = ['mª', 'ma', 'm.ª', 'm.a', 'mᵃ', 'm.', 'ma.']


def remove_accents(text: str) -> str:
    """
    Elimina acentos y caracteres especiales de un texto.

    Args:
        text: Texto con posibles acentos

    Returns:
        Texto sin acentos (ej: "García" -> "Garcia")
    """
    # Normalización NFD: separa caracteres base de sus marcas diacríticas
    nfkd_form = unicodedata.normalize('NFKD', text)
    # Filtrar solo caracteres ASCII
    return ''.join(c for c in nfkd_form if not unicodedata.combining(c))


def normalize_maria(name: str) -> str:
    """
    Normaliza las diferentes abreviaturas de "María".

    Args:
        name: Nombre que puede contener variantes de María

    Returns:
        Nombre con María normalizado
    """
    name_lower = name.lower()
    for variant in MARIA_VARIANTS:
        if variant in name_lower:
            # Reemplazar manteniendo el caso original si es posible
            name_lower = name_lower.replace(variant, 'maria')
    return name_lower


def normalize_compound_names(name: str) -> str:
    """
    Normaliza apellidos compuestos y partículas.

    - Convierte guiones a espacios
    - Normaliza partículas (de, de la, del)

    Args:
        name: Nombre con posibles guiones o partículas

    Returns:
        Nombre normalizado
    """
    # Convertir guiones a espacios
    name = name.replace('-', ' ')

    # Normalizar partículas (mantener en minúsculas)
    # Ya está en minúsculas después de otros pasos
    return name


def normalize_punctuation(name: str) -> str:
    """
    Elimina puntuación innecesaria.

    Args:
        name: Nombre con posible puntuación

    Returns:
        Nombre sin puntuación extra
    """
    # Eliminar puntos (excepto los que son parte de abreviaturas)
    name = re.sub(r'\.(?!\s|$)', '', name)  # Puntos no seguidos de espacio o final
    name = name.replace('.', '')  # Puntos restantes

    return name


def normalize_spaces(name: str) -> str:
    """
    Normaliza espacios múltiples y elimina espacios al inicio/final.

    Args:
        name: Nombre con posibles espacios extra

    Returns:
        Nombre con espacios normalizados
    """
    return ' '.join(name.split())


def get_canonical_name(name: str) -> str:
    """
    Genera el nombre canónico para comparación y deduplicación.

    Este es el nombre que se usa como clave para identificar autores únicos.

    Pasos:
    1. Convertir a minúsculas
    2. Eliminar acentos
    3. Normalizar abreviaturas de María
    4. Normalizar apellidos compuestos (guiones -> espacios)
    5. Eliminar puntuación
    6. Normalizar espacios

    Args:
        name: Nombre original del autor

    Returns:
        Nombre canónico (lowercase, sin acentos, normalizado)

    Examples:
        >>> get_canonical_name("García-Pavia, Pablo")
        'garcia pavia, pablo'
        >>> get_canonical_name("García Pavía, Pablo")
        'garcia pavia, pablo'
        >>> get_canonical_name("Martínez, José Mª")
        'martinez, jose maria'
        >>> get_canonical_name("de Luis-Román, Daniel")
        'de luis roman, daniel'
    """
    if not name:
        return ''

    # 1. Lowercase
    name = name.lower()

    # 2. Normalizar María (antes de eliminar acentos)
    name = normalize_maria(name)

    # 3. Eliminar acentos
    name = remove_accents(name)

    # 4. Normalizar compuestos
    name = normalize_compound_names(name)

    # 5. Eliminar puntuación
    name = normalize_punctuation(name)

    # 6. Normalizar espacios
    name = normalize_spaces(name)

    return name


def is_initial_only(name_part: str) -> bool:
    """
    Verifica si una parte del nombre es solo una inicial.

    Args:
        name_part: Parte del nombre a verificar

    Returns:
        True si es solo inicial (ej: "J", "A M")
    """
    # Eliminar espacios y verificar si son solo letras mayúsculas
    clean = name_part.replace(' ', '').replace('.', '')
    return len(clean) <= 2 and clean.isupper()


def has_full_name(name: str) -> bool:
    """
    Verifica si el nombre contiene un nombre completo (no solo iniciales).

    Args:
        name: Nombre completo "Apellido, Nombre"

    Returns:
        True si tiene nombre completo
    """
    if ',' not in name:
        return True

    parts = name.split(',', 1)
    if len(parts) < 2:
        return True

    first_name = parts[1].strip()
    return not is_initial_only(first_name)


def has_accents(name: str) -> bool:
    """
    Verifica si el nombre contiene caracteres acentuados.

    Args:
        name: Nombre a verificar

    Returns:
        True si tiene acentos
    """
    return bool(re.search(r'[áéíóúñüÁÉÍÓÚÑÜ]', name))


def score_name_quality(name: str, frequency: int = 1) -> Tuple[int, int, int, int]:
    """
    Calcula una puntuación de calidad para un nombre.

    Se usa para seleccionar el mejor nombre entre variantes.

    Criterios (en orden de prioridad):
    1. Tiene nombre completo (no solo iniciales)
    2. Tiene acentos
    3. Frecuencia de aparición
    4. Longitud del nombre

    Args:
        name: Nombre a evaluar
        frequency: Número de veces que aparece este nombre

    Returns:
        Tupla de puntuaciones para ordenación
    """
    return (
        1 if has_full_name(name) else 0,
        1 if has_accents(name) else 0,
        frequency,
        len(name)
    )


def select_display_name(name_variants: List[str],
                         name_counts: Optional[Dict[str, int]] = None) -> str:
    """
    Selecciona el mejor nombre para mostrar entre las variantes.

    Criterios de selección:
    1. Priorizar nombres completos sobre iniciales
    2. Priorizar nombres con acentos
    3. Si hay empate, usar el más frecuente
    4. Si aún hay empate, usar el más largo

    Args:
        name_variants: Lista de variantes del nombre
        name_counts: Diccionario con frecuencias de cada variante

    Returns:
        El nombre más apropiado para mostrar

    Examples:
        >>> select_display_name(['García, J', 'García, Juan', 'Garcia, Juan'])
        'García, Juan'
    """
    if not name_variants:
        return ''

    if len(name_variants) == 1:
        return name_variants[0]

    if name_counts is None:
        name_counts = {n: 1 for n in name_variants}

    def sort_key(name: str) -> Tuple:
        return score_name_quality(name, name_counts.get(name, 1))

    return max(name_variants, key=sort_key)


def are_names_similar(name1: str, name2: str) -> bool:
    """
    Verifica si dos nombres son similares (podrían ser la misma persona).

    Args:
        name1: Primer nombre
        name2: Segundo nombre

    Returns:
        True si los nombres normalizados son iguales
    """
    return get_canonical_name(name1) == get_canonical_name(name2)


def extract_surname(name: str) -> str:
    """
    Extrae el apellido de un nombre en formato "Apellido, Nombre".

    Args:
        name: Nombre completo

    Returns:
        Apellido
    """
    if ',' in name:
        return name.split(',')[0].strip()
    return name.strip()


def extract_first_name(name: str) -> str:
    """
    Extrae el nombre de pila de un nombre en formato "Apellido, Nombre".

    Args:
        name: Nombre completo

    Returns:
        Nombre de pila
    """
    if ',' in name:
        parts = name.split(',', 1)
        if len(parts) > 1:
            return parts[1].strip()
    return ''


# =============================================================================
# TESTS
# =============================================================================

if __name__ == '__main__':
    # Tests básicos
    test_cases = [
        ("García-Pavia, Pablo", "garcia pavia, pablo"),
        ("García Pavía, Pablo", "garcia pavia, pablo"),
        ("Garcia-Pavia, P", "garcia pavia, p"),
        ("Martínez, José Mª", "martinez, jose maria"),
        ("de Luis-Román, Daniel", "de luis roman, daniel"),
        ("De Luis Román, Daniel Antonio", "de luis roman, daniel antonio"),
        ("Muñoz-Fernández, Mª Ángeles", "munoz fernandez, maria angeles"),
        ("González, J. A.", "gonzalez, j a"),
    ]

    print("=== Tests de normalización ===\n")
    all_passed = True
    for original, expected in test_cases:
        result = get_canonical_name(original)
        status = "✓" if result == expected else "✗"
        if result != expected:
            all_passed = False
        print(f"{status} '{original}'")
        print(f"  → '{result}'")
        if result != expected:
            print(f"  ✗ Esperado: '{expected}'")
        print()

    print("=" * 40)
    print(f"Resultado: {'TODOS PASARON' if all_passed else 'HAY ERRORES'}")

    # Test de selección de nombre
    print("\n=== Tests de selección de nombre ===\n")
    variants = ['García, J', 'García, Juan', 'Garcia, Juan', 'García, J A']
    counts = {'García, J': 10, 'García, Juan': 5, 'Garcia, Juan': 3, 'García, J A': 2}
    selected = select_display_name(variants, counts)
    print(f"Variantes: {variants}")
    print(f"Frecuencias: {counts}")
    print(f"Seleccionado: {selected}")
