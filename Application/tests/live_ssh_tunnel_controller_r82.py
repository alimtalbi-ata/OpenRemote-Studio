"""R82 real OpenSSH key-only tunnel controller acceptance, disposable loopback CI.
Public host key comes from disposable Docker fixture only, never production.
Author: Abdelhalim Talbi.
"""
import os
import socket
import tempfile
import time
from pathlib import Path
import paramiko
from live_ssh_hostkey_r77 import fixture_known_hosts
from live_ssh_tunnel_r78 import free_port
from ssh_transport import SSHSettings
from tunnel_controller import TunnelController


def wait_for(predicate, seconds=15):
    deadline=time.monotonic()+seconds
    while time.monotonic()<deadline:
        if predicate():return True
        time.sleep(.05)
    return predicate()


def run():
    host=os.environ.get('SFTP_TEST_HOST','127.0.0.1')
    port=int(os.environ.get('SFTP_TEST_PORT','2222'))
    key=os.environ['R82_SSH_KEY_PATH']
    if host!='127.0.0.1' or not Path(key).is_file():
        raise RuntimeError('R82 only accepts disposable loopback SSH fixture')
    with tempfile.TemporaryDirectory(prefix='ors-r82-') as directory:
        trusted=fixture_known_hosts(host,port,Path(directory)/'known_hosts')
        settings=SSHSettings(host,'tester',port=port,timeout=10,known_hosts=str(trusted))
        local=free_port()
        controller=TunnelController()
        controller.start(settings,key_filename=key,local_port=local,
                         target_host='127.0.0.1',target_port=22)
        assert wait_for(lambda:controller.poll().phase in ('active','failed'))
        assert controller.poll().phase=='active','key-only pinned SSH failed'
        with socket.create_connection(('127.0.0.1',local),timeout=5) as peer:
            peer.settimeout(5)
            assert peer.recv(64).startswith(b'SSH-2.0-'), 'real forwarding failed'
            controller.stop()
            assert wait_for(controller.is_shutdown_complete), 'tunnel did not drain'
            assert controller.poll().phase=='closed'
        with socket.socket() as probe:
            probe.setsockopt(socket.SOL_SOCKET,socket.SO_REUSEADDR,1)
            probe.bind(('127.0.0.1',local))
        wrong=Path(directory)/'wrong_hosts'
        hostkeys=paramiko.HostKeys()
        hostkeys.add(f'[{host}]:{port}', 'ssh-rsa', paramiko.RSAKey.generate(2048))
        hostkeys.save(str(wrong))
        rejected=TunnelController()
        rejected.start(SSHSettings(host,'tester',port=port,timeout=10,known_hosts=str(wrong)),
                       key_filename=key,local_port=free_port(),
                       target_host='127.0.0.1',target_port=22)
        assert wait_for(rejected.is_shutdown_complete), 'negative pin check timed out'
        assert rejected.poll().phase=='failed', 'wrong host key accepted'
    print('LIVE_OPENSSH_R82_PASS: pinned key-only forwarding, revocation, wrong pin denied')


if __name__=='__main__':run()
