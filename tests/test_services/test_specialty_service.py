"""
Tests para el servicio de inferencia de especialidades.
"""

import pytest
import sys
import os
from unittest.mock import MagicMock, patch

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from src.services.specialty_service import SpecialtyService, SpecialtyMatch


class TestSpecialtyMatch:
    """Tests para SpecialtyMatch dataclass."""

    def test_create_specialty_match(self):
        """Debe crear un SpecialtyMatch correctamente."""
        match = SpecialtyMatch(
            snomed_code='394579002',
            name_en='Cardiology',
            name_es='Cardiología',
            confidence=0.95,
            source='mesh',
            detail='Heart Diseases [C14.280]'
        )

        assert match.snomed_code == '394579002'
        assert match.name_en == 'Cardiology'
        assert match.confidence == 0.95
        assert match.source == 'mesh'


class TestSpecialtyService:
    """Tests para SpecialtyService."""

    def test_weights_sum_to_one(self):
        """Los pesos de las fuentes deben sumar 1.0."""
        total = sum(SpecialtyService.WEIGHTS.values())
        assert total == pytest.approx(1.0, abs=0.01)

    def test_combine_matches_empty(self):
        """Combinar lista vacía debe retornar lista vacía."""
        result = SpecialtyService._combine_matches([])
        assert result == []

    def test_combine_matches_single(self):
        """Combinar un solo match."""
        matches = [
            SpecialtyMatch(
                snomed_code='394579002',
                name_en='Cardiology',
                name_es='Cardiología',
                confidence=0.9,
                source='mesh',
                detail='Heart [C14.280]'
            )
        ]

        result = SpecialtyService._combine_matches(matches)

        assert len(result) == 1
        assert result[0]['snomed_code'] == '394579002'
        assert result[0]['name_en'] == 'Cardiology'
        assert 'mesh' in result[0]['sources']

    def test_combine_matches_multiple_sources(self):
        """Combinar matches de múltiples fuentes para misma especialidad."""
        matches = [
            SpecialtyMatch(
                snomed_code='394579002',
                name_en='Cardiology',
                name_es='Cardiología',
                confidence=0.9,
                source='mesh',
                detail='Heart [C14.280]'
            ),
            SpecialtyMatch(
                snomed_code='394579002',
                name_en='Cardiology',
                name_es='Cardiología',
                confidence=0.85,
                source='journal',
                detail='Journal of Cardiology'
            ),
        ]

        result = SpecialtyService._combine_matches(matches)

        assert len(result) == 1
        assert result[0]['snomed_code'] == '394579002'
        assert 'mesh' in result[0]['sources']
        assert 'journal' in result[0]['sources']
        # Score debe ser mayor que con una sola fuente
        assert result[0]['score'] > 0.3

    def test_combine_matches_different_specialties(self):
        """Combinar matches de diferentes especialidades."""
        matches = [
            SpecialtyMatch(
                snomed_code='394579002',
                name_en='Cardiology',
                name_es='Cardiología',
                confidence=0.9,
                source='mesh',
                detail='Heart [C14.280]'
            ),
            SpecialtyMatch(
                snomed_code='394591006',
                name_en='Neurology',
                name_es='Neurología',
                confidence=0.85,
                source='mesh',
                detail='Brain [C10.228]'
            ),
        ]

        result = SpecialtyService._combine_matches(matches)

        assert len(result) == 2
        codes = [r['snomed_code'] for r in result]
        assert '394579002' in codes
        assert '394591006' in codes


class TestMeshParsing:
    """Tests para el parsing de MeSH terms."""

    def test_match_from_mesh_empty(self):
        """MeSH vacío debe retornar lista vacía."""
        mock_cursor = MagicMock()
        mock_cursor.fetchall.return_value = []

        result = SpecialtyService._match_from_mesh(mock_cursor, "")
        assert result == []

    def test_match_from_mesh_no_tree(self):
        """MeSH sin tree number debe retornar lista vacía."""
        mock_cursor = MagicMock()
        mock_cursor.fetchall.return_value = []

        result = SpecialtyService._match_from_mesh(mock_cursor, "Heart Failure")
        assert result == []


class TestJournalMatching:
    """Tests para matching de revistas."""

    def test_match_from_journal_by_issn(self):
        """Matching por ISSN."""
        mock_cursor = MagicMock()
        mock_cursor.fetchall.return_value = [
            ('394579002', 'Cardiology', 'Cardiología')
        ]

        result = SpecialtyService._match_from_journal(
            mock_cursor,
            issn='0735-1097',
            name=None
        )

        assert len(result) == 1
        assert result[0].snomed_code == '394579002'
        assert result[0].source == 'journal'

    def test_match_from_journal_none(self):
        """Sin ISSN ni nombre debe retornar vacío."""
        mock_cursor = MagicMock()

        result = SpecialtyService._match_from_journal(
            mock_cursor,
            issn=None,
            name=None
        )

        assert result == []


class TestKeywordMatching:
    """Tests para matching de keywords."""

    def test_match_from_keywords_empty(self):
        """Keywords vacío debe retornar lista vacía."""
        mock_cursor = MagicMock()

        result = SpecialtyService._match_from_keywords(mock_cursor, "")
        assert result == []

    def test_match_from_keywords_multiple(self):
        """Múltiples keywords separados por punto y coma."""
        mock_cursor = MagicMock()
        mock_cursor.fetchall.side_effect = [
            [('394579002', 'Cardiology', 'Cardiología')],
            [],
        ]

        result = SpecialtyService._match_from_keywords(
            mock_cursor,
            "heart failure; diabetes"
        )

        assert mock_cursor.execute.call_count == 2


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
