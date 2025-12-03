"""
Tests para el módulo de configuración.
"""

import pytest
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))


class TestEnvironmentVariables:
    """Tests para la carga de variables de entorno."""

    def test_db_password_from_env(self, monkeypatch):
        """La contraseña debe leerse de variable de entorno."""
        # Configurar variable de entorno
        monkeypatch.setenv('PUBMED_DB_PASSWORD', 'test_password_123')

        # Reimportar settings para recargar
        from config.settings import Settings
        settings = Settings.__new__(Settings)
        settings._initialized = False
        settings.__init__()

        params = settings.get_db_connection_params()
        assert params['password'] == 'test_password_123'

    def test_db_host_from_env(self, monkeypatch):
        """El host debe leerse de variable de entorno."""
        monkeypatch.setenv('PUBMED_DB_HOST', 'test-host.example.com')

        from config.settings import Settings
        settings = Settings.__new__(Settings)
        settings._initialized = False
        settings.__init__()

        params = settings.get_db_connection_params()
        assert params['host'] == 'test-host.example.com'

    def test_db_port_from_env(self, monkeypatch):
        """El puerto debe leerse de variable de entorno."""
        monkeypatch.setenv('PUBMED_DB_PORT', '5433')

        from config.settings import Settings
        settings = Settings.__new__(Settings)
        settings._initialized = False
        settings.__init__()

        params = settings.get_db_connection_params()
        assert params['port'] == 5433

    def test_default_values_without_env(self, monkeypatch):
        """Sin variables de entorno, usar valores por defecto."""
        # Limpiar variables de entorno
        for var in ['PUBMED_DB_HOST', 'PUBMED_DB_PORT', 'PUBMED_DB_NAME',
                    'PUBMED_DB_USER', 'PUBMED_DB_PASSWORD']:
            monkeypatch.delenv(var, raising=False)

        from config.settings import Settings
        settings = Settings.__new__(Settings)
        settings._initialized = False
        settings.__init__()

        params = settings.get_db_connection_params()
        assert params['host'] == 'localhost'
        assert params['port'] == 5432


class TestSettingsSingleton:
    """Tests para el patrón singleton de Settings."""

    def test_singleton_instance(self):
        """Settings debe ser singleton."""
        from config.settings import Settings

        s1 = Settings()
        s2 = Settings()

        assert s1 is s2


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
