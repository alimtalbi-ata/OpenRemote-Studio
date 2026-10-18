"""Map common Qt key events to VT input bytes. Author: Abdelhalim Talbi."""
# Numeric Qt key constants keep this mapper testable without a GUI runtime.
class Qt:
    NoModifier=0;ControlModifier=0x04000000;AltModifier=0x08000000
    Key_Up=0x01000013;Key_Down=0x01000015;Key_Right=0x01000014;Key_Left=0x01000012
    Key_Home=0x01000010;Key_End=0x01000011;Key_Insert=0x01000006;Key_Delete=0x01000007
    Key_PageUp=0x01000016;Key_PageDown=0x01000017;Key_Backspace=0x01000003
    Key_Return=0x01000004;Key_Enter=0x01000005;Key_Tab=0x01000001;Key_Backtab=0x01000002;Key_Escape=0x01000000
    Key_F1=0x01000030;Key_F4=0x01000033;Key_F5=0x01000034;Key_F12=0x0100003b
    Key_A=65;Key_C=67;Key_Z=90;Key_Shift=0x01000020

def encode_key(key, modifiers=Qt.NoModifier, text='', application_cursor=False):
    """Return VT sequence, or None for an unhandled key."""
    special={Qt.Key_Up:'\x1b[A',Qt.Key_Down:'\x1b[B',Qt.Key_Right:'\x1b[C',Qt.Key_Left:'\x1b[D',
             Qt.Key_Home:'\x1b[H',Qt.Key_End:'\x1b[F',Qt.Key_Insert:'\x1b[2~',Qt.Key_Delete:'\x1b[3~',
             Qt.Key_PageUp:'\x1b[5~',Qt.Key_PageDown:'\x1b[6~',Qt.Key_Backspace:'\x7f',
             Qt.Key_Return:'\r',Qt.Key_Enter:'\r',Qt.Key_Tab:'\t',Qt.Key_Backtab:'\x1b[Z',Qt.Key_Escape:'\x1b'}
    if key in special:
        if application_cursor and key in (Qt.Key_Up,Qt.Key_Down,Qt.Key_Right,Qt.Key_Left,Qt.Key_Home,Qt.Key_End):
            return '\x1bO'+{Qt.Key_Up:'A',Qt.Key_Down:'B',Qt.Key_Right:'C',Qt.Key_Left:'D',Qt.Key_Home:'H',Qt.Key_End:'F'}[key]
        return special[key]
    if Qt.Key_F1<=key<=Qt.Key_F4:return ('\x1bOP','\x1bOQ','\x1bOR','\x1bOS')[key-Qt.Key_F1]
    if Qt.Key_F5<=key<=Qt.Key_F12:return '\x1b['+('15','17','18','19','20','21','23','24')[key-Qt.Key_F5]+'~'
    if modifiers & Qt.ControlModifier and Qt.Key_A<=key<=Qt.Key_Z:return chr(key-Qt.Key_A+1)
    if modifiers & Qt.AltModifier and text and text.isprintable():return '\x1b'+text
    if text and text.isprintable():return text
    return None
