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
└── (Future Service Directories)
```

## Development Phases
1. **Phase 1:** Foundation (Documentation, Requirements, Guardrails)
2. **Phase 2:** Scaffolding (Service skeletons, Dockerfiles, K8s manifests)
3. **Phase 3:** Core Logic (Synchronous APIs and simple business logic)
4. **Phase 4:** Frontend (React UI and Gateway integration)
5. **Phase 5:** Infrastructure & CI/CD (Terraform, Argo CD, Actions)
6. **Phase 6:** Advanced Systems (Asynchronous messaging, caching)
7. **Phase 7:** Chaos & Resilience (Failure injection, observability deep-dive)

## Local Development
Local development will utilize Docker and local Kubernetes clusters (e.g., minikube or kind) to simulate the distributed environment without relying on unnecessary cloud dependencies. Services can be run independently or orchestrated together using local manifests. 
*(Detailed local setup instructions to follow in later phases).*
