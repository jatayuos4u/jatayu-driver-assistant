"""Unprivileged service protocol prototype. NEVER runs package operations."""
from dataclasses import dataclass
from .backend_contract import RepairRequest, validate_request, Decision

MAX_FIELD = 128

@dataclass(frozen=True)
class ServiceReply:
    state: str
    message: str
    installation_enabled: bool = False

class DisabledRepairService:
    """Fail-closed contract for future D-Bus boundary; not a root daemon."""
    def get_capabilities(self):
        return {"protocol_version": 1, "service_mode": "simulation_only",
                "installation_enabled": False, "polkit_enabled": False}

    def request_installation(self, package, device_id, evidence_id):
        if any(not isinstance(x, str) or len(x) > MAX_FIELD
               for x in (package, device_id, evidence_id)):
            return ServiceReply("blocked", "Malformed or oversized request")
        result = validate_request(RepairRequest(package, device_id, evidence_id))
        if result.decision == Decision.BLOCKED:
            return ServiceReply("blocked", "; ".join(result.reasons))
        return ServiceReply("blocked", "Privileged installation not implemented")

    def request_reinstallation(self, package, device_id, evidence_id):
        return ServiceReply("blocked", "Reinstallation not implemented")
