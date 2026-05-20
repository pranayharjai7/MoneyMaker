from backend.db.repository import SupabaseRepository


def get_repository() -> SupabaseRepository:
    return SupabaseRepository()

