"""
Custom MySQL/MariaDB database features for Warungio.
Relaxes the minimum MariaDB version from 10.6 to 10.4 for XAMPP compatibility.
"""

from django.db.backends.mysql.features import DatabaseFeatures


class MySQLCompatDatabaseFeatures(DatabaseFeatures):
    """DatabaseFeatures that supports MariaDB 10.4+ (XAMPP default)."""

    @property
    def minimum_database_version(self):
        if self.connection.mysql_is_mariadb:
            return (10, 4)
        return (8, 0, 11)
