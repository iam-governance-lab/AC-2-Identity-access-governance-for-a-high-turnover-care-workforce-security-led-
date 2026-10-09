> Historical v7/v8 document. For current behavior, use Sunhaven_v9_Final_Report.md and Sunhaven_v9_Operator_Handbook.md in this directory.

# Research informing version 7

Official documentation consulted on 24 September 2026. Implementations are local educational equivalents, not Microsoft product functionality or licence entitlements. No future vendor release is predicted.

1. Microsoft Entra ID Governance: https://learn.microsoft.com/en-us/entra/id-governance/identity-governance-overview
   Informed request/approval, expiry and temporary access.
2. Secure governance practices: https://learn.microsoft.com/en-us/entra/id-governance/best-practices-secure-id-governance
   Informed limited duration and explicit role boundaries.
3. Authentication strengths: https://learn.microsoft.com/en-us/entra/identity/authentication/concept-authentication-strengths
   Informed the phishing-resistant authentication what-if exercise; actual enforcement needs an identity provider.
4. Microsoft Entra Agent ID: https://learn.microsoft.com/en-us/entra/agent-id/what-is-microsoft-entra-agent-id
   Informed explicit nonhuman identity ownership and scoped governance. This registry does not create Entra objects.
5. Agent governance: https://learn.microsoft.com/en-us/entra/id-governance/agent-id-governance-overview
   Informed owner lifecycle and expiry checks.

Pages may change. Recheck licences and rollout states before implementing tenant connectors. References explain design choices and do not certify this software.
