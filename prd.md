# Product Requirements Document: TravelHub

## 1. Product Vision
TravelHub is a straightforward travel and hotel booking platform designed primarily as an educational testbed for DevOps, distributed systems, and microservices architecture. It simulates a real-world travel booking experience to provide a robust environment for learning and experimenting with modern infrastructure.

## 2. Problem Statement
Learning distributed systems, Kubernetes, CI/CD, observability, and microservices requires a realistic, multi-service application. Simple "Hello World" apps or single-service monoliths do not adequately demonstrate the complexities of service-to-service communication, distributed data ownership, or infrastructure-as-code.

## 3. Target Users
- **End-Users (Simulated):** People browsing hotels, checking availability, and booking rooms.
- **Engineers/Learners (Actual):** Developers, DevOps engineers, and architects using this platform to practice deployment, scaling, observability, and distributed system patterns.

## 4. Product Goals
- Provide a functioning, multi-service application that realistically mimics a travel booking platform.
- Serve as a foundation for exploring Kubernetes orchestration, GitOps, CI/CD, and infrastructure automation.
- Demonstrate proper microservice boundaries and independent deployability.
- Keep application code simple so the focus remains on infrastructure and distributed behaviors.

## 5. Core User Journeys
- **Discovery:** A user browses and searches for hotels in specific locations.
- **Selection:** A user views hotel details, available rooms, and pricing.
- **Booking:** A user selects a room, creates a booking, and completes a mock payment.
- **Post-Booking:** A user views their booking status, receives notifications, and can leave a review after their stay.
- **Support:** A user interacts with an AI travel assistant for help and recommendations.

## 6. Functional Requirements
- Browse and search hotels by criteria.
- View detailed information about specific hotels.
- Check real-time room availability and pricing.
- Create and manage room bookings.
- Process mock payments for bookings.
- View booking status and history.
- Submit and view hotel reviews.
- Send and receive booking-related notifications.
- Chat with an AI travel assistant.

## 7. The 10 Services and Their Responsibilities
1. **user-service:** Manages user accounts, profiles, and authentication.
2. **hotel-service:** Manages hotel catalog, descriptions, and static details.
3. **room-service:** Manages room types, pricing, and hotel-room associations.
4. **search-service:** Provides a unified search API over hotels and rooms.
5. **availability-service:** Tracks and manages real-time room inventory and dates.
6. **booking-service:** Orchestrates the booking workflow and manages booking states.
7. **payment-service:** Handles mock financial transactions for bookings.
8. **review-service:** Manages user reviews and ratings for hotels.
9. **notification-service:** Handles asynchronous communication (e.g., email/SMS simulation) with users.
10. **ai-service:** Powers the AI travel assistant and chatbot interactions.

## 8. Service Boundaries
- Services must operate independently and communicate only via defined APIs or events.
- No shared databases; each service owns and manages its own data store.
- Services should not bypass another service's API (e.g., `booking-service` must call `payment-service` via API, not update the payment database directly).

## 9. High-Level Architecture
- **Frontend:** A React/Vite SPA serving as the user interface.
- **API Gateway:** Routes incoming frontend requests to the appropriate backend microservices.
- **Backend Services:** 10 FastAPI Python microservices handling specific business domains.
- **Infrastructure:** Dockerized services orchestrated by Kubernetes, provisioned via Terraform on AWS.

## 10. Service Communication Expectations
- **Synchronous:** REST/HTTP for immediate responses (e.g., frontend querying `hotel-service`).
- **Asynchronous (Future Phase):** Event-driven communication via Kafka/Redis for decoupled workflows (e.g., `booking-service` notifying `notification-service`).

## 11. Data Ownership Principles
- Each microservice is the sole source of truth for its domain data.
- Data required by multiple services must be fetched via API calls or replicated via asynchronous events.
- Direct cross-service database access is strictly prohibited.

## 12. Frontend Requirements
- Built with React, TypeScript, and Vite.
- Styled using Tailwind CSS and shadcn/ui.
- Provides a clean, modern, and responsive user interface for all core journeys.
- Communicates solely through the API Gateway.

## 13. AI Assistant Requirements
- Integrated into the frontend interface.
- Powered by the `ai-service`.
- Capable of answering basic travel queries, recommending hotels based on mock data, and guiding users through the booking process.

## 14. Observability Requirements
- Comprehensive logging, metrics, and distributed tracing.
- Core stack: Prometheus (metrics), Grafana (dashboards), Loki (logs).
- Every service must expose `/health`, `/ready`, and `/metrics` endpoints.

## 15. Non-Functional Requirements
- **Simplicity:** Application code must prioritize readability over premature optimization or complex abstractions.
- **Deployability:** Every service must be independently deployable with its own Kubernetes manifests.
- **Statelessness:** Services should be designed as stateless applications to allow horizontal scaling.

## 16. Development Phases
- **Phase 1 (Foundation):** Repository setup, architectural documentation, and guardrails.
- **Phase 2 (Scaffolding):** Basic implementation of the 10 services with Dockerfiles and Kubernetes manifests.
- **Phase 3 (Core Logic):** Implementation of synchronous business logic and API endpoints.
- **Phase 4 (Frontend):** UI development and integration.
- **Phase 5 (Infrastructure & CI/CD):** Terraform, Argo CD, and GitHub Actions setup.
- **Phase 6 (Advanced Systems):** Introduction of asynchronous messaging (Kafka), caching (Redis), and observability.
- **Phase 7 (Chaos & Resilience):** Failure injection and reliability testing.

## 17. Definition of Done
- All 10 services are implemented, containerized, and deployed to Kubernetes.
- Services communicate successfully to complete the core user journeys.
- Frontend is fully functional and integrated.
- CI/CD pipelines are active.
- Observability stack is collecting metrics and logs.
- Code adheres strictly to the architectural principles and guardrails.
