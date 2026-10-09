"""Versioned connector boundary. No network transport or credentials embedded."""
from dataclasses import dataclass
from typing import Protocol

@dataclass(frozen=True)
class ProvisioningChange:
    idempotency_key: str
    employee_id: str
    operation: str
    role: str | None = None

@dataclass(frozen=True)
class ConnectorResult:
    state: str
    reference: str
    retryable: bool = False

class WorkforceConnector(Protocol):
    def apply(self, change: ProvisioningChange) -> ConnectorResult: ...
    def health(self) -> dict: ...

class IntegrationUnavailable(RuntimeError): pass

class UnconfiguredConnector:
    """Fail closed until an adapter with authentication, retry and reconciliation is supplied."""
    def __init__(self, provider): self.provider=provider
    def apply(self, change):
        raise IntegrationUnavailable(self.provider+' is not configured; no remote change was made.')
    def health(self): return {'provider':self.provider,'connected':False,'mode':'integration contract only'}

PROVIDERS=('Entra ID','Okta','HRIS','Payroll','Rostering','Microsoft 365','SCIM','SIEM','Email')

def connector(provider):
    if provider not in PROVIDERS:raise ValueError('Unknown provider')
    return UnconfiguredConnector(provider)
