"""R12 typed SFTP cancellation: unit, worker-stub and source-contract tests.
Author: Abdelhalim Talbi. These are NOT native Windows UI or protocol tests.
"""
import importlib.util
import sys
import types
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from transfer_queue import TransferQueue

class Job:
    def __init__(self): self.was_cancelled=False
    def cancel(self): self.was_cancelled=True

class QueueContract(unittest.TestCase):
    def test_cancel_does_not_release_active_slot(self):
        q=TransferQueue(); a=q.submit(Job()); b=q.submit(Job())
        q.start_next(); q.cancel_active()
        self.assertTrue(a['job'].was_cancelled)
        self.assertTrue(a['cancel_requested'])
        self.assertIsNone(q.start_next())
        q.complete(a,False,cancelled=True)
        self.assertEqual(a['state'],'cancelled')
        self.assertIs(q.start_next(),b)
    def test_network_error_after_cancel_is_failure(self):
        q=TransferQueue(); a=q.submit(Job()); q.start_next(); q.cancel_active()
        q.complete(a,False)
        self.assertEqual(a['state'],'failed')
    def test_success_after_cancel_is_success(self):
        q=TransferQueue(); a=q.submit(Job()); q.start_next(); q.cancel_active()
        q.complete(a,True)
        self.assertEqual(a['state'],'done')
    def test_invalid_outcomes_do_not_advance(self):
        q=TransferQueue(); a=q.submit(Job()); q.start_next()
        for ok,cancelled in [(True,True),(False,1),(1,False)]:
            with self.assertRaises(ValueError):q.complete(a,ok,cancelled=cancelled)
        self.assertIs(q.active,a)

class FakeSignal:
    def __init__(self): self.events=[]
    def emit(self,*args): self.events.append(args)

class SignalDescriptor:
    def __init__(self,*args): self.name=None
    def __set_name__(self,owner,name): self.name=name
    def __get__(self,obj,owner):
        if obj is None:return self
        return obj.__dict__.setdefault(self.name,FakeSignal())

class FakeSftp:
    def __enter__(self):return self
    def __exit__(self,*args):return False
class FakeClient:
    def __init__(self):self.closed=False
    def open_sftp(self):return FakeSftp()
    def close(self):self.closed=True

def worker_for(download):
    core=types.ModuleType('PySide6.QtCore')
    core.QObject=object;core.QRunnable=object;core.Signal=SignalDescriptor
    safety=types.ModuleType('transfer_safety')
    safety.download_atomic=download
    safety.upload_exclusive=download
    safety.download_resume_verified=download
    with patch.dict(sys.modules,{'PySide6':types.ModuleType('PySide6'),
                                 'PySide6.QtCore':core,'transfer_safety':safety}):
        spec=importlib.util.spec_from_file_location('qt_workers_r12',ROOT/'qt_workers.py')
        module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    client=FakeClient()
    job=module.SftpJob(lambda _:client,{'id':'test'},'download','/remote','/tmp/test')
    return job,client

class WorkerContract(unittest.TestCase):
    def test_precancelled_emits_cancelled(self):
        job,client=worker_for(lambda *a,**kw:True)
        job.cancel();job.run()
        self.assertEqual(job.signals.cancelled.events,[()])
        self.assertEqual(job.signals.failed.events,[])
    def test_network_error_while_cancelled_is_failure(self):
        def broken(*a,**kw):
            job.cancel()
            raise OSError('network')
        job,client=worker_for(broken);job.run()
        self.assertEqual(job.signals.cancelled.events,[])
        self.assertEqual(len(job.signals.failed.events),1)
        self.assertTrue(client.closed)
    def test_unrequested_interruption_is_failure(self):
        def broken(*a,**kw):raise InterruptedError('remote error')
        job,client=worker_for(broken);job.run()
        self.assertEqual(job.signals.cancelled.events,[])
        self.assertEqual(len(job.signals.failed.events),1)
    def test_requested_interruption_is_cancelled(self):
        def stop(*a,**kw):
            job.cancel()
            raise InterruptedError('stop')
        job,client=worker_for(stop);job.run()
        self.assertEqual(job.signals.cancelled.events,[()])
        self.assertEqual(job.signals.failed.events,[])
    def test_success(self):
        job,client=worker_for(lambda *a,**kw:True);job.run()
        self.assertEqual(job.signals.finished.events,[(True,)])
        self.assertTrue(client.closed)

class UiSourceContract(unittest.TestCase):
    def test_typed_signal_wired_to_queue(self):
        source=(ROOT/'qt_app.py').read_text(encoding='utf-8')
        self.assertIn('item.signals.cancelled.connect(on_cancelled)',source)
        self.assertIn('queue.complete(current,False,cancelled=confirmed)',source)
        self.assertIn("state='cancelled' if confirmed else 'failed'",source)
        self.assertIn("item._journal_failed=True",source)
    def test_legacy_signal_wired(self):
        source=(ROOT/'qt_app.py').read_text(encoding='utf-8')
        self.assertIn('job.signals.cancelled.connect(cancelled)',source)
    def test_no_error_string_cancellation_classification(self):
        source=(ROOT/'qt_app.py').read_text(encoding='utf-8')
        block=source.split('def on_cancelled():',1)[1].split('item.signals.progress.connect(on_progress)',1)[0]
        self.assertNotIn('message.lower()',block)
        self.assertIn("journal_error=None",block)

if __name__=='__main__':unittest.main()
