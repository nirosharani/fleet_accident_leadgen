import sqlite3
from typing import Any, Optional


class CompanyRepository:

    def __init__(self, connection: sqlite3.Connection) -> None:
        self.connection = connection

    def load_all_companies(self) -> list[sqlite3.Row]:
        cursor = self.connection.execute(
            "SELECT id, company_name, sector, aliases FROM company_master ORDER BY company_name"
        )
        return cursor.fetchall()

    def get_company_by_name(self, name: str) -> Optional[sqlite3.Row]:
        cursor = self.connection.execute(
            "SELECT id, company_name, sector FROM company_master WHERE company_name = ?",
            (name,),
        )
        return cursor.fetchone()

    def get_company_by_name_or_alias(self, name: str) -> Optional[sqlite3.Row]:
        cursor = self.connection.execute(
            "SELECT id, company_name, sector FROM company_master WHERE company_name = ?",
            (name,),
        )
        row = cursor.fetchone()
        if row is not None:
            return row

        cursor = self.connection.execute(
            "SELECT id, company_name, sector FROM company_master WHERE aliases IS NOT NULL"
        )
        for cm in cursor.fetchall():
            aliases_raw: Optional[str] = cm["aliases"] if "aliases" in cm.keys() else None
            if aliases_raw:
                alias_list = [a.strip().lower() for a in aliases_raw.split("|")]
                if name.lower() in alias_list:
                    return cm
        return None

    def get_company_aliases(self, name: str) -> list[str]:
        cursor = self.connection.execute(
            "SELECT aliases FROM company_master WHERE company_name = ?",
            (name,),
        )
        row = cursor.fetchone()
        if row is None:
            return []
        aliases_raw: Optional[str] = row["aliases"] if row and "aliases" in row.keys() else None
        if not aliases_raw:
            return []
        return [a.strip() for a in aliases_raw.split("|") if a.strip()]

    def company_exists(self, name: str) -> bool:
        cursor = self.connection.execute(
            "SELECT 1 FROM company_master WHERE company_name = ? LIMIT 1",
            (name,),
        )
        return cursor.fetchone() is not None

    def search_company(self, query: str) -> list[sqlite3.Row]:
        pattern = f"%{query}%"
        cursor = self.connection.execute(
            "SELECT id, company_name, sector FROM company_master WHERE company_name LIKE ? OR sector LIKE ? ORDER BY company_name",
            (pattern, pattern),
        )
        return cursor.fetchall()

    def insert_company(self, company_name: str, sector: str, aliases: Optional[str] = None) -> int:
        cursor = self.connection.execute(
            "INSERT OR IGNORE INTO company_master (company_name, sector, aliases) VALUES (?, ?, ?)",
            (company_name, sector, aliases),
        )
        return cursor.rowcount

    def count(self) -> int:
        cursor = self.connection.execute("SELECT COUNT(*) FROM company_master")
        return cursor.fetchone()[0]
