"""
Gestor de conexiones a base de datos PostgreSQL.
"""

from contextlib import contextmanager
from typing import Generator, Optional

import psycopg2
from psycopg2.extensions import connection, cursor

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from config.settings import settings


class DatabaseConnection:
    """
    Gestor de conexiones a PostgreSQL.

    Proporciona:
    - Conexión única reutilizable
    - Context manager para transacciones
    - Manejo automático de commits/rollbacks
    """

    _instance: Optional['DatabaseConnection'] = None
    _connection: Optional[connection] = None

    def __new__(cls):
        """Singleton: solo una instancia de DatabaseConnection."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        self._connection_params = settings.get_db_connection_params()

    def get_connection(self) -> connection:
        """
        Obtiene la conexión a la base de datos.

        Crea una nueva conexión si no existe o está cerrada.

        Returns:
            Conexión psycopg2
        """
        if self._connection is None or self._connection.closed:
            self._connection = psycopg2.connect(**self._connection_params)
        return self._connection

    def get_cursor(self) -> cursor:
        """
        Obtiene un cursor de la conexión.

        Returns:
            Cursor psycopg2
        """
        return self.get_connection().cursor()

    def commit(self):
        """Hace commit de la transacción actual."""
        if self._connection and not self._connection.closed:
            self._connection.commit()

    def rollback(self):
        """Hace rollback de la transacción actual."""
        if self._connection and not self._connection.closed:
            self._connection.rollback()

    def close(self):
        """Cierra la conexión."""
        if self._connection and not self._connection.closed:
            self._connection.close()
            self._connection = None

    @contextmanager
    def transaction(self) -> Generator[cursor, None, None]:
        """
        Context manager para transacciones.

        Uso:
            with db.transaction() as cur:
                cur.execute("INSERT ...")

        Hace commit automático si no hay errores,
        rollback si hay excepción.

        Yields:
            Cursor de base de datos
        """
        cur = self.get_cursor()
        try:
            yield cur
            self.commit()
        except Exception:
            self.rollback()
            raise
        finally:
            cur.close()

    @contextmanager
    def cursor_context(self) -> Generator[cursor, None, None]:
        """
        Context manager para cursor sin auto-commit.

        Útil para operaciones que necesitan control manual
        de transacciones.

        Yields:
            Cursor de base de datos
        """
        cur = self.get_cursor()
        try:
            yield cur
        finally:
            cur.close()


# Instancia global
db = DatabaseConnection()
