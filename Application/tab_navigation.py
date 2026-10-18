"""Safe tab navigation helpers. Author: Abdelhalim Talbi."""

def next_tab(current, count, reverse=False):
    if count <= 0: return -1
    return (current + (-1 if reverse else 1)) % count

def tab_at_position(position, count):
    """1-based tab position, no implicit wrapping."""
    return position-1 if 1 <= position <= count else -1

def closable_tab(index, home_index=0):
    return index >= 0 and index != home_index
