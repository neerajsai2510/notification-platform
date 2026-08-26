from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from backend.main import app
from backend.database import Base, get_db


TEST_DATABASE_URL = "sqlite://"

test_engine = create_engine(
    TEST_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)

TestingSessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=test_engine,
)


Base.metadata.create_all(bind=test_engine)


def override_get_db():
    db = TestingSessionLocal()

    try:
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = override_get_db


client = TestClient(app)


def test_root_endpoint():
    response = client.get("/")

    assert response.status_code == 200

    assert response.json() == {
        "message": "Notification Platform API is running"
    }


def test_create_notification_validation():
    response = client.post(
        "/notifications",
        json={
            "recipient": "",
            "message": "",
        },
    )

    assert response.status_code == 422


def test_create_notification_message_too_long():
    response = client.post(
        "/notifications",
        json={
            "recipient": "user123",
            "message": "a" * 501,
        },
    )

    assert response.status_code == 422


def test_create_notification_recipient_too_long():
    response = client.post(
        "/notifications",
        json={
            "recipient": "a" * 101,
            "message": "Hello",
        },
    )

    assert response.status_code == 422


def test_create_notification_success(monkeypatch):
    class MockTask:
        def delay(self, notification_id):
            return None

    monkeypatch.setattr(
        "backend.main.process_notification",
        MockTask(),
    )

    response = client.post(
        "/notifications",
        json={
            "recipient": "user123",
            "message": "Your order has shipped!",
        },
    )

    assert response.status_code == 200

    data = response.json()

    assert data["recipient"] == "user123"
    assert data["message"] == "Your order has shipped!"
    assert data["status"] == "PENDING"
    assert "id" in data


def test_get_notifications():
    response = client.get("/notifications")

    assert response.status_code == 200
    assert isinstance(response.json(), list)


def test_process_notification_not_found(monkeypatch):
    from backend import tasks

    monkeypatch.setattr(
        tasks,
        "publish_notification_update",
        lambda notification: None,
    )

    result = tasks.process_notification.run(999999)

    assert result["status"] == "NOT_FOUND"


def test_process_notification_delivered(monkeypatch):
    from backend import tasks

    notification = type(
        "Notification",
        (),
        {
            "id": 1,
            "recipient": "user123",
            "message": "Test notification",
            "status": "PROCESSING",
            "retry_count": 2,
        },
    )()

    class MockQuery:
        def filter(self, *args):
            return self

        def first(self):
            return notification

    class MockDB:
        def query(self, *args):
            return MockQuery()

        def commit(self):
            pass

        def rollback(self):
            pass

        def close(self):
            pass

    monkeypatch.setattr(
        tasks,
        "SessionLocal",
        lambda: MockDB(),
    )

    monkeypatch.setattr(
        tasks,
        "publish_notification_update",
        lambda notification: None,
    )

    result = tasks.process_notification.run(1)

    assert result["status"] == "DELIVERED"
    assert notification.status == "DELIVERED"


def test_process_notification_retry(monkeypatch):
    from backend import tasks

    notification = type(
        "Notification",
        (),
        {
            "id": 1,
            "recipient": "user123",
            "message": "Test notification",
            "status": "PENDING",
            "retry_count": 0,
        },
    )()

    class MockQuery:
        def filter(self, *args):
            return self

        def first(self):
            return notification

    class MockDB:
        def query(self, *args):
            return MockQuery()

        def commit(self):
            pass

        def rollback(self):
            pass

        def close(self):
            pass

    monkeypatch.setattr(
        tasks,
        "SessionLocal",
        lambda: MockDB(),
    )

    monkeypatch.setattr(
        tasks,
        "publish_notification_update",
        lambda notification: None,
    )

    class RetryCalled(Exception):
        pass

    def mock_retry(*args, **kwargs):
        assert kwargs["countdown"] == 2
        raise RetryCalled()

    monkeypatch.setattr(
        tasks.process_notification,
        "retry",
        mock_retry,
    )

    try:
        tasks.process_notification.run(1)
    except RetryCalled:
        pass

    assert notification.retry_count == 1
    assert notification.status == "FAILED"










def test_process_notification_permanently_failed(monkeypatch):
    from backend import tasks

    notification = type(
        "Notification",
        (),
        {
            "id": 1,
            "recipient": "user123",
            "message": "Test notification",
            "status": "PROCESSING",
            "retry_count": 2,
        },
    )()

    class MockQuery:
        def filter(self, *args):
            return self

        def first(self):
            return notification

    class MockDB:
        def query(self, *args):
            return MockQuery()

        def commit(self):
            pass

        def rollback(self):
            pass

        def close(self):
            pass

    monkeypatch.setattr(
        tasks,
        "SessionLocal",
        lambda: MockDB(),
    )

    publish_calls = 0

    def mock_publish(notification):
        nonlocal publish_calls

        publish_calls += 1

        # Fail only once.
        if publish_calls == 2:
            raise Exception("Simulated permanent failure")

    monkeypatch.setattr(
        tasks,
        "publish_notification_update",
        mock_publish,
    )

    tasks.process_notification.push_request(retries=3)

    try:
        result = tasks.process_notification.run(1)
    finally:
        tasks.process_notification.pop_request()

    assert result["status"] == "FAILED"
    assert result["retry_count"] == 2
    assert notification.status == "FAILED"


def test_exponential_backoff(monkeypatch):
    from backend import tasks

    notification = type(
        "Notification",
        (),
        {
            "id": 1,
            "recipient": "user123",
            "message": "Test notification",
            "status": "PENDING",
            "retry_count": 0,
        },
    )()

    class MockQuery:
        def filter(self, *args):
            return self

        def first(self):
            return notification

    class MockDB:
        def query(self, *args):
            return MockQuery()

        def commit(self):
            pass

        def rollback(self):
            pass

        def close(self):
            pass

    monkeypatch.setattr(
        tasks,
        "SessionLocal",
        lambda: MockDB(),
    )

    monkeypatch.setattr(
        tasks,
        "publish_notification_update",
        lambda notification: None,
    )

    retry_delays = []

    def mock_retry(*args, **kwargs):
        retry_delays.append(kwargs["countdown"])
        raise Exception("Retry triggered")

    monkeypatch.setattr(
        tasks.process_notification,
        "retry",
        mock_retry,
    )

    for retry_count in range(3):
        notification.retry_count = 0

        tasks.process_notification.push_request(
            retries=retry_count
        )

        try:
            tasks.process_notification.run(1)
        except Exception:
            pass
        finally:
            tasks.process_notification.pop_request()

    assert retry_delays == [2, 4, 8]
