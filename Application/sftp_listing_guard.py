"""Pure guard for asynchronous SFTP directory results.

A queued directory response must not overwrite a view whose requested
directory changed. Author: Abdelhalim Talbi.
"""


def should_display_listing(requested_path, current_path):
    if not isinstance(requested_path, str) or not isinstance(current_path, str):
        return False
    return requested_path == current_path
