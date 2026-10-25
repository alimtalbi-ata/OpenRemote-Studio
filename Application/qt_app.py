from session_presentation import session_process_details, session_visibility_summary
from session_selection import selected_session, preserved_session_identity, session_identity
import sqlite3
from pam_lab_reports import export_report,load_and_verify_report
from pam_lab_scenarios import run_scenarios
"""Modern Qt connection cockpit, optional alternative to legacy Tk UI. Author: Abdelhalim Talbi."""
import os,sys,subprocess,webbrowser,tempfile
from html import escape
from pathlib import Path
from PySide6.QtCore import Qt, QObject, Signal, QRunnable, QThreadPool, QTimer, QSettings
from PySide6.QtGui import QKeySequence, QColor, QShortcut
from PySide6.QtWidgets import (QApplication,QMainWindow,QWidget,QVBoxLayout,QHBoxLayout,QLineEdit,QPushButton,QTreeWidget,QTreeWidgetItem,QTabWidget,QScrollArea,QTextEdit,QLabel,QDialog,QFormLayout,QComboBox,QDialogButtonBox,QMessageBox,QSplitter,QInputDialog,QFileDialog,QPlainTextEdit,QListWidget,QAbstractItemView,QDockWidget,QListWidgetItem,QMenu,QTableWidget,QTableWidgetItem,QCheckBox)
from core import Store,validate,PROTOCOLS
from tool_catalog import TOOLS, search_tools
from profiles import PROFILES, visible_tools
from diagnostics import command_args
from sftp_paths import remote_child, local_entries
from gateways import validate_route,ssh_jump_args,rdp_content
from rdp_sessions import write_session,cleanup_stale
from access_preview import describe_path
from routes import RouteStore
from connection_policy import connection_route
from access_preflight import inspect_access
from launch_plan import build_launch_plan
from connection_diagnostics import json_report
from probe_history import ProbeHistory, classify_ssh_result
from network_probe import probe
from external_sessions import ExternalSessionRegistry
from session_history import SessionHistory
from reliability_metrics import enrich_statistics,filter_statistics
from connection_health import summarize_connection
from connection_timeline import timeline, export_timeline
from incident_correlation import correlate, overview
from connection_inspector import inspect_connection
from connection_filter_state import filter_status
from connection_actions import actions_for_selection
from tab_navigation import next_tab,tab_at_position,closable_tab
from terminal_output import readable_output,command_is_valid
from pty_session import PtyShell,validate_pty_target
from session_view import filter_sessions,session_counts,prioritized_sessions
from session_presentation import session_status_label,session_empty_message,can_reconnect,selected_reconnect_allowed,session_visual_state
from session_diagnostics import summarize_diagnostics, format_session_diagnostic, format_guided_diagnostic
from session_incident_center import incident_index, incident_counts
from vault import Vault
from workspace import Workspace
from dashboard import summarize, command_search, quick_access
from inventory import export_csv, export_json, summary
from integrations import discover, filter_tools
ROOT=Path(os.getenv('APPDATA') or Path.home())/'OpenRemoteStudio'

from qt_workers import SftpJob, TcpJob
from transfer_queue import TransferQueue
from transfer_journal import TransferJournal
from journal_policy import progress_or_cancel
from pam_refs import capability_report,PROVIDERS
from pam_profiles import PamProfileStore
from pam_binding import resolve_pam_profile
from pam_connectors import ConnectorRegistry
from pam_simulator import SimulatedPamBroker
import time

def application_version():
    """Read the bundled release version; never display a stale hardcoded title."""
    from version_info import read_application_version
    return read_application_version(Path(__file__).resolve().parent)

class Editor(QDialog):
    def __init__(self,parent,item=None):
        super().__init__(parent);self.setWindowTitle('Connexion');self.fields={};self.item=item or {};form=QFormLayout(self)
        for key,label in [('name','Nom'),('protocol','Protocole'),('host','Hôte / URL'),('port','Port'),('user','Utilisateur'),('group','Groupe'),('tags','Tags')]:
            w=QComboBox() if key=='protocol' else QLineEdit()
            if key=='protocol':w.addItems(PROTOCOLS);w.setCurrentText(self.item.get(key,'SSH'))
            else:w.setText(self.item.get(key,''))
            self.fields[key]=w;form.addRow(label,w)
        btn=QDialogButtonBox(QDialogButtonBox.Ok|QDialogButtonBox.Cancel);form.addRow(btn);btn.accepted.connect(self.check);btn.rejected.connect(self.reject)
    def check(self):
        try:self.result=validate(dict(id=self.item.get('id',''),**{k:(w.currentText() if isinstance(w,QComboBox) else w.text()) for k,w in self.fields.items()}))
        except ValueError as exc:QMessageBox.warning(self,'Validation',str(exc));return
        self.accept()

class JumpChainDialog(QDialog):
    """Edit the additional SSH hops without exposing secrets or opening sockets."""
    def __init__(self, parent, chain=''):
        super().__init__(parent)
        from jump_chain_editor import decode_chain
        self.setWindowTitle('Éditeur de rebonds SSH supplémentaires')
        self.resize(620,420)
        self.hops=decode_chain(chain)
        layout=QVBoxLayout(self)
        layout.addWidget(QLabel('Ordre des rebonds après le bastion principal (maximum 3). Aucun mot de passe stocké.'))
        self.entries=QListWidget();layout.addWidget(self.entries)
        form=QFormLayout();layout.addLayout(form)
        self.user=QLineEdit();self.host=QLineEdit();self.port=QLineEdit('22')
        form.addRow('Utilisateur SSH (facultatif)',self.user)
        form.addRow('Hôte DNS ou IPv4',self.host)
        form.addRow('Port SSH',self.port)
        controls=QHBoxLayout();layout.addLayout(controls)
        for label,method in [('Ajouter',self.add_hop),('Modifier',self.edit_hop),('Supprimer',self.remove_hop),('Monter',lambda:self.move(-1)),('Descendre',lambda:self.move(1))]:
            button=QPushButton(label);button.clicked.connect(method);controls.addWidget(button)
        self.preview=QLabel();self.preview.setWordWrap(True);layout.addWidget(self.preview)
        buttons=QDialogButtonBox(QDialogButtonBox.Save|QDialogButtonBox.Cancel)
        layout.addWidget(buttons);buttons.accepted.connect(self.accept);buttons.rejected.connect(self.reject)
        self.entries.currentRowChanged.connect(self.select_hop)
        self.refresh()
    def refresh(self,selected=-1):
        from jump_chain_editor import encode_chain
        self.entries.clear()
        for i,hop in enumerate(self.hops,1):
            self.entries.addItem(f"{i}. {hop['user']+'@' if hop['user'] else ''}{hop['host']}:{hop['port']}")
        self.preview.setText('Parcours : '+(' → '.join(h['host'] for h in self.hops) if self.hops else 'aucun rebond supplémentaire'))
        if selected>=0 and selected<len(self.hops):self.entries.setCurrentRow(selected)
    def select_hop(self,index):
        if 0<=index<len(self.hops):
            hop=self.hops[index];self.user.setText(hop['user']);self.host.setText(hop['host']);self.port.setText(str(hop['port']))
    def form_hop(self):
        from jump_chain_editor import validate_hop
        return validate_hop(self.host.text(),self.port.text(),self.user.text())
    def add_hop(self):
        from jump_chain_editor import insert_hop
        try:self.hops=insert_hop(self.hops,self.form_hop());self.refresh(len(self.hops)-1)
        except ValueError as exc:QMessageBox.warning(self,'Rebond invalide',str(exc))
    def edit_hop(self):
        from jump_chain_editor import encode_chain
        index=self.entries.currentRow()
        if index<0:return
        try:
            updated=[dict(h) for h in self.hops];updated[index]=self.form_hop();encode_chain(updated)
            self.hops=updated;self.refresh(index)
        except ValueError as exc:QMessageBox.warning(self,'Rebond invalide',str(exc))
    def remove_hop(self):
        from jump_chain_editor import remove_hop
        index=self.entries.currentRow()
        if index<0:return
        self.hops=remove_hop(self.hops,index);self.refresh(min(index,len(self.hops)-1))
    def move(self,delta):
        from jump_chain_editor import move_hop
        index=self.entries.currentRow()
        try:self.hops=move_hop(self.hops,index,delta);self.refresh(index+delta)
        except ValueError:pass
    def encoded(self):
        from jump_chain_editor import encode_chain
        return encode_chain(self.hops)

class SSHPathDialog(QDialog):
    """Edit the complete SSH path including the primary bastion."""
    def __init__(self,parent,route,target=''):
        super().__init__(parent)
        from ssh_path_editor import route_to_hops
        self.setWindowTitle('Parcours SSH complet — bastion principal inclus')
        self.resize(820,620)
        self.hops=route_to_hops(route)
        self.base=dict(route)
        self.target=target
        outer=QVBoxLayout(self)
        self.ssh_sections=QTabWidget()
        self.ssh_sections.setObjectName('sshPathSections')
        self.ssh_sections.setDocumentMode(True)
        self.ssh_sections.setUsesScrollButtons(True)
        self.ssh_sections.setToolTip('Parcours : configuration · Diagnostic : tests explicites · Historique et audit : rapports locaux')
        outer.addWidget(self.ssh_sections)
        editor_page=QWidget();layout=QVBoxLayout(editor_page)
        self.ssh_sections.addTab(editor_page,'Parcours')
        layout.addWidget(QLabel('Ordre de connexion : premier bastion → rebonds → cible. Maximum quatre bastions. Aucun secret.'))
        self.entries=QListWidget();layout.addWidget(self.entries)
        form=QFormLayout();layout.addLayout(form)
        self.user=QLineEdit();self.host=QLineEdit();self.port=QLineEdit('22')
        form.addRow('Compte SSH',self.user);form.addRow('Hôte SSH',self.host);form.addRow('Port',self.port)
        buttons=QHBoxLayout();layout.addLayout(buttons)
        for title,callback in [('Ajouter',self.add_hop),('Modifier',self.edit_hop),('Supprimer',self.remove_hop),('Monter',lambda:self.move(-1)),('Descendre',lambda:self.move(1))]:
            b=QPushButton(title);b.clicked.connect(callback);buttons.addWidget(b)
        self.preview=QLabel();self.preview.setWordWrap(True);layout.addWidget(self.preview)
        diagnostic_page=QWidget();layout=QVBoxLayout(diagnostic_page)
        self.ssh_sections.addTab(diagnostic_page,'Diagnostic')
        self.diagnose=QPushButton('Tester les ports TCP depuis ce poste (consentement)')
        self.diagnose.clicked.connect(self.test_local_hops);layout.addWidget(self.diagnose)
        self.diagnostic_output=QPlainTextEdit();self.diagnostic_output.setReadOnly(True)
        self.diagnostic_output.setMaximumHeight(110);layout.addWidget(self.diagnostic_output)
        layout.addWidget(QLabel('Tests TCP locaux uniquement : ni SSH, ni tunnel, ni authentification cible.'))
        target_form=QFormLayout();layout.addLayout(target_form)
        self.ssh_target=QLineEdit(self.target);self.ssh_target_port=QLineEdit('22');self.ssh_target_user=QLineEdit()
        target_form.addRow('Cible SSH pour diagnostic bout en bout',self.ssh_target)
        target_form.addRow('Port cible SSH',self.ssh_target_port)
        target_form.addRow('Compte cible (clé/agent)',self.ssh_target_user)
        self.ssh_timeout=QComboBox()
        for seconds in (3,5,10,15,20):self.ssh_timeout.addItem(f'{seconds} secondes / opération',seconds)
        self.ssh_timeout.setCurrentIndex(2)
        target_form.addRow('Délai SSH par opération',self.ssh_timeout)
        self.ssh_stage_view=QTreeWidget();self.ssh_stage_view.setHeaderLabels(['Étape','État','Durée'])
        self.ssh_stage_view.setAlternatingRowColors(True)
        self.ssh_stage_view.setToolTip('Une ligne par bastion ou cible ; état et durée du dernier diagnostic')
        self.ssh_stage_view.setMaximumHeight(145);layout.addWidget(self.ssh_stage_view)
        self.ssh_e2e=QPushButton('Tester la chaîne SSH complète (authentification, consentement)')
        self.ssh_e2e.clicked.connect(self.test_e2e_hops);layout.addWidget(self.ssh_e2e)
        self.ssh_e2e_cancel=QPushButton('Annuler le diagnostic SSH')
        self.ssh_e2e_cancel.setEnabled(False)
        self.ssh_e2e_cancel.clicked.connect(self.cancel_e2e_hops)
        layout.addWidget(self.ssh_e2e_cancel)
        self.ssh_export=QPushButton('Exporter le diagnostic anonymisé (JSON)')
        self.ssh_export.setEnabled(False)
        self.ssh_export.clicked.connect(self.export_e2e_report)
        layout.addWidget(self.ssh_export)
        self.ssh_compare=QPushButton('Comparer avec un rapport JSON anonymisé précédent')
        self.ssh_compare.setEnabled(False)
        self.ssh_compare.clicked.connect(self.compare_e2e_report)
        layout.addWidget(self.ssh_compare)
        self.ssh_save_history=QPushButton('Enregistrer ce diagnostic anonymisé dans l’historique local')
        self.ssh_save_history.setEnabled(False)
        self.ssh_save_history.clicked.connect(self.save_e2e_history)
        layout.addWidget(self.ssh_save_history)
        history_page=QWidget();layout=QVBoxLayout(history_page)
        history_scroll=QScrollArea()
        history_scroll.setObjectName('sshHistoryScroll')
        history_scroll.setWidgetResizable(True)
        history_scroll.setFrameShape(QScrollArea.NoFrame)
        history_scroll.setWidget(history_page)
        self.ssh_sections.addTab(history_scroll,'Historique et audit')
        # Scope is opt-in. The secret is never persisted and is cleared after derivation.
        self.ssh_scope_name=QLineEdit()
        self.ssh_scope_name.setPlaceholderText('Identifiant stable choisi par l’utilisateur')
        self.ssh_scope_secret=QLineEdit()
        self.ssh_scope_secret.setEchoMode(QLineEdit.Password)
        self.ssh_scope_secret.setPlaceholderText('Clé externe aléatoire de 32 octets minimum (non enregistrée)')
        scope_form=QFormLayout()
        scope_form.addRow('Parcours pseudonymisé (facultatif)',self.ssh_scope_name)
        scope_form.addRow('Clé de pseudonymisation',self.ssh_scope_secret)
        layout.addLayout(scope_form)
        layout.addWidget(QLabel('Même identifiant + même clé externe = même parcours. Sans clé, l’historique mélange les parcours. Ne réutilisez pas un mot de passe SSH.'))
        self.ssh_history_view=QPushButton('Tableau de bord des diagnostics SSH enregistrés')
        self.ssh_history_view.clicked.connect(self.show_e2e_history)
        layout.addWidget(self.ssh_history_view)
        signed_actions=QHBoxLayout()
        self.ssh_signed_export=QPushButton('Exporter historique signé')
        self.ssh_signed_export.clicked.connect(self.export_signed_history)
        signed_actions.addWidget(self.ssh_signed_export)
        self.ssh_signed_import=QPushButton('Vérifier puis importer un export signé')
        self.ssh_signed_import.clicked.connect(self.import_signed_history)
        signed_actions.addWidget(self.ssh_signed_import)
        layout.addLayout(signed_actions)
        self.ssh_audit_view=QPushButton('Journal des imports SSH · filtres et export signé')
        self.ssh_audit_view.clicked.connect(self.show_import_audit)
        layout.addWidget(self.ssh_audit_view)
        self.ssh_history_filter=QComboBox()
        for label,value in [('Tous les états',None),('Réussis','authenticated'),('Échecs','failed'),('Annulés','cancelled')]:
            self.ssh_history_filter.addItem(label,value)
        layout.addWidget(self.ssh_history_filter)
        self.ssh_history_purge=QPushButton('Purger les diagnostics de plus de 30 jours (confirmation)')
        self.ssh_history_purge.clicked.connect(self.purge_e2e_history)
        layout.addWidget(self.ssh_history_purge)
        layout.addWidget(QLabel('Ce test authentifie chaque saut et la cible avec clés/agent et known_hosts ; aucune commande ni shell.'))
        # Contextual assistance: no network action is triggered by hovering or changing tabs.
        for widget, hint in (
            (self.entries, 'Bastions dans l’ordre de traversée. Sélectionnez un saut pour le modifier.'),
            (self.diagnose, 'Ouvre un test TCP local uniquement après clic et consentement.'),
            (self.ssh_e2e, 'Authentifie les sauts SSH après confirmation ; n’exécute aucune commande distante.'),
            (self.ssh_e2e_cancel, 'Demande l’arrêt coopératif du diagnostic en cours.'),
            (self.ssh_export, 'Produit un rapport anonymisé ; aucune adresse IP ni identifiant SSH.'),
            (self.ssh_scope_secret, 'Clé externe dédiée, non persistée. Ne jamais utiliser le mot de passe SSH.'),
            (self.ssh_signed_import, 'Vérifie la signature HMAC avant de proposer un import SQLite.'),
            (self.ssh_history_purge, 'Suppression locale irréversible, uniquement après confirmation.'),
        ):
            widget.setToolTip(hint)
            widget.setAccessibleDescription(hint)
        outer.addWidget(QLabel('Les diagnostics réseau nécessitent un consentement explicite. Les clés ne sont pas sauvegardées.'))
        actions=QDialogButtonBox(QDialogButtonBox.Save|QDialogButtonBox.Cancel)
        actions.accepted.connect(self.save);actions.rejected.connect(self.reject);outer.addWidget(actions)
        self.entries.currentRowChanged.connect(self.select_hop)
        self.refresh(0)
    def _history_signing_key(self):
        from PySide6.QtWidgets import QInputDialog, QLineEdit
        value,ok=QInputDialog.getText(self,'Clé externe HMAC',
            'Saisir une clé externe dédiée (minimum 32 octets UTF-8). Ne pas réutiliser un mot de passe :',
            QLineEdit.Password)
        if not ok:return None
        key=value.encode('utf-8')
        value=''
        if len(key)<32:
            QMessageBox.warning(self,'Clé invalide','La clé doit contenir au moins 32 octets UTF-8.')
            return None
        return key

    def export_signed_history(self):
        from pathlib import Path
        import json
        from ssh_diagnostic_history import DiagnosticHistory
        from ssh_history_integrity import create_export
        key=self._history_signing_key()
        if key is None:return
        if QMessageBox.question(self,'Export historique SSH',
            'Exporter les 200 diagnostics anonymisés au maximum ? La signature authentifie le fichier mais ne le chiffre.',
            QMessageBox.Yes|QMessageBox.No)!=QMessageBox.Yes:return
        try:
            records=DiagnosticHistory(ROOT/'ssh-diagnostics.sqlite3').recent(200)
            document=create_export(records,key)
            path,_=QFileDialog.getSaveFileName(self,'Enregistrer export SSH signé',
                'openremote-ssh-history-signed.json','JSON (*.json)')
            if not path:return
            Path(path).write_text(json.dumps(document,ensure_ascii=False,indent=2,sort_keys=True)+'\n',encoding='utf-8')
            QMessageBox.information(self,'Export signé',f'Export signé créé ({len(document["payload"]["records"])} enregistrements).')
        except (ValueError,TypeError,KeyError,OSError,sqlite3.Error):
            QMessageBox.warning(self,'Export signé','Export impossible. Vérifier la clé, l’historique et les permissions du fichier.')
        finally:
            key=b''

    def import_signed_history(self):
        from pathlib import Path
        import json
        from ssh_diagnostic_history import DiagnosticHistory
        from ssh_history_integrity import verify_export
        path,_=QFileDialog.getOpenFileName(self,'Choisir un export SSH signé','','JSON (*.json)')
        if not path:return
        key=self._history_signing_key()
        if key is None:return
        try:
            file_path=Path(path)
            if file_path.stat().st_size>2*1024*1024:raise ValueError('Fichier trop volumineux')
            document=json.loads(file_path.read_text(encoding='utf-8'))
            records=verify_export(document,key)
        except (OSError,UnicodeError,json.JSONDecodeError,ValueError,TypeError,KeyError):
            QMessageBox.warning(self,'Import SSH','Signature invalide, clé incorrecte ou fichier non conforme. Aucun enregistrement importé.')
            return
        finally:
            key=b''
        try:
            history=DiagnosticHistory(ROOT/'ssh-diagnostics.sqlite3')
            preview=history.preview_import(records)
            preview.update(history.preview_import_details(records))
        except (ValueError,TypeError,KeyError,OSError,sqlite3.Error):
            QMessageBox.warning(self,'Import SSH','Prévisualisation impossible. Aucun enregistrement importé.')
            return
        prompt=(f"Signature valide. Fichier : {preview['total']} diagnostic(s).\n"
                f"Nouveaux : {preview['new']} · Doublons exacts ignorés : {preview['duplicates']}.\n"
                f"Conflits d'horodatage : {preview['timestamp_conflicts']} (conservés séparément).\n"
                f"Aperçu (5 max) : {preview['sample']}\n\n"
                'Importer les nouveaux diagnostics ? Les données ne sont pas chiffrées.')
        if QMessageBox.question(self,'Prévisualiser l’import',prompt,
            QMessageBox.Yes|QMessageBox.No)!=QMessageBox.Yes:return
        try:
            count=history.import_verified(records)
            QMessageBox.information(self,'Import SSH',f'{count} nouveau(x) diagnostic(s) importé(s). Les doublons exacts ont été ignorés ; les horodatages d’origine sont conservés.')
        except (ValueError,TypeError,KeyError,OSError,sqlite3.Error):
            QMessageBox.warning(self,'Import SSH','Import impossible ; la base locale reste cohérente grâce à la transaction.')

    def show_import_audit(self):
        """Read-only, bounded import journal; explicit consent for signed export."""
        import json
        from datetime import datetime,timezone
        from ssh_diagnostic_history import DiagnosticHistory
        from ssh_import_audit import filter_rows,summary,export_signed,verify_signed
        dialog=QDialog(self)
        dialog.setWindowTitle('Journal des imports SSH — données anonymisées')
        dialog.resize(800,500)
        layout=QVBoxLayout(dialog)
        filters=QHBoxLayout();layout.addLayout(filters)
        period=QComboBox()
        for label,days in [('Toutes périodes',0),('7 derniers jours',7),('30 derniers jours',30),('90 derniers jours',90)]:
            period.addItem(label,days)
        filters.addWidget(period)
        conflicts=QCheckBox('Conflits uniquement');filters.addWidget(conflicts)
        search=QLineEdit();search.setPlaceholderText('Rechercher dans les compteurs ou dates affichées')
        filters.addWidget(search)
        totals=QLabel();layout.addWidget(totals)
        table=QTableWidget(0,5)
        table.setHorizontalHeaderLabels(['Date UTC','Total','Importés','Doublons','Conflits'])
        table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        layout.addWidget(table)
        status=QLabel('');layout.addWidget(status)
        actions=QHBoxLayout();layout.addLayout(actions)
        export=QPushButton('Exporter le journal signé');actions.addWidget(export)
        verify=QPushButton('Vérifier un export signé');actions.addWidget(verify)
        def show_local_groups():
            identity=selected_dashboard_id()
            if not identity or identity not in {c['id'] for c in self.store.items}:
                return
            from local_incident_groups import group_local_errors, format_summary
            try:
                result=group_local_errors(self.session_history.recent(1000),
                    self.probe_history.recent(identity,limit=500),identity)
                QMessageBox.information(dialog,'Regroupement des échecs locaux',format_summary(result))
            except (OSError,ValueError,sqlite3.Error) as exc:
                QMessageBox.warning(dialog,'Regroupement indisponible',type(exc).__name__)
        group_button=QPushButton('Regrouper les échecs')
        group_button.setToolTip('Regrouper les erreurs locales par type et heure, sans attribuer une panne distante')
        group_button.clicked.connect(show_local_groups)
        actions.addWidget(group_button)
        def show_incident_trends():
            identity=selected_dashboard_id()
            if not identity or identity not in {c['id'] for c in self.store.items}: return
            from incident_trends import build_trends
            view=QDialog(dialog);view.setWindowTitle('Chronologie des échecs locaux');view.resize(720,430)
            body=QVBoxLayout(view)
            body.addWidget(QLabel('Observations locales uniquement : aucune panne distante confirmée.'))
            window=QComboBox();window.addItems(['30','60','120','240','480','1440'])
            window.setCurrentText('60');window.setToolTip('Période d’observation en minutes')
            body.addWidget(window)
            comparison=QLabel();body.addWidget(comparison)
            timeline_table=QTableWidget(0,5)
            timeline_table.setHorizontalHeaderLabels(['Début UTC','TCP','SSH','Client','Total'])
            timeline_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
            body.addWidget(timeline_table)
            from qt_trend_chart import LocalTrendChart
            chart=LocalTrendChart(view)
            body.insertWidget(body.indexOf(timeline_table),chart)
            legend=QLabel('■ TCP (bleu)    ■ SSH (orange)    ■ Client (gris) — observations locales')
            body.insertWidget(body.indexOf(timeline_table),legend)
            def refresh_trends(*_):
                try:
                    period=int(window.currentText())
                    report=build_trends(self.session_history.recent(1000),
                        self.probe_history.recent(identity,limit=500),identity,
                        minutes=period,bucket_minutes=15 if period<=120 else 60)
                except (OSError,ValueError,sqlite3.Error) as exc:
                    comparison.setText('Données indisponibles : '+type(exc).__name__)
                    timeline_table.setRowCount(0);return
                chart.set_report(report)
                comparison.setText(f"Échecs locaux : {report['total_errors']} | Première moitié : {report['earlier_half']} | Seconde moitié : {report['later_half']} | Variation : {report['delta']:+d}")
                timeline_table.setRowCount(len(report['buckets']))
                for index,bucket in enumerate(report['buckets']):
                    values=(bucket['start_utc'],bucket['counts']['tcp_local'],
                        bucket['counts']['ssh_jump'],bucket['counts']['session_exit'],bucket['total'])
                    for col,value in enumerate(values):timeline_table.setItem(index,col,QTableWidgetItem(str(value)))
            window.currentTextChanged.connect(refresh_trends)
            refresh_trends()
            done=QPushButton('Fermer');done.clicked.connect(view.accept);body.addWidget(done)
            view.exec()
        trend_button=QPushButton('Chronologie des échecs')
        trend_button.setToolTip('Comparer deux périodes et visualiser les erreurs locales, sans test réseau')
        trend_button.clicked.connect(show_incident_trends)
        actions.addWidget(trend_button)
        close=QPushButton('Fermer');close.clicked.connect(dialog.accept);actions.addWidget(close)
        current=[]
        def refresh():
            nonlocal current
            try:
                rows=DiagnosticHistory(ROOT/'ssh-diagnostics.sqlite3').import_audit(100)
                days=period.currentData()
                since=int(__import__('time').time())-days*86400 if days else None
                filtered=filter_rows(rows,since=since,conflicts_only=conflicts.isChecked())
                query=search.text().strip().casefold()
                current=[r for r in filtered if not query or query in ' '.join(str(v) for v in r.values()).casefold()]
                info=summary(current)
                totals.setText(f"Opérations : {info['operations']} · Importés : {info['inserted']} · Doublons : {info['duplicates']} · Conflits : {info['conflicts']}")
                table.setRowCount(len(current))
                for i,row in enumerate(current):
                    stamp=datetime.fromtimestamp(row['imported_at'],timezone.utc).strftime('%Y-%m-%d %H:%M:%S')
                    for j,value in enumerate((stamp,row['total'],row['inserted'],row['duplicates'],row['conflicts'])):
                        table.setItem(i,j,QTableWidgetItem(str(value)))
                status.setText('Journal local uniquement · 100 opérations au maximum')
            except (ValueError,TypeError,OverflowError,OSError,sqlite3.Error):
                current=[];table.setRowCount(0);totals.setText('Journal indisponible')
                status.setText('Lecture impossible ; aucune donnée modifiée')
        def save_signed():
            key=self._history_signing_key()
            if key is None:return
            try:
                envelope=export_signed(current,key)
                path,_=QFileDialog.getSaveFileName(dialog,'Exporter journal signé','openremote-import-audit-signed.json','JSON (*.json)')
                if not path:return
                from pathlib import Path
                Path(path).write_text(json.dumps(envelope,ensure_ascii=False,sort_keys=True,indent=2)+'\n',encoding='utf-8')
                QMessageBox.information(dialog,'Export','Journal signé exporté ; données non chiffrées.')
            except (ValueError,TypeError,OSError):
                QMessageBox.warning(dialog,'Export','Export impossible ; vérifiez les permissions et la clé.')
            finally:key=b''
        def check_signed():
            path,_=QFileDialog.getOpenFileName(dialog,'Vérifier journal signé','','JSON (*.json)')
            if not path:return
            key=self._history_signing_key()
            if key is None:return
            try:
                from pathlib import Path
                source=Path(path)
                if source.stat().st_size>256*1024:raise ValueError('Fichier trop volumineux')
                rows=verify_signed(json.loads(source.read_text(encoding='utf-8')),key)
                QMessageBox.information(dialog,'Vérification',f'Signature valide · {len(rows)} opérations. Aucun import effectué.')
            except (ValueError,TypeError,KeyError,OSError,UnicodeError,json.JSONDecodeError):
                QMessageBox.warning(dialog,'Vérification','Signature invalide ou fichier non conforme.')
            finally:key=b''
        period.currentIndexChanged.connect(refresh)
        conflicts.toggled.connect(refresh)
        search.textChanged.connect(refresh)
        export.clicked.connect(save_signed)
        verify.clicked.connect(check_signed)
        refresh();dialog.exec()

    def refresh(self,index=-1):
        from ssh_path_editor import path_preview
        self.entries.clear()
        for i,h in enumerate(self.hops):
            label='Principal' if i==0 else f'Rebond {i+1}'
            self.entries.addItem(f"{label} · {h['user']+'@' if h['user'] else ''}{h['host']}:{h['port']}")
        self.preview.setText('Parcours : '+path_preview(self.hops,self.target))
        if 0<=index<len(self.hops):self.entries.setCurrentRow(index)
    def select_hop(self,index):
        if 0<=index<len(self.hops):
            h=self.hops[index];self.user.setText(h['user']);self.host.setText(h['host']);self.port.setText(str(h['port']))
    def form_hop(self):
        from jump_chain_editor import validate_hop
        return validate_hop(self.host.text(),self.port.text(),self.user.text())
    def mutate(self,operation):
        from ssh_path_editor import validate_path
        try:
            updated,index=operation([dict(h) for h in self.hops]);self.hops=validate_path(updated);self.refresh(index)
        except ValueError as exc:QMessageBox.warning(self,'Parcours SSH invalide',str(exc))
    def add_hop(self):
        self.mutate(lambda hops:(hops+[self.form_hop()],len(hops)))
    def edit_hop(self):
        i=self.entries.currentRow()
        if i<0:return
        def op(hops):hops[i]=self.form_hop();return hops,i
        self.mutate(op)
    def remove_hop(self):
        i=self.entries.currentRow()
        if i<0:return
        def op(hops):hops.pop(i);return hops,max(0,i-1)
        self.mutate(op)
    def move(self,delta):
        i=self.entries.currentRow();j=i+delta
        if i<0 or j<0 or j>=len(self.hops):return
        def op(hops):hops[i],hops[j]=hops[j],hops[i];return hops,j
        self.mutate(op)
    def test_local_hops(self):
        from ssh_path_editor import validate_path
        try:hops=validate_path(self.hops)
        except ValueError as exc:
            QMessageBox.warning(self,'Diagnostic TCP',str(exc));return
        if QMessageBox.question(self,'Consentement — ports TCP locaux',
            'Tester directement depuis ce poste les ports des bastions configurés ?\n'
            'Aucun tunnel ni connexion SSH ne sera établi. Les résultats ne prouvent PAS '
            'la disponibilité des rebonds successifs. Des traces réseau peuvent être créées.',
            QMessageBox.Yes|QMessageBox.No)!=QMessageBox.Yes:return
        from qt_workers import SshHopLocalJob
        self.diagnose.setEnabled(False)
        self.diagnostic_output.setPlainText('Tests TCP locaux en cours…')
        self._hop_probe_job=SshHopLocalJob(hops)
        self._hop_probe_job.signals.finished.connect(self._on_hop_probe_done)
        QThreadPool.globalInstance().start(self._hop_probe_job)
    def _on_hop_probe_done(self,results):
        self.diagnostic_output.setPlainText('\n'.join(r['message'] for r in results))
        self.diagnose.setEnabled(True)

    def test_e2e_hops(self):
        from gateways import host as valid_host, port as valid_port
        from ssh_path_editor import validate_path
        try:
            hops=validate_path(self.hops)
            target=valid_host(self.ssh_target.text())
            port=valid_port(self.ssh_target_port.text(),22)
            user=self.ssh_target_user.text()
            if len(user)>128 or any(ch in user for ch in ('\n','\r','\x00')):raise ValueError('Compte cible invalide')
        except (ValueError,TypeError) as exc:
            QMessageBox.warning(self,'Diagnostic SSH',str(exc));return
        if QMessageBox.question(self,'Consentement — authentification SSH réelle',
            'Établir des connexions SSH réelles sur tous les bastions et la cible ?\n'
            'Ce test peut déclencher des journaux de sécurité, des alertes et des tentatives '
            'd’authentification. Vérification stricte known_hosts. Aucun shell ni commande. '
            'Continuer ?',QMessageBox.Yes|QMessageBox.No)!=QMessageBox.Yes:return
        from qt_workers import SshEndToEndJob
        self.ssh_e2e.setEnabled(False)
        self.ssh_e2e_cancel.setEnabled(True)
        self.diagnostic_output.setPlainText('Diagnostic SSH authentifié en cours…')
        self.ssh_stage_view.clear()
        self._ssh_live_events=[]
        self.ssh_export.setEnabled(False)
        self.ssh_compare.setEnabled(False)
        self.ssh_save_history.setEnabled(False)
        self._e2e_result=None
        self._e2e_job=SshEndToEndJob(hops,target,port,user,self.ssh_timeout.currentData())
        self._e2e_job.signals.progress.connect(self._on_e2e_progress)
        self._e2e_job.signals.finished.connect(self._on_e2e_done)
        QThreadPool.globalInstance().start(self._e2e_job)
    def cancel_e2e_hops(self):
        job=getattr(self,'_e2e_job',None)
        if job is not None:job.cancel()
        self.ssh_e2e_cancel.setEnabled(False)
        self.diagnostic_output.appendPlainText('Annulation demandée ; attente de la fin des opérations réseau en cours…')
    def _on_e2e_progress(self,event):
        from ssh_diagnostic_view import stage_rows
        try: stage_rows([event])
        except (ValueError,TypeError): return
        self.diagnostic_output.appendPlainText(event['step']+' : '+event['state'])
        if not hasattr(self,'_ssh_live_events'): self._ssh_live_events=[]
        self._ssh_live_events.append(dict(event))
        self._render_ssh_stages(self._ssh_live_events)

    def _render_ssh_stages(self,events,status=None):
        from ssh_diagnostic_view import compact_stage_rows
        try: rows=compact_stage_rows(events,status)
        except (ValueError,TypeError): return
        self.ssh_stage_view.clear()
        for row in rows:
            duration=row.get('duration_ms')
            item=QTreeWidgetItem([row['step'],row['label'],f'{duration} ms' if duration is not None else '—'])
            item.setForeground(1,QColor(row['color']))
            self.ssh_stage_view.addTopLevelItem(item)
        for col in range(3):self.ssh_stage_view.resizeColumnToContents(col)

    def _on_e2e_done(self,result):
        self.diagnostic_output.setPlainText('\n'.join(
            e['step']+' : '+e['state'] for e in result.get('events',[]))+'\n'+result.get('message',''))
        self._render_ssh_stages(result.get('events',[]),result.get('status'))
        try:
            from ssh_troubleshooting_playbook import build_playbook, format_playbook
            self.diagnostic_output.appendPlainText('\n'+format_playbook(build_playbook(result)))
        except (ValueError,TypeError):
            self.diagnostic_output.appendPlainText('\nAnalyse indicative indisponible.')
        self._ssh_live_events=[]
        self.ssh_e2e.setEnabled(True)
        self.ssh_e2e_cancel.setEnabled(False)
        self._e2e_result=result
        self.ssh_export.setEnabled(True)
        self.ssh_compare.setEnabled(True)
        self.ssh_save_history.setEnabled(True)

    def _ssh_history(self):
        from ssh_diagnostic_history import DiagnosticHistory
        return DiagnosticHistory(ROOT / 'ssh-diagnostics.sqlite3')

    def _selected_route_token(self):
        name=self.ssh_scope_name.text()
        secret=self.ssh_scope_secret.text()
        if not name and not secret:return None
        if not name or not secret:
            self.ssh_scope_secret.clear()
            raise ValueError('Identifiant et clé requis ensemble')
        from ssh_route_scope import route_token
        try:return route_token(name,secret.encode('utf-8'))
        finally:self.ssh_scope_secret.clear()

    def save_e2e_history(self):
        result=getattr(self,'_e2e_result',None)
        if result is None:return
        if QMessageBox.question(self,'Historique SSH local','Enregistrer uniquement les états et durées anonymisés dans une base SQLite locale ?',QMessageBox.Yes|QMessageBox.No)!=QMessageBox.Yes:return
        try:
            from ssh_diagnostic_report import summarize
            self._ssh_history().add(summarize(result),route_id=self._selected_route_token())
            self.ssh_save_history.setEnabled(False)
        except (ValueError,TypeError,KeyError,OSError,sqlite3.Error):
            QMessageBox.warning(self,'Historique SSH','Enregistrement impossible (vérifier l’identifiant et la clé).')

    def show_e2e_history(self):
        from ssh_history_dashboard import HistoryDashboard
        try:token=self._selected_route_token()
        except ValueError:
            QMessageBox.warning(self,'Parcours SSH','Identifiant ou clé de pseudonymisation invalide.');return
        dialog=HistoryDashboard(self._ssh_history(),self,route_id=token)
        dialog.exec()

    def purge_e2e_history(self):
        if QMessageBox.question(self,'Purge SSH','Supprimer définitivement les diagnostics de plus de 30 jours ?',QMessageBox.Yes|QMessageBox.No)!=QMessageBox.Yes:return
        try:
            import time
            deleted=self._ssh_history().purge_before(int(time.time())-30*86400)
            self.diagnostic_output.setPlainText(f'Purge terminée : {deleted} diagnostic(s) supprimé(s).')
        except (ValueError,OSError,sqlite3.Error):
            QMessageBox.warning(self,'Purge SSH','Purge impossible.')

    def compare_e2e_report(self):
        result=getattr(self,'_e2e_result',None)
        if result is None:return
        path,_=QFileDialog.getOpenFileName(self,'Comparer les diagnostics SSH','','JSON (*.json)')
        if not path:return
        try:
            from pathlib import Path
            from ssh_diagnostic_compare import compare_with_result
            if Path(path).stat().st_size>65536:raise ValueError('Rapport trop volumineux')
            comparison=compare_with_result(Path(path).read_text(encoding='utf-8'),result)
        except (OSError,UnicodeError,ValueError,TypeError,KeyError):
            QMessageBox.warning(self,'Comparaison SSH','Rapport JSON invalide ou inaccessible.');return
        lines=['Comparaison SSH : ancien → actuel (durées en ms)']
        for row in comparison['steps']:
            delta='non comparable' if row['delta_ms'] is None else f"{row['delta_ms']:+d} ms"
            lines.append(f"{row['step']} : {row['previous_state']} → {row['current_state']} · {delta}")
        lines.append('Attention : comparer uniquement des parcours SSH identiques.')
        self.diagnostic_output.setPlainText('\n'.join(lines))

    def export_e2e_report(self):
        result=getattr(self,'_e2e_result',None)
        if result is None:return
        from ssh_diagnostic_report import export_json
        try:payload=export_json(result)
        except (ValueError,TypeError,KeyError):
            QMessageBox.warning(self,'Export SSH','Résultat de diagnostic invalide.');return
        path,_=QFileDialog.getSaveFileName(self,'Exporter le diagnostic anonymisé','openremote-ssh-diagnostic.json','JSON (*.json)')
        if not path:return
        try:
            from pathlib import Path
            Path(path).write_text(payload,encoding='utf-8')
        except OSError:
            QMessageBox.warning(self,'Export SSH','Impossible de sauvegarder le rapport.')

    def save(self):
        try:self.result_route=self.route_value()
        except ValueError as exc:QMessageBox.warning(self,'Parcours SSH invalide',str(exc));return
        self.accept()
    def route_value(self):
        from ssh_path_editor import hops_to_route
        return hops_to_route(self.hops,self.base)

