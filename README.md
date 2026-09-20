# TravelHub

## Overview
TravelHub is a simple travel and hotel booking platform built specifically as an educational project for learning DevOps, distributed systems, and microservices architecture. It simulates a realistic booking application to provide a robust testbed for Kubernetes orchestration, CI/CD, observability, and infrastructure-as-code.

While the application allows users to browse hotels, check availability, and make mock bookings, it is **not** intended to be a production commercial platform.

## Architecture Overview
TravelHub follows a strict microservices architecture. Every service is entirely decoupled, owning its own data, deployment lifecycle, and infrastructure manifests. The application is designed to prioritize infrastructure complexity and distributed system behaviors over complex internal business logic.

## Microservices
The system is composed of exactly 10 business microservices:
1. **user-service:** User account and profile management.
2. **hotel-service:** Hotel catalog and details.
3. **room-service:** Room types and pricing.
4. **search-service:** Unified search over hotels and rooms.
5. **availability-service:** Real-time room inventory management.
6. **booking-service:** Booking workflow orchestration.
7. **payment-service:** Mock financial transactions.
8. **review-service:** User reviews and ratings.
9. **notification-service:** Mock email/SMS notifications.
10. **ai-service:** AI travel assistant interactions.

## Technology Stack
- **Backend:** Python, FastAPI
- **Frontend:** React, TypeScript, Vite, shadcn/ui
- **Containerization:** Docker
- **Orchestration:** Kubernetes
- **Infrastructure as Code:** Terraform, AWS
- **GitOps & CI/CD:** Argo CD, GitHub Actions
- **Observability:** Prometheus, Grafana, Loki

## Repository Structure
```text
.
├── prd.md               # Product Requirements Document
├── not-in-scope.md      # Features/tech explicitly omitted
├── agents.md            # Guidelines for AI coding agents
├── guardrails.md        # Hard engineering constraints
├── README.md            # Project overview
├── frontend/            # React/Vite frontend
└── services/            # Backend microservices
    ├── user-service/    # User management service
    ├── hotel-service/   # Hotel catalog service
    └── room-service/    # Room catalog service
```

## Development Phases
1. **Phase 1 (Complete):** Frontend Foundation (React, Vite, shadcn/ui).
2. **Phase 2:** Scaffolding (Service skeletons, Dockerfiles, K8s manifests).
3. **Phase 3:** Core Logic (Synchronous APIs and simple business logic).
4. **Phase 4:** Infrastructure & CI/CD (Terraform, Argo CD, Actions).
5. **Phase 5:** Advanced Systems (Asynchronous messaging, caching).
6. **Phase 6:** Chaos & Resilience (Failure injection, observability deep-dive).

## Frontend Structure
The frontend is built with:
- React + TypeScript
- Vite
- shadcn/ui + Tailwind CSS

**Note:** Backend services are **not** implemented yet. The frontend currently uses mocked data and does not make real API calls.

### Available Routes
- `/` - Home Page
- `/search` - Search Results
- `/hotels/:id` - Hotel Details
- `/bookings` - My Bookings
- `/assistant` - AI Travel Assistant

### Local Development
To run the frontend locally:
```bash
cd frontend
npm install
npm run dev
```

## Phase 2: First Three Microservices

Phase 2 establishes the canonical backend service pattern using FastAPI for the first three microservices:
1. **`user-service`** (Port: `8001`): Manages user accounts and profiles.
2. **`hotel-service`** (Port: `8002`): Manages the hotel catalog and details.
3. **`room-service`** (Port: `8003`): Manages room listings, pricing, and hotel associations.

> **Note on Architecture:**
> - Data is currently held strictly **in memory** (no external database or cache).
> - There is **no inter-service communication** in this phase.
> - **Kubernetes has not yet been introduced**; manifests will follow in a subsequent phase after service review.

### Available Endpoints

#### `user-service` (`http://localhost:8001`)
- `GET /health` - Service health status
- `GET /ready` - Service readiness status
- `GET /metrics` - Prometheus metrics (`travelhub_service_up`)
- `GET /users` - List all users
- `GET /users/{user_id}` - Retrieve a single user by ID
- `POST /users` - Create a new user (`{"name": "...", "email": "..."}`)

#### `hotel-service` (`http://localhost:8002`)
- `GET /health` - Service health status
- `GET /ready` - Service readiness status
- `GET /metrics` - Prometheus metrics (`travelhub_service_up`)
- `GET /hotels` - List all hotels
- `GET /hotels/{hotel_id}` - Retrieve a single hotel by ID
- `POST /hotels` - Create a new hotel (`{"name": "...", "city": "...", "country": "...", "description": "...", "rating": 4.5}`)

#### `room-service` (`http://localhost:8003`)
- `GET /health` - Service health status
- `GET /ready` - Service readiness status
- `GET /metrics` - Prometheus metrics (`travelhub_service_up`)
- `GET /rooms` - List all rooms
- `GET /rooms/{room_id}` - Retrieve a single room by ID
- `GET /hotels/{hotel_id}/rooms` - List all rooms associated with a specific hotel
- `POST /rooms` - Create a new room (`{"hotel_id": 1, "room_type": "...", "capacity": 2, "price_per_night": 150.0, "currency": "USD", "available": true}`)

### Running Microservices Locally

Each service can be run independently using Uvicorn:

```bash
# user-service
cd services/user-service
uvicorn app.main:app --reload --port 8001

# hotel-service
cd services/hotel-service
uvicorn app.main:app --reload --port 8002

# room-service
cd services/room-service
uvicorn app.main:app --reload --port 8003
```

### Running Tests

Run pytest independently in each service directory:

```bash
cd services/user-service && pytest
cd services/hotel-service && pytest
cd services/room-service && pytest
```

### Building Docker Images & Versioning

All TravelHub container images follow strict **Semantic Versioning** (`MAJOR.MINOR.PATCH`).
The `latest` tag is prohibited in Kubernetes deployments.

- **MAJOR:** Breaking API or service contract changes.
- **MINOR:** Backward-compatible new functionality.
- **PATCH:** Backward-compatible bug fixes.

Services are independently versioned and do not need to increment together.

To build the initial `1.0.0` images locally:

```bash
docker build -t travelhub/user-service:1.0.0 ./services/user-service
docker build -t travelhub/hotel-service:1.0.0 ./services/hotel-service
docker build -t travelhub/room-service:1.0.0 ./services/room-service
```


