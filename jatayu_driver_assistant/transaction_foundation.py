"""v0.7 read-only, fail-closed driver transaction planning.

This module never executes APT, writes logs, or authorizes installation.
It validates pre-collected evidence and simulation results supplied by callers.
"""
from dataclasses import dataclass, asdict
from hashlib import sha256
import json
import re
from .backend_contract import RepairRequest, validate_request, Decision
from .recommendations import ALLOWED, PACKAGE_RE

_VERSION = 1
MAX_OPERATIONS = 100
_OPERATION = re.compile(r'^(Inst|Conf|Remv) ([a-z0-9][a-z0-9+.-]*)(?:\s|$)')

@dataclass(frozen=True)
class TransactionPlan:
    schema_version: int
    package: str
    device_id: str
    evidence_id: str
    state: str
    operations: tuple[str, ...]
    warnings: tuple[str, ...]
    fingerprint: str
    installation_enabled: bool = False

    def to_dict(self):
        result = asdict(self)
        result['operations'] = list(self.operations)
        result['warnings'] = list(self.warnings)
        return result


def _fingerprint(package, device_id, evidence_id, operations):
    payload = json.dumps([_VERSION, package, device_id, evidence_id, list(operations)],
                         separators=(',', ':'), ensure_ascii=True)
    return sha256(payload.encode('ascii')).hexdigest()


def create_plan(request, *, evidence_packages=(), simulation_ok=False, operations=()):
    """Produce an informational plan; no user-controlled command execution.

    An acceptable preview is still NOT authorization for installation.
    """
    if not isinstance(request, RepairRequest):
        raise ValueError('RepairRequest required')
    package = request.package if isinstance(request.package, str) else ''
    device = request.device_id if isinstance(request.device_id, str) else ''
    evidence = request.evidence_id if isinstance(request.evidence_id, str) else ''
    if any(len(v) > 128 for v in (package, device, evidence)):
        raise ValueError('Oversized request')
    validation = validate_request(request, evidence_packages=evidence_packages)
    warnings = list(validation.reasons) if validation.decision == Decision.BLOCKED else []
    clean = []
    if not simulation_ok:
        warnings.append('APT simulation did not succeed')
    if not isinstance(operations, (tuple, list)) or len(operations) > MAX_OPERATIONS:
        warnings.append('Missing, oversized, or truncated operation list')
    else:
        for op in operations:
            if not isinstance(op, str) or len(op) > 300 or '\n' in op or '\r' in op:
                warnings.append('Malformed operation record')
                break
            match = _OPERATION.match(op)
            if match is None:
                warnings.append('Unknown operation record')
                break
            kind, name = match.groups()
            if not PACKAGE_RE.fullmatch(name):
                warnings.append('Invalid package identifier')
                break
            if kind == 'Remv':
                warnings.append('Package removal detected')
            if kind == 'Inst' and name not in ALLOWED:
                warnings.append('Non-allowlisted dependency or package in simulation')
            clean.append(op)
    if not clean:
        warnings.append('No recognized transaction operations')
    if package not in [m.group(2) for op in clean if (m := _OPERATION.match(op)) and m.group(1) == 'Inst']:
        warnings.append('Requested package not listed for installation')
    if len(clean) >= MAX_OPERATIONS:
        warnings.append('Operation list at truncation boundary')
    if not warnings:
        warnings.append('Human review and privileged revalidation still required')
        state = 'review_required'
    else:
        state = 'blocked' if warnings != ['Human review and privileged revalidation still required'] else 'review_required'
    return TransactionPlan(_VERSION, package, device, evidence, state, tuple(clean),
                           tuple(warnings), _fingerprint(package, device, evidence, clean))


def audit_record(plan, outcome='preview_only'):
    """Return structured data for caller-controlled export; never write a file."""
    if not isinstance(plan, TransactionPlan) or outcome != 'preview_only':
        raise ValueError('Only preview-only audit records are supported')
    return {'event': 'transaction_preview', 'outcome': outcome, 'state': plan.state,
            'package': plan.package, 'fingerprint': plan.fingerprint,
            'installation_enabled': False}