class Main(QMainWindow):
    def __init__(self):
        super().__init__();self.setWindowTitle('OpenRemote Studio V'+application_version()+' — Abdelhalim Talbi');self.resize(1350,850)
        self.workspace=Workspace(ROOT/'workspace.json');self.store=Store(ROOT/'connections.json');self.routes=RouteStore(ROOT/'routes.json');self.pam_profiles=PamProfileStore(ROOT/'pam-profiles.json');self.rdp_files=[];self.rdp_directory=ROOT/'rdp-sessions';cleanup_stale(self.rdp_directory);self.vault=Vault(ROOT/'vault.enc');self.vault_data=None;self.vault_password=None;self.processes=[];self.probe_history=ProbeHistory(ROOT/'probes.sqlite3');self.session_history=SessionHistory(ROOT/'sessions.sqlite3');self.external_sessions=ExternalSessionRegistry(self.session_history);self.pool=QThreadPool.globalInstance();self.sftp_jobs=[];self.transfer_journal=TransferJournal(ROOT/'transfers.sqlite3')
        self.session_refresh_timer=QTimer(self)
        self.session_refresh_timer.setInterval(3000)
        self.session_refresh_timer.timeout.connect(self.refresh_session_overview)
        self.vault_timer=QTimer(self);self.vault_timer.setSingleShot(True)
        self.vault_timer.setInterval(5*60*1000);self.vault_timer.timeout.connect(self.lock_vault)
        root=QWidget();self.setCentralWidget(root);layout=QVBoxLayout(root);bar=QHBoxLayout();layout.addLayout(bar)
        # Keep the primary workflow visible; move advanced operations into menus.
        self.primary_action_buttons={}
        self.responsive_toolbar_buttons={}
        for title,key,fn,tip in [
            ('＋ Nouvelle connexion',None,self.add,'Créer un nouvel accès SSH, RDP, VNC ou SFTP'),
            ('▶ Ouvrir', 'connect',self.connect,'Ouvrir la connexion sélectionnée · double-clic dans la liste'),
            ('Vérifier accès','check_access',self.check_access,'Vérifier explicitement l’accès sélectionné'),
            ('Transfert SFTP','sftp',self.sftp,'Disponible uniquement pour une connexion SSH ou SFTP'),
            ('Diagnostic local',None,self.show_local_readiness,'Vérifier les clients installés sur ce poste'),
            ('Aide',None,self.show_quick_guide,'Démarrage rapide et raccourcis · F1'),
        ]:
            button=QPushButton(title);button.setToolTip(tip);button.setAccessibleName(title)
            button.clicked.connect(fn);bar.addWidget(button)
            if key:self.primary_action_buttons[key]=button
            action_name = {"▶ Ouvrir":"connect", "Vérifier accès":"check_access", "Transfert SFTP":"sftp", "Diagnostic local":"diagnostic", "Aide":"help"}.get(title)
            if action_name:self.responsive_toolbar_buttons[action_name]=button
        self.toolbar_more_button=QPushButton("Plus ▾")
        self.toolbar_more_button.setObjectName("responsiveToolbarMore")
        self.toolbar_more_button.setAccessibleName("Autres actions de connexion")
        self.toolbar_more_menu=QMenu(self.toolbar_more_button)
        self.toolbar_more_menu.aboutToShow.connect(self._update_responsive_toolbar)
        self.toolbar_more_button.setMenu(self.toolbar_more_menu)
        bar.addWidget(self.toolbar_more_button)
        self._update_primary_action_buttons(None)
        # Unified, always-visible navigation: reuse existing workspace tabs.
        from workspace_navigation import primary_views
        navigation=QHBoxLayout();layout.addLayout(navigation)
        self.primary_navigation_buttons=[]
        for title,method,shortcut in primary_views():
            button=QPushButton(title)
            button.setObjectName('primaryNavigation'+method)
            button.setCheckable(True)
            button.setAccessibleName('Navigation '+title)
            button.setToolTip('Vue principale · '+shortcut)
            button.clicked.connect(getattr(self,method))
            navigation.addWidget(button)
            self.primary_navigation_buttons.append(button)
        navigation.addStretch(1)
        menu=self.menuBar().addMenu('Connexions')
        for title,fn in [('Ajouter',self.add),('Modifier',self.edit),('Supprimer',self.remove),
                         ('Favori',self.toggle_favorite),('Fiche de connexion',self.show_connection_card),('Chronologie connexion',self.show_connection_timeline),('Reconnecter (session terminée)',self.reconnect_selected),('Inventaire',self.show_inventory),
                         ('Exporter',self.export_inventory),('Assistant accès',self.access_wizard),('Passerelle / Rebond',self.edit_route),('Vérifier accès',self.check_access),('Tester port TCP',self.test_tcp_connection),('Tester via bastion SSH',self.test_ssh_jump_path),('Exporter diagnostic accès',self.export_access_diagnostic),('État PAM',self.show_pam_status),('Profils PAM',self.show_pam_profiles),('Corriger routes PAM',self.show_invalid_routes),('Laboratoire PAM (simulation)',self.show_pam_lab)]:
            menu.addAction(title,fn)
        menu=self.menuBar().addMenu('Sécurité')
        for title,fn in [('Ouvrir le coffre',self.open_vault),
                         ('Verrouiller le coffre',self.lock_vault),
                         ('Modifier un secret',self.edit_secret)]:
            menu.addAction(title,fn)
        menu=self.menuBar().addMenu('Outils')
        for title,fn in [('Accueil',self.show_home),('Fractionner la vue',self.split_view),
                         ('Diagnostic local',self.show_local_readiness),('Outils installés',self.show_integrations),('Diagnostic clients Windows',self.show_windows_clients),('Vue sessions',self.show_session_overview),('Historique sessions',self.show_session_history),('Fiabilité connexions',self.show_connection_reliability),('Historique diagnostics',self.show_probe_history),('Sessions externes',self.show_external_sessions),('Historique SFTP',self.show_transfer_history),('Tunnel SSH local (sécurisé)',self.show_ssh_tunnel),('Comparer NetBox (lecture seule)',self.show_netbox_preview),('Inventaire Windows WinRM (lecture seule)',self.show_winrm_inventory),('Services Windows WinRM (lecture seule)',self.show_winrm_services),('Alertes Zabbix (lecture seule)',self.show_zabbix_alerts),('Tableaux Grafana (lecture seule)',self.show_grafana_dashboards),('Ansible — prévalidation et check mode',self.show_ansible_preflight),('Qualification interface',self.show_qa_summary)]:
            menu.addAction(title,fn)
        help_menu=self.menuBar().addMenu('Aide')
        help_menu.addAction('Démarrage rapide et raccourcis (F1)',self.show_quick_guide)
        self.favorites_only=QPushButton('★ Favoris uniquement');self.favorites_only.setCheckable(True)
        self.favorites_only.setToolTip('Afficher seulement les connexions favorites')
        self.favorites_only.toggled.connect(self.refresh);bar.addWidget(self.favorites_only)
        self.search=QLineEdit();self.search.setObjectName('globalConnectionSearch');self.search.setClearButtonEnabled(True);self.search.setToolTip('Recherche immédiate dans les connexions · Ctrl+F');self.search.setPlaceholderText('Rechercher : serveur, groupe, protocole, tag…');self.search.textChanged.connect(self.refresh);bar.addWidget(self.search,1)
        self.filter_info=QLabel();self.filter_info.setObjectName('connectionFilterInfo');self.filter_info.setAccessibleName('Résultats de recherche des connexions');bar.addWidget(self.filter_info)
        self.reset_filters_button=QPushButton('Effacer filtres');self.reset_filters_button.setObjectName('resetConnectionFilters');self.reset_filters_button.setToolTip('Effacer la recherche et afficher toutes les connexions');self.reset_filters_button.clicked.connect(self.reset_connection_filters);bar.addWidget(self.reset_filters_button)
        split=QSplitter();split.setObjectName('mainWorkspaceSplitter');layout.addWidget(split,1);self.tree=QTreeWidget();self.tree.setHeaderLabels(['Connexions','Protocole','Hôte']);self.tree.itemDoubleClicked.connect(lambda *_:self.connect());self.tree.currentItemChanged.connect(self.update_inspector);self.tree.setToolTip('Double-clic : ouvrir · Clic droit : actions de connexion');self.tree.setContextMenuPolicy(Qt.CustomContextMenu);self.tree.customContextMenuRequested.connect(self.connection_context_menu);split.addWidget(self.tree)
        self.tabs=QTabWidget();self.tabs.currentChanged.connect(self._update_session_refresh);self.tabs.currentChanged.connect(self._sync_primary_navigation);self.tabs.setDocumentMode(True);self.tabs.setMovable(True);self.tabs.setTabsClosable(True);self.tabs.tabCloseRequested.connect(self.close_tab);split.addWidget(self.tabs);split.setStretchFactor(1,4);split.setChildrenCollapsible(False);split.setSizes([370,980])
        home=QWidget();h=QVBoxLayout(home)
        from home_workspace import create_home_header
        h.addWidget(create_home_header({name:getattr(self,name) for name in ('add','connect','check_access','show_session_overview','show_local_readiness','show_session_history','show_incident_overview','focus_connection_search')}))
        tool=QHBoxLayout();h.addLayout(tool)
        for name,cmd in [('Ping','ping'),('DNS','nslookup'),('Traceroute','tracert' if os.name=='nt' else 'traceroute')]:
            b=QPushButton(name);b.clicked.connect(lambda _,c=cmd:self.network(c));tool.addWidget(b)
        self.log=QTextEdit();self.log.setReadOnly(True);h.addWidget(self.log);self.tabs.addTab(home,'Accueil');self.home=home;self._sync_primary_navigation();self.install_tab_shortcuts();self.refresh()
        self._install_dashboard(h)
        self._install_quick_access(h)
        self.incident_label=QLabel('Incidents de connexion : ouvrir la synthèse pour actualiser.')
        self.incident_label.setWordWrap(True);h.insertWidget(1,self.incident_label)
        operations_button=QPushButton('Tableau de bord opérationnel');operations_button.setToolTip('Synthèse locale en lecture seule, sans test réseau');operations_button.clicked.connect(self.show_operations_dashboard);h.insertWidget(3,operations_button)
        self._install_toolbox()
        self._install_connection_inspector()
        self.statusBar().showMessage('Sélectionnez un serveur puis ▶ Ouvrir · Ctrl+F : rechercher · F1 : aide')
        self.statusBar().setAccessibleName('État de l’application et des connexions')
        self.tree.setAccessibleName('Inventaire des connexions')
        self.tabs.setAccessibleName('Espace de travail et sessions')
        self.tree.setAlternatingRowColors(True)
        self.tree.setUniformRowHeights(True)
        self.tree.setAllColumnsShowFocus(True)
        self.tabs.setElideMode(Qt.TextElideMode.ElideRight)
        self._show_route_warning()
        self._install_shortcuts()
        from windows_ui_theme import MAIN_STYLESHEET
        self.setStyleSheet(MAIN_STYLESHEET)
        self._update_responsive_toolbar()
        self.setMinimumSize(900,600)
        self.search.setFocusPolicy(Qt.StrongFocus)
    def resizeEvent(self, event):
        super().resizeEvent(event)
        if hasattr(self, 'toolbar_more_menu'):
            self._update_responsive_toolbar()

    def _update_responsive_toolbar(self):
        from responsive_toolbar import collapsed_actions
        hidden = collapsed_actions(self.width())
        self.toolbar_more_menu.clear()
        for name in ('check_access', 'sftp', 'diagnostic', 'help'):
            button = self.responsive_toolbar_buttons[name]
            button.setVisible(name not in hidden)
            if name in hidden:
                action = self.toolbar_more_menu.addAction(button.text())
                action.setEnabled(button.isEnabled())
                action.setToolTip(button.toolTip())
                action.triggered.connect(button.click)
        self.toolbar_more_button.setVisible(bool(hidden))

    def focus_connection_search(self):
        """Return to the connection workspace and focus its global search."""
        self.tabs.setCurrentWidget(self.home)
        self.search.setFocus()
        self.search.selectAll()

    def show_quick_guide(self):
        """Contextual onboarding in one reusable workspace tab, without network activity."""
        if hasattr(self, 'quick_guide_tab') and self.tabs.indexOf(self.quick_guide_tab) >= 0:
            self.tabs.setCurrentWidget(self.quick_guide_tab)
            return
        pane=QWidget()
        pane.setObjectName('quickGuideTab')
        layout=QVBoxLayout(pane)
        heading=QLabel('Démarrage rapide · OpenRemote Studio')
        heading.setObjectName('quickGuideHeading')
        layout.addWidget(heading)
        for label,details in [
            ('1 · Créer une connexion', 'Utilisez ＋ Connexion puis choisissez SSH, RDP, VNC ou SFTP.'),
            ('2 · Retrouver un serveur', 'Recherchez son nom, hôte, groupe ou protocole avec Ctrl+F.'),
            ('3 · Vérifier avant ouverture', 'Sélectionnez une connexion puis utilisez Vérifier accès ou Diagnostic.'),
            ('4 · Ouvrir la session', 'Double-cliquez sur la connexion ou choisissez Connecter.'),
            ('5 · Gérer les accès indirects', 'Connexions → Passerelle / Rebond ; configurez la route avant de vous connecter.'),
            ('Raccourcis clavier', 'F1 : aide · Ctrl+F : rechercher · Ctrl+Maj+F : effacer filtres · Ctrl+E : favoris · Ctrl+1/2/3/4 : Connexions/Sessions/Diagnostics/Transferts.')]:
            title=QLabel(label);title.setWordWrap(True)
            body=QLabel(details);body.setWordWrap(True)
            layout.addWidget(title);layout.addWidget(body)
        layout.addStretch(1)
        self.quick_guide_tab=pane
        self.tabs.addTab(pane,'Guide rapide')
        self.tabs.setCurrentWidget(pane)

    def show_qa_summary(self):
        """Show only sanitized statuses; never start probes or expose report contents."""
        from qa_ui_summary import load_summary
        try:
            summary=load_summary(ROOT/'qualification-windows-campaign.json')
        except (OSError,ValueError,UnicodeError):
            summary='Rapport de qualification invalide ou illisible. Relancer la campagne Windows.'
        pane=QWidget();layout=QVBoxLayout(pane)
        label=QLabel('Qualification de l’interface · Résultats locaux');layout.addWidget(label)
        content=QPlainTextEdit();content.setReadOnly(True);content.setPlainText(summary);layout.addWidget(content)
        self.tabs.addTab(pane,'Qualification');self.tabs.setCurrentWidget(pane)

    def _install_connection_inspector(self):
        """Docked contextual actions, never a second portal or embedded credential view."""
        from inspector_panel import create_inspector_panel
        from inspector_action_layout import inspector_action_groups
        handlers={method:getattr(self,method) for _,actions in inspector_action_groups() for _,method,_ in actions}
        dock,self.inspector_text,self.inspector_actions=create_inspector_panel(self,handlers)
        self.addDockWidget(Qt.RightDockWidgetArea,dock)
        self.inspector_dock=dock
        view_menu=self.menuBar().addMenu('Affichage')
        view_menu.addAction(dock.toggleViewAction())
        self.update_inspector()

    def _update_primary_action_buttons(self, selected):
        from connection_action_state import primary_action_state
        states=primary_action_state(selected)
        for key,button in self.primary_action_buttons.items():
            button.setEnabled(states[key])

    def update_inspector(self,*_):
        if not hasattr(self,'inspector_text'):return
        selected=self.selected()
        self._update_primary_action_buttons(selected)
        favorites=self.workspace.data.get('favorites',[])
        active_ids=()
        if selected and self.external_sessions.has_running(selected['id']):active_ids=(selected['id'],)
        self.inspector_text.setText(inspect_connection(selected,favorites,active_ids) if selected else 'Sélectionnez une connexion dans la liste pour afficher ses détails et les actions disponibles.')
        for button in self.inspector_actions:
            button.setEnabled(selected is not None)

    def _install_shortcuts(self):
        """Shortcuts stay bound to the main window; no global key interception."""
        self.shortcuts=[]
        from workspace_shortcuts import workspace_shortcuts
        for keys,method in workspace_shortcuts():
            handler=getattr(self,method)
            shortcut=QShortcut(QKeySequence(keys),self)
            shortcut.activated.connect(handler)
            self.shortcuts.append(shortcut)
        self.search.setToolTip('Ctrl+F / Ctrl+L : rechercher · Ctrl+Maj+F : effacer · Ctrl+E : favoris')

    def clear_and_focus_connection_search(self):
        """Reset filters and return keyboard focus to the inventory search."""
        self.reset_connection_filters()

    def toggle_favorites_filter(self):
        """Toggle local favorites without initiating a remote session."""
        self.favorites_only.setChecked(not self.favorites_only.isChecked())

    def close_current_tab(self):
        self.close_tab(self.tabs.currentIndex())

    def next_tab(self):
        if self.tabs.count()>1:self.tabs.setCurrentIndex((self.tabs.currentIndex()+1)%self.tabs.count())

    def previous_tab(self):
        if self.tabs.count()>1:self.tabs.setCurrentIndex((self.tabs.currentIndex()-1)%self.tabs.count())

    def show_connection_reliability(self):
        """One searchable, local-process reliability view; no extra portal."""
        self.external_sessions.snapshot()
        dialog=QDialog(self);dialog.setWindowTitle('Fiabilité des connexions — processus locaux')
        dialog.resize(980,520);layout=QVBoxLayout(dialog)
        layout.addWidget(QLabel('Codes de sortie locaux uniquement : un code zéro ne confirme pas une session distante.'))
        controls=QHBoxLayout();layout.addLayout(controls)
        search=QLineEdit();search.setPlaceholderText('Rechercher connexion ou protocole…');controls.addWidget(search)
        failures=QCheckBox('Avec échecs observés');controls.addWidget(failures)
        view=QTreeWidget();view.setHeaderLabels(['Connexion','Protocole','Tentatives','Sorties observées','Code 0','Échecs','Inconnues','Couverture','Codes 0 / observées','Diagnostic'])
        layout.addWidget(view)
        try:
            rows=enrich_statistics(self.session_history.statistics())
        except Exception as exc:
            rows=[];QMessageBox.warning(dialog,'Statistiques indisponibles',str(exc))
        def render():
            view.clear()
            for r in filter_statistics(rows,search.text(),failures.isChecked()):
                pct=lambda n:'—' if n is None else f'{n:.1f}%'
                view.addTopLevelItem(QTreeWidgetItem([r['name'],r['protocol'],str(r['attempts']),
                    str(r['observed']),str(r['success']),str(r['failed']),str(r['unobserved']),
                    pct(r['observation_rate']),pct(r['local_zero_exit_rate']),r['risk']]))
            for i in range(view.columnCount()):view.resizeColumnToContents(i)
        search.textChanged.connect(lambda *_:render());failures.toggled.connect(lambda *_:render());render()
        close=QPushButton('Fermer');close.clicked.connect(dialog.accept);layout.addWidget(close)
        dialog.exec()

    def show_session_history(self):
        self.external_sessions.snapshot()  # Reconcile finished processes before reading.
        dialog=QDialog(self);dialog.setWindowTitle('Historique local des sessions')
        dialog.resize(800,470);layout=QVBoxLayout(dialog)
        layout.addWidget(QLabel('Historique SQLite local — aucune adresse, commande ni donnée secrète enregistrée.'))
        view=QTreeWidget();view.setHeaderLabels(['Connexion','Protocole','PID','Début UTC','Fin UTC','Code'])
        layout.addWidget(view)
        try:
            for r in self.session_history.recent():
                view.addTopLevelItem(QTreeWidgetItem([str(r['name']),str(r['protocol']),str(r['pid']),
                    str(r['started_at']),str(r['finished_at'] or 'Non observée'),
                    str(r['exit_code']) if r['exit_code'] is not None else '—']))
        except Exception as exc:
            QMessageBox.warning(dialog,'Historique indisponible',str(exc))
        if self.external_sessions.history_errors:
            layout.addWidget(QLabel('Attention : des écritures du journal ont échoué pendant cette exécution.'))
        close=QPushButton('Fermer');close.clicked.connect(dialog.accept);layout.addWidget(close)
        dialog.exec()

    def show_session_overview(self):
        """Internal tab summarizing external processes, without embedding remote desktops."""
        if getattr(self,'session_overview',None) is not None:
            if self.tabs.indexOf(self.session_overview)>=0:
                self.tabs.setCurrentWidget(self.session_overview)
                self.refresh_session_overview()
                return
        pane=QWidget();self.session_overview=pane
        layout=QVBoxLayout(pane)
        layout.addWidget(QLabel('Sessions externes · suivi local des processus SSH / SFTP / RDP / VNC'))
        layout.addWidget(QLabel('Une fenêtre cliente reste externe. Son PID ne prouve pas l’état de la session distante.'))
        filters=QHBoxLayout();layout.addLayout(filters)
        self.session_search=QLineEdit();self.session_search.setPlaceholderText('Filtrer nom, protocole, PID…')
        self.session_search.textChanged.connect(self.refresh_session_overview)
        filters.addWidget(self.session_search)
        self.session_state=QComboBox();self.session_state.addItem('Toutes','all')
        self.session_state.addItem('Actives','running');self.session_state.addItem('Terminées','exited');self.session_state.addItem('En erreur','failed');self.session_state.addItem('État inconnu','unknown')
        self.session_state.currentIndexChanged.connect(self.refresh_session_overview)
        filters.addWidget(self.session_state)
        self.session_reset_filters=QPushButton('Effacer les filtres')
        self.session_reset_filters.setObjectName('resetSessionFilters')
        self.session_reset_filters.setToolTip('Afficher toutes les sessions sans supprimer leur historique')
        self.session_reset_filters.clicked.connect(self.reset_session_filters)
        filters.addWidget(self.session_reset_filters)
        self.session_summary=QLabel('');layout.addWidget(self.session_summary)
        self.session_visible_summary=QLabel('');self.session_visible_summary.setObjectName('sessionVisibleSummary');layout.addWidget(self.session_visible_summary)
        self.session_empty=QLabel('');self.session_empty.setWordWrap(True);layout.addWidget(self.session_empty)
        self.session_overview_list=QTreeWidget()
        self.session_overview_list.setHeaderLabels(['Connexion','Protocole','PID','État','Démarrage UTC'])
        self.session_overview_list.setToolTip('Sessions actives en premier, puis état inconnu, échecs et sessions terminées ; état du processus local uniquement.')
        self.session_overview_list.setContextMenuPolicy(Qt.CustomContextMenu)
        self.session_overview_list.customContextMenuRequested.connect(self.session_overview_context_menu)
        self.session_overview_list.itemSelectionChanged.connect(self._update_session_reconnect)
        self.session_overview_list.itemSelectionChanged.connect(self.refresh_guidance_panel)
        self.session_overview_list.itemDoubleClicked.connect(self.inspect_selected_session)
        self.session_overview_list.setAccessibleName('Liste des sessions externes')
        self.session_overview_list.setAccessibleDescription('F5 actualise ; Ctrl+C copie les détails ; double-clic affiche les détails ; menu contextuel pour reconnecter.')
        self.session_copy_shortcut=QShortcut(QKeySequence('Ctrl+C'),self.session_overview_list)
        self.session_copy_shortcut.activated.connect(self.copy_selected_session_details)
        self.session_refresh_shortcut=QShortcut(QKeySequence('F5'),self.session_overview_list)
        self.session_refresh_shortcut.activated.connect(self.refresh_session_overview)
        self.session_workspace_splitter=QSplitter(Qt.Vertical)
        self.session_workspace_splitter.setObjectName('sessionWorkspaceSplitter')
        self.session_workspace_splitter.setChildrenCollapsible(False)
        self.session_workspace_splitter.addWidget(self.session_overview_list)
        self.session_incident_container=QWidget()
        self.session_incident_layout=QVBoxLayout(self.session_incident_container)
        self.session_incident_heading=QLabel('Incidents locaux — sélectionnez une ligne pour retrouver la session')
        self.session_incident_heading.setObjectName('sessionIncidentHeading')
        self.session_incident_layout.addWidget(self.session_incident_heading)
        incident_filters=QHBoxLayout();self.session_incident_layout.addLayout(incident_filters)
        self.session_incident_search=QLineEdit();self.session_incident_search.setObjectName('sessionIncidentSearch')
        self.session_incident_search.setPlaceholderText('Rechercher une connexion en erreur…')
        self.session_incident_search.textChanged.connect(self.refresh_session_incidents)
        incident_filters.addWidget(self.session_incident_search)
        self.session_incident_severity=QComboBox();self.session_incident_severity.addItems(['Toutes les anomalies','Erreurs confirmées','États incertains'])
        self.session_incident_severity.setAccessibleName('Filtre de gravité des incidents')
        self.session_incident_severity.currentIndexChanged.connect(self.refresh_session_incidents)
        incident_filters.addWidget(self.session_incident_severity)
        self.session_incident_list=QTreeWidget();self.session_incident_list.setObjectName('sessionIncidentCenter')
        self.session_incident_list.setHeaderLabels(['Connexion','Protocole','Diagnostic','État'])
        self.session_incident_list.setMinimumHeight(120)
        self.session_incident_list.setAlternatingRowColors(True)
        self.session_incident_list.setSortingEnabled(False)
        self.session_incident_list.setToolTip('Double-clic : localiser une session après revalidation ; aucune reconnexion automatique.')
        self.session_incident_list.setAccessibleName('Centre des incidents de session')
        self.session_incident_list.itemDoubleClicked.connect(self.navigate_session_incident)
        self.session_incident_list.setAccessibleDescription('Flèches : parcourir les incidents ; Entrée : localiser la session après revalidation.')
        self.session_incident_list.itemActivated.connect(self.navigate_session_incident)
        self.session_incident_layout.addWidget(self.session_incident_list)
        self.session_incident_summary=QLabel('');self.session_incident_layout.addWidget(self.session_incident_summary)
        self.session_guidance_panel=QPlainTextEdit();self.session_guidance_panel.setReadOnly(True)
        self.session_guidance_panel.setObjectName('sessionGuidancePanel')
        self.session_guidance_panel.setAccessibleName('Diagnostic de la session sélectionnée')
        self.session_guidance_panel.setPlaceholderText('Sélectionnez une session pour afficher son diagnostic local.')
        self.session_incident_layout.addWidget(self.session_guidance_panel)
        self.session_incident_list.itemSelectionChanged.connect(self._focus_incident_guidance)
        self.session_workspace_splitter.addWidget(self.session_incident_container)
        self.session_workspace_splitter.setStretchFactor(0,3)
        self.session_workspace_splitter.setStretchFactor(1,2)
        self._restore_session_ui_preferences()
        layout.addWidget(self.session_workspace_splitter,1)
        self.session_incident_search.setToolTip('Ctrl+Alt+I : rechercher dans les incidents')
        self.session_incident_shortcut=QShortcut(QKeySequence('Ctrl+Alt+I'),pane)
        self.session_incident_shortcut.activated.connect(self.session_incident_search.setFocus)
        controls=QHBoxLayout();layout.addLayout(controls)
        refresh=QPushButton('Actualiser');refresh.clicked.connect(self.refresh_session_overview)
        controls.addWidget(refresh)
        clear=QPushButton('Purger les processus terminés');clear.setToolTip('Retire uniquement les entrées terminées du suivi local ; ne ferme aucune session.')
        clear.clicked.connect(self.clear_exited_overview);controls.addWidget(clear)
        details=QPushButton('Détails du processus');self.session_details_button=details;details.setEnabled(False);details.clicked.connect(self.inspect_selected_session)
        controls.addWidget(details)
        guided=QPushButton('Comprendre l’erreur');guided.setObjectName('guidedSessionDiagnosis');self.session_guided_button=guided;guided.setEnabled(False);guided.clicked.connect(self.show_selected_session_guidance);controls.addWidget(guided)
        reconnect=QPushButton('Reconnecter la session sélectionnée');self.session_reconnect_button=reconnect;reconnect.setEnabled(False);reconnect.clicked.connect(self.reconnect_overview_session)
        controls.addWidget(reconnect)
        diagnose=QPushButton('Diagnostiquer les échecs');diagnose.clicked.connect(self.show_session_diagnostics)
        controls.addWidget(diagnose)
        manage=QPushButton('Gestionnaire de sessions');manage.clicked.connect(self.show_external_sessions)
        controls.addWidget(manage)
        self.tabs.addTab(pane,'Sessions');self.tabs.setCurrentWidget(pane)
        self._update_session_refresh()
        self.refresh_session_overview()

    def _session_ui_settings(self):
        return QSettings('OpenRemoteStudio', 'OpenRemoteStudio')

    def _restore_session_ui_preferences(self):
        """Restore only harmless UI state; never restore process/session identity."""
        settings=self._session_ui_settings()
        try:
            severity=int(settings.value('sessions/incident_severity', 0))
            if 0 <= severity < self.session_incident_severity.count():
                self.session_incident_severity.setCurrentIndex(severity)
            sizes=settings.value('sessions/splitter_sizes', None)
            if isinstance(sizes,list) and len(sizes)==2:
                sizes=[int(v) for v in sizes]
                if all(120 <= v <= 10000 for v in sizes):
                    self.session_workspace_splitter.setSizes(sizes)
        except (ValueError, TypeError, OverflowError):
            pass

    def _save_session_ui_preferences(self):
        if not hasattr(self,'session_workspace_splitter'):
            return
        settings=self._session_ui_settings()
        settings.setValue('sessions/incident_severity', self.session_incident_severity.currentIndex())
        settings.setValue('sessions/splitter_sizes', self.session_workspace_splitter.sizes())

    def reset_session_filters(self):
        """Restore the complete session list; never alter the registry."""
        self.session_search.clear()
        self.session_state.setCurrentIndex(0)
        self.refresh_session_overview()

    def _update_session_refresh(self,*_):
        pane=getattr(self,'session_overview',None)
        visible=pane is not None and self.tabs.currentWidget() is pane
        if visible:
            if not self.session_refresh_timer.isActive():self.session_refresh_timer.start()
        else:self.session_refresh_timer.stop()

    def session_overview_context_menu(self,position):
        item=self.session_overview_list.itemAt(position)
        if item is None:return
        self.session_overview_list.setCurrentItem(item)
        menu=QMenu(self)
        reconnect=menu.addAction('Reconnecter la connexion (si session terminée)')
        reconnect.setEnabled(self._selected_session_reconnect_allowed())
        inspect=menu.addAction('Afficher détails du processus')
        copy=menu.addAction('Copier les détails du processus')
        choice=menu.exec(self.session_overview_list.viewport().mapToGlobal(position))
        if choice is reconnect:self.reconnect_overview_session()
        elif choice is inspect or choice is copy:
            identity=item.data(0,Qt.UserRole)
            pid=item.data(0,Qt.UserRole+1)
            row=selected_session(self.external_sessions.snapshot(), identity, pid)
            if row:
                details=session_process_details(row)
                if choice is copy:QApplication.clipboard().setText(details)
                else:QMessageBox.information(self,'Processus externe',details)

    def copy_selected_session_details(self,*_):
        """Copy only the selected, uniquely identified process; never launch it."""
        item=self.session_overview_list.currentItem()
        if item is None:return
        identity=item.data(0,Qt.UserRole)
        pid=item.data(0,Qt.UserRole+1)
        row=selected_session(self.external_sessions.snapshot(),identity,pid)
        if row is None:
            QMessageBox.information(self,'Processus indisponible',
                'La session sélectionnée a disparu ou son identité est ambiguë. Actualisez la liste.')
            return
        QApplication.clipboard().setText(session_process_details(row))

    def inspect_selected_session(self,*_):
        """Read-only inspection of the exact selected local process; never reconnect."""
        item=self.session_overview_list.currentItem()
        if item is None:return
        identity=item.data(0,Qt.UserRole)
        pid=item.data(0,Qt.UserRole+1)
        row=selected_session(self.external_sessions.snapshot(),identity,pid)
        if row is None:
            QMessageBox.information(self,'Processus indisponible',
                'La session sélectionnée a disparu ou son identité est ambiguë. Actualisez la liste.')
            return
        QMessageBox.information(self,'Détails du processus',session_process_details(row))

    def _selected_session_reconnect_allowed(self):
        item=self.session_overview_list.currentItem()
        if item is None:return False
        identity=item.data(0,Qt.UserRole)
        pid=item.data(0,Qt.UserRole+1)
        return selected_reconnect_allowed(self.external_sessions.snapshot(),identity,pid)

    def _update_session_reconnect(self):
        self.session_reconnect_button.setEnabled(self._selected_session_reconnect_allowed())
        self.session_details_button.setEnabled(self.session_overview_list.currentItem() is not None)
        self.session_guided_button.setEnabled(self.session_overview_list.currentItem() is not None)

    def refresh_session_overview(self,*_):
        if not getattr(self,'session_overview_list',None):return
        rows=self.external_sessions.snapshot()
        counts=session_counts(rows)
        self.session_summary.setText(f"{counts['running']} active(s) · {counts['exited']} terminée(s) · {counts['failed']} en erreur · {counts['unknown']} indéterminée(s) · {counts['total']} au total")
        selected=self.session_overview_list.currentItem()
        previous=(selected.data(0,Qt.UserRole),selected.data(0,Qt.UserRole+1)) if selected else None
        self.session_overview_list.clear()
        visible=prioritized_sessions(filter_sessions(rows,self.session_search.text(),self.session_state.currentData()))
        self.session_visible_summary.setText(session_visibility_summary(len(rows),len(visible)))
        self.session_empty.setText(session_empty_message(len(rows),self.session_search.text(),self.session_state.currentData()) if not visible else '')
        preserved=preserved_session_identity(visible, previous)
        for item in visible:
            entry=QTreeWidgetItem([item['name'],item['protocol'],str(item['pid']),
                session_status_label(item),item['started_at']])
            state, explanation = session_visual_state(item)
            entry.setToolTip(3, explanation)
            entry.setAccessibleDescription(explanation)
            # Highlight the state column only: never equate a local PID with a healthy remote session.
            state_colors = {'running':'#166534','completed':'#1d4ed8','failed':'#b91c1c','unknown':'#854d0e'}
            entry.setForeground(3, QColor(state_colors[state]))
            entry.setData(0,Qt.UserRole,item['connection_id'])
            entry.setData(0,Qt.UserRole+1,str(item['pid']))
            self.session_overview_list.addTopLevelItem(entry)
            if preserved is not None and session_identity(item)==preserved:self.session_overview_list.setCurrentItem(entry)
        self._update_session_reconnect()
        self.refresh_guidance_panel()
        self.refresh_session_incidents()

    def refresh_session_incidents(self,*_):
        """Index a fresh snapshot; no remote probe or reconnection."""
        if not hasattr(self,'session_incident_list'):return
        rows=self.external_sessions.snapshot()
        items=incident_index(rows,self.session_incident_search.text())
        counts=incident_counts(items)
        level=self.session_incident_severity.currentIndex()
        if level==1:items=[i for i in items if i['diagnostic']['severity']=='error']
        elif level==2:items=[i for i in items if i['diagnostic']['severity']=='warning']
        self.session_incident_summary.setText(f"{len(items)} affiché(s) / {counts['total']} trouvé(s) · {counts['errors']} erreur(s) · {counts['uncertain']} état(s) incertain(s) · Entrée/double-clic : localiser")
        previous=self.session_incident_list.currentItem()
        previous_key=(previous.data(0,Qt.UserRole),previous.data(0,Qt.UserRole+1)) if previous else None
        self.session_incident_list.clear()
        for incident in items:
            item=QTreeWidgetItem([incident['name'],incident['protocol'],incident['diagnostic']['summary'],str(incident['status'])])
            # Capture an exact process identifier from the indexed snapshot, not merely a PID.
            row=rows[incident['row_index']]
            item.setData(0,Qt.UserRole,incident['connection_id'])
            item.setData(0,Qt.UserRole+1,str(row.get('pid')))
            self.session_incident_list.addTopLevelItem(item)
            if previous_key==(incident['connection_id'],str(row.get('pid'))):
                self.session_incident_list.setCurrentItem(item)
        if not items:self.session_guidance_panel.setPlainText('Aucun incident correspondant aux filtres. Aucun diagnostic distant n’a été exécuté.')

    def _focus_incident_guidance(self):
        """Explain selection without initiating a connection or trusting stale PID."""
        selected=self.session_incident_list.selectedItems()
        if not selected:
            self.session_guidance_panel.setPlainText('Sélectionnez un incident pour afficher ses détails.')
            return
        item=selected[0]
        self.session_guidance_panel.setPlainText(
            'Incident sélectionné : '+item.text(0)+'\nProtocole : '+item.text(1)+
            '\nDiagnostic : '+item.text(2)+'\nÉtat : '+item.text(3)+
            '\n\nDouble-clic : retrouver la session après contrôle d’identité. Aucune reconnexion automatique.')

    def navigate_session_incident(self,item,*_):
        """Locate only if the original process is still uniquely identifiable."""
        identity=item.data(0,Qt.UserRole);pid=item.data(0,Qt.UserRole+1)
        row=selected_session(self.external_sessions.snapshot(),identity,pid)
        if row is None:
            QMessageBox.warning(self,'Session modifiée','Identité absente ou ambiguë : actualisez les sessions.')
            self.refresh_session_overview();return
        self.session_search.clear();self.session_state.setCurrentIndex(0)
        self.refresh_session_overview()
        for i in range(self.session_overview_list.topLevelItemCount()):
            candidate=self.session_overview_list.topLevelItem(i)
            if candidate.data(0,Qt.UserRole)==identity and candidate.data(0,Qt.UserRole+1)==pid:
                self.session_overview_list.setCurrentItem(candidate)
                self.session_overview_list.scrollToItem(candidate)
                return
        QMessageBox.information(self,'Session introuvable','La session n’est plus visible dans la liste actuelle.')

    def refresh_guidance_panel(self):
        panel=getattr(self,'session_guidance_panel',None)
        if panel is None:return
        item=self.session_overview_list.currentItem()
        if item is None:
            panel.setPlainText('Sélectionnez une session pour afficher un diagnostic local.')
            return
        row=selected_session(self.external_sessions.snapshot(),item.data(0,Qt.UserRole),item.data(0,Qt.UserRole+1))
        if row is None:
            panel.setPlainText('Identité du processus absente ou ambiguë. Actualisez la liste avant toute action.')
            return
        panel.setPlainText(format_guided_diagnostic(row)+'\n\nAucune connexion distante n’est testée automatiquement.')

    def show_selected_session_guidance(self):
        """Read-only guidance for an exact selected process, without network probes."""
        item=self.session_overview_list.currentItem()
        if item is None:return
        row=selected_session(self.external_sessions.snapshot(),item.data(0,Qt.UserRole),item.data(0,Qt.UserRole+1))
        if row is None:
            QMessageBox.warning(self,'Diagnostic indisponible','Session absente ou identité ambiguë. Actualisez la liste.')
            return
        message=format_guided_diagnostic(row)
        dialog=QDialog(self);dialog.setWindowTitle('Comprendre l’erreur de session')
        dialog.resize(680,350);layout=QVBoxLayout(dialog)
        note=QLabel('Diagnostic indicatif du processus local uniquement. Aucune vérification distante ni reconnexion automatique.')
        note.setWordWrap(True);layout.addWidget(note)
        view=QPlainTextEdit();view.setReadOnly(True);view.setPlainText(message);layout.addWidget(view)
        buttons=QHBoxLayout();layout.addLayout(buttons)
        copy=QPushButton('Copier le diagnostic');copy.clicked.connect(lambda:QApplication.clipboard().setText(message));buttons.addWidget(copy)
        close=QPushButton('Fermer');close.clicked.connect(dialog.accept);buttons.addWidget(close)
        dialog.exec()

    def show_session_diagnostics(self):
        """Display suggestions only; never reconnect or modify remote systems."""
        report=summarize_diagnostics(self.external_sessions.snapshot())
        diagnostic_text=format_session_diagnostic(report)
        dialog=QDialog(self);dialog.setWindowTitle('Diagnostic local des sessions')
        dialog.resize(740,470);layout=QVBoxLayout(dialog)
        layout.addWidget(QLabel('Suggestions indicatives basées sur les codes de sortie locaux ; aucun diagnostic réseau réel.'))
        view=QPlainTextEdit();view.setReadOnly(True);view.setPlainText(diagnostic_text);layout.addWidget(view)
        actions=QHBoxLayout();layout.addLayout(actions)
        copy=QPushButton('Copier le diagnostic')
        copy.setObjectName('copySessionDiagnostics')
        copy.setToolTip('Copier uniquement la synthèse locale, sans identifiants ni secrets')
        copy.clicked.connect(lambda: QApplication.clipboard().setText(diagnostic_text))
        actions.addWidget(copy)
        close=QPushButton('Fermer');close.clicked.connect(dialog.accept);actions.addWidget(close)
        dialog.exec()

    def clear_exited_overview(self):
        count=self.external_sessions.clear_exited()
        self.refresh_session_overview()
        self.statusBar().showMessage(f'{count} entrée(s) de processus terminés retirée(s) du suivi local',7000)

    def reconnect_overview_session(self):
        item=self.session_overview_list.currentItem()
        if item is None:
            QMessageBox.information(self,'Reconnexion','Sélectionnez une session terminée.');return
        identity=item.data(0,Qt.UserRole)
        pid=item.data(0,Qt.UserRole+1)
        if not self._selected_session_reconnect_allowed():
            QMessageBox.information(self,'Reconnexion indisponible','Sélectionnez un processus terminé sans autre session active pour cette connexion.');return
        if self.external_sessions.has_running(identity):
            QMessageBox.information(self,'Session active','Une session externe est déjà active.');return
        target=next((c for c in self.store.items if c['id']==identity),None)
        if target is None:
            QMessageBox.warning(self,'Connexion absente','Cette connexion a été supprimée.');return
        # Do not consume a reconnect candidate for a deleted connection.
        # Resolve the destination in the tree BEFORE consuming the reconnect candidate.
        # A filtered or stale tree must never destroy the user's reconnect opportunity.
        self.tree.clearSelection()
        self.search.clear()
        self.favorites_only.setChecked(False)
        self.refresh()
        destination=None
        for index in range(self.tree.topLevelItemCount()):
            group=self.tree.topLevelItem(index)
            for subindex in range(group.childCount()):
                child=group.child(subindex)
                if child.data(0,Qt.UserRole)==identity:
                    destination=child
                    break
            if destination is not None:break
        if destination is None:
            QMessageBox.warning(self,'Connexion introuvable','Impossible de sélectionner la connexion.');return
        # Validate a fresh snapshot after UI navigation and before candidate consumption.
        from session_reconnect_choices import reconnect_choice_still_valid
        if not reconnect_choice_still_valid(self.external_sessions.snapshot(),identity,pid):
            QMessageBox.information(self,'Reconnexion indisponible','La session a changé ; actualisez la liste.');return
        from session_reconnect_controller import resolve_reconnect_target
        verified,reason=resolve_reconnect_target(self.external_sessions,self.store.items,identity,pid)
        if verified is None:
            QMessageBox.information(self,'Reconnexion indisponible',f'Contrôle préalable refusé : {reason}');return
        if not self.external_sessions.reconnect_candidate(identity,pid):
            QMessageBox.information(self,'Reconnexion','Aucune session terminée à reconnecter.');return
        self.tree.setCurrentItem(destination)
        self.connect()
        self.refresh_session_overview()

    def _show_route_warning(self):
        count=len(self.routes.invalid_routes)
        if count:
            self.statusBar().showMessage(f'ATTENTION : {count} route(s) PAM héritée(s) bloquée(s) — Connexions > Corriger routes PAM')

    def show_invalid_routes(self):
        invalid=self.routes.invalid_routes
        if not invalid:
            QMessageBox.information(self,'Routes PAM','Aucune route PAM invalide détectée.')
            return
        names={c['id']:c['name'] for c in self.store.items}
        lines=[f"{names.get(key,key)} : {reason}" for key,reason in sorted(invalid.items())]
        QMessageBox.warning(self,'Routes PAM à corriger',
            '\n'.join(lines)+'\n\nSélectionnez une connexion, puis Connexions > Passerelle / Rebond pour la corriger.')

    def _safe_route(self,connection_id):
        try:return self.routes.for_connection(connection_id)
        except ValueError as exc:
            QMessageBox.warning(self,'Route PAM bloquée',str(exc))
            return None

    def _install_dashboard(self,layout):
        self.dashboard_label=QLabel();self.dashboard_label.setWordWrap(True)
        layout.insertWidget(0,self.dashboard_label)
        self.update_dashboard()

    def update_dashboard(self):
        if not hasattr(self,'dashboard_label'):return
        info=summarize(self.store.items,self.workspace.data)
        by_protocol=' · '.join(f'{escape(str(k))}: {v}' for k,v in sorted(info['protocols'].items())) or 'Aucune connexion'
        names={c['id']:c['name'] for c in self.store.items}
        recent=', '.join(escape(names[i]) for i in info['recent'] if i in names) or 'Aucune'
        self.dashboard_label.setText(f"<h2>Bienvenue dans OpenRemote Studio</h2>"
            f"<p><b>{info['total']}</b> connexions · <b>{info['favorites']}</b> favoris</p>"
            f"<p>{by_protocol}</p><p><b>Récentes :</b> {recent}</p>"
            "<p>Ctrl+K : rechercher un outil ou une connexion.</p>")

    def _install_quick_access(self, layout):
        """Compact favorites/recent list: single click selects, double click opens."""
        panel=QWidget();vertical=QVBoxLayout(panel)
        heading=QLabel('Accès rapides · Favoris et connexions récentes')
        heading.setObjectName('quickAccessHeading');vertical.addWidget(heading)
        self.quick_access_list=QListWidget()
        self.quick_access_list.setObjectName('quickAccessList')
        self.quick_access_list.setMaximumHeight(175)
        self.quick_access_list.setToolTip('Un clic : sélectionner · Double-clic : ouvrir la session')
        self.quick_access_list.itemClicked.connect(lambda item:self._select_quick_access(item.data(Qt.UserRole)))
        self.quick_access_list.itemDoubleClicked.connect(lambda item:self._open_quick_access(item.data(Qt.UserRole)))
        self.quick_access_list.itemActivated.connect(lambda item:self._open_quick_access(item.data(Qt.UserRole)))
        vertical.addWidget(self.quick_access_list)
        hint=QLabel('Un clic sélectionne le serveur. Double-clic ouvre la connexion. Aucun test réseau automatique.')
        hint.setWordWrap(True);vertical.addWidget(hint)
        layout.insertWidget(1,panel)
        self._refresh_quick_access()

    def _refresh_quick_access(self):
        if not hasattr(self,'quick_access_list'):return
        entries=quick_access(self.store.items,self.workspace.data,limit=8)
        self.quick_access_list.clear()
        for entry in entries:
            prefix='★ ' if entry['favorite'] else '↺ '
            item=QListWidgetItem(prefix+entry['name']+' · '+entry['protocol']+' · '+entry['host'])
            item.setData(Qt.UserRole,entry['id'])
            self.quick_access_list.addItem(item)
        if not entries:
            empty=QListWidgetItem('Aucun favori ni connexion récente · ★ pour ajouter un favori')
            empty.setFlags(Qt.NoItemFlags)
            self.quick_access_list.addItem(empty)
        self.quick_access_list.setVisible(True)

    def _select_quick_access(self,identity):
        if not isinstance(identity,str) or sum(c['id']==identity for c in self.store.items)!=1:return False
        # Reset both filters so the chosen connection is always visible.
        self.search.clear()
        self.favorites_only.setChecked(False)
        self.refresh()
        for i in range(self.tree.topLevelItemCount()):
            parent=self.tree.topLevelItem(i)
            for j in range(parent.childCount()):
                child=parent.child(j)
                if child.data(0,Qt.UserRole)==identity:
                    self.tree.setCurrentItem(child)
                    return True
        return False

    def _open_quick_access(self,identity):
        if self._select_quick_access(identity):self.connect()

    def show_operations_dashboard(self):
        """Local evidence only; no network probes and no automatic reconnect."""
        from operations_dashboard import build_dashboard
        try:
            self.external_sessions.snapshot()
            report=build_dashboard(self.store.items,self.session_history.recent(1000),
                                   self.probe_history.recent(limit=500))
        except (OSError,ValueError,sqlite3.Error) as exc:
            QMessageBox.warning(self,'Tableau de bord indisponible',type(exc).__name__);return
        dialog=QDialog(self);dialog.setWindowTitle('Tableau de bord opérationnel — observations locales');dialog.resize(940,750)
        layout=QVBoxLayout(dialog)
        layout.addWidget(QLabel(f"Connexions : {report['connections']} | Échecs récurrents (30 min) : {report['recurrent_local_failures']} | Sans observations : {report['without_observations']}"))
        layout.addWidget(QLabel('Aucune disponibilité distante ni authentification validée par cette synthèse.'))
        from operations_dashboard_view import filtered_rows, diagnostic_hint
        controls=QHBoxLayout()
        search=QLineEdit();search.setPlaceholderText('Rechercher une connexion ou un protocole…')
        protocol=QComboBox();protocol.addItems(['ALL','SSH','RDP','VNC','SFTP','WEB','TELNET','LOCAL','OTHER'])
        status_filter=QComboBox();status_filter.addItems(['ALL','attention','observed','not_tested']);status_filter.setToolTip('Filtrer par statut des observations locales, sans préjuger de la santé distante')
        controls.addWidget(search,1);controls.addWidget(protocol);controls.addWidget(status_filter);layout.addLayout(controls)
        table=QTableWidget(0,4)
        table.setHorizontalHeaderLabels(['Connexion','Protocole','Échecs locaux / 30 min','Statut local'])
        table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        table.setSelectionBehavior(QAbstractItemView.SelectRows)
        names={c['id']:c.get('name','') for c in self.store.items}
        def redraw(*_):
            rows=filtered_rows(report,names,protocol.currentText(),search.text(),status_filter.currentText())
            table.setRowCount(len(rows))
            for index,item in enumerate(rows):
                for col,value in enumerate((names.get(item['id'],'Connexion'),item['protocol'],str(item['local_errors_30m']),item['status'])):
                    cell=QTableWidgetItem(str(value))
                    if col==0:cell.setData(Qt.UserRole,item['id'])
                    table.setItem(index,col,cell)
        search.textChanged.connect(redraw);protocol.currentTextChanged.connect(redraw);status_filter.currentTextChanged.connect(redraw)
        redraw();layout.addWidget(table)
        # V15.3: compact dependency trends directly in the existing dashboard.
        from dependency_trends import compare_dependency_trends
        from dependency_summary import summarize_trends
        summary_controls=QHBoxLayout()
        summary_controls.addWidget(QLabel('Synthèse des dépendances (observations locales)'))
        summary_period=QComboBox();summary_period.addItems(['15','30','60','180','720']);summary_period.setCurrentText('30')
        summary_controls.addWidget(QLabel('Minutes'));summary_controls.addWidget(summary_period)
        summary_affected=QCheckBox('Avec échecs uniquement')
        summary_controls.addWidget(summary_affected)
        summary_refresh=QPushButton('Actualiser la synthèse')
        summary_controls.addWidget(summary_refresh);layout.addLayout(summary_controls)
        summary_table=QTableWidget(0,5)
        summary_table.setHorizontalHeaderLabels(['Dépendance','Connexions','Précédent','Actuel','Simultanéités'])
        summary_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        summary_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        summary_table.setMaximumHeight(185)
        summary_table.setSortingEnabled(True)
        summary_table.setToolTip('Sélectionner une dépendance pour consulter ses connexions ; aucune action réseau automatique')
        layout.addWidget(summary_table)
        summary_note=QLabel('Synthèse locale : aucune cause distante confirmée.')
        summary_note.setWordWrap(True);layout.addWidget(summary_note)
        def refresh_summary(*_):
            try:
                routes={item['id']:item['route'] for item in self.routes.items
                        if item['id'] not in self.routes.invalid_routes}
                comparison=compare_dependency_trends(self.store.items,routes,report,
                    self.session_history.recent(1000),self.probe_history.recent(limit=500),
                    minutes=int(summary_period.currentText()))
                rows=summarize_trends(comparison,limit=8,affected_only=summary_affected.isChecked())
            except (ValueError,KeyError,TypeError,OSError,sqlite3.Error) as exc:
                summary_note.setText('Synthèse indisponible : '+type(exc).__name__)
                summary_table.setRowCount(0);return
            summary_table.setSortingEnabled(False)
            summary_table.setRowCount(len(rows))
            for i,item in enumerate(rows):
                for j,value in enumerate((item['dependency_type'],item['connections'],
                    item['previous'],item['current'],item['simultaneous'])):
                    cell=QTableWidgetItem(str(value))
                    if j in (1,2,3,4):
                        cell.setData(Qt.DisplayRole,int(value))
                    if j==0:cell.setData(Qt.UserRole,tuple(item['connection_ids']))
                    summary_table.setItem(i,j,cell)
            summary_table.setSortingEnabled(True)
            summary_note.setText(f'{len(rows)} groupes affichés (maximum 8). Données locales uniquement.')
        summary_refresh.clicked.connect(refresh_summary)
        summary_period.currentTextChanged.connect(refresh_summary)
        summary_affected.toggled.connect(refresh_summary)
        refresh_summary()
        summary_actions=QHBoxLayout()
        summary_details=QPushButton('Connexions du groupe…')
        summary_details.setToolTip('Choisir une connexion du groupe et ouvrir sa fiche, sans connexion réseau')
        summary_timeline=QPushButton('Chronologie du groupe…')
        summary_timeline.setToolTip('Choisir une connexion du groupe et consulter son historique local')
        def open_summary_connection(timeline=False):
            from dependency_summary import resolve_group_connections
            index=summary_table.currentRow()
            cell=summary_table.item(index,0) if index>=0 else None
            if cell is None:return
            identities=resolve_group_connections({'connection_ids':cell.data(Qt.UserRole)},
                                                  {c['id'] for c in self.store.items})
            if not identities:return
            labels={c['id']:c.get('name',c['id']) for c in self.store.items}
            options=[f'{labels[identity]} [{identity}]' for identity in identities]
            choice,accepted=QInputDialog.getItem(dialog,'Connexion du groupe',
                'Choisir une connexion :',options,0,False)
            if not accepted:return
            position=options.index(choice)
            identity=identities[position]
            self.search.clear();self.favorites_only.setChecked(False);self.refresh()
            for i in range(self.tree.topLevelItemCount()):
                parent=self.tree.topLevelItem(i)
                for j in range(parent.childCount()):
                    child=parent.child(j)
                    if child.data(0,Qt.UserRole)==identity:
                        self.tree.setCurrentItem(child)
                        dialog.accept()
                        (self.show_connection_timeline if timeline else self.show_connection_card)()
                        return
        summary_details.clicked.connect(lambda _checked=False:open_summary_connection(False))
        summary_timeline.clicked.connect(lambda _checked=False:open_summary_connection(True))
        summary_actions.addWidget(summary_details);summary_actions.addWidget(summary_timeline)
        layout.addLayout(summary_actions)
        hint=QLabel('Sélectionner une ligne pour afficher une recommandation locale.');hint.setWordWrap(True);layout.addWidget(hint)
        def show_hint():
            row=table.currentRow()
            cell=table.item(row,0) if row>=0 else None
            identity=cell.data(Qt.UserRole) if cell else None
            selected=next((r for r in report['rows'] if r['id']==identity),None)
            hint.setText(diagnostic_hint(selected) if selected else 'Sélectionner une ligne pour afficher une recommandation locale.')
        table.itemSelectionChanged.connect(show_hint)
        actions=QHBoxLayout()
        def selected_dashboard_id():
            row=table.currentRow()
            cell=table.item(row,0) if row>=0 else None
            identity=cell.data(Qt.UserRole) if cell else None
            return identity if isinstance(identity,str) and identity else None
        def select_dashboard_connection():
            identity=selected_dashboard_id()
            from dashboard_actions import allowed_action
            if not allowed_action('details',identity,{c['id'] for c in self.store.items}):return False
            self.search.clear();self.favorites_only.setChecked(False);self.refresh()
            for i in range(self.tree.topLevelItemCount()):
                parent=self.tree.topLevelItem(i)
                for j in range(parent.childCount()):
                    child=parent.child(j)
                    if child.data(0,Qt.UserRole)==identity:
                        self.tree.setCurrentItem(child)
                        return True
            return False
        def run_dashboard_action(handler):
            if select_dashboard_connection():
                dialog.accept()
                handler()
        for title,handler,tooltip in [
            ('Ouvrir',self.connect,'Ouvrir explicitement la connexion sélectionnée'),
            ('Fiche',self.show_connection_card,'Consulter la fiche et ses recommandations'),
            ('Chronologie',self.show_connection_timeline,'Consulter les événements locaux enregistrés'),
            ('Précontrôle',self.check_access,'Lancer explicitement le contrôle d’accès'),
            ('Port TCP',self.test_tcp_connection,'Tester explicitement le port TCP de la cible')]:
            button=QPushButton(title)
            button.setToolTip(tooltip)
            button.clicked.connect(lambda _checked=False, fn=handler:run_dashboard_action(fn))
            actions.addWidget(button)
        def show_local_groups():
            identity=selected_dashboard_id()
            if not identity or identity not in {c['id'] for c in self.store.items}:
                return
            from local_incident_groups import group_local_errors, format_summary
            try:
                result=group_local_errors(self.session_history.recent(1000),
                    self.probe_history.recent(identity,limit=500),identity)
                QMessageBox.information(dialog,'Regroupement des échecs locaux',format_summary(result))
            except (OSError,ValueError,sqlite3.Error) as exc:
                QMessageBox.warning(dialog,'Regroupement indisponible',type(exc).__name__)
        group_button=QPushButton('Regrouper les échecs')
        group_button.setToolTip('Regrouper les erreurs locales par type et heure, sans attribuer une panne distante')
        group_button.clicked.connect(show_local_groups)
        actions.addWidget(group_button)
        def show_incident_trends():
            identity=selected_dashboard_id()
            if not identity or identity not in {c['id'] for c in self.store.items}: return
            from incident_trends import build_trends
            view=QDialog(dialog);view.setWindowTitle('Chronologie des échecs locaux');view.resize(720,430)
            body=QVBoxLayout(view)
            body.addWidget(QLabel('Observations locales uniquement : aucune panne distante confirmée.'))
            window=QComboBox();window.addItems(['30','60','120','240','480','1440'])
            window.setCurrentText('60');window.setToolTip('Période d’observation en minutes')
            body.addWidget(window)
            comparison=QLabel();body.addWidget(comparison)
            timeline_table=QTableWidget(0,5)
            timeline_table.setHorizontalHeaderLabels(['Début UTC','TCP','SSH','Client','Total'])
            timeline_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
            body.addWidget(timeline_table)
            from qt_trend_chart import LocalTrendChart
            chart=LocalTrendChart(view)
            body.insertWidget(body.indexOf(timeline_table),chart)
            body.insertWidget(body.indexOf(timeline_table),QLabel('TCP (bleu) | SSH (orange) | Client (gris)'))
            def refresh_trends(*_):
                try:
                    period=int(window.currentText())
                    report=build_trends(self.session_history.recent(1000),
                        self.probe_history.recent(identity,limit=500),identity,
                        minutes=period,bucket_minutes=15 if period<=120 else 60)
                except (OSError,ValueError,sqlite3.Error) as exc:
                    comparison.setText('Données indisponibles : '+type(exc).__name__)
                    timeline_table.setRowCount(0);return
                chart.set_report(report)
                comparison.setText(f"Échecs locaux : {report['total_errors']} | Première moitié : {report['earlier_half']} | Seconde moitié : {report['later_half']} | Variation : {report['delta']:+d}")
                timeline_table.setRowCount(len(report['buckets']))
                for index,bucket in enumerate(report['buckets']):
                    values=(bucket['start_utc'],bucket['counts']['tcp_local'],
                        bucket['counts']['ssh_jump'],bucket['counts']['session_exit'],bucket['total'])
                    for col,value in enumerate(values):timeline_table.setItem(index,col,QTableWidgetItem(str(value)))
            window.currentTextChanged.connect(refresh_trends)
            refresh_trends()
            done=QPushButton('Fermer');done.clicked.connect(view.accept);body.addWidget(done)
            view.exec()
        trend_button=QPushButton('Chronologie des échecs')
        trend_button.setToolTip('Comparer deux périodes et visualiser les erreurs locales, sans test réseau')
        trend_button.clicked.connect(show_incident_trends)
        actions.addWidget(trend_button)
        def show_shared_dependencies():
            from shared_dependency_analysis import compare_dependencies
            try:
                routes={item['id']:item['route'] for item in self.routes.items
                        if item['id'] not in self.routes.invalid_routes}
                result=compare_dependencies(self.store.items,routes,report)
            except (ValueError,KeyError,TypeError) as exc:
                QMessageBox.warning(dialog,'Comparaison indisponible',type(exc).__name__);return
            view=QDialog(dialog);view.setWindowTitle('Comparaison des dépendances — observations locales')
            view.resize(800,430);body=QVBoxLayout(view)
            body.addWidget(QLabel('Corrélation indicative des échecs locaux sur 30 min. Aucune panne de bastion ou passerelle confirmée.'))
            if result['skipped_invalid_routes']:
                body.addWidget(QLabel(f"Routes invalides ignorées : {result['skipped_invalid_routes']}"))
            table_groups=QTableWidget(len(result['groups']),4)
            table_groups.setHorizontalHeaderLabels(['Dépendance','Connexions','Avec échecs','Échecs locaux'])
            table_groups.setEditTriggers(QAbstractItemView.NoEditTriggers)
            for i,item in enumerate(result['groups']):
                for j,value in enumerate((item['dependency_type'],item['connections'],item['affected_connections'],item['local_errors_30m'])):
                    table_groups.setItem(i,j,QTableWidgetItem(str(value)))
            body.addWidget(table_groups)
            body.addWidget(QLabel('Les hôtes, chaînes de rebonds et références PAM ne sont pas affichés.'))
            done=QPushButton('Fermer');done.clicked.connect(view.accept);body.addWidget(done)
            view.exec()
        def show_temporal_dependencies():
            from dependency_temporal import compare_temporal
            from dependency_matrix_view import eligible_connection_ids, group_at_index
            from dependency_matrix_filters import incident_priority, visible_group_indices
            view=QDialog(dialog);view.setWindowTitle('Incidents simultanés — dépendances partagées')
            view.resize(920,540);body=QVBoxLayout(view)
            body.addWidget(QLabel('Observations locales uniquement : une simultanéité ne confirme pas une panne distante.'))
            controls=QHBoxLayout()
            window=QComboBox();window.addItems(['15','30','60','180','1440']);window.setCurrentText('30')
            tolerance=QComboBox();tolerance.addItems(['0','30','60','120','300']);tolerance.setCurrentText('60')
            controls.addWidget(QLabel('Période (min)'));controls.addWidget(window)
            controls.addWidget(QLabel('Simultanéité (s)'));controls.addWidget(tolerance)
            body.addLayout(controls)
            mode_filter=QComboBox();mode_filter.addItem('Tous les groupes','ALL');mode_filter.addItem('Groupes avec échecs','AFFECTED');mode_filter.addItem('Incidents simultanés uniquement','SIMULTANEOUS')
            body.addWidget(mode_filter)
            matrix_search=QLineEdit()
            matrix_search.setPlaceholderText('Filtrer les groupes (type, nombre de connexions)… Ctrl+F')
            matrix_search.setToolTip('Recherche locale dans les colonnes affichées ; aucune requête réseau')
            body.addWidget(matrix_search)
            matrix=QTableWidget(0,6)
            matrix.setHorizontalHeaderLabels(['Dépendance','Connexions','Avec échecs','Fenêtres simultanées','Max simultanées','Priorité locale'])
            matrix.setSelectionBehavior(QAbstractItemView.SelectRows)
            matrix.setEditTriggers(QAbstractItemView.NoEditTriggers)
            matrix.setSortingEnabled(True)
            matrix.setToolTip('Cliquer sur un en-tête pour trier les groupes')
            body.addWidget(matrix)
            detail=QLabel('Sélectionner un groupe pour afficher ses connexions.');detail.setWordWrap(True);body.addWidget(detail)
            result={'groups':[]}
            def selected_group():
                row=matrix.currentRow()
                cell=matrix.item(row,0) if row>=0 else None
                index=cell.data(Qt.UserRole) if cell else None
                return group_at_index(result['groups'],index)
            def filter_matrix(*_):
                term=matrix_search.text().casefold().strip()
                for row in range(matrix.rowCount()):
                    values=[matrix.item(row,col).text() if matrix.item(row,col) else '' for col in range(matrix.columnCount())]
                    matrix.setRowHidden(row,bool(term and not any(term in value.casefold() for value in values)))
                update_detail()
            def update_detail():
                item=selected_group()
                if item is None:
                    detail.setText('Sélectionner un groupe pour afficher ses connexions.');return
                names_by_id={c['id']:str(c.get('name','Connexion')) for c in self.store.items}
                detail.setText('Priorité locale : '+incident_priority(item)+' | Connexions : '+', '.join(names_by_id.get(i,'Connexion') for i in item['connection_ids'])+
                    ' | Simultanées : '+(', '.join(names_by_id.get(i,'Connexion') for i in item['overlapping_connection_ids']) or 'aucune'))
            def reload_matrix(*_):
                try:
                    routes={item['id']:item['route'] for item in self.routes.items
                            if item['id'] not in self.routes.invalid_routes}
                    updated=compare_temporal(self.store.items,routes,report,
                        self.session_history.recent(1000),self.probe_history.recent(limit=500),
                        minutes=int(window.currentText()),tolerance_seconds=int(tolerance.currentText()))
                except (ValueError,KeyError,TypeError,OSError,sqlite3.Error) as exc:
                    QMessageBox.warning(view,'Corrélation temporelle indisponible',type(exc).__name__);return
                result.clear();result.update(updated)
                matrix.setSortingEnabled(False)
                indices=visible_group_indices(result['groups'],mode_filter.currentData())
                matrix.setRowCount(len(indices))
                for i,original_index in enumerate(indices):
                    item=result['groups'][original_index]
                    for j,value in enumerate((item['dependency_type'],item['connections'],item['affected_connections'],
                                              item['overlap_windows'],item['max_simultaneous_connections'],incident_priority(item))):
                        cell=QTableWidgetItem(str(value))
                        if j==0:cell.setData(Qt.UserRole,original_index)
                        if 0<j<5:cell.setData(Qt.DisplayRole,int(value))
                        matrix.setItem(i,j,cell)
                matrix.setSortingEnabled(True)
                filter_matrix()
            matrix.itemSelectionChanged.connect(update_detail)
            matrix_search.textChanged.connect(filter_matrix)
            mode_filter.currentIndexChanged.connect(reload_matrix)
            search_shortcut=QShortcut(QKeySequence('Ctrl+F'),view)
            search_shortcut.activated.connect(matrix_search.setFocus)
            window.currentTextChanged.connect(reload_matrix)
            tolerance.currentTextChanged.connect(reload_matrix)
            actions_temporal=QHBoxLayout()
            open_card=QPushButton('Fiche de connexion…')
            def open_group_card():
                group=selected_group()
                if group is None:return
                valid=eligible_connection_ids(group,{c['id'] for c in self.store.items})
                if not valid:return
                names={c['id']:str(c.get('name','Connexion')) for c in self.store.items}
                labels=[f'{names.get(identity,"Connexion")} [{identity}]' for identity in valid]
                choice,ok=QInputDialog.getItem(view,'Connexion du groupe','Choisir une connexion :',labels,0,False)
                if not ok or choice not in labels:return
                identity=valid[labels.index(choice)]
                self.search.clear();self.favorites_only.setChecked(False);self.refresh()
                for i in range(self.tree.topLevelItemCount()):
                    parent=self.tree.topLevelItem(i)
                    for j in range(parent.childCount()):
                        child=parent.child(j)
                        if child.data(0,Qt.UserRole)==identity:
                            self.tree.setCurrentItem(child);view.accept();dialog.accept();self.show_connection_card();return
            open_card.clicked.connect(open_group_card);actions_temporal.addWidget(open_card)
            open_timeline=QPushButton('Chronologie de connexion…')
            def open_group_timeline():
                group=selected_group()
                if group is None:return
                valid=eligible_connection_ids(group,{c['id'] for c in self.store.items})
                if not valid:return
                names={c['id']:str(c.get('name','Connexion')) for c in self.store.items}
                labels=[f'{names.get(identity,"Connexion")} [{identity}]' for identity in valid]
                choice,ok=QInputDialog.getItem(view,'Chronologie du groupe','Choisir une connexion :',labels,0,False)
                if not ok or choice not in labels:return
                identity=valid[labels.index(choice)]
                self.search.clear();self.favorites_only.setChecked(False);self.refresh()
                for i in range(self.tree.topLevelItemCount()):
                    parent=self.tree.topLevelItem(i)
                    for j in range(parent.childCount()):
                        child=parent.child(j)
                        if child.data(0,Qt.UserRole)==identity:
                            self.tree.setCurrentItem(child);view.accept();dialog.accept();self.show_connection_timeline();return
            open_timeline.clicked.connect(open_group_timeline);actions_temporal.addWidget(open_timeline)
            matrix.itemDoubleClicked.connect(lambda *_:open_group_card())
            close_temporal=QPushButton('Fermer');close_temporal.clicked.connect(view.accept);actions_temporal.addWidget(close_temporal)
            body.addLayout(actions_temporal)
            body.addWidget(QLabel('Les noms de bastions, chaînes de rebonds et références PAM ne sont pas exposés.'))
            reload_matrix();view.exec()
        def show_dependency_trends():
            from dependency_trends import compare_dependency_trends
            view=QDialog(dialog);view.setWindowTitle('Tendances des dépendances — observations locales')
            view.resize(860,470);body=QVBoxLayout(view)
            body.addWidget(QLabel('Deux périodes consécutives de même durée. Aucun diagnostic distant confirmé.'))
            controls=QHBoxLayout();controls.addWidget(QLabel('Durée par période (min)'))
            period=QComboBox();period.addItems(['15','30','60','180','720']);period.setCurrentText('30')
            controls.addWidget(period);body.addLayout(controls)
            table=QTableWidget(0,6)
            table.setHorizontalHeaderLabels(['Dépendance','Connexions','Précédent','Actuel','Évolution','Simultanéités'])
            table.setSelectionBehavior(QAbstractItemView.SelectRows)
            table.setEditTriggers(QAbstractItemView.NoEditTriggers)
            body.addWidget(table)
            advice=QLabel('Sélectionner un groupe pour consulter la recommandation.');advice.setWordWrap(True)
            body.addWidget(advice)
            result={'groups':[]}
            def selected_trend():
                row=table.currentRow();cell=table.item(row,0) if row>=0 else None
                index=cell.data(Qt.UserRole) if cell else None
                return result['groups'][index] if type(index) is int and 0<=index<len(result['groups']) else None
            def update_advice():
                group=selected_trend()
                advice.setText(group['recommendation'] if group else 'Sélectionner un groupe pour consulter la recommandation.')
            def reload_trends(*_):
                try:
                    routes={item['id']:item['route'] for item in self.routes.items
                            if item['id'] not in self.routes.invalid_routes}
                    updated=compare_dependency_trends(self.store.items,routes,report,
                        self.session_history.recent(1000),self.probe_history.recent(limit=500),
                        minutes=int(period.currentText()))
                except (ValueError,KeyError,TypeError,OSError,sqlite3.Error) as exc:
                    QMessageBox.warning(view,'Tendances indisponibles',type(exc).__name__);return
                result.clear();result.update(updated)
                table.setRowCount(len(result['groups']))
                for i,group in enumerate(result['groups']):
                    values=(group['dependency_type'],group['connections'],group['previous_errors'],
                            group['current_errors'],group['trend']+' ('+str(group['delta'])+')',group['simultaneous_windows'])
                    for j,value in enumerate(values):
                        cell=QTableWidgetItem(str(value))
                        if j==0:cell.setData(Qt.UserRole,i)
                        table.setItem(i,j,cell)
                update_advice()
            table.itemSelectionChanged.connect(update_advice)
            period.currentTextChanged.connect(reload_trends)
            close_trends=QPushButton('Fermer');close_trends.clicked.connect(view.accept);body.addWidget(close_trends)
            reload_trends();view.exec()
        trends_button=QPushButton('Tendances des dépendances')
        trends_button.setToolTip('Comparer deux périodes d’échecs locaux, sans connexion réseau')
        trends_button.clicked.connect(show_dependency_trends)
        actions.addWidget(trends_button)
        temporal_button=QPushButton('Incidents simultanés')
        temporal_button.setToolTip('Comparer les échecs locaux dans une fenêtre de 60 secondes, sans test réseau')
        temporal_button.clicked.connect(show_temporal_dependencies)
        actions.addWidget(temporal_button)
        compare_button=QPushButton('Dépendances communes')
        compare_button.setToolTip('Comparer les observations locales de connexions partageant un bastion ou une passerelle, sans test réseau')
        compare_button.clicked.connect(show_shared_dependencies)
        actions.addWidget(compare_button)
        close=QPushButton('Fermer');close.clicked.connect(dialog.accept);actions.addWidget(close)
        layout.addLayout(actions)
        dialog.exec()

    def show_incident_overview(self):
        """On-demand, read-only overview: no automatic network tests or reconnect."""
        try:
            self.external_sessions.snapshot()
            rows=overview(self.store.items,self.session_history.recent(1000),self.probe_history.recent(limit=500))
        except (OSError,ValueError,sqlite3.Error) as exc:
            QMessageBox.warning(self,'Analyse indisponible',type(exc).__name__);return
        self.incident_label.setText('Connexions avec au moins 3 erreurs locales sur 30 min : '+str(len(rows)))
        dialog=QDialog(self);dialog.setWindowTitle('Échecs locaux récurrents — 30 minutes');dialog.resize(680,420)
        layout=QVBoxLayout(dialog)
        layout.addWidget(QLabel('Indicateurs locaux uniquement : aucune preuve d’indisponibilité distante.'))
        table=QTableWidget(len(rows),2);table.setHorizontalHeaderLabels(['Connexion','Erreurs observées'])
        table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        for i,row in enumerate(rows):
            table.setItem(i,0,QTableWidgetItem(str(row['name'])))
            table.setItem(i,1,QTableWidgetItem(str(row['count'])))
        layout.addWidget(table)
        if not rows:layout.addWidget(QLabel('Aucune répétition au seuil défini dans les événements consultés.'))
        close=QPushButton('Fermer');close.clicked.connect(dialog.accept);layout.addWidget(close)
        dialog.exec()

    def open_palette(self):
        dialog=QDialog(self);dialog.setWindowTitle('Actions rapides · Ctrl+K');dialog.resize(650,460)
        layout=QVBoxLayout(dialog);query=QLineEdit();query.setPlaceholderText('Outil, protocole, serveur, groupe, tag…');layout.addWidget(query)
        results=QListWidget();layout.addWidget(results)
        def fill(text=''):
            results.clear()
            for entry in command_search(text,self.store.items):
                item=QListWidgetItem(entry['label']);item.setToolTip(entry['detail']);item.setData(Qt.UserRole,entry);results.addItem(item)
            if results.count():results.setCurrentRow(0)
        def activate(item):
            if item is None:return
            entry=item.data(Qt.UserRole);dialog.accept()
            if entry['kind']=='tool':self._invoke_tool(entry['action'])
            else:
                for c in self.store.items:
                    if c['id']==entry['action']:
                        self._open_connection_by_id(c['id']);break
        query.textChanged.connect(fill);query.returnPressed.connect(lambda:activate(results.currentItem()))
        results.itemDoubleClicked.connect(activate);fill();query.setFocus();dialog.exec()

    def _open_connection_by_id(self,identity):
        for i in range(self.tree.topLevelItemCount()):
            parent=self.tree.topLevelItem(i)
            for j in range(parent.childCount()):
                child=parent.child(j)
                if child.data(0,Qt.UserRole)==identity:
                    self.tree.setCurrentItem(child);self.connect();return
        # A search filter may hide the selected connection.
        self.search.clear()
        for i in range(self.tree.topLevelItemCount()):
            parent=self.tree.topLevelItem(i)
            for j in range(parent.childCount()):
                child=parent.child(j)
                if child.data(0,Qt.UserRole)==identity:
                    self.tree.setCurrentItem(child);self.connect();return

    def _install_toolbox(self):
        dock=QDockWidget('Boîte à outils · Administration',self)
        dock.setObjectName('admin_toolbox')
        panel=QWidget();v=QVBoxLayout(panel)
        selector=QComboBox()
        selector.addItems(PROFILES)
        selector.setToolTip('Filtre d’affichage uniquement : aucune restriction de permissions')
        v.addWidget(QLabel('Profil métier'))
        v.addWidget(selector)
        finder=QLineEdit();finder.setPlaceholderText('Rechercher un outil (Ctrl+K)…');v.addWidget(finder)
        listing=QListWidget();v.addWidget(listing)
        self.tool_search=finder;self.tool_list=listing;self.profile_selector=selector
        def populate(query=''):
            listing.clear()
            for category,name,action,description in visible_tools(TOOLS,selector.currentText(),query):
                item=QListWidgetItem(f'{category}  /  {name}')
                item.setToolTip(description)
                item.setData(Qt.UserRole,action)
                listing.addItem(item)
        finder.textChanged.connect(populate)
        selector.currentTextChanged.connect(lambda _:populate(finder.text()))
        listing.itemDoubleClicked.connect(lambda item:self._invoke_tool(item.data(Qt.UserRole)))
        populate()
        dock.setWidget(panel);self.addDockWidget(Qt.RightDockWidgetArea,dock)
        menu=self.menuBar().addMenu('Affichage')
        menu.addAction(dock.toggleViewAction())
        shortcut=menu.addAction('Rechercher un outil')
        shortcut.setShortcut('Ctrl+K');shortcut.triggered.connect(self.open_palette)
        self.tool_dock=dock

    def _invoke_tool(self,action):
        handlers={'ping':lambda:self.network('ping'),'nslookup':lambda:self.network('nslookup'),
                  'traceroute':lambda:self.network('tracert' if os.name=='nt' else 'traceroute'),
                  'tcp':self.tcp_check,'ssh':self.ssh_tab,'sftp':self.sftp,
                  'connect':self.connect,'vault':self.open_vault,'secret':self.edit_secret,
                  'split':self.split_view}
        if action in handlers:handlers[action]()

    def tcp_check(self):
        c=self.selected()
        if not c or c['protocol']=='WEB':
            QMessageBox.information(self,'Test TCP','Sélectionner une connexion réseau.');return
        port,ok=QInputDialog.getInt(self,'Test TCP','Port TCP',int(c['port'] or 22),1,65535)
        if not ok:return
        job=TcpJob(c['host'],port)
        self.tcp_jobs=getattr(self,'tcp_jobs',[])
        self.tcp_jobs.append(job)
        job.signals.finished.connect(lambda result:self.log.append(result))
        job.signals.finished.connect(lambda _:self.tabs.setCurrentWidget(self.home))
        job.signals.finished.connect(lambda _:self.tcp_jobs.remove(job) if job in self.tcp_jobs else None)
        self.pool.start(job)
        self.statusBar().showMessage('Diagnostic TCP en arrière-plan',3000)

    def navigate_tab(self,reverse=False):
        index=next_tab(self.tabs.currentIndex(),self.tabs.count(),reverse)
        if index >= 0:self.tabs.setCurrentIndex(index)

    def select_tab_number(self,number):
        index=tab_at_position(number,self.tabs.count())
        if index >= 0:self.tabs.setCurrentIndex(index)

    def close_current_tab(self):
        index=self.tabs.currentIndex()
        if closable_tab(index,self.tabs.indexOf(self.home)):
            self.close_tab(index)

    def install_tab_shortcuts(self):
        """Keyboard-first Windows navigation; never closes the home tab."""
        for sequence,callback in [
            ('Ctrl+Tab',lambda:self.navigate_tab()),
            ('Ctrl+Shift+Tab',lambda:self.navigate_tab(True)),
            ('Ctrl+W',self.close_current_tab)]:
            shortcut=QShortcut(QKeySequence(sequence),self)
            shortcut.activated.connect(callback)
            if not hasattr(self,'tab_shortcuts'):self.tab_shortcuts=[]
            self.tab_shortcuts.append(shortcut)
        for number in range(1,10):
            shortcut=QShortcut(QKeySequence('Alt+'+str(number)),self)
            shortcut.activated.connect(lambda n=number:self.select_tab_number(n))
            self.tab_shortcuts.append(shortcut)

    def close_tab(self,index):
        widget=self.tabs.widget(index)
        if widget is None:return
        if widget is self.home:
            return
        from ssh_tunnel_qt import SSHTunnelPanel
        if isinstance(widget, SSHTunnelPanel) and not widget.is_shutdown_complete():
            widget.request_close(lambda w=widget: self._finish_tunnel_tab(w))
            self.statusBar().showMessage('Révocation du tunnel SSH en cours…',5000)
            return
        # Non-blocking tab shutdown: poll QThread state on the GUI event loop.
        # Keep the widget alive until all PTY workers have actually stopped.
        if getattr(widget, '_ssh_close_pending', False):
            return
        workers=widget.findChildren(PtyShell)
        active=[worker for worker in workers if worker.isRunning()]
        if active:
            widget._ssh_close_pending=True
            widget._ssh_close_attempts=0
            for worker in active:
                worker.stop()
            self.statusBar().showMessage('Arrêt SSH en cours (interface disponible)…', 5000)
            def finish_when_stopped():
                if not getattr(widget, '_ssh_close_pending', False):
                    return
                if any(worker.isRunning() for worker in workers):
                    widget._ssh_close_attempts+=1
                    if widget._ssh_close_attempts >= 30:
                        widget._ssh_close_pending=False
                        self.statusBar().showMessage('Arrêt SSH non confirmé : onglet conservé', 8000)
                        QMessageBox.warning(self,'SSH PTY','La session SSH ne s’est pas arrêtée en 3 secondes. Onglet conservé.')
                        return
                    QTimer.singleShot(100,finish_when_stopped)
                    return
                widget._ssh_close_pending=False
                current=self.tabs.indexOf(widget)
                if current >= 0:
                    self.close_tab(current)
            QTimer.singleShot(100,finish_when_stopped)
            return
        # Invalidate SFTP callbacks before stopping auxiliary processes or deleting UI.
        # This must follow successful PTY shutdown: a refused close keeps its tab active.
        cancel_sftp=getattr(widget,'_cancel_sftp_transfers',None)
        if callable(cancel_sftp):
            widget._sftp_closing=True
            cancel_sftp()
        for proc in list(self.processes):
            if proc.parent()==widget:
                if proc.state()!=proc.NotRunning:proc.kill();proc.waitForFinished(1000)
                self.processes.remove(proc)
        self.tabs.removeTab(index)
        if widget is getattr(self,'transfer_history_tab',None):
            self.transfer_history_tab=None
            self.transfer_history_refresh=None
        if widget is getattr(self,'session_overview',None):
            self.session_refresh_timer.stop()
            self.session_overview=None
            self.session_overview_list=None
        widget.deleteLater()

    def _finish_tunnel_tab(self, widget):
        index=self.tabs.indexOf(widget)
        if index >= 0:
            self.close_tab(index)

    def show_integrations(self):
        """Read-only detection: never execute binaries merely to discover them."""
        pane=QWidget();layout=QVBoxLayout(pane)
        heading=QLabel('Catalogue des outils locaux · détection sans exécution');layout.addWidget(heading)
        search=QLineEdit();search.setPlaceholderText('Filtrer : Docker, Kubernetes, réseau, cloud…');layout.addWidget(search)
        listing=QTreeWidget();listing.setHeaderLabels(['Domaine','Outil','État','Chemin détecté']);layout.addWidget(listing)
        note=QLabel('Détecté = exécutable trouvé dans le PATH, pas intégration validée. Aucune commande lancée.')
        note.setWordWrap(True);layout.addWidget(note)
        entries=discover()
        def populate(query=''):
            listing.clear()
            for entry in filter_tools(query,entries):
                item=QTreeWidgetItem(listing,[entry['category'],entry['name'],
                    'Détecté' if entry['available'] else 'Absent',entry['path']])
                item.setToolTip(1,entry['description'])
            listing.resizeColumnToContents(0);listing.resizeColumnToContents(1)
        search.textChanged.connect(populate);populate()
        self.tabs.addTab(pane,'Outils installés');self.tabs.setCurrentWidget(pane)

    def show_ssh_tunnel(self):
        """Open a new opt-in local tunnel workspace; no network on creation."""
        from ssh_tunnel_qt import SSHTunnelPanel
        pane=SSHTunnelPanel(self.selected(), parent=self.tabs)
        self.tabs.addTab(pane,'Tunnel SSH local')
        self.tabs.setCurrentWidget(pane)

    def show_netbox_preview(self):
        """Opt-in, asynchronous, non-destructive NetBox inventory comparison."""
        from netbox_preview_qt import NetBoxPreviewPanel
        pane = NetBoxPreviewPanel(self.store.items, parent=self.tabs)
        self.tabs.addTab(pane, 'NetBox · aperçu')
        self.tabs.setCurrentWidget(pane)

    def show_zabbix_alerts(self):
        """Open an offline-by-default, read-only Zabbix alert triage panel."""
        from zabbix_alerts_qt import ZabbixAlertsPanel
        pane = ZabbixAlertsPanel(self.store.items, parent=self.tabs)
        self.tabs.addTab(pane, 'Zabbix · alertes')
        self.tabs.setCurrentWidget(pane)

    def show_grafana_dashboards(self):
        """Open offline-by-default Grafana dashboard discovery; no writes or polling."""
        from grafana_dashboard_qt import GrafanaDashboardsPanel
        pane = GrafanaDashboardsPanel(parent=self.tabs)
        self.tabs.addTab(pane, 'Grafana · tableaux')
        self.tabs.setCurrentWidget(pane)

    def show_ansible_preflight(self):
        """Open static offline Ansible preflight; execution is opt-in, allowlisted and check-only."""
        from ansible_preflight_qt import AnsiblePreflightPanel
        pane = AnsiblePreflightPanel(parent=self.tabs)
        self.tabs.addTab(pane, 'Ansible · aperçu')
        self.tabs.setCurrentWidget(pane)


    def show_winrm_inventory(self):
        """Open the offline-by-default Windows inventory; no socket until consent."""
        from winrm_inventory_qt import WinRMInventoryPanel
        pane = WinRMInventoryPanel(parent=self.tabs)
        self.tabs.addTab(pane, 'WinRM · inventaire')
        self.tabs.setCurrentWidget(pane)

    def show_winrm_services(self):
        """Open the offline-by-default services view; never starts/stops services."""
        from winrm_inventory_qt import WinRMServicesPanel
        pane = WinRMServicesPanel(parent=self.tabs)
        self.tabs.addTab(pane, 'WinRM · services')
        self.tabs.setCurrentWidget(pane)

    def show_inventory(self):
        info=summary(self.store.items)
        pane=QPlainTextEdit();pane.setReadOnly(True)
        lines=['INVENTAIRE INFRASTRUCTURE',f"Connexions : {info['total']}",'','PAR PROTOCOLE']
        lines += [f'  {k}: {v}' for k,v in info['protocols'].items()]
        lines += ['','PAR GROUPE']+[f'  {k}: {v}' for k,v in info['groups'].items()]
        pane.setPlainText('\n'.join(lines))
        self.tabs.addTab(pane,'Inventaire');self.tabs.setCurrentWidget(pane)

    def export_inventory(self):
        filename,chosen=QFileDialog.getSaveFileName(self,'Exporter l’inventaire','openremote-inventory.csv',
                                                   'CSV (*.csv);;JSON (*.json)')
        if not filename:return
        try:
            is_json=filename.lower().endswith('.json') or ('JSON' in chosen and not filename.lower().endswith('.csv'))
            payload=export_json(self.store.items) if is_json else export_csv(self.store.items)
            Path(filename).write_text(payload,encoding='utf-8-sig' if not is_json else 'utf-8')
            self.statusBar().showMessage('Inventaire exporté (sans secrets)',5000)
        except OSError as exc:
            QMessageBox.warning(self,'Export impossible',str(exc))

    def _sync_primary_navigation(self, *_):
        """Reflect the active workspace view without launching external clients."""
        if not hasattr(self, 'tabs') or not hasattr(self, 'primary_navigation_buttons'):
            return
        current = self.tabs.currentWidget()
        active = ('show_home' if current is getattr(self, 'home', None)
                  else 'show_session_overview' if current is getattr(self, 'session_overview', None)
                  else 'show_local_readiness' if current is not None and current.objectName() == 'localReadinessTab'
                  else 'show_transfer_history' if current is not None and current.objectName() == 'transferHistoryTab'
                  else None)
        for button in self.primary_navigation_buttons:
            button.setChecked(button.objectName() == 'primaryNavigation' + active if active else False)

    def show_home(self):
        self.tabs.setCurrentWidget(self.home)
    def toggle_favorite(self):
        c=self.selected()
        if c:self.workspace.toggle_favorite(c['id']);self.refresh()
    def _record_open(self,c):
        self.workspace.mark_recent(c['id'])
    def reset_connection_filters(self):
        """Restore the full connection list without opening a session."""
        self.search.clear()
        self.favorites_only.setChecked(False)
        self.refresh()
        self.search.setFocus()

    def refresh(self):
        # Preserve the selected connection when rebuilding the filtered tree.
        # A hidden or deleted selection must not leave contextual actions active.
        selected_id = self.selected_connection_id()
        self.tree.clear();groups={};query=self.search.text().lower()
        for c in sorted(self.store.items,key=lambda x:(x['id'] not in self.workspace.data['favorites'],x['group'],x['name'])):
            if self.favorites_only.isChecked() and c['id'] not in self.workspace.data['favorites']:continue
            if query and query not in ' '.join(str(c.get(field,'') or '') for field in ('name','host','group','protocol','tags','user')).lower():continue
            group=('★ Favoris' if c['id'] in self.workspace.data['favorites'] else c['group'] or 'Sans groupe')
            if group not in groups:groups[group]=QTreeWidgetItem(self.tree,[group]);groups[group].setExpanded(True)
            child=QTreeWidgetItem(groups[group],[c['name'],c['protocol'],c['host']]);child.setData(0,Qt.UserRole,c['id'])
            if c['id'] == selected_id:
                self.tree.setCurrentItem(child)
        visible=sum(group.childCount() for group in groups.values())
        label, can_reset=filter_status(len(self.store.items),visible,query,self.favorites_only.isChecked())
        self.filter_info.setText(label)
        # Keep an actionable empty-state hint on the inventory itself.
        if visible == 0:
            if len(self.store.items) == 0:
                hint = 'Aucune connexion enregistrée. Cliquez sur « Nouvelle connexion » pour commencer.'
            elif can_reset:
                hint = 'Aucun résultat pour ces filtres. Cliquez sur « Effacer filtres ».'
            else:
                hint = 'Aucune connexion à afficher.'
            self.tree.setToolTip(hint)
            self.statusBar().showMessage(hint)
        else:
            self.tree.setToolTip('Double-clic : ouvrir · Clic droit : actions de connexion')
        self.reset_filters_button.setVisible(can_reset)
        self.update_dashboard()
        self._refresh_quick_access()
        self.update_inspector()
        if hasattr(self,'tabs'):self._show_route_warning()
    def connection_context_menu(self,position):
        """Only actual connection rows expose connection actions, not group headers."""
        item=self.tree.itemAt(position)
        if item is None or not item.data(0,Qt.UserRole):return
        self.tree.setCurrentItem(item)
        menu=QMenu(self)
        for label,method_name in actions_for_selection(item.data(0,Qt.UserRole)):
            menu.addAction(label,getattr(self,method_name))
        menu.exec(self.tree.viewport().mapToGlobal(position))

    def selected_connection_id(self):
        item = self.tree.currentItem()
        return item.data(0, Qt.UserRole) if item else None

    def selected(self):
        id=self.selected_connection_id()
        return next((c for c in self.store.items if c['id']==id),None)
    def add(self):
        d=Editor(self)
        if d.exec()==QDialog.Accepted:self.store.upsert(d.result);self.refresh()
    def edit(self):
        c=self.selected()
        if c:
            d=Editor(self,c)
            if d.exec()==QDialog.Accepted:self.store.upsert(d.result);self.refresh()
    def remove(self):
        c=self.selected()
        if c and QMessageBox.question(self,'Confirmer',f"Supprimer {c['name']} ?")==QMessageBox.Yes:
            try:
                self.store.remove(c['id'])
                self.routes.remove_route(c['id'])
                self.workspace.purge(c['id'])
                self.refresh()
            except (OSError,ValueError) as exc:
                QMessageBox.warning(self,'Suppression incomplète',str(exc))
    def access_wizard(self):
        c=self.selected()
        if not c:
            QMessageBox.information(self,'Assistant accès','Sélectionnez une connexion dans la liste.')
            return
        old=self.routes.raw_for_edit(c['id'])
        dialog=QDialog(self)
        dialog.setWindowTitle('Assistant accès · '+c['name'])
        dialog.resize(540,440)
        layout=QVBoxLayout(dialog)
        layout.addWidget(QLabel(f"Cible : {c['name']} · {c['protocol']} · {c['host']}"))
        form=QFormLayout();layout.addLayout(form)
        mode=QComboBox()
        available=['direct']
        if c['protocol']=='RDP':available+=['rd_gateway','rds_collection']
        elif c['protocol'] in ('SSH','SFTP'):available+=['ssh_jump']
        mode.addItems(available)
        if old.get('mode') in available:mode.setCurrentText(old['mode'])
        form.addRow('Chemin de connexion',mode)
        fields={}
        labels=[('gateway_host','Passerelle RD Gateway'),('gateway_port','Port RD Gateway'),
                ('gateway_user','Compte RD Gateway'),('collection','Collection RDS'),
                ('jump_host','Serveur bastion SSH'),('jump_port','Port SSH'),
                ('jump_user','Compte bastion SSH'),('jump_chain','Rebonds suivants (user@host:port,...)'),('vault_ref','Référence coffre PAM (sans secret)')]
        for key,label in labels:
            field=QLineEdit(old.get(key,''));fields[key]=field;form.addRow(label,field)
        jump_editor=QPushButton('Éditer graphiquement les rebonds SSH…')
        form.addRow('Chaîne SSH',jump_editor)
        def open_jump_editor():
            try:editor=JumpChainDialog(dialog,fields['jump_chain'].text())
            except ValueError as exc:
                QMessageBox.warning(dialog,'Chaîne invalide',str(exc));return
            if editor.exec()==QDialog.Accepted:fields['jump_chain'].setText(editor.encoded())
        jump_editor.clicked.connect(open_jump_editor)
        full_editor=QPushButton('Éditer tout le parcours SSH (principal inclus)…')
        form.addRow('Parcours complet',full_editor)
        def open_full_editor():
            try:
                from ssh_path_editor import hops_to_route
                from jump_chain_editor import decode_chain,validate_hop
                hops=[validate_hop(fields['jump_host'].text(),fields['jump_port'].text(),fields['jump_user'].text())]+decode_chain(fields['jump_chain'].text())
                current=hops_to_route(hops)
                editor=SSHPathDialog(dialog,current,c['host'])
            except ValueError as exc:
                QMessageBox.warning(dialog,'Parcours SSH invalide',str(exc));return
            if editor.exec()==QDialog.Accepted:
                updated=editor.result_route
                for key in ('jump_host','jump_port','jump_user','jump_chain'):
                    fields[key].setText(updated[key])
        full_editor.clicked.connect(open_full_editor)
        status=QPlainTextEdit();status.setReadOnly(True);layout.addWidget(status)
        actions=QDialogButtonBox(QDialogButtonBox.Save|QDialogButtonBox.Cancel)
        layout.addWidget(actions)
        def update_fields():
            current=mode.currentText()
            for key in ('gateway_host','gateway_port','gateway_user'):
                fields[key].setEnabled(current in ('rd_gateway','rds_collection'))
            fields['collection'].setEnabled(current=='rds_collection')
            for key in ('jump_host','jump_port','jump_user','jump_chain'):
                fields[key].setEnabled(current=='ssh_jump')
            jump_editor.setEnabled(current=='ssh_jump')
            full_editor.setEnabled(current=='ssh_jump')
            preview()
        def current_route():
            current=mode.currentText()
            keys={'direct':(), 'rd_gateway':('gateway_host','gateway_port','gateway_user'),
                  'rds_collection':('gateway_host','gateway_port','gateway_user','collection'),
                  'ssh_jump':('jump_host','jump_port','jump_user','jump_chain')}[current]
            route={'mode':current,'vault_ref':fields['vault_ref'].text()}
            route.update({k:fields[k].text() for k in keys})
            return connection_route(c['protocol'],route)
        def preview():
            try:
                route=current_route()
                result=inspect_access(c,route)
                lines=describe_path(c,route)+[f"Mode : {result['mode']}",f"Client : {result['client'] or 'navigateur'}",
                       'Prérequis locaux : '+('OK' if result['ready'] else 'NON')]
                lines.extend('ERREUR : '+x for x in result['issues'])
                lines.extend('ATTENTION : '+x for x in result['warnings'])
                lines.append('Aucun mot de passe récupéré, aucune connexion testée.')
                status.setPlainText('\n'.join(lines))
            except ValueError as exc:status.setPlainText('ERREUR : '+str(exc))
        def save():
            try:
                route=current_route()
                self.routes.set_route(c['id'],route)
                dialog.accept()
                self.statusBar().showMessage('Chemin de connexion enregistré',5000)
                self._show_route_warning()
            except (ValueError,OSError) as exc:
                QMessageBox.warning(dialog,'Configuration invalide',str(exc))
        mode.currentTextChanged.connect(update_fields)
        for field in fields.values():field.textChanged.connect(preview)
        actions.accepted.connect(save);actions.rejected.connect(dialog.reject)
        update_fields()
        dialog.exec()

    def edit_route(self):
        c=self.selected()
        if not c:return
        old=self.routes.raw_for_edit(c['id'])
        dialog=QDialog(self);dialog.setWindowTitle('Passerelle / Rebond · '+c['name'])
        form=QFormLayout(dialog)
        mode=QComboBox();mode.addItems(['direct','rd_gateway','rds_collection','ssh_jump'])
        mode.setCurrentText(old.get('mode') or 'direct')
        form.addRow('Type de connexion',mode)
        fields={}
        for key,label in [('gateway_host','RD Gateway (FQDN)'),('gateway_port','Port RD Gateway (443)'),
                          ('gateway_user','Utilisateur RD Gateway'),('collection','Collection RDS'),
                          ('jump_host','Hôte SSH de rebond'),('jump_port','Port SSH (22)'),
                          ('jump_user','Utilisateur SSH rebond'),('jump_chain','Rebonds suivants (user@host:port,...)'),('vault_ref','Référence coffre externe (indicative)')]:
            edit=QLineEdit(old.get(key,''));fields[key]=edit;form.addRow(label,edit)
        jump_editor=QPushButton('Éditer graphiquement les rebonds SSH…')
        form.addRow('Chaîne SSH',jump_editor)
        def open_jump_editor():
            try:editor=JumpChainDialog(dialog,fields['jump_chain'].text())
            except ValueError as exc:
                QMessageBox.warning(dialog,'Chaîne invalide',str(exc));return
            if editor.exec()==QDialog.Accepted:fields['jump_chain'].setText(editor.encoded())
        jump_editor.clicked.connect(open_jump_editor)
        full_editor=QPushButton('Éditer tout le parcours SSH (principal inclus)…')
        form.addRow('Parcours complet',full_editor)
        def open_full_editor():
            try:
                from ssh_path_editor import hops_to_route
                from jump_chain_editor import decode_chain,validate_hop
                hops=[validate_hop(fields['jump_host'].text(),fields['jump_port'].text(),fields['jump_user'].text())]+decode_chain(fields['jump_chain'].text())
                current=hops_to_route(hops)
                editor=SSHPathDialog(dialog,current,c['host'])
            except ValueError as exc:
                QMessageBox.warning(dialog,'Parcours SSH invalide',str(exc));return
            if editor.exec()==QDialog.Accepted:
                updated=editor.result_route
                for key in ('jump_host','jump_port','jump_user','jump_chain'):
                    fields[key].setText(updated[key])
        full_editor.clicked.connect(open_full_editor)
        jump_editor.setEnabled(mode.currentText()=='ssh_jump')
        full_editor.setEnabled(mode.currentText()=='ssh_jump')
        mode.currentTextChanged.connect(lambda value:jump_editor.setEnabled(value=='ssh_jump'))
        mode.currentTextChanged.connect(lambda value:full_editor.setEnabled(value=='ssh_jump'))
        form.addRow(QLabel('Coffre externe : référence documentaire uniquement, aucune récupération de secret.'))
        buttons=QDialogButtonBox(QDialogButtonBox.Ok|QDialogButtonBox.Cancel)
        form.addRow(buttons);buttons.accepted.connect(dialog.accept);buttons.rejected.connect(dialog.reject)
        if dialog.exec()!=QDialog.Accepted:return
        try:
            route=validate_route({'mode':mode.currentText(),**{k:v.text() for k,v in fields.items()}})
            route=connection_route(c['protocol'],route)
            self.routes.set_route(c['id'],route)
            self.statusBar().showMessage('Passerelle enregistrée pour '+c['name'],5000)
            self._show_route_warning()
        except (ValueError,OSError) as exc:QMessageBox.warning(self,'Passerelle',str(exc))

    def show_pam_profiles(self):
        dialog=QDialog(self);dialog.setWindowTitle('Profils PAM — sans secrets');dialog.resize(690,380)
        layout=QVBoxLayout(dialog)
        layout.addWidget(QLabel('Configuration des fournisseurs seulement : aucun accès au coffre ni broker de session.'))
        entries=QListWidget();layout.addWidget(entries)
        def refresh():
            entries.clear()
            for p in sorted(self.pam_profiles.items,key=lambda x:x['name'].casefold()):
                item=QListWidgetItem(f"{p['name']} | {p['provider']} | {p['endpoint']}")
                item.setData(Qt.UserRole,p['name']);entries.addItem(item)
        refresh()
        buttons=QHBoxLayout();layout.addLayout(buttons)
        add=QPushButton('Ajouter / Modifier');remove=QPushButton('Supprimer')
        buttons.addWidget(add);buttons.addWidget(remove)
        def edit():
            selected=entries.currentItem()
            current=next((p for p in self.pam_profiles.items if selected and p['name']==selected.data(Qt.UserRole)),None)
            name,ok=QInputDialog.getText(dialog,'Profil PAM','Nom du profil :',text=current['name'] if current else '')
            if not ok:return
            provider,ok=QInputDialog.getItem(dialog,'Fournisseur','Type :',list(PROVIDERS),
                                              list(PROVIDERS).index(current['provider']) if current else 0,False)
            if not ok:return
            endpoint,ok=QInputDialog.getText(dialog,'Point d’accès HTTPS','URL (sans identifiant ni secret) :',
                                             text=current['endpoint'] if current else 'https://')
            if not ok:return
            try:self.pam_profiles.set_profile({'name':name,'provider':provider,'endpoint':endpoint})
            except (ValueError,OSError) as exc:
                QMessageBox.warning(dialog,'Profil refusé',str(exc));return
            refresh()
        def delete():
            item=entries.currentItem()
            if item is None:return
            name=item.data(Qt.UserRole)
            if QMessageBox.question(dialog,'Supprimer',f'Supprimer le profil {name} ?')!=QMessageBox.Yes:return
            try:self.pam_profiles.remove_profile(name)
            except OSError as exc:QMessageBox.warning(dialog,'Erreur',str(exc));return
            refresh()
        add.clicked.connect(edit);remove.clicked.connect(delete)
        dialog.exec()

    def show_pam_lab(self):
        """Deliberately isolated laboratory: never launches a network session."""
        dialog=QDialog(self);dialog.setWindowTitle('Laboratoire PAM — SIMULATION UNIQUEMENT')
        dialog.resize(750,520)
        layout=QVBoxLayout(dialog)
        layout.addWidget(QLabel('Simulation locale sans accès au coffre ni ouverture de session réelle.'))
        form=QFormLayout();layout.addLayout(form)
        principal=QLineEdit();reference=QLineEdit();target=QLineEdit()
        selected=self.selected()
        if selected:
            principal.setText(selected.get('user','') or 'operator')
            target.setText(selected.get('host',''))
            try:reference.setText(self.routes.for_connection(selected['id']).get('vault_ref',''))
            except ValueError:pass
        form.addRow('Utilisateur simulé',principal)
        form.addRow('Référence PAM',reference)
        form.addRow('Machine cible',target)
        ttl=QComboBox();ttl.addItems(['5','30','60','300']);ttl.setCurrentText('60')
        form.addRow('Durée de validité (secondes)',ttl)
        approval=QCheckBox('J’autorise explicitement cette simulation locale (aucune session réelle)')
        layout.addWidget(approval)
        buttons=QHBoxLayout();layout.addLayout(buttons)
        authorize=QPushButton('Simuler autorisation')
        consume=QPushButton('Simuler ouverture de session')
        consume.setEnabled(False)
        buttons.addWidget(authorize);buttons.addWidget(consume)
        scenarios=QPushButton('Exécuter scénarios');save_audit=QPushButton('Exporter audit JSON');verify_audit=QPushButton('Vérifier audit JSON');verify_signature=QPushButton('Vérifier signature Ed25519')
        buttons.addWidget(scenarios);buttons.addWidget(save_audit);buttons.addWidget(verify_audit);buttons.addWidget(verify_signature)
        output=QPlainTextEdit();output.setReadOnly(True);layout.addWidget(output)
        state={'broker':None,'grant':None}
        def render_audit():
            broker=state['broker']
            if broker is None:return
            for event in broker.audit()[state.get('shown',0):]:
                output.appendPlainText(f"{event['timestamp']} | {event['action']} | {event['decision']} | {event['reason']}")
            state['shown']=len(broker.audit())
        def request_grant():
            state['broker']=SimulatedPamBroker(time.time,int(ttl.currentText()))
            state['grant']=None;state['shown']=0;consume.setEnabled(False)
            try:
                state['grant']=state['broker'].authorize(principal.text(),reference.text(),target.text(),approved=approval.isChecked())
                consume.setEnabled(True)
                output.appendPlainText('Autorisation simulée accordée ; usage unique et durée limitée.')
            except (PermissionError,ValueError) as exc:
                output.appendPlainText('REFUS : '+str(exc))
            render_audit()
        def open_simulated():
            broker=state['broker'];grant=state['grant']
            consume.setEnabled(False)
            if broker is None or grant is None:return
            try:
                result=broker.open_session(grant.grant_id,principal.text(),reference.text(),target.text())
                output.appendPlainText(result['message'])
            except PermissionError as exc:output.appendPlainText('REFUS : '+str(exc))
            finally:
                state['grant']=None
                render_audit()
        def run_tests():
            report=run_scenarios()
            for entry in report['results']:
                output.appendPlainText(f"TEST {entry['scenario']} : {entry['result']}")
            output.appendPlainText('Tests isolés du broker actif : aucune session réelle.')
        def save_events():
            broker=state['broker']
            if broker is None or not broker.audit():
                QMessageBox.information(dialog,'Audit vide','Effectuez une simulation avant export.')
                return
            filename,_=QFileDialog.getSaveFileName(dialog,'Exporter audit PAM simulé','pam-lab-audit.json','JSON (*.json)')
            if not filename:return
            try:
                report=export_report(filename,broker.audit())
                output.appendPlainText('Audit exporté, SHA-256 final : '+report['final_hash'])
            except (OSError,ValueError) as exc:
                QMessageBox.warning(dialog,'Export impossible',str(exc))
        def verify_events():
            filename,_=QFileDialog.getOpenFileName(dialog,'Vérifier un audit PAM','', 'JSON (*.json)')
            if not filename:return
            try:
                report=load_and_verify_report(filename)
                verdict='INTÈGRE (non signé)' if report['valid'] else 'NON VALIDE / MODIFIÉ'
                output.appendPlainText(f"Vérification audit : {verdict} | événements : {report['event_count']}")
                QMessageBox.information(dialog,'Vérification audit',verdict)
            except (OSError,ValueError) as exc:
                QMessageBox.warning(dialog,'Audit illisible',str(exc))
        scenarios.clicked.connect(run_tests)
        def verify_signed_events():
            from pam_audit_signatures import verify_signed_files
            report,_=QFileDialog.getOpenFileName(dialog,'Audit JSON','', 'JSON (*.json)')
            if not report:return
            signature,_=QFileDialog.getOpenFileName(dialog,'Signature détachée','', 'JSON (*.json)')
            if not signature:return
            public,_=QFileDialog.getOpenFileName(dialog,'Clé publique Ed25519','', 'PEM (*.pem);;Tous (*.*)')
            if not public:return
            try:
                valid=verify_signed_files(report,signature,public)
                message='Signature VALIDE' if valid else 'Signature INVALIDE'
                output.appendPlainText(message)
                QMessageBox.information(dialog,'Signature Ed25519',message)
            except (OSError,ValueError) as exc:
                QMessageBox.warning(dialog,'Vérification impossible',str(exc))
        verify_signature.clicked.connect(verify_signed_events)
        verify_audit.clicked.connect(verify_events)
        save_audit.clicked.connect(save_events)
        authorize.clicked.connect(request_grant)
        consume.clicked.connect(open_simulated)
        dialog.exec()

    def show_pam_status(self):
        c=self.selected()
        if not c:
            QMessageBox.information(self,'État PAM','Sélectionnez une connexion.')
            return
        try:
            route=self.routes.for_connection(c['id'])
            result=capability_report(route.get('vault_ref',''))
            binding=resolve_pam_profile(route.get('vault_ref',''),self.pam_profiles.items)
            connector_status=ConnectorRegistry(self.pam_profiles.items).inspect(route.get('vault_ref',''))
            lines=[
                'Connexion : '+c['name'],
                'Fournisseur : '+str(result['provider'] or 'Aucun'),
                'Référence : '+str(result['reference'] or 'Aucune'),
                'Récupération de secret : NON DISPONIBLE',
                'Ouverture de session PAM : NON DISPONIBLE',
                '',
                result['message'],
                'Profils fournisseurs correspondants : '+(', '.join(binding['profiles']) or 'aucun'),
                'Ouverture de session autorisée via PAM : NON',
                'Politique connecteur : '+connector_status['reason'],
            ]
            QMessageBox.information(self,'État PAM','\\n'.join(lines))
        except ValueError as exc:
            QMessageBox.warning(self,'Référence PAM invalide',str(exc))

    def export_access_diagnostic(self):
        c=self.selected()
        if not c:return
        route=self._safe_route(c['id'])
        if route is None:return
        try:payload=json_report(c,route)
        except (ValueError,KeyError) as exc:
            QMessageBox.warning(self,'Diagnostic non disponible',str(exc));return
        filename,_=QFileDialog.getSaveFileName(self,'Exporter le diagnostic',
            'openremote-access-diagnostic.json','JSON (*.json)')
        if not filename:return
        try:
            from pathlib import Path
            Path(filename).write_text(payload,encoding='utf-8')
        except OSError as exc:
            QMessageBox.warning(self,'Export impossible',str(exc));return
        QMessageBox.information(self,'Diagnostic exporté',
            'Rapport local enregistré. Aucun test réseau ou PAM n’a été effectué.')

    def check_access(self):
        c=self.selected()
        if not c:return
        route=self._safe_route(c['id'])
        if route is None:return
        result=inspect_access(c,route)
        lines=describe_path(c,route)+['Protocole : '+c['protocol'],'Route : '+str(result['mode']),
               'Client : '+str(result['client'] or 'navigateur')]
        lines.extend('ERREUR : '+issue for issue in result['issues'])
        lines.extend('ATTENTION : '+warning for warning in result['warnings'])
        lines.append('Préparation locale : '+('OK' if result['ready'] else 'NON'))
        lines.append('Aucune connexion réseau ni authentification testée.')
        QMessageBox.information(self,'Pré-vérification de connexion','\n'.join(lines))

    def test_tcp_connection(self):
        """Probe each configured endpoint independently, with explicit consent."""
        c=self.selected()
        if not c:return
        route=self._safe_route(c['id'])
        if route is None:return
        try:
            from network_probe import route_hops
            hops=route_hops(c,route)
        except ValueError as exc:
            QMessageBox.warning(self,'Diagnostic TCP',str(exc));return
        targets='\n'.join(f"• {hop['role']} : {hop['host']}:{hop['port']} — {hop['scope']}" for hop in hops)
        if QMessageBox.question(self,'Diagnostic TCP — consentement',
            'Tester séparément les ports TCP suivants ?\n'+targets+
            '\n\nLes tests partent de ce poste et ne traversent aucun rebond. '
            'Aucune authentification ne sera tentée.',
            QMessageBox.Yes|QMessageBox.No)!=QMessageBox.Yes:return
        dialog=QDialog(self);dialog.setWindowTitle('Diagnostic de chemin TCP (local)')
        dialog.resize(650,350)
        layout=QVBoxLayout(dialog)
        layout.addWidget(QLabel('Chaque point est testé directement depuis ce poste ; aucune route distante validée.'))
        output=QPlainTextEdit();output.setReadOnly(True);layout.addWidget(output)
        close=QPushButton('Fermer');close.clicked.connect(dialog.accept);layout.addWidget(close)
        self._tcp_probe_jobs=[]
        for hop in hops:
            job=TcpJob(hop['host'],hop['port'])
            job.signals.finished.connect(lambda result,h=hop,identity=c['id']:self._record_tcp_probe(identity,h,result,output))
            self._tcp_probe_jobs.append(job)
            self.pool.start(job)
        dialog.exec()

    def test_ssh_jump_path(self):
        """Explicit opt-in; a bounded worker never blocks the Qt event loop."""
        c=self.selected()
        if not c:return
        route=self._safe_route(c['id'])
        if route is None:return
        try:
            from ssh_path_probe import command
            command(c,route)
        except ValueError as exc:
            QMessageBox.warning(self,'Diagnostic via bastion SSH',str(exc));return
        if QMessageBox.question(self,'Diagnostic SSH — consentement',
            'Ouvrir un canal SSH -W vers la cible via le bastion configuré ?\n'
            'Le client SSH utilise les clés locales et known_hosts, sans demande interactive de mot de passe.\n'
            'Aucune commande distante ne sera exécutée. Ce test peut produire des traces réseau.',
            QMessageBox.Yes|QMessageBox.No)!=QMessageBox.Yes:return
        from qt_workers import SshPathJob
        dialog=QDialog(self);dialog.setWindowTitle('Diagnostic via bastion SSH')
        layout=QVBoxLayout(dialog)
        result=QLabel('Contrôle en cours…');layout.addWidget(result)
        job=SshPathJob(c.copy(),route.copy())
        job.signals.finished.connect(lambda message,identity=c['id']:self._record_ssh_probe(identity,message,result))
        self._ssh_path_job=job
        self.pool.start(job)
        dialog.exec()

    def _save_probe(self, identity, kind, outcome):
        try:
            self.probe_history.add(identity,kind,outcome)
        except (OSError,ValueError,sqlite3.Error) as exc:
            self.statusBar().showMessage('Historique diagnostic indisponible : '+type(exc).__name__,10000)

    def _record_tcp_probe(self, identity, hop, message, output):
        # Raw diagnostic output stays on screen; only sanitized status is persisted.
        output.appendPlainText(hop['role']+' — '+message+'\nTest direct local, pas de validation de chemin distant.')
        lower=message.lower()
        outcome='failed' if any(word in lower for word in ('refus','failed','error','échec','impossible','timeout','expir')) else 'unknown'
        self._save_probe(identity,'tcp_local',outcome)

    def _record_ssh_probe(self, identity, message, label):
        label.setText(message)
        self._save_probe(identity,'ssh_jump',classify_ssh_result(message))

    def show_connection_timeline(self):
        """Read-only chronological view of local events for the selected connection."""
        c=self.selected()
        if not c:return
        dialog=QDialog(self);dialog.setWindowTitle('Chronologie locale — '+c['name']);dialog.resize(850,540)
        layout=QVBoxLayout(dialog)
        layout.addWidget(QLabel('Événements locaux uniquement : aucune preuve de connexion distante réussie.'))
        controls=QHBoxLayout();layout.addLayout(controls)
        selector=QComboBox()
        for label,key in [('Tous','all'),('Sessions','session'),('Diagnostics','probe'),('Erreurs','error')]:selector.addItem(label,key)
        controls.addWidget(selector)
        table=QTableWidget(0,4);table.setHorizontalHeaderLabels(['Date UTC','Catégorie','État','Détail'])
        table.setEditTriggers(QAbstractItemView.NoEditTriggers);layout.addWidget(table)
        def load():
            try:
                self.external_sessions.snapshot()
                rows=timeline(self.session_history.recent(1000),self.probe_history.recent(c['id'],500),c['id'],kind=selector.currentData())
            except (OSError,ValueError,sqlite3.Error) as exc:
                QMessageBox.warning(dialog,'Chronologie indisponible',type(exc).__name__);return []
            table.setRowCount(len(rows))
            for i,row in enumerate(rows):
                for j,value in enumerate((row['at'],row['kind'],row['state'],row['detail'])):
                    table.setItem(i,j,QTableWidgetItem(value))
            return rows
        def export():
            rows=load()
            if not rows:return
            path,_=QFileDialog.getSaveFileName(dialog,'Exporter la chronologie','chronologie.csv','CSV (*.csv)')
            if not path:return
            try:Path(path).write_text(export_timeline(rows),encoding='utf-8')
            except OSError as exc:QMessageBox.warning(dialog,'Export impossible',type(exc).__name__)
        selector.currentIndexChanged.connect(load)
        refresh=QPushButton('Actualiser');refresh.clicked.connect(load);controls.addWidget(refresh)
        save=QPushButton('Exporter CSV');save.clicked.connect(export);controls.addWidget(save)
        load();dialog.exec()

    def show_connection_card(self):
        """Unified, read-only connection card; network probes remain explicit opt-in."""
        c=self.selected()
        if not c:return
        dialog=QDialog(self);dialog.setWindowTitle('Fiche de connexion — '+c['name']);dialog.resize(790,530)
        layout=QVBoxLayout(dialog)
        layout.addWidget(QLabel('Connexion : '+c['name']+'  |  Protocole : '+c['protocol']))
        layout.addWidget(QLabel('Hôte : '+c['host']+'  |  Port : '+str(c.get('port') or 'défaut')))
        layout.addWidget(QLabel('Historique local indicatif ; aucune authentification distante validée.'))
        health=None
        try:
            self.external_sessions.snapshot()
            health=summarize_connection(self.session_history.statistics(),c['id'])
            coverage='—' if health['coverage'] is None else f"{health['coverage']:.1f}%"
            layout.addWidget(QLabel(f"Fiabilité locale : {health['status']}"))
            layout.addWidget(QLabel(f"Tentatives : {health['attempts']} | Sorties observées : {health['observed']} | Échecs : {health['failures']} | Inconnues : {health['unknown']} | Couverture : {coverage}"))
            layout.addWidget(QLabel('Conseil : '+health['advice']))
        except (OSError,ValueError,sqlite3.Error) as exc:
            layout.addWidget(QLabel('Statistiques locales indisponibles : '+type(exc).__name__))

        try:
            events=timeline(self.session_history.recent(1000),self.probe_history.recent(c['id'],500),c['id'],limit=500)
            alert=correlate(events)
            layout.addWidget(QLabel(f"Échecs locaux récents (30 min) : {alert['count']} | Récurrence : {'oui' if alert['recurrent'] else 'non'}"))
            layout.addWidget(QLabel('Conseil : '+alert['advice']))
        except (OSError,ValueError,sqlite3.Error) as exc:
            layout.addWidget(QLabel('Corrélation indisponible : '+type(exc).__name__))

        from connection_guidance import guidance, format_guidance
        def show_protocol_guide():
            try:
                result=guidance(c['protocol'],failures=health.get('failures',0) if isinstance(health,dict) else 0,
                                pam=bool(c.get('vault_ref')))
                QMessageBox.information(dialog,'Diagnostic guidé',format_guidance(result))
            except ValueError:
                QMessageBox.warning(dialog,'Diagnostic guidé','Protocole non pris en charge.')
        def show_path_diagnostics():
            from connection_path_diagnostics import topology, format_topology
            try:
                route=self._safe_route(c['id'])
                if route is None:return
                result=topology(c['protocol'],route)
                QMessageBox.information(dialog,'Parcours et dépendances',format_topology(result))
            except ValueError:
                QMessageBox.warning(dialog,'Parcours et dépendances','Parcours invalide ou incompatible avec le protocole.')
        path_button=QPushButton('Parcours et dépendances (hors ligne)')
        path_button.setToolTip('Visualiser les étapes du chemin sans révéler les hôtes ni contacter le réseau')
        path_button.clicked.connect(show_path_diagnostics)
        layout.addWidget(path_button)
        def show_path_evidence():
            from connection_path_evidence import correlate, format_evidence
            try:
                route=self._safe_route(c['id'])
                if route is None:return
                local=health if isinstance(health,dict) else {}
                result=correlate(c['protocol'],route,attempts=local.get('attempts',0),
                                 failures=local.get('failures',0),unknown=local.get('unknown',0))
                QMessageBox.information(dialog,'Corrélation du parcours',format_evidence(result))
            except (ValueError,TypeError):
                QMessageBox.warning(dialog,'Corrélation du parcours','Historique local ou parcours invalide.')
        evidence_button=QPushButton('Corréler le parcours avec les échecs locaux')
        evidence_button.setToolTip('Ne désigne jamais un bastion ou une cible comme défaillant sans preuve directe')
        evidence_button.clicked.connect(show_path_evidence)
        layout.addWidget(evidence_button)
        def show_probe_path_evidence():
            from connection_probe_evidence import correlate_probes, format_probe_evidence
            try:
                route=self._safe_route(c['id'])
                if route is None:return
                rows=self.probe_history.recent(c['id'],limit=50)
                # ProbeHistory returns connection_id, kind, outcome, observed_at.
                records=[(row[1],row[2]) for row in reversed(rows)]
                result=correlate_probes(c['protocol'],route,records)
                QMessageBox.information(dialog,'Observations du parcours',format_probe_evidence(result))
            except (ValueError,TypeError,IndexError,sqlite3.Error,OSError):
                QMessageBox.warning(dialog,'Observations du parcours','Historique ou parcours indisponible.')
        probe_evidence_button=QPushButton('Chronologie des précontrôles TCP / SSH')
        probe_evidence_button.setToolTip('Présente les observations locales sans attribuer une panne à un saut distant')
        probe_evidence_button.clicked.connect(show_probe_path_evidence)
        layout.addWidget(probe_evidence_button)
        guide_button=QPushButton('Conseils protocole (hors ligne)')
        guide_button.clicked.connect(show_protocol_guide)
        layout.addWidget(guide_button)
        table=QTableWidget(0,3);table.setHorizontalHeaderLabels(['Diagnostic','Résultat','Date UTC'])
        table.setEditTriggers(QAbstractItemView.NoEditTriggers);layout.addWidget(table)
        def refresh():
            try:rows=self.probe_history.recent(c['id'],limit=50)
            except (OSError,ValueError,sqlite3.Error) as exc:
                QMessageBox.warning(dialog,'Historique indisponible',type(exc).__name__);return
            table.setRowCount(len(rows))
            for i,(_,kind,outcome,when) in enumerate(rows):
                for j,value in enumerate((kind,outcome,when)):
                    table.setItem(i,j,QTableWidgetItem(str(value)))
        actions=QHBoxLayout();layout.addLayout(actions)
        for title,fn in [('Actualiser',refresh),('Chronologie',self.show_connection_timeline),('Vérifier accès',self.check_access),
                         ('Tester TCP',self.test_tcp_connection),('Tester via bastion',self.test_ssh_jump_path)]:
            button=QPushButton(title);button.clicked.connect(fn);actions.addWidget(button)
        close=QPushButton('Fermer');close.clicked.connect(dialog.accept);layout.addWidget(close)
        refresh();dialog.exec()

    def show_probe_history(self):
        dialog=QDialog(self);dialog.setWindowTitle('Historique des diagnostics — métadonnées uniquement')
        dialog.resize(820,470)
        layout=QVBoxLayout(dialog)
        layout.addWidget(QLabel('Résultats indicatifs : aucun secret, cible, stderr ou commande conservé dans cet historique.'))
        controls=QHBoxLayout();layout.addLayout(controls)
        selector=QComboBox();selector.addItem('Toutes les connexions',None)
        for c in self.store.items:selector.addItem(c.get('name',c['id']),c['id'])
        controls.addWidget(selector)
        refresh=QPushButton('Actualiser');controls.addWidget(refresh)
        table=QTableWidget(0,4);table.setHorizontalHeaderLabels(['Connexion','Type','Résultat','Date UTC'])
        table.setEditTriggers(QAbstractItemView.NoEditTriggers);layout.addWidget(table)
        def populate():
            try:rows=self.probe_history.recent(selector.currentData())
            except (OSError,ValueError,sqlite3.Error) as exc:
                QMessageBox.warning(dialog,'Historique indisponible',type(exc).__name__);return
            names={c['id']:c.get('name',c['id']) for c in self.store.items}
            table.setRowCount(len(rows))
            for index,(identity,kind,outcome,when) in enumerate(rows):
                for column,value in enumerate((names.get(identity,'Connexion supprimée'),kind,outcome,when)):
                    table.setItem(index,column,QTableWidgetItem(value))
        refresh.clicked.connect(populate);selector.currentIndexChanged.connect(populate)
        populate();dialog.exec()

    def reconnect_selected(self):
        """Require an explicit process choice for connection-level reconnect actions."""
        from session_reconnect_choices import reconnectable_processes, reconnect_choice_still_valid
        c=self.selected()
        if not c:return
        rows=self.external_sessions.snapshot()
        candidates=reconnectable_processes(rows,c['id'])
        if not candidates:
            QMessageBox.information(self,'Reconnexion indisponible',
                'Aucune session terminée identifiable sans ambiguïté, ou une session est encore active.');return
        labels=[f"{i+1}. PID {row['pid']} — {row.get('protocol','client externe')}" for i,row in enumerate(candidates)]
        label,ok=QInputDialog.getItem(self,'Reconnecter une session',
            'Choisir le processus terminé à reconnecter :',labels,0,False)
        if not ok:return
        index=labels.index(label)
        pid=candidates[index]['pid']
        # The user may have changed the selected connection while the dialog was open.
        current=self.selected()
        if not current or current.get('id') != c['id']:
            QMessageBox.information(self,'Reconnexion indisponible','La connexion sélectionnée a changé.');return
        # Re-evaluate immediately before launch: a process may have changed state.
        if not reconnect_choice_still_valid(self.external_sessions.snapshot(), c['id'], pid):
            QMessageBox.information(self,'Reconnexion indisponible',
                'La liste des sessions a changé ; actualisez les sessions.');return
        if not any(item.get('id') == c['id'] for item in self.store.items):
            QMessageBox.warning(self,'Connexion absente','Cette connexion a été supprimée.');return
        from session_reconnect_controller import resolve_reconnect_target
        verified,reason=resolve_reconnect_target(self.external_sessions,self.store.items,c['id'],pid)
        if verified is None:
            QMessageBox.information(self,'Reconnexion indisponible',f'Contrôle préalable refusé : {reason}');return
        if not self.external_sessions.reconnect_candidate(c['id'],pid):
            QMessageBox.information(self,'Reconnexion indisponible',
                'La session sélectionnée a changé ; actualisez les sessions.');return
        self.launch_connection(c)

    def connect(self):
        c=self.selected()
        if c:self.launch_connection(c)

    def show_local_readiness(self):
        """Reusable in-workspace local readiness view; no remote probes or credentials."""
        from windows_client_health import inspect_clients
        from local_readiness_filter import visible_local_clients
        from local_diagnostic_summary import summarize_local_clients
        from local_readiness_actions import repair_guidance
        for index in range(self.tabs.count()):
            if self.tabs.widget(index).objectName() == 'localReadinessTab':
                self.tabs.setCurrentIndex(index)
                self.tabs.widget(index).reload_local_clients()
                return
        pane = QWidget()
        pane.setObjectName('localReadinessTab')
        layout = QVBoxLayout(pane)
        heading = QLabel('Diagnostic local des clients SSH · SFTP · RDP · VNC')
        layout.addWidget(heading)
        layout.addWidget(QLabel('Lecture seule : aucune connexion distante, aucun secret consulté.'))
        summary = QLabel('Inventaire en attente')
        summary.setObjectName('localReadinessSummary')
        layout.addWidget(summary)
        guidance = QLabel('')
        guidance.setWordWrap(True)
        guidance.setObjectName('localReadinessGuidance')
        layout.addWidget(guidance)
        repairs = QPlainTextEdit()
        repairs.setObjectName('localReadinessRepairs')
        repairs.setReadOnly(True)
        repairs.setPlaceholderText('Conseils de correction locaux, sans modification automatique du système')
        repairs.setMaximumHeight(135)
        layout.addWidget(repairs)
        issues_only = QCheckBox('Afficher uniquement les clients à corriger')
        issues_only.setToolTip('Filtre local de présentation : ne modifie ni le système ni le rapport copié')
        layout.addWidget(issues_only)
        count_label = QLabel('Clients affichés : 0')
        count_label.setObjectName('localReadinessCount')
        layout.addWidget(count_label)
        table = QTableWidget(0, 3)
        table.setHorizontalHeaderLabels(['Protocole', 'Client', 'État local'])
        table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        table.setSelectionBehavior(QAbstractItemView.SelectRows)
        layout.addWidget(table)
        def reload():
            try:
                report = inspect_clients()
                rows, visible_count, total_count = visible_local_clients(report, issues_only.isChecked())
                headline, advice = summarize_local_clients(report)
            except (OSError, ValueError, TypeError):
                QMessageBox.warning(self, 'Diagnostic local', 'Inventaire local indisponible.')
                return
            summary.setText(headline)
            count_label.setText(f'Clients affichés : {visible_count} / {total_count}')
            guidance.setText(advice)
            repairs.setPlainText(repair_guidance(report))
            table.setRowCount(len(rows))
            for i, row in enumerate(rows):
                for j, value in enumerate(row):
                    table.setItem(i, j, QTableWidgetItem(value))
        pane.reload_local_clients = reload
        issues_only.toggled.connect(lambda _checked: reload())
        controls = QHBoxLayout()
        refresh = QPushButton('Actualiser les clients locaux')
        refresh.clicked.connect(reload)
        controls.addWidget(refresh)
        copy_report = QPushButton('Copier le diagnostic et les conseils')
        copy_report.setToolTip('Copie le diagnostic local dans le presse-papiers, sans identifiants ni connexion distante')
        copy_report.clicked.connect(lambda: QApplication.clipboard().setText(summary.text() + '\n' + guidance.text() + '\n' + repairs.toPlainText()))
        controls.addWidget(copy_report)
        layout.addLayout(controls)
        self.tabs.addTab(pane, 'Diagnostic local')
        self.tabs.setCurrentWidget(pane)
        reload()

    def show_windows_clients(self):
        """Explicit read-only inventory of external clients on this workstation."""
        from windows_client_health import inspect_clients
        report = inspect_clients()
        dialog = QDialog(self)
        dialog.setWindowTitle('Diagnostic clients locaux — SSH / SFTP / RDP / VNC')
        dialog.resize(680, 350)
        layout = QVBoxLayout(dialog)
        layout.addWidget(QLabel('Inventaire local uniquement : aucun serveur distant ni accès PAM testé.'))
        layout.addWidget(QLabel(f"Clients disponibles : {report['ready_count']} / 4"))
        table = QTableWidget(len(report['rows']), 3)
        table.setHorizontalHeaderLabels(['Protocole', 'Client attendu', 'Diagnostic local'])
        table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        for index, item in enumerate(report['rows']):
            for column, value in enumerate((item['protocol'], item['client'], item['status'])):
                table.setItem(index, column, QTableWidgetItem(value))
        layout.addWidget(table)
        layout.addWidget(QLabel('RDP utilise mstsc.exe sur Windows ; VNC nécessite un client externe compatible.'))
        close = QPushButton('Fermer')
        close.clicked.connect(dialog.accept)
        layout.addWidget(close)
        dialog.exec()

    def launch_connection(self,c):
        # Apply the same duplicate guard to the toolbar, double-click and reconnect actions.
        # WEB launches are not tracked as child processes and remain unaffected.
        if c['protocol']!='WEB' and self.external_sessions.has_running(c['id']):
            QMessageBox.information(self,'Session déjà active',
                'Un client externe est déjà actif pour cette connexion. Consultez Outils > Sessions externes.')
            return
        route=self._safe_route(c['id'])
        if route is None:return
        session_file=None
        try:
            plan=build_launch_plan(c,route)
            if not plan['ready']:raise RuntimeError('Pré-vérification : '+' ; '.join(plan['issues']))
            if c['protocol']=='WEB':
                webbrowser.open(c['host'] if '://' in c['host'] else 'https://'+c['host']);return
            if plan['rdp']:
                session_file=write_session(self.rdp_directory,c['host'],c['port'],c['user'],route)
                args=['mstsc',str(session_file)]
            else:args=plan['args']
            proc=subprocess.Popen(args,creationflags=subprocess.CREATE_NEW_CONSOLE if os.name=='nt' else 0)
            self.external_sessions.register(c,proc)
            if session_file is not None:self.rdp_files.append(str(session_file))
            self._record_open(c)
            self.log.append('Client externe ouvert : '+c['protocol']+' · '+c['name'])
            self.refresh_session_overview()
        except (OSError,RuntimeError,ValueError) as exc:
            if session_file is not None:
                try:session_file.unlink(missing_ok=True)
                except OSError:pass
            from client_launch_diagnostics import launch_failure
            diagnosis=launch_failure(c['protocol'],exc)
            QMessageBox.warning(self,'Connexion impossible',diagnosis['message'])
    def show_external_sessions(self):
        dialog=QDialog(self);dialog.setWindowTitle('Sessions externes — suivi local')
        dialog.resize(850,430)
        layout=QVBoxLayout(dialog)
        layout.addWidget(QLabel('Clients externes lancés depuis cette instance. Fermer ce dialogue ne termine aucune session.'))
        listing=QTreeWidget();listing.setHeaderLabels(['Connexion','Protocole','PID','État','Début (UTC)']);layout.addWidget(listing)
        controls=QHBoxLayout();layout.addLayout(controls)
        refresh=QPushButton('Actualiser');cleanup=QPushButton('Masquer les sessions terminées');reconnect=QPushButton('Reconnecter la session sélectionnée')
        controls.addWidget(refresh);controls.addWidget(cleanup);controls.addWidget(reconnect)
        def populate():
            listing.clear()
            for item in self.external_sessions.snapshot():
                row=QTreeWidgetItem([item['name'],item['protocol'],str(item['pid']),
                    session_status_label(item),item['started_at']])
                row.setData(0,Qt.UserRole,item['connection_id']);row.setData(0,Qt.UserRole+1,item['pid']);listing.addTopLevelItem(row)
        def clear():
            self.external_sessions.clear_exited();populate()
        def reconnect_row():
            row=listing.currentItem()
            if row is None:return
            identity=row.data(0,Qt.UserRole)
            pid=row.data(0,Qt.UserRole+1)
            # Recheck the exact process on a fresh snapshot: the dialog can be stale.
            from session_reconnect_choices import reconnect_choice_still_valid
            if not reconnect_choice_still_valid(self.external_sessions.snapshot(), identity, pid):
                QMessageBox.information(dialog,'Reconnexion indisponible',
                    'Le processus sélectionné a changé, est ambigu ou une session est active. Actualisez la liste.');return
            connection=next((c for c in self.store.items if c['id']==identity),None)
            if connection is None:
                QMessageBox.warning(dialog,'Connexion supprimée','Cette connexion n’existe plus.');return
            # Validate the target before consuming the selected reconnect candidate.
            from session_reconnect_controller import resolve_reconnect_target
            verified,reason=resolve_reconnect_target(self.external_sessions,self.store.items,identity,pid)
            if verified is None:
                QMessageBox.information(dialog,'Reconnexion indisponible',f'Contrôle préalable refusé : {reason}');return
            if not self.external_sessions.reconnect_candidate(identity,pid):
                QMessageBox.information(dialog,'Reconnexion','Aucune session terminée à reconnecter.');return
            self.launch_connection(connection)
            populate()
        refresh.clicked.connect(populate);cleanup.clicked.connect(clear);reconnect.clicked.connect(reconnect_row)
        populate();dialog.exec()

    def network(self,command):
        c=self.selected()
        if not c or c['protocol']=='WEB':
            QMessageBox.information(self,'Outils','Sélectionner un hôte');return
        kind={'ping':'ping','nslookup':'dns','tracert':'traceroute','traceroute':'traceroute'}.get(command)
        try:
            args=command_args(kind,c['host'])
        except ValueError as exc:
            QMessageBox.warning(self,'Diagnostic',str(exc));return
        from PySide6.QtCore import QProcess
        pane=QWidget();layout=QVBoxLayout(pane)
        output=QPlainTextEdit();output.setReadOnly(True);layout.addWidget(output)
        stop=QPushButton('Arrêter le diagnostic');layout.addWidget(stop)
        self.tabs.addTab(pane,args[0]+' · '+c['name']);self.tabs.setCurrentWidget(pane)
        proc=QProcess(pane);proc.setProgram(args[0]);proc.setArguments(args[1:])
        proc.setProcessChannelMode(QProcess.MergedChannels)
        proc.readyReadStandardOutput.connect(
            lambda:output.insertPlainText(bytes(proc.readAllStandardOutput()).decode(errors='replace')))
        proc.errorOccurred.connect(lambda _:output.appendPlainText('Impossible de lancer le diagnostic'))
        proc.finished.connect(lambda code,*_:output.appendPlainText(f'Diagnostic terminé (code {code})'))
        stop.clicked.connect(lambda:proc.kill() if proc.state()!=QProcess.NotRunning else None)
        timeout=QTimer(pane);timeout.setSingleShot(True);timeout.setInterval(15000)
        def expired():
            if proc.state()!=QProcess.NotRunning:
                output.appendPlainText('Délai maximal atteint (15 secondes)')
                proc.kill()
        timeout.timeout.connect(expired)
        proc.finished.connect(lambda *_:timeout.stop())
        proc.start();timeout.start()
        self.processes.append(proc)

    def open_vault(self):
        password,ok=QInputDialog.getText(self,'Coffre chiffré','Phrase secrète (12 caractères minimum)',QLineEdit.Password)
        if not ok:return
        try:
            if self.vault.path.exists():self.vault_data=self.vault.load(password)
            else:self.vault.save({},password);self.vault_data={}
            self.vault_password=password;self.vault_timer.start();QMessageBox.information(self,'Coffre','Coffre déverrouillé. Secrets accessibles via le bouton Secret. Aucun mot de passe injecté dans la ligne de commande SSH.')
        except Exception as exc:
            self.lock_vault()
            QMessageBox.warning(self,'Coffre',f'Échec du déverrouillage : {type(exc).__name__}')

    def show_transfer_history(self):
        """Consult persisted transfer outcomes without executing remote operations."""
        if getattr(self, 'transfer_history_tab', None) is not None and self.tabs.indexOf(self.transfer_history_tab) >= 0:
            self.transfer_history_refresh()
            self.tabs.setCurrentWidget(self.transfer_history_tab)
            return
        pane=QWidget();pane.setObjectName('transferHistoryTab')
        layout=QVBoxLayout(pane);controls=QHBoxLayout();layout.addLayout(controls)
        controls.addWidget(QLabel('État'))
        from transfer_presentation import TRANSFER_COLUMNS, TRANSFER_STATES, transfer_query_state, transfer_row_cells, transfer_count_label
        state=QComboBox();state.addItems(list(TRANSFER_STATES));controls.addWidget(state)
        controls.addWidget(QLabel('Connexion'))
        connection=QComboBox();connection.addItem('Toutes','')
        for item in self.store.items:connection.addItem(item.get('name',item['id']),item['id'])
        controls.addWidget(connection)
        refresh=QPushButton('Actualiser');controls.addWidget(refresh)
        table=QTableWidget(0,8);table.setHorizontalHeaderLabels(list(TRANSFER_COLUMNS));table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        layout.addWidget(table)
        warning=QLabel('Historique en lecture seule : aucun transfert n’est relancé automatiquement.');layout.addWidget(warning)
        def populate():
            try:
                rows=self.transfer_journal.search(transfer_query_state(state.currentText()),connection.currentData() or None)
                # Validate the complete snapshot before modifying the visible table.
                cells=[transfer_row_cells(row) for row in rows]
                table.setRowCount(0)
                table.setRowCount(len(cells))
                for row_index,row in enumerate(cells):
                    for col_index,value in enumerate(row):table.setItem(row_index,col_index,QTableWidgetItem(value))
                warning.setText(transfer_count_label(len(cells)))
            except Exception:
                # Do not retain stale results or expose local paths in exception messages.
                table.setRowCount(0)
                warning.setText('Historique indisponible : consultez le diagnostic local.')
        refresh.clicked.connect(populate);state.currentTextChanged.connect(populate);connection.currentIndexChanged.connect(populate)
        populate()
        self.transfer_history_refresh=populate
        self.transfer_history_tab=pane
        self.tabs.addTab(pane,'Transferts')
        self.tabs.setCurrentWidget(pane)

    def closeEvent(self,event):
        # Revoke local SSH tunnels before allowing process termination.
        # A pending SSH connection can finish after scope cleanup starts;
        # wait for both startup and drain without blocking Qt.
        from ssh_tunnel_qt import SSHTunnelPanel
        panels=[self.tabs.widget(i) for i in range(self.tabs.count())
                if isinstance(self.tabs.widget(i), SSHTunnelPanel)]
        pending=[panel for panel in panels if not panel.is_shutdown_complete()]
        if pending:
            for panel in pending:
                panel.request_close()
            event.ignore()
            if not getattr(self,'_tunnel_window_close_pending',False):
                self._tunnel_window_close_pending=True
                def finish_tunnel_shutdown():
                    if any(not panel.is_shutdown_complete() for panel in panels):
                        QTimer.singleShot(200,finish_tunnel_shutdown)
                        return
                    self._tunnel_window_close_pending=False
                    self.close()
                QTimer.singleShot(200,finish_tunnel_shutdown)
            return
        # Exit is two-phase: do not block the GUI event loop while PTYs stop.
        # Refuse destructive shutdown while transfers are active.
        if self.sftp_jobs:
            QMessageBox.warning(self,'Transferts actifs','Attendez la fin des transferts SFTP avant de quitter. Vous pouvez demander leur annulation dans les onglets SFTP.')
            event.ignore();return
        if getattr(self,'_window_close_pending',False):
            event.ignore();return
        workers=[worker for worker in self.findChildren(PtyShell) if worker.isRunning()]
        if workers:
            self._window_close_pending=True
            self._window_close_attempts=0
            self.statusBar().showMessage('Fermeture SSH en cours…',5000)
            for worker in workers:
                worker.stop()
            event.ignore()
            def finish_window_shutdown():
                if not getattr(self,'_window_close_pending',False):return
                # A newly started SFTP transfer invalidates the pending exit.
                if self.sftp_jobs:
                    self._window_close_pending=False
                    self.statusBar().showMessage('Fermeture reportée : transfert SFTP actif',8000)
                    return
                if any(worker.isRunning() for worker in workers):
                    self._window_close_attempts+=1
                    if self._window_close_attempts>=30:
                        self._window_close_pending=False
                        self.statusBar().showMessage('Fermeture reportée : session SSH toujours active',8000)
                        QMessageBox.warning(self,'SSH PTY','Une session PTY est encore en cours de fermeture. Réessayez.')
                        return
                    QTimer.singleShot(100,finish_window_shutdown)
                    return
                self._window_close_pending=False
                self.close()
            QTimer.singleShot(100,finish_window_shutdown)
            return
        # Only after all shutdown guards succeed, release helper processes.
        for proc in list(self.processes):
            if proc.state()!=proc.NotRunning:
                proc.kill()
                proc.waitForFinished(1000)
            self.processes.remove(proc)
        for filename in self.rdp_files:
            try:os.unlink(filename)
            except OSError:pass
        self._save_session_ui_preferences()
        self.lock_vault()
        self.transfer_journal.close()
        super().closeEvent(event)

    def lock_vault(self):
        """Discard references to decrypted data and stop the idle timer."""
        self.vault_timer.stop()
        if self.vault_data is not None:
            self.vault_data.clear()
        self.vault_data=None
        self.vault_password=None
        self.statusBar().showMessage('Coffre verrouillé',5000)

    def edit_secret(self):
        c=self.selected()
        if not c:return
        if self.vault_data is None:
            self.open_vault()
            if self.vault_data is None:return
        secret,ok=QInputDialog.getText(self,'Secret de connexion','Secret (stocké chiffré, jamais passé en argument)',QLineEdit.Password)
        if not ok:return
        updated=dict(self.vault_data)
        if secret:updated[c['id']]=secret
        else:updated.pop(c['id'],None)
        try:
            self.vault.save(updated,self.vault_password)
        except Exception as exc:
            QMessageBox.warning(self,'Coffre',f'Enregistrement impossible : {type(exc).__name__}')
            return
        self.vault_data.clear()
        self.vault_data=updated
        self.vault_timer.start()
        self.statusBar().showMessage('Secret chiffré enregistré',5000)

    def ssh_pty_tab(self):
        """Interactive SSH shell over a real PTY; plain-text viewer is not ANSI emulation."""
        c=self.selected()
        if not c:return
        route=self._safe_route(c['id'])
        if route is None:return
        try:validate_pty_target(c,route)
        except (ValueError,TypeError) as exc:
            QMessageBox.warning(self,'SSH PTY',str(exc));return
        pane=QWidget();layout=QVBoxLayout(pane)
        note=QLabel('SSH PTY — écran ANSI/VT partiel ; pas encore un émulateur complet. Clés SSH/agent uniquement.')
        note.setWordWrap(True);layout.addWidget(note)
        from ansi_screen import AnsiScreen
        screen=AnsiScreen(30,100)
        output=QTextEdit();output.setReadOnly(True)
        output.setLineWrapMode(QTextEdit.NoWrap)
        layout.addWidget(output)
        from PySide6.QtCore import QTimer
        from PySide6.QtGui import QFontMetrics
        resize_timer=QTimer(pane);resize_timer.setSingleShot(True);resize_timer.setInterval(150)
        def resize_terminal():
            metrics=QFontMetrics(output.font())
            cell_width=max(1,metrics.horizontalAdvance('M'))
            cell_height=max(1,metrics.lineSpacing())
            viewport=output.viewport()
            cols=max(20,min(500,viewport.width()//cell_width))
            rows=max(5,min(200,viewport.height()//cell_height))
            if (rows,cols)!=(screen.rows,screen.cols):
                screen.resize(rows,cols)
                paint_terminal()
                worker.resize_pty(cols,rows)
        resize_timer.timeout.connect(resize_terminal)
        # Track viewport changes without hijacking the editor's normal event processing.
        from PySide6.QtCore import QObject,QEvent
        class ViewportResizeFilter(QObject):
            def eventFilter(self,obj,event):
                if event.type()==QEvent.Resize:resize_timer.start()
                return False
        viewport_filter=ViewportResizeFilter(pane)
        output.viewport().installEventFilter(viewport_filter)
        # Direct keyboard mode forwards terminal keys without requiring a command line.
        from terminal_keys import encode_key
        from PySide6.QtCore import Qt
        keyboard=QLineEdit();keyboard.setPlaceholderText('Clavier interactif SSH — saisir ici (touches VT transmises directement)')
        keyboard.setMaxLength(4096)
        class TerminalKeyboardFilter(QObject):
            def eventFilter(self,obj,event):
                if event.type()==QEvent.KeyPress:
                    sequence=encode_key(event.key(),event.modifiers(),event.text(),screen.application_cursor)
                    if sequence is not None:
                        worker.send_raw(sequence)
                        return True
                return False
        keyboard_filter=TerminalKeyboardFilter(pane)
        keyboard.installEventFilter(keyboard_filter)
        layout.addWidget(keyboard)
        line=QLineEdit();line.setPlaceholderText('Commande complète (Entrée pour envoyer)');layout.addWidget(line)
        controls=QHBoxLayout();layout.addLayout(controls)
        reconnect=QPushButton('Nouvelle connexion SSH')
        reconnect.setToolTip('Ouvre une nouvelle session après vérification de la route et des clés SSH ; aucune reconnexion automatique')
        controls.addWidget(reconnect)
        stop=QPushButton('Fermer la session PTY')
        worker=PtyShell(c,route,pane)
        # Coalesce bursts of network output into one Qt repaint (max ~30 fps).
        paint_timer=QTimer(pane);paint_timer.setSingleShot(True);paint_timer.setInterval(33)
        from terminal_diff import changed_rows
        from PySide6.QtGui import QTextCursor
        last_rows=[None]
        def paint_terminal():
            # Update only modified QTextDocument blocks when possible.
            rows=tuple(screen.line_html(i,show_cursor=True) for i in range(screen.rows))
            changes=changed_rows(last_rows[0],rows)
            if changes is None or output.document().blockCount()!=len(rows):
                output.setHtml('<pre style="white-space:pre;font-family:monospace;margin:0">'+'\n'.join(rows)+'</pre>')
            elif changes:
                doc=output.document()
                for index in changes:
                    block=doc.findBlockByNumber(index)
                    if not block.isValid():
                        output.setHtml('<pre style="white-space:pre;font-family:monospace;margin:0">'+'\n'.join(rows)+'</pre>')
                        break
                    cursor=QTextCursor(block)
                    cursor.select(QTextCursor.BlockUnderCursor)
                    cursor.insertHtml(rows[index] or ' ')
            last_rows[0]=rows
        paint_timer.timeout.connect(paint_terminal)
        def receive(data):
            screen.feed(data)
            if not paint_timer.isActive():paint_timer.start()
        worker.received.connect(receive)
        worker.state_message.connect(note.setText)
        worker.hop_diagnostic.connect(lambda message: note.setText("Diagnostic " + message))
        def update_pty_status(state):
            active=state=='connected'
            line.setEnabled(active)
            keyboard.setEnabled(active)
            for button in key_buttons:button.setEnabled(active)
            stop.setEnabled(state not in ('closed','failed'))
            if state=='connecting':note.setText('SSH PTY — connexion en cours…')
            elif state=='stopping':note.setText('SSH PTY — fermeture en cours…')
            elif state=='closed' and worker._connected:note.setText('SSH PTY — session terminée. Fermer puis rouvrir l’onglet pour se reconnecter.')
        worker.status.connect(update_pty_status)
        worker.closed.connect(lambda:update_pty_status('closed'))
        def send():
            if worker.send_text(line.text()):line.clear()
        line.returnPressed.connect(send)
        key_buttons=[]
        for label,sequence in [('Tab','\t'),('Ctrl+C','\x03'),('↑','\x1b[A'),('↓','\x1b[B'),('←','\x1b[D'),('→','\x1b[C'),('Échap','\x1b')]:
            button=QPushButton(label);controls.addWidget(button);key_buttons.append(button)
            button.clicked.connect(lambda checked=False, seq=sequence:worker.send_raw(seq))
        controls.addWidget(stop)
        stop.clicked.connect(worker.stop)
        reconnect.clicked.connect(self.ssh_pty_tab)
        pane.destroyed.connect(worker.stop)
        self.tabs.addTab(pane,'PTY · '+c['name']);self.tabs.setCurrentWidget(pane)
        update_pty_status('connecting')
        worker.start()
        resize_timer.start()

    def ssh_tab(self):
        c=self.selected()
        if not c or c['protocol'] not in ('SSH','SFTP'):return
        # Command console only: QProcess is not a PTY and cannot run full-screen TUI.
        route=self._safe_route(c['id'])
        if route is None:return
        try:
            args=['-o','StrictHostKeyChecking=yes','-o','BatchMode=yes']+ssh_jump_args(route)
        except ValueError as exc:
            QMessageBox.warning(self,'Rebond SSH',str(exc));return
        if c['port']:args+=['-p',str(c['port'])]
        args+=[(c['user']+'@' if c['user'] else '')+c['host'],'sh']
        pane=QWidget();layout=QVBoxLayout(pane)
        info=QLabel('Console de commandes SSH (sans PTY) — applications interactives plein écran non prises en charge')
        info.setWordWrap(True);layout.addWidget(info)
        output=QPlainTextEdit();output.setReadOnly(True);output.document().setMaximumBlockCount(2000);layout.addWidget(output)
        line=QLineEdit();line.setPlaceholderText('Commande distante — Entrée pour envoyer (4096 caractères max)');layout.addWidget(line)
        stop=QPushButton('Arrêter le client SSH');layout.addWidget(stop)
        from PySide6.QtCore import QProcess
        proc=QProcess(pane);proc.setProgram('ssh');proc.setArguments(args)
        proc.setProcessChannelMode(QProcess.MergedChannels)
        proc.readyReadStandardOutput.connect(lambda:output.insertPlainText(readable_output(bytes(proc.readAllStandardOutput()))))
        proc.errorOccurred.connect(lambda _:output.appendPlainText('Erreur SSH : vérifier OpenSSH, clés et known_hosts'))
        proc.finished.connect(lambda *_:(output.appendPlainText('Processus SSH terminé'),line.setEnabled(False),stop.setEnabled(False)))
        def send():
            cmd=line.text()
            if not command_is_valid(cmd):
                QMessageBox.warning(self,'Commande invalide','Commande vide, trop longue ou contenant un saut de ligne.');return
            if proc.state()!=QProcess.Running:return
            proc.write((cmd+'\n').encode('utf-8'));line.clear()
        line.returnPressed.connect(send)
        stop.clicked.connect(lambda:proc.terminate() if proc.state()!=QProcess.NotRunning else None)
        proc.start()
        if not proc.waitForStarted(1500):
            QMessageBox.warning(self,'Client SSH','Démarrage impossible : vérifier la disponibilité du client OpenSSH.');pane.deleteLater();return
        self.processes.append(proc)
        self._record_open(c)
        self.tabs.addTab(pane,'SSH · '+c['name']);self.tabs.setCurrentWidget(pane)

    def split_view(self):
        current=self.tabs.currentWidget()
        if not current:return
        # Independent command pane, preserving the current session.
        split=QSplitter(Qt.Vertical);top=QLabel('Panneau de travail secondaire — commandes réseau');top.setAlignment(Qt.AlignCenter)
        bottom=QPlainTextEdit();bottom.setReadOnly(True);bottom.setPlainText('Sélectionner un hôte puis utiliser les outils réseau pour lancer un diagnostic.')
        split.addWidget(top);split.addWidget(bottom)
        self.tabs.addTab(split,'Vue divisée');self.tabs.setCurrentWidget(split)

    def sftp(self):
        c=self.selected()
        if not c or c['protocol'] not in ('SSH','SFTP'):return
        route=self._safe_route(c['id'])
        if route is None:return
        self._record_open(c)
        pane=QWidget();layout=QVBoxLayout(pane)
        panels=QSplitter(Qt.Horizontal);layout.addWidget(panels)
        local_panel=QWidget();lv=QVBoxLayout(local_panel)
        lv.addWidget(QLabel('Local'))
        local_path=QLineEdit(str(Path.home()));lv.addWidget(local_path)
        local_listing=QListWidget();lv.addWidget(local_listing)
        local_refresh=QPushButton('Actualiser local');lv.addWidget(local_refresh)
        panels.addWidget(local_panel)
        remote_panel=QWidget();rv=QVBoxLayout(remote_panel)
        rv.addWidget(QLabel('Distant · '+c['name']))
        path=QLineEdit('/');rv.addWidget(path)
        listing=QListWidget();rv.addWidget(listing)
        remote_refresh=QPushButton('Actualiser distant');rv.addWidget(remote_refresh)
        panels.addWidget(remote_panel)
        status=QLabel('Prêt');layout.addWidget(status)
        cancel_button=QPushButton('Annuler les transferts de cet onglet')
        layout.addWidget(cancel_button)
        active_jobs=[]
        queue=TransferQueue()
        def cancel_transfers():
            for entry in list(queue.pending):
                if entry.get('journal_id') is not None:
                    try:self.transfer_journal.update(entry['journal_id'],'cancelled')
                    except Exception as exc:status.setText('Journal indisponible : '+str(exc))
            queue.cancel_pending()
            queue.cancel_active()
            render_queue()
            status.setText('Annulation demandée ; tâches en attente annulées')
        cancel_button.clicked.connect(cancel_transfers)
        pane._cancel_sftp_transfers=cancel_transfers
        pane._sftp_closing=False
        queue_list=QListWidget();queue_list.setMaximumHeight(110);layout.addWidget(queue_list)
        def render_queue():
            queue_list.clear()
            entries=queue.history[-15:]+([queue.active] if queue.active else [])+list(queue.pending)
            for entry in entries:
                queue_list.addItem(f"#{entry['id']} · {entry['state']} · {entry['progress']}%")
        def journal_failure(item,exc):
            # Fail closed: prevent any further I/O at the next cancellation checkpoint.
            item.cancel()
            status.setText('Journal indisponible : transfert interrompu par sécurité : '+str(exc))

        def queue_job(operation,remote,local,on_success):
            if pane._sftp_closing:
                return
            job=SftpJob(self._sftp_client,c,operation,remote,local)
            entry=queue.submit(job)
            entry['journal_id']=None
            if operation in ('upload','download','resume_download'):
                try:entry['journal_id']=self.transfer_journal.add(c['id'],operation,remote,local)
                except Exception as exc:
                    queue.pending.remove(entry)
                    status.setText('Transfert refusé : journal indisponible : '+str(exc))
                    return
            render_queue()
            def advance():
                if pane._sftp_closing:
                    return
                current=queue.start_next()
                if current is None:
                    render_queue()
                    return
                item=current['job']
                if current.get('journal_id') is not None:
                    try:self.transfer_journal.update(current['journal_id'],'running')
                    except Exception as exc:
                        queue.complete(current,False)
                        status.setText('Transfert refusé : journal indisponible : '+str(exc))
                        render_queue();advance();return
                active_jobs.append(item)
                self.sftp_jobs.append(item)
                status.setText('Opération en cours…')
                def on_progress(value):
                    if pane._sftp_closing:return
                    queue.progress(current,value)
                    if current.get('journal_id') is not None:
                        try:progress_or_cancel(self.transfer_journal,item,current['journal_id'],current['progress'])
                        except Exception as exc:
                            journal_failure(item,exc)
                            render_queue()
                            return
                    status.setText(f"Transfert : {value}%")
                    render_queue()
                def finish(result):
                    journal_error=None
                    if current.get('journal_id') is not None:
                        try:self.transfer_journal.update(current['journal_id'],'done',100)
                        except Exception as exc:journal_error=exc
                    queue.complete(current,journal_error is None)
                    if item in active_jobs:active_jobs.remove(item)
                    if item in self.sftp_jobs:self.sftp_jobs.remove(item)
                    status.setText('Terminé' if journal_error is None else 'Transfert effectué mais audit non confirmé : '+str(journal_error))
                    render_queue()
                    try:
                        if journal_error is None and not pane._sftp_closing:on_success(result)
                    finally:advance()
                def error(message):
                    queue.complete(current,False)
                    if current.get('journal_id') is not None:
                        try:self.transfer_journal.update(current['journal_id'],'failed')
                        except Exception as exc:status.setText('Journal indisponible : '+str(exc))
                    if item in active_jobs:active_jobs.remove(item)
                    if item in self.sftp_jobs:self.sftp_jobs.remove(item)
                    status.setText('Erreur : '+message)
                    render_queue()
                    advance()
                item.signals.progress.connect(on_progress)
                item.signals.finished.connect(finish)
                item.signals.failed.connect(error)
                self.pool.start(item)
                render_queue()
            if queue.active is None:advance()
        
        row=QHBoxLayout();layout.addLayout(row)
        def refresh_local():
            try:
                root=Path(local_path.text()).expanduser()
                local_listing.clear();local_listing.addItem('../')
                for name,is_dir in local_entries(root):
                    local_listing.addItem(name+('/' if is_dir else ''))
                status.setText('Local : '+str(root))
            except (ValueError,OSError) as exc:status.setText('Erreur locale : '+str(exc))
        def navigate_local(item):
            if item.text().endswith('/'):
                root=Path(local_path.text()).expanduser()
                local_path.setText(str((root/item.text().rstrip('/')).resolve()))
                refresh_local()
        def refresh_remote():queue_job('list',path.text(),None,lambda items:self._display_sftp_items(items,path.text(),listing,status))
        def navigate_remote(item):
            import posixpath
            if item.text().endswith('/'):
                path.setText(posixpath.normpath(posixpath.join(path.text(),item.text())))
                refresh_remote()
        def upload():
            item=local_listing.currentItem()
            if not item or item.text().endswith('/'):return
            try:remote=remote_child(path.text(),item.text())
            except ValueError as exc:status.setText(str(exc));return
            local=str(Path(local_path.text()).expanduser()/item.text())
            if not Path(local).is_file():return
            status.setText('Envoi exclusif : aucune substitution distante autorisée')
            queue_job('upload',remote,local,lambda _:refresh_remote())
        def download():
            item=listing.currentItem()
            if not item or item.text().endswith('/'):return
            try:remote=remote_child(path.text(),item.text())
            except ValueError as exc:status.setText(str(exc));return
            local=Path(local_path.text()).expanduser()/item.text()
            if local.exists():
                if QMessageBox.question(pane,'Écraser le fichier ?',
                    f'Le fichier {local.name} existe. Le remplacer ?')!=QMessageBox.Yes:return
            queue_job('download',remote,str(local),lambda _:refresh_local())
        def resume_download():
            item=listing.currentItem()
            if not item or item.text().endswith('/'):return
            try:remote=remote_child(path.text(),item.text())
            except ValueError as exc:status.setText(str(exc));return
            local=Path(local_path.text()).expanduser()/item.text()
            if local.exists():
                if QMessageBox.question(pane,'Remplacer le fichier local ?',
                    f'La reprise remplacera {local.name} après vérification complète. Continuer ?')!=QMessageBox.Yes:return
            queue_job('resume_download',remote,str(local),lambda _:refresh_local())
        for name,fn in [('Envoyer →',upload),('← Télécharger',download),('↻ Reprendre téléchargement',resume_download)]:
            button=QPushButton(name);button.clicked.connect(fn);row.addWidget(button)
        local_refresh.clicked.connect(refresh_local)
        remote_refresh.clicked.connect(refresh_remote)
        local_listing.itemDoubleClicked.connect(navigate_local)
        listing.itemDoubleClicked.connect(navigate_remote)
        local_path.returnPressed.connect(refresh_local)
        path.returnPressed.connect(refresh_remote)
        self.tabs.addTab(pane,'SFTP · '+c['name']);self.tabs.setCurrentWidget(pane)
        refresh_local();refresh_remote()

    def _run_sftp(self,c,operation,remote,local,status,success,active_jobs=None):
        job=SftpJob(self._sftp_client,c,operation,remote,local)
        self.sftp_jobs.append(job)
        if active_jobs is not None:active_jobs.append(job)
        status.setText('Opération en cours…')
        job.signals.progress.connect(lambda value:status.setText(f'Transfert : {value}%'))
        def finish(result):
            status.setText('Terminé');success(result)
            if job in self.sftp_jobs:self.sftp_jobs.remove(job)
            if active_jobs is not None and job in active_jobs:active_jobs.remove(job)
        def error(message):
            status.setText('Erreur : '+message)
            if job in self.sftp_jobs:self.sftp_jobs.remove(job)
            if active_jobs is not None and job in active_jobs:active_jobs.remove(job)
        job.signals.finished.connect(finish)
        job.signals.failed.connect(error)
        self.pool.start(job)

    def _sftp_client(self,c):
        from ssh_route_client import RoutedSshClient
        route=self._safe_route(c['id'])
        if route is None:raise ValueError('Route SSH non valide')
        return RoutedSshClient(c,route).connect()

    def _display_sftp_items(self,items,remote,listing,status):
        listing.clear();listing.addItem('../')
        for name,is_dir,size in sorted(items,key=lambda x:(not x[1],x[0].lower())):
            listing.addItem(name+('/' if is_dir else ''))
        status.setText(f'{len(items)} éléments · {remote}')

    def _sftp_refresh(self,c,path,listing,status,active_jobs=None):
        remote=path.text()
        def display(items):
            listing.clear();listing.addItem('../')
            for name,is_dir,size in sorted(items,key=lambda x:(not x[1],x[0].lower())):
                listing.addItem(name+('/' if is_dir else ''))
            status.setText(f'{len(items)} éléments · {remote}')
        self._run_sftp(c,'list',remote,None,status,display,active_jobs)

    def _sftp_transfer(self,c,path,listing,status,upload):
        import posixpath
        if upload:
            local,_=QFileDialog.getOpenFileName(self,'Fichier à envoyer')
            if not local:return
            remote=posixpath.join(path.text(),Path(local).name)
        else:
            item=listing.currentItem()
            if not item or item.text().endswith('/'):return
            remote=posixpath.join(path.text(),item.text())
            local,_=QFileDialog.getSaveFileName(self,'Enregistrer sous',item.text())
            if not local:return
        operation='upload' if upload else 'download'
        self._run_sftp(c,operation,remote,local,status,lambda _ :self._sftp_refresh(c,path,listing,status) if upload else None)

def main():
    # Offline binary gate: no WinRM connection, credential access or GUI event loop.
    if '--check-winrm-runtime' in sys.argv:
        from winrm_runtime_check import runtime_dependency_available
        sys.exit(0 if runtime_dependency_available() else 13)
    # Smoke mode is opt-in and exits automatically; no remote connections are initiated.
    from startup_diagnostics import safe_record
    smoke = '--smoke-gui' in sys.argv
    argv = [arg for arg in sys.argv if arg != '--smoke-gui']
    try:
        app = QApplication(argv)
        safe_record('qt_init', 'ok')
    except Exception as exc:
        safe_record('qt_init', 'failed', exc)
        raise
    try:
        w = Main()
        w.show()
        safe_record('main_window', 'ok')
    except Exception as exc:
        safe_record('main_window', 'failed', exc)
        raise
    if smoke:
        QTimer.singleShot(1500, app.quit)
    try:
        result = app.exec()
        safe_record('event_loop', 'ok' if result == 0 else 'failed')
    except Exception as exc:
        safe_record('event_loop', 'failed', exc)
        raise
    if smoke:
        print('OPENREMOTE_GUI_SMOKE_PASS' if result == 0 else 'OPENREMOTE_GUI_SMOKE_FAIL', flush=True)
    sys.exit(result)
if __name__=='__main__':main()
