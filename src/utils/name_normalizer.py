"""
Author name normalization module.

This module provides functions to normalize author names, so that
variations of the same name can be identified as a single entity.

Documentation: docs/deduplicacion_autores.md
"""

import re
import unicodedata
from typing import List, Dict, Optional, Tuple


# "María" variants that must be normalized
MARIA_VARIANTS = ['mª', 'ma', 'm.ª', 'm.a', 'mᵃ', 'm.', 'ma.']


def remove_accents(text: str) -> str:
    """
    Remove accents and special characters from a text.

    Args:
        text: Text that may contain accents

    Returns:
        Text without accents (e.g. "García" -> "Garcia")
    """
    # NFD normalization: splits base characters from their diacritical marks
    nfkd_form = unicodedata.normalize('NFKD', text)
    # Keep only ASCII characters
    return ''.join(c for c in nfkd_form if not unicodedata.combining(c))


def normalize_maria(name: str) -> str:
    """
    Normalize the different abbreviations of "María".

    Args:
        name: Name that may contain María variants

    Returns:
        Name with María normalized
    """
    name_lower = name.lower()
    for variant in MARIA_VARIANTS:
        if variant in name_lower:
            # Replace while preserving the original case if possible
            name_lower = name_lower.replace(variant, 'maria')
    return name_lower


def normalize_compound_names(name: str) -> str:
    """
    Normalize compound surnames and particles.

    - Convert hyphens to spaces
    - Normalize particles (de, de la, del)

    Args:
        name: Name that may contain hyphens or particles

    Returns:
        Normalized name
    """
    # Convert hyphens to spaces
    name = name.replace('-', ' ')

    # Normalize particles (keep lowercase)
    # Already lowercase after the previous steps
    return name


def normalize_punctuation(name: str) -> str:
    """
    Remove unnecessary punctuation.

    Args:
        name: Name that may contain punctuation

    Returns:
        Name without extra punctuation
    """
    # Remove periods (except those that are part of abbreviations)
    name = re.sub(r'\.(?!\s|$)', '', name)  # Periods not followed by space or end
    name = name.replace('.', '')  # Remaining periods

    return name


def normalize_spaces(name: str) -> str:
    """
    Normalize multiple spaces and strip leading/trailing whitespace.

    Args:
        name: Name that may contain extra spaces

    Returns:
        Name with normalized spaces
    """
    return ' '.join(name.split())


def get_canonical_name(name: str) -> str:
    """
    Generate the canonical name used for comparison and deduplication.

    This is the name used as a key to identify unique authors.

    Steps:
    1. Lowercase
    2. Remove accents
    3. Normalize María abbreviations
    4. Normalize compound surnames (hyphens -> spaces)
    5. Remove punctuation
    6. Normalize spaces

    Args:
        name: Original author name

    Returns:
        Canonical name (lowercase, no accents, normalized)

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

    # 2. Normalize María (before removing accents)
    name = normalize_maria(name)

    # 3. Remove accents
    name = remove_accents(name)

    # 4. Normalize compound names
    name = normalize_compound_names(name)

    # 5. Remove punctuation
    name = normalize_punctuation(name)

    # 6. Normalize spaces
    name = normalize_spaces(name)

    return name


def is_initial_only(name_part: str) -> bool:
    """
    Check whether a name part is only an initial.

    Args:
        name_part: Name part to check

    Returns:
        True if it is only an initial (e.g. "J", "A M")
    """
    # Remove spaces and check if only uppercase letters remain
    clean = name_part.replace(' ', '').replace('.', '')
    return len(clean) <= 2 and clean.isupper()


def has_full_name(name: str) -> bool:
    """
    Check whether the name contains a full name (not just initials).

    Args:
        name: Full name "Lastname, Forename"

    Returns:
        True if it has a full name
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
    Check whether the name contains accented characters.

    Args:
        name: Name to check

    Returns:
        True if it has accents
    """
    return bool(re.search(r'[áéíóúñüÁÉÍÓÚÑÜ]', name))


def score_name_quality(name: str, frequency: int = 1) -> Tuple[int, int, int, int]:
    """
    Compute a quality score for a name.

    Used to pick the best name among variants.

    Criteria (in priority order):
    1. Has a full name (not just initials)
    2. Has accents
    3. Frequency of appearance
    4. Name length

    Args:
        name: Name to evaluate
        frequency: Number of times this name appears

    Returns:
        Tuple of scores for sorting
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
    Select the best name to display among the variants.

    Selection criteria:
    1. Prefer full names over initials
    2. Prefer names with accents
    3. On tie, use the most frequent one
    4. If still tied, use the longest one

    Args:
        name_variants: List of name variants
        name_counts: Dictionary with the frequencies of each variant

    Returns:
        The most appropriate name to display

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
    Check whether two names are similar (could be the same person).

    Args:
        name1: First name
        name2: Second name

    Returns:
        True if the normalized names are equal
    """
    return get_canonical_name(name1) == get_canonical_name(name2)


def extract_surname(name: str) -> str:
    """
    Extract the surname from a name in "Lastname, Forename" format.

    Args:
        name: Full name

    Returns:
        Surname
    """
    if ',' in name:
        return name.split(',')[0].strip()
    return name.strip()


def extract_first_name(name: str) -> str:
    """
    Extract the given name from a name in "Lastname, Forename" format.

    Args:
        name: Full name

    Returns:
        Given name
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
    # Basic tests
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

    print("=== Normalization tests ===\n")
    all_passed = True
    for original, expected in test_cases:
        result = get_canonical_name(original)
        status = "✓" if result == expected else "✗"
        if result != expected:
            all_passed = False
        print(f"{status} '{original}'")
        print(f"  → '{result}'")
        if result != expected:
            print(f"  ✗ Expected: '{expected}'")
        print()

    print("=" * 40)
    print(f"Result: {'ALL PASSED' if all_passed else 'ERRORS FOUND'}")

    # Name selection test
    print("\n=== Name selection tests ===\n")
    variants = ['García, J', 'García, Juan', 'Garcia, Juan', 'García, J A']
    counts = {'García, J': 10, 'García, Juan': 5, 'Garcia, Juan': 3, 'García, J A': 2}
    selected = select_display_name(variants, counts)
    print(f"Variants: {variants}")
    print(f"Frequencies: {counts}")
    print(f"Selected: {selected}")
