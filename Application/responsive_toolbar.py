"""Pure layout policy for the main toolbar. Author: Abdelhalim Talbi."""

SECONDARY_ACTIONS = ('check_access', 'sftp', 'diagnostic', 'help')

def collapsed_actions(width):
    """Keep search and the two most frequent actions visible at narrow widths."""
    if isinstance(width, bool) or not isinstance(width, (int, float)):
        raise TypeError('width must be numeric')
    if width < 1050:
        return SECONDARY_ACTIONS
    if width < 1250:
        return ('diagnostic', 'help')
    return ()
