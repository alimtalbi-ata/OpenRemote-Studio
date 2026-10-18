"""OpenRemote Studio V0.3. Author: Abdelhalim Talbi."""
import os, sys, subprocess, threading, queue, webbrowser, tkinter as tk
from pathlib import Path
from tkinter import ttk, messagebox, filedialog
from core import Store, PROTOCOLS, validate
from tk_ssh_event_bridge import TkSSHEventBridge
from network_resource_scope import NetworkResourceScope

ROOT = Path(os.getenv('APPDATA') or Path.home()) / 'OpenRemoteStudio'
class ConnectionDialog(tk.Toplevel):
    def __init__(self, master, item=None):
        super().__init__(master); self.title('Connexion'); self.resizable(False,False); self.result=None
        self.transient(master); self.grab_set()
        self.vars = {}
        for row, (key, label) in enumerate([('name','Nom'),('protocol','Protocole'),('host','Hôte / URL'),('port','Port (optionnel)'),('user','Utilisateur'),('group','Groupe'),('tags','Tags')]):
            ttk.Label(self,text=label).grid(row=row,column=0,sticky='w',padx=12,pady=5)
            v=tk.StringVar(value=(item or {}).get(key,'SSH' if key=='protocol' else '')); self.vars[key]=v
            widget=ttk.Combobox(self,textvariable=v,values=PROTOCOLS,state='readonly',width=36) if key=='protocol' else ttk.Entry(self,textvariable=v,width=39)
            widget.grid(row=row,column=1,padx=12,pady=5)
        ttk.Button(self,text='Enregistrer',command=self.submit).grid(row=7,column=1,sticky='e',padx=12,pady=12)
        self.item_id=(item or {}).get('id',''); self.bind('<Escape>',lambda e:self.destroy()); self.wait_window()
    def submit(self):
        try: self.result=validate(dict(id=self.item_id,**{k:v.get() for k,v in self.vars.items()}))
        except ValueError as exc: messagebox.showerror('Validation',str(exc),parent=self); return
        self.destroy()

