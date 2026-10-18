import unittest
from jump_chain_editor import validate_hop,encode_chain,decode_chain,insert_hop,move_hop,remove_hop
class JumpChainEditorTests(unittest.TestCase):
    def test_roundtrip(self):
        hops=[validate_hop('jump2',2222,'ops'),validate_hop('jump3',22,'')]
        self.assertEqual(decode_chain(encode_chain(hops)),hops)
    def test_insert(self):
        self.assertEqual(insert_hop([],validate_hop('jump2'))[0]['host'],'jump2')
    def test_move(self):
        hops=decode_chain('a,b')
        self.assertEqual(move_hop(hops,0,1)[0]['host'],'b')
    def test_remove(self):
        self.assertEqual(len(remove_hop(decode_chain('a,b'),0)),1)
    def test_duplicate(self):
        with self.assertRaises(ValueError):encode_chain(decode_chain('a')+decode_chain('A'))
    def test_capacity(self):
        with self.assertRaises(ValueError):encode_chain(decode_chain('a,b,c')+decode_chain('d'))
    def test_reject_unsafe_user(self):
        with self.assertRaises(ValueError):validate_hop('jump',22,'-bad')
    def test_reject_ipv6_ambiguous(self):
        with self.assertRaises(ValueError):validate_hop('2001:db8::1')
    def test_no_mutation(self):
        hops=decode_chain('a,b');move_hop(hops,0,1);self.assertEqual(hops[0]['host'],'a')
if __name__=='__main__':unittest.main()
