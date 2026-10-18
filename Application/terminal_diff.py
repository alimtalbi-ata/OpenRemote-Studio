"""Pure incremental terminal frame planner. Author: Abdelhalim Talbi."""

def changed_rows(previous, current, *, max_changes=80):
    """Return changed row indices or None when a full repaint is safer.

    A shape change or a large repaint uses a complete document replacement.
    """
    if previous is None or len(previous)!=len(current):
        return None
    if not isinstance(max_changes,int) or max_changes<1:
        raise ValueError('max_changes must be positive')
    changes=[i for i,(old,new) in enumerate(zip(previous,current)) if old!=new]
    if len(changes)>max_changes or len(changes)>max(1,len(current)//2):
        return None
    return changes
