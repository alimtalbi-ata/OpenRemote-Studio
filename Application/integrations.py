"""Read-only discovery of optional administration tools. Author: Abdelhalim Talbi."""
from dataclasses import dataclass
import shutil

@dataclass(frozen=True)
class Tool:
    category: str
    name: str
    executables: tuple[str, ...]
    description: str

TOOLS = (
    Tool('Accès distant','OpenSSH',('ssh',),'Sessions SSH et tunnels'),
    Tool('Accès distant','SFTP',('sftp',),'Transferts sécurisés'),
    Tool('Accès distant','RDP Windows',('mstsc',),'Bureau distant Windows'),
    Tool('Accès distant','VNC Viewer',('vncviewer',),'Bureau distant VNC'),
    Tool('DevOps','Docker',('docker',),'Conteneurs et images'),
    Tool('DevOps','Kubernetes',('kubectl',),'Clusters et workloads'),
    Tool('DevOps','Helm',('helm',),'Packages Kubernetes'),
    Tool('DevOps','Terraform',('terraform',),'Infrastructure as Code'),
    Tool('DevOps','Ansible',('ansible',),'Automatisation'),
    Tool('DevOps','Git',('git',),'Versionnement'),
    Tool('Cloud','AWS CLI',('aws',),'Amazon Web Services'),
    Tool('Cloud','Azure CLI',('az',),'Microsoft Azure'),
    Tool('Cloud','Google Cloud CLI',('gcloud',),'Google Cloud'),
    Tool('Virtualisation','VMware govc',('govc',),'vSphere'),
    Tool('Virtualisation','Proxmox CLI',('pvesh',),'Proxmox VE (sur hôte)'),
    Tool('Réseau','Nmap',('nmap',),'Diagnostic de ports autorisé'),
    Tool('Réseau','Wireshark',('wireshark',),'Analyse de paquets'),
    Tool('Observabilité','Promtool',('promtool',),'Validation Prometheus'),
)

def discover(which=None):
    """Return installation status without executing any third-party binary."""
    which = which or shutil.which
    return [{'category': t.category, 'name': t.name, 'description': t.description,
             'available': bool(path := next((p for executable in t.executables if (p := which(executable))), None)),
             'path': path or ''} for t in TOOLS]

def filter_tools(query, items):
    q=query.strip().casefold()
    return [t for t in items if q in ' '.join((t['category'],t['name'],t['description'])).casefold()]
