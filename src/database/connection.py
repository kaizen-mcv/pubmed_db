"""
PostgreSQL database connection manager.
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
    PostgreSQL connection manager.

    Provides:
    - Single reusable connection
    - Context manager for transactions
    - Automatic commit/rollback handling
    """

    _instance: Optional['DatabaseConnection'] = None
    _connection: Optional[connection] = None

    def __new__(cls):
        """Singleton: only one DatabaseConnection instance."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        self._connection_params = settings.get_db_connection_params()

    def get_connection(self) -> connection:
        """
        Get the database connection.

        Creates a new connection if none exists or it is closed.

        Returns:
            psycopg2 connection
        """
        if self._connection is None or self._connection.closed:
            self._connection = psycopg2.connect(**self._connection_params)
        return self._connection

    def get_cursor(self) -> cursor:
        """
        Get a cursor from the connection.

        Returns:
            psycopg2 cursor
        """
        return self.get_connection().cursor()

    def commit(self):
        """Commit the current transaction."""
        if self._connection and not self._connection.closed:
            self._connection.commit()

    def rollback(self):
        """Roll back the current transaction."""
        if self._connection and not self._connection.closed:
            self._connection.rollback()

    def close(self):
        """Close the connection."""
        if self._connection and not self._connection.closed:
            self._connection.close()
            self._connection = None

    @contextmanager
    def transaction(self) -> Generator[cursor, None, None]:
        """
        Context manager for transactions.

        Usage:
            with db.transaction() as cur:
                cur.execute("INSERT ...")

        Commits automatically if no errors occur,
        rolls back on exception.

        Yields:
            Database cursor
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
        Context manager for a cursor without auto-commit.

        Useful for operations that need manual transaction
        control.

        Yields:
            Database cursor
        """
        cur = self.get_cursor()
        try:
            yield cur
        finally:
            cur.close()


# Global instance
db = DatabaseConnection()
