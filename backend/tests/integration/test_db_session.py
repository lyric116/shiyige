from sqlalchemy import text

from backend.app.core.database import get_db, get_engine, reset_database_state


def test_database_session_executes_simple_query(monkeypatch, tmp_path) -> None:
    database_file = tmp_path / "test.db"
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{database_file}")
    reset_database_state()

    engine = get_engine()
    with engine.connect() as connection:
        result = connection.execute(text("SELECT 1"))
        assert result.scalar_one() == 1

    session = next(get_db())
    try:
        result = session.execute(text("SELECT 1"))
        assert result.scalar_one() == 1
    finally:
        session.close()
        reset_database_state()