class App:
    def __init__(self):
        self.root=tk.Tk(); self.root.title('OpenRemote Studio V0.3 — Abdelhalim Talbi'); self.root.geometry('1260x790')
        self.store=Store(ROOT/'connections.json'); self.events=queue.Queue(); self.sessions=[]; self._closing=False; self.ui_events=queue.Queue(); self.network_scopes=[]
        style=ttk.Style(); style.theme_use('clam'); style.configure('Treeview',rowheight=26)
        bar=ttk.Frame(self.root);bar.pack(fill='x',padx=9,pady=8)
        for label,fn in [('Ajouter',self.add),('Modifier',self.edit),('Supprimer',self.delete),('Connecter',self.connect),('Importer',self.import_file),('Exporter',self.export_file)]:
            ttk.Button(bar,text=label,command=fn).pack(side='left',padx=3)
        self.search=tk.StringVar(); self.search.trace_add('write',lambda *_:self.refresh())
        ttk.Label(bar,text='Rechercher :').pack(side='left',padx=(22,5));ttk.Entry(bar,textvariable=self.search,width=28).pack(side='left')
        pan=ttk.Panedwindow(self.root,orient='horizontal');pan.pack(fill='both',expand=True,padx=9,pady=5)
        left=ttk.Frame(pan);right=ttk.Frame(pan);pan.add(left,weight=1);pan.add(right,weight=4)
        self.tree=ttk.Treeview(left,columns=('proto','host'),show='tree headings',selectmode='browse')
        self.tree.heading('#0',text='Nom / groupe');self.tree.heading('proto',text='Protocole');self.tree.heading('host',text='Hôte')
        self.tree.column('#0',width=160);self.tree.column('proto',width=75);self.tree.column('host',width=160)
        self.tree.pack(fill='both',expand=True);self.tree.bind('<Double-1>',lambda e:self.connect())
        self.tabs=ttk.Notebook(right);self.tabs.pack(fill='both',expand=True)
        home=ttk.Frame(self.tabs);self.tabs.add(home,text='Accueil / outils')
        ttk.Label(home,text='OpenRemote Studio — Centre d’administration',font=('Segoe UI',16,'bold')).pack(anchor='w',padx=18,pady=16)
        ttk.Label(home,text='SSH intégré (Paramiko) • RDP Windows • SFTP externe • VNC externe • Outils réseau').pack(anchor='w',padx=18)
        tools=ttk.Frame(home);tools.pack(anchor='w',padx=18,pady=18)
        for label,command in [('Ping',lambda:self.network_tool('ping')),('Traceroute',lambda:self.network_tool('trace')),('DNS',lambda:self.network_tool('dns')),('SFTP graphique',self.sftp_browser),('Tunnel SSH',self.tunnel_dialog)]:
            ttk.Button(tools,text=label,command=command).pack(side='left',padx=4)
        self.log=tk.Text(home,height=13,bg='#15202b',fg='#d9e8f5',font=('Consolas',10),state='disabled');self.log.pack(fill='both',expand=True,padx=18,pady=12)
        self.note('Bienvenue. Les mots de passe et clés privées ne sont pas enregistrés.\n')
        self.refresh();self.root.after(80,self.poll)
    def note(self,msg):
        self.log.configure(state='normal');self.log.insert('end',msg);self.log.see('end');self.log.configure(state='disabled')
    def selected(self):
        selected=self.tree.selection(); return next((x for x in self.store.items if selected and x['id']==selected[0]),None)
    def refresh(self):
        self.tree.delete(*self.tree.get_children()); query=self.search.get().lower(); groups={}
        for c in sorted(self.store.items,key=lambda x:(x['group'].lower(),x['name'].lower())):
            if query and query not in ' '.join(c.values()).lower():continue
            group=c['group'] or 'Sans groupe'
            if group not in groups:
                gid='group:'+group;groups[group]=gid;self.tree.insert('','end',iid=gid,text=group,open=True)
            self.tree.insert(groups[group],'end',iid=c['id'],text=c['name'],values=(c['protocol'],c['host']))
    def add(self):
        d=ConnectionDialog(self.root)
        if d.result:self.store.upsert(d.result);self.refresh()
    def edit(self):
        c=self.selected()
        if not c:return
        d=ConnectionDialog(self.root,c)
        if d.result:self.store.upsert(d.result);self.refresh()
    def delete(self):
        c=self.selected()
        if c and messagebox.askyesno('Supprimer',f"Supprimer {c['name']} ?"):
            self.store.remove(c['id']);self.refresh()
    def import_file(self):
        p=filedialog.askopenfilename(filetypes=[('JSON','*.json')]);
        if p:
            try:self.note(f"Import : {self.store.import_json(p)} connexions\n");self.refresh()
            except (ValueError,OSError) as e:messagebox.showerror('Import',str(e))
    def export_file(self):
        p=filedialog.asksaveasfilename(defaultextension='.json',filetypes=[('JSON','*.json')])
        if p:
            import json
            Path(p).write_text(json.dumps(self.store.items,ensure_ascii=False,indent=2),encoding='utf-8');self.note('Export effectué (sans secrets).\n')
    def launch(self,args):
        try:subprocess.Popen(args,creationflags=subprocess.CREATE_NEW_CONSOLE if os.name=='nt' else 0)
        except OSError as e:messagebox.showerror('Client indisponible',str(e))
    def connect(self):
        c=self.selected()
        if not c:return
        host,user,proto=c['host'],c['user'],c['protocol'];port=c['port']
        self.note(f"Ouverture {proto}: {c['name']}\n")
        if proto=='SSH':self.ssh_tab(c)
        elif proto=='RDP':
            if os.name!='nt':messagebox.showinfo('RDP','Le client mstsc nécessite Windows');return
            self.launch(['mstsc',f'/v:{host}'+(f':{port}' if port else '')])
        elif proto=='SFTP':self.launch(['sftp']+(['-P',port] if port else [])+[f'{user}@{host}' if user else host])
        elif proto=='VNC':self.launch(['vncviewer',f'{host}::{port}' if port else host])
        else:webbrowser.open(host if '://' in host else 'https://'+host)
    def ssh_tab(self,c):
        try: import paramiko
        except ImportError:
            messagebox.showinfo('Dépendance SSH','Installer Paramiko : python -m pip install -r requirements.txt')
            return
        frame=ttk.Frame(self.tabs);self.tabs.add(frame,text='SSH '+c['name']);self.tabs.select(frame)
        out=tk.Text(frame,bg='#101923',fg='#d7e6ed',insertbackground='white',font=('Consolas',11),wrap='none')
        out.pack(fill='both',expand=True)
        bottom=ttk.Frame(frame);bottom.pack(fill='x');line=tk.StringVar()
        ttk.Entry(bottom,textvariable=line).pack(side='left',fill='x',expand=True)
        state={'channel':None,'client':None,'closed':False,'frame':frame}
        self.sessions.append(state)
        def render(message):
            if not state['closed'] and frame.winfo_exists():
                out.insert('end',message);out.see('end')
        bridge=TkSSHEventBridge(render,lambda error:render('\nErreur SSH : '+str(error)+'\n'))
        state['bridge']=bridge
        generation=bridge.begin()
        def send(event=None):
            channel=state['channel'];value=line.get();line.set('')
            if channel and not channel.closed:channel.send(value+'\n')
        def close_tab():
            if state['closed']:return
            state['closed']=True
            bridge.close()
            client=state['client']
            if client:client.close()
            if frame.winfo_exists():self.tabs.forget(frame);frame.destroy()
        state['close']=close_tab
        ttk.Button(bottom,text='Envoyer',command=send).pack(side='left')
        ttk.Button(bottom,text='Fermer',command=close_tab).pack(side='right')
        frame.bind('<Return>',send)
        def worker():
            client=paramiko.SSHClient()
            try:
                client.load_system_host_keys();client.set_missing_host_key_policy(paramiko.RejectPolicy())
                bridge.post_success(generation,'Connexion SSH : vérification stricte de la clé hôte.\n')
                client.connect(c['host'],port=int(c['port'] or 22),username=c['user'] or None,
                               look_for_keys=True,allow_agent=True,timeout=12,auth_timeout=15)
                if state['closed']:return
                state['client']=client
                channel=client.invoke_shell(width=120,height=35)
                state['channel']=channel
                while not state['closed'] and not channel.closed:
                    if channel.recv_ready():
                        bridge.post_success(generation,channel.recv(65536).decode('utf-8',errors='replace'))
                    else:threading.Event().wait(.08)
            except Exception as exc:bridge.post_error(generation,exc)
            finally:
                client.close()
                bridge.post_success(generation,'\n[Session terminée]\n')
        threading.Thread(target=worker,daemon=True).start()
    def ssh_client(self, c):
        import paramiko
        client=paramiko.SSHClient()
        client.load_system_host_keys()
        client.set_missing_host_key_policy(paramiko.RejectPolicy())
        client.connect(c['host'],port=int(c['port'] or 22),username=c['user'] or None,
                       look_for_keys=True,allow_agent=True,timeout=12,auth_timeout=15)
        return client
    def _post_ui(self, state, callback, *args):
        """Workers only enqueue immutable arguments; Tk callbacks run in poll()."""
        self.ui_events.put((state, callback, args))

    def sftp_browser(self):
        c=self.selected()
        if not c or c['protocol'] not in ('SSH','SFTP'):
            messagebox.showinfo('SFTP','Sélectionner une connexion SSH ou SFTP');return
        try:import paramiko
        except ImportError:messagebox.showerror('Dépendance','Installer Paramiko');return
        win=tk.Toplevel(self.root);win.title('SFTP — '+c['name']);win.geometry('800x540')
        path=tk.StringVar(value='.');status=tk.StringVar(value='Connexion…')
        bar=ttk.Frame(win);bar.pack(fill='x',padx=8,pady=8)
        ttk.Entry(bar,textvariable=path).pack(side='left',fill='x',expand=True)
        tree=ttk.Treeview(win,columns=('size','kind'),show='tree headings')
        tree.heading('#0',text='Nom');tree.heading('size',text='Taille (octets)');tree.heading('kind',text='Type')
        tree.pack(fill='both',expand=True,padx=8,pady=8)
        ttk.Label(win,textvariable=status).pack(fill='x',padx=8)
        scope=NetworkResourceScope();self.network_scopes.append(scope)
        state={'closed':False,'client':None,'sftp':None,'busy':False}
        def task(fn):
            if state['closed'] or scope.cancelled or state['busy']:return
            state['busy']=True
            def run():
                try:fn()
                except Exception as exc:self._post_ui(state,status.set,'Erreur : '+str(exc))
                finally:self._post_ui(state,lambda:state.update(busy=False))
            threading.Thread(target=run,daemon=True).start()
        def refresh():
            requested=path.get()
            def run():
                import stat
                if scope.cancelled:return
                s=state['sftp'];folder=s.normalize(requested)
                if scope.cancelled:return
                entries=s.listdir_attr(folder)
                if scope.cancelled:return
                rows=[(e.filename,str(e.st_size),'Dossier' if stat.S_ISDIR(e.st_mode) else 'Fichier') for e in entries]
                def show():
                    path.set(folder);tree.delete(*tree.get_children())
                    for name,size,kind in sorted(rows,key=lambda r:(r[2]!='Dossier',r[0].lower())):
                        tree.insert('','end',text=name,values=(size,kind))
                    status.set(f'{len(rows)} éléments — {folder}')
                self._post_ui(state,show)
            task(run)
        def connect():
            if scope.cancelled:return
            client=self.ssh_client(c)
            if not scope.register(client):return
            if scope.cancelled:return
            sftp=client.open_sftp()
            if not scope.register(sftp):return
            if scope.cancelled:return
            if scope.cancelled or state['closed']:return
            state.update(client=client,sftp=sftp)
            self._post_ui(state,refresh)
        def selected():
            ids=tree.selection()
            if not ids:return None
            return tree.item(ids[0],'text'),tree.item(ids[0],'values')[1]
        def open_folder(event=None):
            item=selected()
            if item and item[1]=='Dossier':
                from remote_tools import safe_remote_path
                path.set(safe_remote_path(path.get(),item[0]));refresh()
        def download():
            item=selected()
            if not item or item[1]!='Fichier':return
            target=filedialog.asksaveasfilename(initialfile=item[0],parent=win)
            if not target:return
            remote=path.get()
            def run():
                from remote_tools import safe_remote_path
                if scope.cancelled:return
                from sftp_atomic_transfer import download_atomic
                download_atomic(state['sftp'],safe_remote_path(remote,item[0]),target,lambda:scope.cancelled)
                if scope.cancelled:return
                self._post_ui(state,status.set,'Téléchargement terminé : '+target)
            task(run)
        def upload():
            source=filedialog.askopenfilename(parent=win)
            if not source:return
            remote=path.get()
            def run():
                from remote_tools import safe_remote_path
                if scope.cancelled:return
                from sftp_atomic_upload import upload_atomic
                upload_atomic(state['sftp'],source,safe_remote_path(remote,Path(source).name),lambda:scope.cancelled)
                if scope.cancelled:return
                self._post_ui(state,refresh)
            task(run)
        for label,command in [('Actualiser',refresh),('Ouvrir dossier',open_folder),('Télécharger',download),('Envoyer',upload)]:
            ttk.Button(bar,text=label,command=command).pack(side='left',padx=3)
        tree.bind('<Double-1>',open_folder)
        def close():
            if state['closed']:return
            state['closed']=True
            state['sftp']=None;state['client']=None
            scope.close()
            win.destroy()
        win.protocol('WM_DELETE_WINDOW',close)
        task(connect)
    def tunnel_dialog(self):
        c=self.selected()
        if not c or c['protocol'] not in ('SSH','SFTP'):
            messagebox.showinfo('Tunnel','Sélectionner une connexion SSH ou SFTP');return
        win=tk.Toplevel(self.root);win.title('Tunnel SSH local');win.resizable(False,False)
        vars={}
        for i,(key,label,default) in enumerate([('local','Port local','8080'),('target','Hôte cible (vu du serveur SSH)','127.0.0.1'),('remote','Port cible','80')]):
            ttk.Label(win,text=label).grid(row=i,column=0,padx=12,pady=8,sticky='w')
            vars[key]=tk.StringVar(value=default)
            ttk.Entry(win,textvariable=vars[key],width=30).grid(row=i,column=1,padx=12,pady=8)
        status=tk.StringVar(value='Tunnel limité à 127.0.0.1 (poste local)')
        ttk.Label(win,textvariable=status).grid(row=4,column=0,columnspan=2,padx=12,pady=8)
        scope=NetworkResourceScope();self.network_scopes.append(scope)
        state={'closed':False,'busy':False,'tunnel':None,'client':None}
        def start():
            if state['closed'] or scope.cancelled or state['busy'] or state['tunnel']:return
            try:
                local=int(vars['local'].get());target=vars['target'].get();remote=int(vars['remote'].get())
                if not (1<=local<=65535 and 1<=remote<=65535):raise ValueError('Port hors limites')
            except ValueError as exc:status.set('Erreur : '+str(exc));return
            state['busy']=True
            def worker():
                client=None;tunnel=None
                try:
                    from remote_tools import Tunnel
                    if scope.cancelled:return
                    client=self.ssh_client(c)
                    if not scope.register(client):return
                    if scope.cancelled:return
                    tunnel=Tunnel(client,'127.0.0.1',local,target,remote)
                    if scope.cancelled:return
                    tunnel.start()
                    if not scope.register(tunnel):return
                    if scope.cancelled:return
                    if scope.cancelled or state['closed']:return
                    state.update(tunnel=tunnel,client=client)
                    self._post_ui(state,status.set,'Actif sur 127.0.0.1:'+str(local))
                except Exception as exc:
                    if tunnel and not scope.closed:tunnel.close()
                    if client and not scope.closed:client.close()
                    self._post_ui(state,status.set,'Erreur : '+str(exc))
                finally:self._post_ui(state,lambda:state.update(busy=False))
            threading.Thread(target=worker,daemon=True).start()
        ttk.Button(win,text='Démarrer',command=start).grid(row=3,column=1,sticky='e',padx=12,pady=8)
        def close():
            if state['closed']:return
            state['closed']=True
            state['tunnel']=None;state['client']=None
            scope.close()
            win.destroy()
        win.protocol('WM_DELETE_WINDOW',close)
    def network_tool(self,kind):
        c=self.selected()
        if not c or c['protocol']=='WEB':messagebox.showinfo('Outils','Sélectionner une connexion avec un hôte');return
        host=c['host'];windows=os.name=='nt'
        args={'ping':['ping','-n' if windows else '-c','4',host], 'trace':['tracert' if windows else 'traceroute',host], 'dns':['nslookup',host]}[kind]
        def work():
            try:
                r=subprocess.run(args,capture_output=True,text=True,errors='replace',timeout=45,check=False)
                self.events.put((self.log,'\n$ '+' '.join(args)+'\n'+(r.stdout+r.stderr)[-10000:]+'\n'))
            except Exception as e:self.events.put((self.log,str(e)+'\n'))
        threading.Thread(target=work,daemon=True).start()
    def poll(self):
        if self._closing:return
        for _ in range(200):
            try:state,callback,args=self.ui_events.get_nowait()
            except queue.Empty:break
            if not state['closed']:
                callback(*args)
        for session in list(self.sessions):
            if not session['closed']:
                session['bridge'].drain(limit=100)
        try:
            while True:
                widget,msg=self.events.get_nowait()
                if widget.winfo_exists():
                    if widget==self.log:self.note(msg)
                    else:widget.insert('end',msg);widget.see('end')
        except queue.Empty:pass
        if not self._closing:self.root.after(80,self.poll)
    def run(self):
        def close():
            self._closing=True
            for s in list(self.sessions):
                s['close']()
            for scope in self.network_scopes:
                scope.close()
            self.root.destroy()
        self.root.protocol('WM_DELETE_WINDOW',close);self.root.mainloop()
if __name__=='__main__':App().run()
