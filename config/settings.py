"""
Carga centralizada de configuración.

Este módulo carga todos los archivos YAML de configuración
y los expone como un objeto Settings único.
"""

import os
from pathlib import Path
from typing import Any, Dict, Optional
import yaml


class Settings:
    """
    Gestor centralizado de configuración.

    Carga y proporciona acceso a:
    - pubmed_config.yaml: Políticas NCBI y parámetros de descarga
    - db_config.yaml: Credenciales de base de datos
    - spanish_filters.yaml: (VL) Listas de filtrado geográfico
    """

    _instance: Optional['Settings'] = None

    def __new__(cls):
        """Singleton: solo una instancia de Settings."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return

        self._config_dir = Path(__file__).parent

        # Cargar configuraciones
        self.pubmed = self._load_yaml('pubmed_config.yaml')
        self.database = self._load_yaml('db_config.yaml')
        self.spanish_filters = self._load_yaml('spanish_filters.yaml')

        self._initialized = True

    def _load_yaml(self, filename: str) -> Dict[str, Any]:
        """
        Carga un archivo YAML de configuración.

        Args:
            filename: Nombre del archivo YAML

        Returns:
            Diccionario con la configuración
        """
        filepath = self._config_dir / filename

        if not filepath.exists():
            print(f"⚠ Archivo de configuración no encontrado: {filepath}")
            return {}

        with open(filepath, 'r', encoding='utf-8') as f:
            return yaml.safe_load(f) or {}

    def get_db_connection_params(self) -> Dict[str, Any]:
        """
        Retorna parámetros de conexión para psycopg2.

        Lee primero de variables de entorno, luego del archivo YAML como fallback.

        Variables de entorno:
            PUBMED_DB_HOST, PUBMED_DB_PORT, PUBMED_DB_NAME,
            PUBMED_DB_USER, PUBMED_DB_PASSWORD

        Returns:
            Dict con host, port, dbname, user, password
        """
        db = self.database.get('database', {})

        # Leer de variables de entorno con fallback a YAML
        return {
            'host': os.environ.get('PUBMED_DB_HOST', db.get('host', 'localhost')),
            'port': int(os.environ.get('PUBMED_DB_PORT', db.get('port', 5432))),
            'dbname': os.environ.get('PUBMED_DB_NAME', db.get('name', 'pubmed_db')),
            'user': os.environ.get('PUBMED_DB_USER', db.get('user', 'pubmed_user')),
            'password': os.environ.get('PUBMED_DB_PASSWORD', db.get('password', '')),
        }

    def get_rate_limit_params(self) -> Dict[str, Any]:
        """
        Retorna parámetros de rate limiting.

        Returns:
            Dict con requests_per_second, min_delay, etc.
        """
        return self.pubmed.get('rate_limiting', {})

    def get_batch_params(self) -> Dict[str, Any]:
        """
        Retorna parámetros de descarga por lotes.

        Returns:
            Dict con ids_per_batch, search_batch_size, etc.
        """
        return self.pubmed.get('batch', {})

    def get_search_params(self) -> Dict[str, Any]:
        """
        Retorna parámetros de búsqueda.

        Returns:
            Dict con query, date_from, date_to, etc.
        """
        return self.pubmed.get('search', {})

    def get_spanish_markers(self) -> list:
        """
        (VL) Retorna lista de marcadores españoles.

        Returns:
            Lista de strings como ['spain', 'españa', ...]
        """
        return self.spanish_filters.get('spanish_markers', [])

    def get_spanish_cities(self) -> list:
        """
        (VL) Retorna lista de ciudades españolas.

        Returns:
            Lista de ciudades españolas
        """
        return self.spanish_filters.get('spanish_cities', [])

    def get_foreign_countries(self) -> list:
        """
        (VL) Retorna lista de países extranjeros (lista negra).

        Returns:
            Lista de países a excluir
        """
        return self.spanish_filters.get('foreign_countries', [])


# Instancia global para importar fácilmente
settings = Settings()
