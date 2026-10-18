"""Pure geometry checks for Windows GUI QA; author Abdelhalim Talbi."""

def rectangle_within(inner, outer, tolerance=0):
    """Return whether an (x,y,w,h) rectangle fits within another."""
    if type(tolerance) not in (int,float) or not 0 <= tolerance <= 100:
        raise ValueError("invalid tolerance")
    for rect in (inner,outer):
        if not isinstance(rect,(list,tuple)) or len(rect)!=4 or any(type(v) not in (int,float) for v in rect):
            raise ValueError("invalid rectangle")
        if rect[2] <= 0 or rect[3] <= 0:
            raise ValueError("non-positive rectangle")
    x,y,w,h=inner; X,Y,W,H=outer
    return x>=X-tolerance and y>=Y-tolerance and x+w<=X+W+tolerance and y+h<=Y+H+tolerance

def inspect_rectangles(items, screen):
    """Report clipped widgets without recording widget content or secrets."""
    if not isinstance(items,dict) or len(items)>200:
        raise ValueError("invalid widget collection")
    checks={}
    for name,rect in items.items():
        if not isinstance(name,str) or not name or len(name)>80:
            raise ValueError("invalid widget name")
        checks[name]=rectangle_within(rect,screen)
    return {'checks':checks,'clipped':sorted(k for k,v in checks.items() if not v),'status':'passed' if all(checks.values()) else 'failed'}
