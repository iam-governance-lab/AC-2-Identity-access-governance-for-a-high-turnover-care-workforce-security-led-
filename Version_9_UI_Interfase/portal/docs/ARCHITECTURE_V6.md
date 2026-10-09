# Version 6 integration architecture

```mermaid
flowchart TD
  A[Approved workforce record] --> B[JML and approved request]
  B --> C[Mock directory state]
  B --> D[Portal audit events]
  E[Entra OIDC optional] --> F[Portal server checks]
  C --> F
  F --> G[Synthetic resident access]
  F --> D
  D --> H[HMAC audit ledger]
  I[Controlled MFA events] --> J[MFA sequence detector]
  J --> H
  C --> K[Policy and threat checks]
  K --> L[Assurance view]
  H --> L
```

The trust boundary around the browser means it cannot assign itself a role or validate its own device. Server-side role, facility and assignment checks guard the protected pages. The workforce/automation boundary has one approved local state and a simulated directory state. The ledger boundary keeps its signing key and head checkpoint outside the SQLite record set. Authentic Entra, Graph mutation and device management need their own test tenant and separate acceptance evidence.
