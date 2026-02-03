from supabase import create_client, Client
from app.config import settings


class SupabaseClient:
    _client: Client = None
    _service_client: Client = None

    @classmethod
    def get_client(cls) -> Client:
        if cls._client is None:
            cls._client = create_client(settings.supabase_url, settings.supabase_key)
        return cls._client

    @classmethod
    def get_service_client(cls) -> Client:
        """Client with service_role key; bypasses RLS. Use in background workers."""
        if cls._service_client is None and settings.supabase_service_role_key:
            cls._service_client = create_client(
                settings.supabase_url, settings.supabase_service_role_key
            )
        return cls._service_client or cls.get_client()

    @classmethod
    def reset_client(cls):
        cls._client = None
        cls._service_client = None


def get_supabase() -> Client:
    return SupabaseClient.get_client()
