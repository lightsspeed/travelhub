# Not In Scope

TravelHub is intentionally designed as an educational tool for DevOps and distributed systems. To maintain focus on infrastructure and architectural patterns, the following features and complexities are explicitly **NOT** in scope:

## Business Logic & Features
- **Real Payment Processing:** We will not integrate with Stripe, PayPal, or any actual payment gateway. The `payment-service` will only simulate successful and failed transactions.
- **Real Hotel Provider Integrations:** No integration with real-world GDS (Global Distribution Systems), Expedia, or Booking.com APIs.
- **Real Flight Booking:** The platform is strictly limited to hotel and room bookings.
- **Real-World Inventory Synchronization:** We do not handle the complexities of syncing availability with external hotel property management systems.
- **Real Financial Transactions:** No ledger systems, currency conversion, or tax calculations.
- **Advanced Recommendation Engine:** We will not build complex machine learning models for personalized hotel recommendations (outside of basic AI assistant interactions).
- **Production-Grade Fraud Detection:** No rate limiting or behavioral analysis for fraud prevention.

## Architecture & Infrastructure
- **Enterprise Authentication:** We will not implement complex SSO, OAuth2 with external providers, or enterprise identity management (basic JWT authentication is sufficient).
- **Multi-Region Deployment:** The application will be deployed to a single region. Cross-region active-active or active-passive setups are out of scope.
- **Service Mesh:** We will not use Istio or Linkerd in the initial implementation phases to avoid unnecessary complexity, unless explicitly introduced for a specific learning module later.
- **Complex Shared Libraries:** We will avoid creating complex internal SDKs or shared libraries across microservices that might tightly couple them.

## Development & Code
- **Over-engineered Abstractions:** We will not use generic repository patterns, complex dependency injection frameworks, or excessive interfaces in the Python code. Keep application logic strictly simple.
