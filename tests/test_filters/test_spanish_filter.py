"""
Tests para el filtro de afiliaciones españolas.
"""

import pytest
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from src.filters.spanish_filter import SpanishFilter


class TestSpanishFilter:
    """Tests del filtro español."""

    @pytest.fixture
    def filter(self):
        """Fixture que crea una instancia del filtro."""
        return SpanishFilter()

    def test_spanish_affiliation_with_spain_marker(self, filter):
        """Afiliación con 'Spain' debe ser española."""
        aff = "Hospital Clinic, Barcelona, Spain"
        assert filter.is_spanish_affiliation(aff) is True

    def test_spanish_affiliation_with_espana_marker(self, filter):
        """Afiliación con 'España' debe ser española."""
        aff = "Universidad de Madrid, España"
        assert filter.is_spanish_affiliation(aff) is True

    def test_non_spanish_affiliation_france(self, filter):
        """Afiliación con 'France' NO debe ser española."""
        aff = "Sorbonne University, Paris, France"
        assert filter.is_spanish_affiliation(aff) is False

    def test_non_spanish_affiliation_usa(self, filter):
        """Afiliación con 'USA' NO debe ser española."""
        aff = "Harvard Medical School, Boston, USA"
        assert filter.is_spanish_affiliation(aff) is False

    def test_mixed_affiliation_rejected(self, filter):
        """Afiliación mixta (España + otro país) debe ser rechazada."""
        aff = "Hospital Clinic, Barcelona, Spain; Sorbonne, France"
        # La parte con France contamina toda la afiliación
        # Pero filter_spanish_parts debería extraer solo la parte española
        spanish_only = filter.filter_spanish_parts(aff)
        assert spanish_only is not None
        assert "France" not in spanish_only
        assert "Spain" in spanish_only

    def test_empty_affiliation(self, filter):
        """Afiliación vacía debe retornar False."""
        assert filter.is_spanish_affiliation("") is False
        assert filter.is_spanish_affiliation(None) is False

    def test_affiliation_without_country(self, filter):
        """Afiliación sin país debe retornar False."""
        aff = "Hospital Clinic, Barcelona"
        assert filter.is_spanish_affiliation(aff) is False

    def test_filter_spanish_parts_multiple(self, filter):
        """Debe filtrar solo las partes españolas."""
        aff = "Dept Medicine, Barcelona, Spain; INSERM, Lyon, France"
        result = filter.filter_spanish_parts(aff)

        assert result is not None
        assert "Spain" in result
        assert "France" not in result

    def test_get_spanish_affiliations_list(self, filter):
        """Debe filtrar lista de afiliaciones."""
        affiliations = [
            "Hospital Clinic, Barcelona, Spain",
            "Harvard University, Boston, USA",
            "Universidad de Sevilla, Spain"
        ]

        result = filter.get_spanish_affiliations(affiliations)

        assert len(result) == 2
        assert any("Barcelona" in r for r in result)
        assert any("Sevilla" in r for r in result)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
