"""Machine-checkable capability acceptance registry for OpenRemote Studio.

This is a planning/verification gate, not proof that features exist.
Author: Abdelhalim Talbi.
"""
from dataclasses import dataclass
from enum import Enum


class Status(str, Enum):
    IMPLEMENTED = "IMPLEMENTED"
    PARTIAL = "PARTIAL"
    NOT_IMPLEMENTED = "NOT_IMPLEMENTED"
    UNVERIFIED = "UNVERIFIED"


@dataclass(frozen=True)
class Capability:
    product: str
    use_case: str
    priority: str
    status: Status = Status.UNVERIFIED
    evidence: tuple[str, ...] = ()


CAPABILITIES = (
    Capability("MobaXterm", "ssh-rdp-sftp-terminal-tunnels", "P0"),
    Capability("Royal TS", "centralized-profiles-rdp-ssh-vnc", "P0"),
    Capability("Devolutions RDM", "credential-vault-audit", "P0"),
    Capability("mRemoteNG", "multi-protocol-tabs-groups", "P0"),
    Capability("Termius", "ssh-hosts-keys-snippets", "P1"),
    Capability("Windows Admin Center", "winrm-powershell-services", "P1"),
    Capability("Ansible", "inventory-playbooks-check-mode", "P1"),
    Capability("Zabbix", "monitoring-alerts", "P1"),
    Capability("Grafana", "dashboards-observability", "P1"),
    Capability("NetBox", "ipam-dcim-inventory", "P1"),
    Capability("Wireshark", "pcap-network-diagnostics", "P2"),
    Capability("HashiCorp Vault", "dynamic-secrets-rotation", "P0"),
)


def validate_registry(items=CAPABILITIES):
    names = [item.product for item in items]
    if len(names) != 12 or len(set(names)) != 12:
        raise ValueError("Expected exactly twelve distinct reference products")
    for item in items:
        if item.priority not in {"P0", "P1", "P2"}:
            raise ValueError("Unknown priority: " + item.product)
        if item.status == Status.IMPLEMENTED and not item.evidence:
            raise ValueError("Implemented feature requires evidence: " + item.product)
        if not item.use_case.strip():
            raise ValueError("Empty use case: " + item.product)
    return True
