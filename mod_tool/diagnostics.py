"""Local, bounded troubleshooting logs. Never records ROM or project contents."""
import atexit
import faulthandler
import logging
from logging.handlers import RotatingFileHandler
import os
from pathlib import Path
import platform
import sys
import tempfile
import threading

LOGGER = logging.getLogger('new_horizons_editor')
LOGGER.setLevel(logging.INFO)
LOGGER.propagate = False
_directory = None
_fatal_file = None


def initialize():
    global _directory, _fatal_file
    if _directory is not None:
        return _directory
    base = Path(os.environ.get('LOCALAPPDATA', Path.home() / '.local' / 'share'))
    for directory in (base / 'New Horizons Editor' / 'Logs',
                      Path(tempfile.gettempdir()) / 'New Horizons Editor' / 'Logs'):
        try:
            directory.mkdir(parents=True, exist_ok=True)
            handler = RotatingFileHandler(directory / 'editor.log', maxBytes=2 * 1024 * 1024,
                                          backupCount=3, encoding='utf-8', delay=False)
        except OSError:
            continue
        handler.setFormatter(logging.Formatter('%(asctime)s %(levelname)s [pid=%(process)d] %(message)s'))
        LOGGER.addHandler(handler)
        _directory = directory
        break
    if _directory is None:
        # An unwritable disk must not prevent the editor from opening.
        LOGGER.addHandler(logging.NullHandler())
        return None
    LOGGER.info('Session started; Python=%s; OS=%s; frozen=%s',
                platform.python_version(), platform.platform(), bool(getattr(sys, 'frozen', False)))
    try:
        fatal_path = _directory / 'native-crash.log'
        if fatal_path.exists() and fatal_path.stat().st_size > 2 * 1024 * 1024:
            fatal_path.replace(_directory / 'native-crash.previous.log')
        _fatal_file = fatal_path.open('a', encoding='utf-8')
        _fatal_file.write(f'\nSession started; pid={os.getpid()}\n')
        _fatal_file.flush()
        faulthandler.enable(file=_fatal_file, all_threads=True)
    except (OSError, RuntimeError, ValueError):
        LOGGER.exception('Native crash reporting could not be enabled')
    sys.excepthook = unhandled_exception
    threading.excepthook = thread_exception
    atexit.register(session_finished)
    return _directory


def session_finished():
    LOGGER.info('Session ended')
    if _fatal_file is not None and not _fatal_file.closed:
        try:
            _fatal_file.write(f'Session ended; pid={os.getpid()}\n')
            _fatal_file.flush()
        except OSError:
            pass


def unhandled_exception(exc_type, value, traceback):
    LOGGER.critical('Unhandled application error', exc_info=(exc_type, value, traceback))
    if sys.stderr is not None:
        sys.__excepthook__(exc_type, value, traceback)


def thread_exception(args):
    LOGGER.error('Unhandled background thread error: %s', args.thread.name if args.thread else 'unknown',
                 exc_info=(args.exc_type, args.exc_value, args.exc_traceback))


def attach_editor(app):
    # The executable entry point initializes logging before importing the UI.
    # Importing Editor in another program or test must not open global files
    # in that caller's temporary profile.
    if _directory is None:
        return
    LOGGER.info('Editor initialization; version=%s', __import__('backend').TOOL_VERSION)
    previous = app.root.report_callback_exception

    def callback_error(exc_type, value, traceback):
        LOGGER.error('UI callback error; section=%s', getattr(app, 'section', 'unknown'),
                     exc_info=(exc_type, value, traceback))
        # Retain Tk's existing error handling; logging adds persistent evidence.
        previous(exc_type, value, traceback)

    app.root.report_callback_exception = callback_error
    def clicked(event):
        widget = event.widget
        if widget.winfo_class() in ('TButton', 'TCheckbutton', 'TMenubutton',
                                    'Button', 'Checkbutton', 'Menubutton'):
            LOGGER.info('Click: %s; section=%s', widget.cget('text'), getattr(app, 'section', 'unknown'))
    app.root.bind('<Button-1>', clicked, add='+')


def open_log_folder(parent=None):
    directory = initialize()
    try:
        if directory is None:
            raise OSError('The log folder could not be created. Check available disk space and permissions.')
        if os.name == 'nt':
            os.startfile(str(directory))
        else:
            import subprocess
            subprocess.Popen(['open' if sys.platform == 'darwin' else 'xdg-open', str(directory)])
    except OSError as error:
        from tkinter import messagebox
        messagebox.showerror('Log folder', str(error), parent=parent)
