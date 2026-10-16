"""Linux host-wide advisory CAModel lease, shared by workers and direct runners.

The canonical path is intentionally not configurable per worktree or queue.
This coordinates this user's participating processes, not hostile processes or
other users. Legacy/unmanaged model processes trigger fail-closed refusal.
"""
import contextlib
import fcntl
import os
from pathlib import Path

LOCK = Path('/tmp/opencode/camodel-host.lock')


def unmanaged_processes():
    ancestors = set()
    pid = os.getpid()
    while pid > 1 and pid not in ancestors:
        ancestors.add(pid)
        try:
            pid = int(Path(f'/proc/{pid}/stat').read_text().rsplit(')', 1)[1].split()[1])
        except (OSError, ValueError, IndexError):
            break
    busy = []
    for entry in Path('/proc').iterdir():
        if not entry.name.isdigit() or int(entry.name) in ancestors:
            continue
        try:
            argv = (entry / 'cmdline').read_bytes().split(b'\0')
            names = [Path(x.decode(errors='replace')).name for x in argv[:2]]
            if any(n.startswith('bench_') or n == 'benchmark.py' or
                   n in ('camodel', 'camodel_run', 'stars') for n in names):
                busy.append(int(entry.name))
        except (OSError, ValueError):
            continue
    return busy


@contextlib.contextmanager
def lease(*, lock_path=LOCK, check_legacy=True):
    lock_path = Path(lock_path)
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    inherited = os.environ.get('CAMODEL_LEASE_FD')
    if inherited is not None:
        fd = int(inherited)
        st, expected = os.fstat(fd), lock_path.stat()
        if (st.st_dev, st.st_ino) != (expected.st_dev, expected.st_ino):
            raise RuntimeError('invalid inherited CAModel lease')
        # Only descendants of the worker receive this descriptor. It remains
        # open across runner/benchmark exec so worker death cannot unlock early.
        yield fd
        return
    with lock_path.open('a+') as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as exc:
            raise RuntimeError('host CAModel lease busy') from exc
        try:
            busy = unmanaged_processes() if check_legacy else []
            if busy:
                raise RuntimeError(f'unmanaged model/benchmark processes active: {busy}')
            yield lock.fileno()
        finally:
            # Closing this reference releases the flock only after all child
            # processes that inherited the descriptor have also exited.
            pass
