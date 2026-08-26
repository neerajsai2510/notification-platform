# Notification Platform

A scalable asynchronous notification platform built with FastAPI, PostgreSQL, Redis, Celery, React, WebSockets, and Docker Compose.

The system accepts notification requests through a REST API, stores them in PostgreSQL, processes delivery asynchronously using Celery, retries failed deliveries using exponential backoff, and streams status updates to the React dashboard through Redis Pub/Sub and WebSockets.

---

## Architecture

```text
                         ┌──────────────────────┐
                         │      React UI        │
                         │   Nginx :5173        │
                         └──────────┬───────────┘
                                    │
                         REST / WebSocket
                                    │
                                    ▼
                         ┌──────────────────────┐
                         │       FastAPI        │
                         │       :8000          │
                         └───────┬───────┬──────┘
                                 │       │
                            SQLAlchemy   │
                                 │       │
                                 ▼       ▼
                         ┌──────────┐  ┌──────────┐
                         │PostgreSQL│  │  Redis   │
                         │  :5432   │  │  :6379   │
                         └──────────┘  └────┬─────┘
                                           │
                              Celery Broker │
                                           │
                                           ▼
                                  ┌────────────────┐
                                  │ Celery Worker  │
                                  │                │
                                  │ Async Delivery │
                                  └───────┬────────┘
                                          │
                                   Redis Pub/Sub
                                          │
                                          ▼
                                  ┌────────────────┐
                                  │    FastAPI     │
                                  │ Redis Listener │
                                  └───────┬────────┘
                                          │
                                      WebSocket
                                          │
                                          ▼
                                     React UI
```

## Notification Lifecycle

```text
PENDING
   │
   ▼
PROCESSING
   │
   ├─────────────── Failure
   │
   ▼
FAILED
   │
   ▼
RETRY
   │
   ├── retry 1 → 2 seconds
   ├── retry 2 → 4 seconds
   └── retry 3 → 8 seconds
   │
   ▼
PROCESSING
   │
   ▼
DELIVERED

If the maximum retry count is reached:

FAILED → PERMANENT FAILED
```

## Features

- REST API using FastAPI
- PostgreSQL persistence with SQLAlchemy
- Asynchronous processing using Celery
- Redis message broker
- Retry mechanism with exponential backoff
- Permanent FAILED state after maximum retries
- Retry count tracking
- Redis Pub/Sub for status events
- WebSocket-based real-time dashboard updates
- React frontend
- API validation and error handling
- Docker Compose deployment
- Automated tests with pytest


## Tech Stack

### Backend
- Python
- FastAPI
- SQLAlchemy
- PostgreSQL

### Asynchronous Processing
- Celery
- Redis

### Frontend
- React
- Vite
- Tailwind CSS
- WebSockets

### Infrastructure
- Docker
- Docker Compose

### Testing
- pytest
- HTTPX
notification-platform/
│
├── backend/
│   ├── main.py
│   ├── models.py
│   ├── database.py
│   ├── celery_app.py
│   ├── tasks.py
│   ├── requirements.txt
│   └── Dockerfile
│
├── frontend/
│   ├── src/
│   │   ├── App.jsx
│   │   └── ...
│   ├── package.json
│   ├── Dockerfile
│   └── nginx.conf
│
├── tests/
│   └── test_notifications.py
│
├── docker-compose.yml
├── .dockerignore
├── .gitignore
├── .env.example
└── README.md
## API

### Create Notification

POST /notifications
{
  "recipient": "user123",
  "message": "Your order has shipped!"
}
### Get Notifications

GET /notifications
### WebSocket

/ws/notifications
## Running with Docker

Clone the repository:

git clone <repository-url>

cd notification-platform

Create the environment file:

cp .env.example .env

Start the application:

docker compose up --build
Frontend:
http://localhost:5173

FastAPI:
http://localhost:8000

Swagger:
http://localhost:8000/docs
docker compose down
## Testing

Run:

pytest -v tests/
The test suite covers:

- API endpoints
- Request validation
- Notification creation
- Notification retrieval
- Celery processing
- Retry behavior
- Permanent failure handling
- Exponential backoff
Celery separates notification processing from the API request lifecycle.
This prevents long-running delivery operations from blocking incoming
requests.
Redis is used as the Celery message broker and as the Pub/Sub mechanism
for real-time notification status events.
PostgreSQL provides durable storage for notifications and their processing
state.
WebSockets allow the dashboard to receive status updates immediately
without continuously polling the backend.
Docker Compose provides reproducible local infrastructure for the complete
multi-service application.
## Future Improvements

- Integration with real SMS/email providers
- Authentication and authorization
- Rate limiting
- Dead-letter queues
- Structured logging
- Metrics and monitoring
- Distributed tracing
- Provider-specific retry policies
- Production deployment
