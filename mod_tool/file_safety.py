"""Durable local writes and cooperative locking, without overwriting exports."""
import os
import shutil
import tempfile
from contextlib import contextmanager
from pathlib import Path


def stage_bytes(path, payload):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, name = tempfile.mkstemp(prefix='.' + path.name + '-', suffix='.tmp', dir=path.parent)
    temporary = Path(name)
    try:
        with os.fdopen(fd, 'wb') as stream:
            stream.write(payload)
            stream.flush()
            os.fsync(stream.fileno())
        return temporary
    except BaseException:
        temporary.unlink(missing_ok=True)
        raise


def atomic_write(path, payload):
    temporary = stage_bytes(path, payload)
    try:
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


def publish_files(files):
    """Stage the entire export first; roll back files owned by this attempt."""
    staged, created = [], []
    try:
        for path, payload in files:
            staged.append((Path(path), stage_bytes(path, payload)))
        for target, temporary in staged:
            with target.open('xb') as destination:
                # Register before writing so a failed current write is removed too.
                created.append(target)
                with temporary.open('rb') as source:
                    shutil.copyfileobj(source, destination)
                destination.flush()
                os.fsync(destination.fileno())
    except BaseException:
        for target in reversed(created):
            target.unlink(missing_ok=True)
        raise
    finally:
        for _, temporary in staged:
            temporary.unlink(missing_ok=True)


@contextmanager
def file_lock(path, resource='the Library'):
    """OS-held lock: released on process exit, even when the lock file remains."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('a+b') as stream:
        if stream.seek(0, 2) == 0:
            stream.write(b'\0')
            stream.flush()
        stream.seek(0)
        if os.name == 'nt':
            import msvcrt
            lock = lambda: msvcrt.locking(stream.fileno(), msvcrt.LK_NBLCK, 1)
            unlock = lambda: msvcrt.locking(stream.fileno(), msvcrt.LK_UNLCK, 1)
        else:
            import fcntl
            lock = lambda: fcntl.flock(stream.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
            unlock = lambda: fcntl.flock(stream.fileno(), fcntl.LOCK_UN)
        try:
            lock()
        except OSError as error:
            raise ValueError(f'Another editor window is saving {resource}. Please try again.') from error
        try:
            yield
        finally:
            unlock()
