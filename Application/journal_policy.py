"""Transfer audit fail-closed decision helpers. Author: Abdelhalim Talbi."""

def progress_or_cancel(journal, job, transfer_id, progress):
    """Raise if persistence fails; cancellation is cooperative at the next I/O checkpoint."""
    try:
        journal.update(transfer_id,'running',progress)
    except Exception:
        job.cancel()
        raise

def terminal_audit(journal, transfer_id, state, progress=None):
    """Do not claim audited success if the terminal transaction failed."""
    journal.update(transfer_id,state,progress)
    return True
