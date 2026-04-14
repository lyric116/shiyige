from backend.app.core.minio import check_minio_connection, reset_minio_state
from backend.app.core.redis import check_redis_connection, reset_redis_state


def test_redis_and_minio_clients_can_connect(monkeypatch) -> None:
    monkeypatch.setenv("REDIS_URL", "redis://127.0.0.1:6379/0")
    monkeypatch.setenv("MINIO_ENDPOINT", "127.0.0.1:9000")
    monkeypatch.setenv("MINIO_ACCESS_KEY", "minioadmin")
    monkeypatch.setenv("MINIO_SECRET_KEY", "minioadmin")
    monkeypatch.setenv("MINIO_SECURE", "false")

    reset_redis_state()
    reset_minio_state()

    assert check_redis_connection() is True
    assert check_minio_connection() is True
