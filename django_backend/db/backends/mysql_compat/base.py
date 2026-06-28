"""
Custom MySQL/MariaDB database backend for Warungio.
Uses MySQLCompatDatabaseFeatures to support MariaDB 10.4 (XAMPP).
"""

from django.db.backends.mysql.base import DatabaseWrapper as MySQLDatabaseWrapper
from .features import MySQLCompatDatabaseFeatures


class DatabaseWrapper(MySQLDatabaseWrapper):
    """DatabaseWrapper subclass that uses MySQLCompatDatabaseFeatures."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.features = MySQLCompatDatabaseFeatures(self)
