# Agent Guidelines

This document outlines the rules and expectations for AI coding agents modifying the TravelHub repository.

## 1. Understand the Architecture
- Before making any code changes, agents must review `prd.md`, `guardrails.md`, and this file.
- Understand the 10 defined microservices and their specific boundaries. Do not blend responsibilities.

## 2. Keep Changes Small and Focused
- Submit focused, atomic changes.
- If a user requests a large feature, break it down into smaller, logical steps.

## 3. Preserve Service Boundaries
- Do not add features to a service that belong in another service's domain.
- Do not introduce direct database access between services. All inter-service communication must happen via APIs or events.

## 4. Do Not Modify Unrelated Services
- When tasked with updating one service, do not modify the code, configurations, or manifests of other services unless strictly necessary and explicitly justified.

## 5. Document Architectural Changes
- Any modification to service communication, data storage, or infrastructure must be accompanied by updates to the relevant `README.md` or architectural diagrams.

## 6. Run Relevant Tests
- Ensure that unit tests and relevant integration tests are run (and pass) after modifying a service.
- If new logic is added, add basic, readable tests for it.

## 7. Do Not Invent Dependencies
- Stick to the approved technology stack (FastAPI, React, Vite, shadcn/ui, Docker, Kubernetes).
- Do not introduce new frameworks, databases, or cloud services without explicit user approval.

## 8. Avoid Unnecessary Abstractions
- Write readable, straightforward human-written code.
- Do not introduce complex design patterns, generic repositories, or premature shared libraries. 
- The complexity of TravelHub belongs in the infrastructure, not the application logic.
- **Do not assume that more abstraction means better engineering. TravelHub intentionally uses simple application code so that infrastructure and distributed-system behavior remain the primary learning focus.**
- When there are two valid approaches, prefer the simpler one. Do not introduce complexity merely because it is technically possible.

## 9. Coding Style & Service Code Structure
- **Coding Style:** TravelHub code must be simple, readable, and human-written in style. Avoid over-engineered architectures, generic helper frameworks, unnecessary interfaces, deep inheritance, and clever one-liners. Optimize for readability ("Could another human engineer understand this quickly?").
- **Service Code:** Every microservice should initially be understandable from a small number of files (e.g., `app/main.py`, `app/routes.py`, `tests/`, `Dockerfile`, `requirements.txt`). Do not create elaborate Clean Architecture / Hexagonal Architecture / DDD structures unless explicitly required in later phases.

## 10. Respect Existing Conventions
- Follow the existing directory structure, naming conventions, and code style.
- Every service must maintain its own independent Dockerfile, Kubernetes namespace, Deployment, Service, and configuration.
- Container images must follow Semantic Versioning (`MAJOR.MINOR.PATCH`). Never use the `latest` tag in Kubernetes manifests.


## 11. Ask for Clarification
- If a user's request conflicts with the PRD, the guardrails, or these agent guidelines, **STOP** and ask for clarification before proceeding.
