"""Security boundary design for a future root service; NO privileged operations.

This module is deliberately unprivileged. A future system D-Bus service must
independently obtain fresh hardware evidence, verify authenticated repository
metadata, coordinate APT locks, and re-simulate at execution time.
"""
from dataclasses import dataclass, asdict
from enum import Enum
import re
from .recommendations import ALLOWED, assess_transaction

class Decision(str, Enum):
    BLOCKED = 'blocked'
    REVIEW = 'review_required'

@dataclass(frozen=True)
class RepairRequest:
    package: str
    device_id: str
    evidence_id: str

@dataclass(frozen=True)
class ReviewResult:
    decision: Decision
    reasons: tuple[str, ...]
    installation_enabled: bool = False

_DEVICE = re.compile(r'^[0-9a-f]{4}:[0-9a-f]{2}:[0-9a-f]{2}\.[0-7]$', re.I)
_EVIDENCE = re.compile(r'^[a-f0-9]{64}$')

def validate_request(request, *, evidence_packages=()):
    """Validate input shape; this does not grant installation authorization."""
    if not isinstance(request, RepairRequest):
        return ReviewResult(Decision.BLOCKED, ('Invalid request type',))
    if request.package not in ALLOWED:
        return ReviewResult(Decision.BLOCKED, ('Package not allowlisted',))
    if not isinstance(request.device_id, str) or not _DEVICE.fullmatch(request.device_id):
        return ReviewResult(Decision.BLOCKED, ('Invalid PCI device identifier',))
    if not isinstance(request.evidence_id, str) or not _EVIDENCE.fullmatch(request.evidence_id):
        return ReviewResult(Decision.BLOCKED, ('Invalid evidence fingerprint',))
    if request.package not in evidence_packages:
        return ReviewResult(Decision.BLOCKED, ('No matching diagnostic evidence',))
    return ReviewResult(Decision.REVIEW, ('Evidence must be revalidated by a privileged service',))

def review_simulation(request, changes, *, evidence_packages=()):
    validation = validate_request(request, evidence_packages=evidence_packages)
    if validation.decision == Decision.BLOCKED:
        return validation
    ok, reasons = assess_transaction(changes, request.package)
    if not ok:
        return ReviewResult(Decision.BLOCKED, tuple(reasons))
    return ReviewResult(Decision.REVIEW, ('APT simulation is not an execution authorization',))

def capabilities():
    return {'protocol_version': 1, 'polkit_available': False,
            'privileged_service_available': False, 'installation_enabled': False,
            'description': 'Read-only backend request validation and simulation review'}
