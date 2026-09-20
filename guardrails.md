# Engineering Guardrails

These are the hard engineering constraints for the TravelHub project. They must not be violated.

## 1. Microservice Count & Scope
- There must be **exactly 10 business microservices**: `user-service`, `hotel-service`, `room-service`, `search-service`, `availability-service`, `booking-service`, `payment-service`, `review-service`, `notification-service`, `ai-service`.
- Do not create new business microservices or consolidate these into fewer services.

## 2. Independent Deployability
- **Every service** must have its own `Dockerfile`.
- **Every service** must be deployed into its own Kubernetes namespace.
- **Every service** must have its own independent Kubernetes Deployment and Service manifests.
- **No shared monolithic manifests:** Do not create a single Kubernetes YAML file containing all services. Each service owns its manifests.
- Services must remain independently deployable at all times.

## 3. Data Isolation
- **No shared databases:** Each microservice must have its own logical (or physical) database.
- **No direct database access:** No service may connect directly to another service's database under any circumstances.

## 4. API & Event Boundaries
- No service may bypass another service's defined API or event boundary to read or mutate data.

## 5. Application Simplicity (Hard Constraint)
- Application code must remain explicitly simple and straightforward.
- **Do not assume that more abstraction means better engineering. TravelHub intentionally uses simple application code so that infrastructure and distributed-system behavior remain the primary learning focus.**
- No premature generic repositories, excessive interfaces, or complex dependency injection frameworks.
- No premature shared libraries across services; slight code duplication is preferred over tight coupling.
- **Coding Style:** Code must be simple, readable, and human-written. Avoid deep inheritance, generic helper frameworks, clever one-liners, and premature optimization. When there are two valid approaches, prefer the simpler one.
- **Service Code Structure:** Every microservice should initially be understandable from a small number of files (e.g., `app/main.py`, `app/routes.py`, `tests/`, `Dockerfile`). Do not create elaborate Clean Architecture / Hexagonal Architecture / DDD structures.

## 6. Infrastructure & Tooling Constraints
- **Initial Implementation:** No premature usage of Kafka, Redis, or advanced cloud dependencies (e.g., AWS SQS, DynamoDB) during local development or initial phases. Stick to basic REST over HTTP first.
- **Service Mesh:** Do not introduce a service mesh (Istio/Linkerd) initially.
- **No real payments:** The system must under no circumstances integrate with real payment processors.

## 7. Security & Configuration
- **No committed secrets:** Never commit passwords, API keys, or tokens to the repository.
- **No hardcoded configuration:** Environment-specific configuration (database URLs, hostnames) must be injected via environment variables or ConfigMaps, not hardcoded in the application.

## 8. Observability Baselines
- Every service must implement the following standard endpoints:
  - `/health` (liveness)
  - `/ready` (readiness)
  - `/metrics` (Prometheus metrics)
