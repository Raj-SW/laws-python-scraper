from typing import Any, Dict
from supabase import create_client, Client


class SupabaseHelper:
    def __init__(self, url: str, service_key: str, table_name: str):
        self.client: Client = create_client(url, service_key)
        self.table_name = table_name

    def insert_judgment(self, record: Dict[str, Any]) -> None:
        self.client.table(self.table_name).insert(record).execute()

