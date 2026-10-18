import unittest
from gateways import ssh_jump_args
from ssh_route_client import RoutedSshClient

class Channel:
    def __init__(self):self.closed=False
    def close(self):self.closed=True
class Transport:
    def __init__(self):self.channels=[]
    def is_active(self):return True
    def open_channel(self,kind,dest,origin,timeout):
        assert kind=='direct-tcpip';c=Channel();self.channels.append((dest,c));return c
class Client:
    instances=[]
    def __init__(self):self.transport=Transport();self.closed=False;self.args=None;Client.instances.append(self)
    def load_system_host_keys(self):pass
    def set_missing_host_key_policy(self,x):pass
    def connect(self,**kwargs):self.args=kwargs
    def get_transport(self):return self.transport
    def open_sftp(self):return 'SFTP'
    def close(self):self.closed=True
class Fake:
    SSHClient=Client
    RejectPolicy=object
class Tests(unittest.TestCase):
    def setUp(self):Client.instances=[]
    def route(self):return {'mode':'ssh_jump','jump_host':'jump1','jump_user':'admin','jump_port':'22','jump_chain':'ops@jump2:2222,jump3:22'}
    def test_external_multi_hop(self):self.assertEqual(ssh_jump_args(self.route()),['-J','admin@jump1,ops@jump2:2222,jump3'])
    def test_external_direct(self):self.assertEqual(ssh_jump_args(None),[])
    def test_integrated_hops(self):
        c=RoutedSshClient({'host':'target','port':22,'user':'root'},self.route(),Fake).connect()
        self.assertEqual(len(c.clients),4)
        self.assertEqual([x.args['hostname'] for x in Client.instances],['jump1','jump2','jump3','target'])
        self.assertEqual(c.open_sftp(),'SFTP')
        self.assertEqual([x.args.get('sock') is not None for x in Client.instances],[False,True,True,True])
        c.close();self.assertTrue(all(x.closed for x in Client.instances))
    def test_direct(self):
        c=RoutedSshClient({'host':'target','port':22},None,Fake).connect()
        self.assertEqual(len(c.clients),1);c.close()
    def test_route_rejected(self):
        with self.assertRaises(ValueError):RoutedSshClient({'host':'target'}, {'mode':'rd_gateway','gateway_host':'gw'},Fake)
    def test_double_connect(self):
        c=RoutedSshClient({'host':'target'},None,Fake).connect()
        with self.assertRaises(RuntimeError):c.connect()
        c.close()
    def test_invalid_host(self):
        with self.assertRaises(ValueError):RoutedSshClient({'host':'-bad'},None,Fake)

if __name__=='__main__':unittest.main()
