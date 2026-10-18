import unittest
from terminal_output import readable_output, command_is_valid

class TestTerminalOutput(unittest.TestCase):
    def test_ansi_removed(self):self.assertEqual(readable_output(b"\x1b[31mERROR\x1b[0m"),"ERROR")
    def test_controls_removed(self):self.assertEqual(readable_output(b"a\x00b\x07c"),"abc")
    def test_unicode(self):self.assertEqual(readable_output("é".encode()),"é")
    def test_bounded(self):self.assertEqual(readable_output(b"123456",3),"456")
    def test_invalid_limit(self):
        with self.assertRaises(ValueError):readable_output(b"a",0)
    def test_command_valid(self):self.assertTrue(command_is_valid("ls -la"))
    def test_command_empty(self):self.assertFalse(command_is_valid("  "))
    def test_command_newline(self):self.assertFalse(command_is_valid("ls\nrm"))
    def test_command_long(self):self.assertFalse(command_is_valid("a"*4097))

if __name__=='__main__':unittest.main()
