"""Bounded incremental ANSI/VT screen subset. Author: Abdelhalim Talbi."""
import re
import html
import unicodedata

class AnsiScreen:
    def __init__(self, rows=30, cols=100):
        self.rows=max(5,min(200,rows));self.cols=max(20,min(500,cols))
        self.grid=[[' ']*self.cols for _ in range(self.rows)]
        self.row=0;self.col=0;self.pending='';self.saved=(0,0);self.alt_grid=None;self.sgr=();self.scroll_top=0;self.scroll_bottom=self.rows-1;self.application_cursor=False;self.origin_mode=False;self.cursor_visible=True;self.styles=[[()]*self.cols for _ in range(self.rows)]
    def resize(self, rows, cols):
        rows=max(5,min(200,int(rows)));cols=max(20,min(500,int(cols)))
        old=self.grid
        old_styles=self.styles
        self.grid=[(r[:cols]+[' ']*max(0,cols-len(r))) for r in old[:rows]]
        self.grid += [[' ']*cols for _ in range(max(0,rows-len(self.grid)))]
        self.styles=[(r[:cols]+[()]*max(0,cols-len(r))) for r in old_styles[:rows]]
        self.styles += [[()]*cols for _ in range(max(0,rows-len(self.styles)))]
        self.rows=rows;self.cols=cols;self.row=min(self.row,rows-1);self.col=min(self.col,cols-1)
        self.scroll_top=0;self.scroll_bottom=rows-1
        # A saved alternate screen must be resized too, otherwise switching
        # back after a window resize restores invalid row/column dimensions.
        if self.alt_grid is not None:
            grid,styles,row,col=self.alt_grid
            grid=[(r[:cols]+[' ']*max(0,cols-len(r))) for r in grid[:rows]]
            grid += [[' ']*cols for _ in range(rows-len(grid))]
            styles=[(r[:cols]+[()]*max(0,cols-len(r))) for r in styles[:rows]]
            styles += [[()]*cols for _ in range(rows-len(styles))]
            self.alt_grid=(grid,styles,min(row,rows-1),min(col,cols-1))
    def _scroll_region(self, top, bottom, upward=True):
        if upward:
            self.grid.pop(top);self.grid.insert(bottom,[' ']*self.cols)
            self.styles.pop(top);self.styles.insert(bottom,[()]*self.cols)
        else:
            self.grid.pop(bottom);self.grid.insert(top,[' ']*self.cols)
            self.styles.pop(bottom);self.styles.insert(top,[()]*self.cols)
    def _scroll(self):
        self._scroll_region(self.scroll_top,self.scroll_bottom)
        self.row=self.scroll_bottom
    def _linefeed(self):
        if self.row==self.scroll_bottom:self._scroll_region(self.scroll_top,self.scroll_bottom)
        elif self.row<self.rows-1:self.row+=1
    def _csi(self, params, cmd):
        if params in ('?1049','?47','?1047') and cmd in ('h','l'):
            if cmd=='h' and self.alt_grid is None:
                self.alt_grid=(self.grid,self.styles,self.row,self.col)
                self.grid=[[' ']*self.cols for _ in range(self.rows)];self.styles=[[()]*self.cols for _ in range(self.rows)];self.row=self.col=0
            elif cmd=='l' and self.alt_grid is not None:
                self.grid,self.styles,self.row,self.col=self.alt_grid;self.alt_grid=None
            return
        if params=='?25' and cmd in ('h','l'):
            self.cursor_visible=(cmd=='h')
            return
        if params in ('?1','?6') and cmd in ('h','l'):
            enabled=cmd=='h'
            if params=='?1':self.application_cursor=enabled
            else:
                self.origin_mode=enabled
                self.row=self.scroll_top if enabled else 0;self.col=0
            return
        if params.startswith('?'):return
        if not re.fullmatch(r'[0-9;]*',params):return
        nums=[int(x) if x else 0 for x in params.split(';')]
        n=max(1,nums[0])
        if cmd=='r':
            top=(nums[0] or 1)-1
            bottom=((nums[1] if len(nums)>1 else self.rows) or self.rows)-1
            if 0<=top<bottom<self.rows:
                self.scroll_top=top;self.scroll_bottom=bottom
                self.row=top if self.origin_mode else 0;self.col=0
            return
        if cmd=='S':
            for _ in range(min(n,self.scroll_bottom-self.scroll_top+1)):
                self._scroll_region(self.scroll_top,self.scroll_bottom)
            return
        if cmd=='T':
            for _ in range(min(n,self.scroll_bottom-self.scroll_top+1)):
                self._scroll_region(self.scroll_top,self.scroll_bottom,False)
            return
        if cmd=='m':
            self.sgr=self._apply_sgr(self.sgr,nums)
        elif cmd=='A':self.row=max(0,self.row-n)
        elif cmd=='B':self.row=min(self.rows-1,self.row+n)
        elif cmd=='C':self.col=min(self.cols-1,self.col+n)
        elif cmd=='D':self.col=max(0,self.col-n)
        elif cmd in 'Hf':
            self.row=min(self.scroll_bottom if self.origin_mode else self.rows-1,max(self.scroll_top if self.origin_mode else 0,(nums[0] or 1)-1+(self.scroll_top if self.origin_mode else 0)));self.col=min(self.cols-1,max(0,((nums[1] if len(nums)>1 else 1) or 1)-1))
        elif cmd=='G':self.col=min(self.cols-1,n-1)
        elif cmd=='d':self.row=min(self.rows-1,n-1)
        elif cmd=='X':
            for i in range(self.col,min(self.cols,self.col+n)):
                self.grid[self.row][i]=' ';self.styles[self.row][i]=()
        elif cmd=='P':
            count=min(n,self.cols-self.col)
            self.grid[self.row]=self.grid[self.row][:self.col]+self.grid[self.row][self.col+count:]+[' ']*count
            self.styles[self.row]=self.styles[self.row][:self.col]+self.styles[self.row][self.col+count:]+[()]*count
        elif cmd=='@':
            count=min(n,self.cols-self.col)
            self.grid[self.row]=(self.grid[self.row][:self.col]+[' ']*count+self.grid[self.row][self.col:])[:self.cols]
            self.styles[self.row]=(self.styles[self.row][:self.col]+[()]*count+self.styles[self.row][self.col:])[:self.cols]
        elif cmd=='K':
            mode=nums[0]
            a,b=(self.col,self.cols) if mode==0 else ((0,self.col+1) if mode==1 else (0,self.cols))
            for i in range(a,b):self.grid[self.row][i]=' ';self.styles[self.row][i]=()
        elif cmd=='J':
            mode=nums[0]
            if mode==2:
                self.grid=[[' ']*self.cols for _ in range(self.rows)];self.styles=[[()]*self.cols for _ in range(self.rows)]
            elif mode==1:
                for r in range(self.row+1):
                    for c in range(self.col+1 if r==self.row else self.cols):
                        self.grid[r][c]=' ';self.styles[r][c]=()
            elif mode==0:
                for r in range(self.row,self.rows):
                    for c in range(self.col if r==self.row else 0,self.cols):self.grid[r][c]=' ';self.styles[r][c]=()
        elif cmd in ('L','M'):
            # IL/DL only affect the active scrolling region, never the footer.
            if self.scroll_top<=self.row<=self.scroll_bottom:
                count=min(n,self.scroll_bottom-self.row+1)
                for _ in range(count):
                    if cmd=='L':
                        self.grid.pop(self.scroll_bottom);self.grid.insert(self.row,[' ']*self.cols)
                        self.styles.pop(self.scroll_bottom);self.styles.insert(self.row,[()]*self.cols)
                    else:
                        self.grid.pop(self.row);self.grid.insert(self.scroll_bottom,[' ']*self.cols)
                        self.styles.pop(self.row);self.styles.insert(self.scroll_bottom,[()]*self.cols)
        elif cmd=='s':self.saved=(self.row,self.col)
        elif cmd=='u':self.row,self.col=self.saved
    def feed(self, data):
        data=self.pending+data;self.pending='';i=0
        while i<len(data):
            ch=data[i]
            if ch=='\x1b':
                if i+1>=len(data):self.pending=data[i:];break
                if data[i+1]=='[':
                    j=i+2
                    while j<len(data) and not ('@'<=data[j]<='~') and j-i<64:j+=1
                    if j==len(data):self.pending=data[i:][-64:];break
                    if j-i>=64:i=j+1;continue
                    self._csi(data[i+2:j],data[j]);i=j+1;continue
                if data[i+1]==']':
                    j=i+2
                    while j<len(data) and data[j]!='\x07' and not (data[j]=='\x1b' and j+1<len(data) and data[j+1]=='\\'):j+=1
                    if j>=len(data):self.pending=data[i:][-256:];break
                    i=j+(2 if data[j]=='\x1b' else 1);continue
                if data[i+1]=='D':self._linefeed()
                elif data[i+1]=='M':
                    if self.row==self.scroll_top:self._scroll_region(self.scroll_top,self.scroll_bottom,False)
                    else:self.row=max(0,self.row-1)
                elif data[i+1]=='E':self.col=0;self._linefeed()
                i+=2;continue
            if ch=='\r':self.col=0
            elif ch=='\n':self._linefeed()
            elif ch=='\b':self.col=max(0,self.col-1)
            elif ch=='\t':self.col=min(self.cols-1,((self.col//8)+1)*8)
            elif ch>=' ' and ch!='\x7f':
                if unicodedata.combining(ch):
                    previous=self.col-1
                    if previous>=0 and self.grid[self.row][previous] not in (' ',''):
                        self.grid[self.row][previous]+=ch
                    i+=1;continue
                width=2 if unicodedata.east_asian_width(ch) in ('W','F') else 1
                if width==2 and self.col==self.cols-1:
                    self.col=0;self._linefeed()
                self.grid[self.row][self.col]=ch
                self.styles[self.row][self.col]=self.sgr
                if width==2:self.grid[self.row][self.col+1]='';self.styles[self.row][self.col+1]=self.sgr
                self.col+=width
                if self.col>=self.cols:self.col=0;self._linefeed()
            i+=1
    def render(self):return '\n'.join(''.join(r).rstrip() for r in self.grid).rstrip()

    @staticmethod
    def _apply_sgr(previous, codes):
        """Apply SGR incrementally; store only validated canonical style tokens."""
        tokens=list(previous)
        def replace(kind, value):
            nonlocal tokens
            tokens=[t for t in tokens if t[0]!=kind]
            if value is not None:tokens.append((kind,value))
        i=0
        while i<len(codes):
            c=codes[i]
            if c==0:tokens=[]
            elif c==1:replace('bold',True)
            elif c==22:replace('bold',None)
            elif c==39:replace('fg',None)
            elif c==49:replace('bg',None)
            elif 30<=c<=37:replace('fg',('ansi',c-30))
            elif 90<=c<=97:replace('fg',('ansi',c-90+8))
            elif 40<=c<=47:replace('bg',('ansi',c-40))
            elif 100<=c<=107:replace('bg',('ansi',c-100+8))
            elif c in (38,48):
                kind='fg' if c==38 else 'bg'
                if i+2<len(codes) and codes[i+1]==5:
                    value=codes[i+2]
                    if 0<=value<=255:replace(kind,('index',value))
                    i+=2
                elif i+4<len(codes) and codes[i+1]==2:
                    rgb=codes[i+2:i+5]
                    if all(0<=x<=255 for x in rgb):replace(kind,('rgb',tuple(rgb)))
                    i+=4
            i+=1
        return tuple(tokens)

    @staticmethod
    def _color(value):
        palette=('#000000','#aa0000','#00aa00','#aa5500','#0000aa','#aa00aa','#00aaaa','#aaaaaa',
                 '#555555','#ff5555','#55ff55','#ffff55','#5555ff','#ff55ff','#55ffff','#ffffff')
        mode,data=value
        if mode=='rgb':return '#%02x%02x%02x'%data
        if mode=='ansi':return palette[data]
        if mode=='index':
            if data<16:return palette[data]
            if data<232:
                n=data-16;levels=(0,95,135,175,215,255)
                return '#%02x%02x%02x'%(levels[n//36],levels[(n//6)%6],levels[n%6])
            shade=8+(data-232)*10
            return '#%02x%02x%02x'%(shade,shade,shade)
        return None

    @classmethod
    def _css(cls,sgr):
        attrs=[]
        for kind,value in sgr:
            if kind in ('fg','bg'):
                color=cls._color(value)
                if color:attrs.append(('color:' if kind=='fg' else 'background-color:')+color)
            elif kind=='bold' and value:attrs.append('font-weight:bold')
        return ';'.join(attrs)

    def line_html(self, row, show_cursor=False):
        """Return safely escaped HTML for one terminal row, optionally with cursor."""
        if not 0 <= row < self.rows:raise IndexError(row)
        cells=self.grid[row]
        styles=self.styles[row]
        limit=len(cells)
        while limit and cells[limit-1]==' ':limit-=1
        if show_cursor and self.cursor_visible and row==self.row:
            limit=max(limit,self.col+1)
        parts=[];run=[];current=None
        def flush():
            if not run:return
            content=html.escape(''.join(run),quote=True)
            css=self._css(current)
            parts.append(('<span style="'+css+'">'+content+'</span>') if css else content)
            run.clear()
        for col in range(limit):
            cell=cells[col];style=styles[col]
            cursor=show_cursor and self.cursor_visible and row==self.row and col==self.col
            if cursor:
                flush();parts.append('<span style="text-decoration:underline">'+html.escape(cell or ' ',quote=True)+'</span>')
                current=None
                continue
            if current is not None and style!=current:flush()
            current=style;run.append(cell)
        flush()
        return ''.join(parts)

    def render_html(self):
        lines=[self.line_html(row,show_cursor=True) for row in range(self.rows)]
        return '<pre style="white-space:pre;font-family:monospace;margin:0">'+'\n'.join(lines)+'</pre>'
