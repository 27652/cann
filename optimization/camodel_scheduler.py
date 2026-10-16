#!/usr/bin/env python3
"""Small, file-backed single-worker scheduler for CAModel experiments.

Submission is deliberately non-blocking: agents enqueue immutable experiment
metadata and continue working.  A worker owns the host-wide CAModel lock only
while running one command.  The queue is JSON so it is inspectable without a
database, while fcntl protects updates between processes.
"""
from __future__ import annotations

import argparse
import contextlib
import fcntl
import hashlib
import json
import math
import os
from pathlib import Path
import shutil
import signal
import subprocess
import sys
import tempfile
import time
import uuid

from camodel_resource import lease

STATUSES = {"queued", "running", "passed", "failed", "timeout", "cancelled"}
TERMINAL = {"passed", "failed", "timeout", "cancelled"}
REQUIRED_METADATA = {
    "candidate_id", "source_sha256", "binary_sha256", "case", "variant",
    "golden_mode", "environment_fingerprint",
}


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


class Scheduler:
    def __init__(self, root: Path, resource_lease=lease):
        self.root = root.resolve()
        self.root.mkdir(parents=True, exist_ok=True)
        self.queue = self.root / "queue.json"
        self.queue_lock = self.root / "queue.lock"
        self.snapshots = self.root / "snapshots"
        self.snapshots.mkdir(exist_ok=True)
        self.resource_lease = resource_lease

    @contextlib.contextmanager
    def _locked_queue(self):
        with self.queue_lock.open("a+") as lock:
            fcntl.flock(lock, fcntl.LOCK_EX)
            try:
                if self.queue.exists():
                    data = json.loads(self.queue.read_text())
                else:
                    data = {"schema_version": 1, "tasks": {}}
                yield data
                fd, name = tempfile.mkstemp(prefix="queue.", dir=self.root)
                try:
                    with os.fdopen(fd, "w") as out:
                        json.dump(data, out, indent=2, sort_keys=True)
                        out.write("\n")
                        out.flush()
                        os.fsync(out.fileno())
                    os.replace(name, self.queue)
                finally:
                    if os.path.exists(name):
                        os.unlink(name)
            finally:
                fcntl.flock(lock, fcntl.LOCK_UN)

    def _validate_result_dir(self, result_dir: Path) -> Path:
        result_dir = result_dir.resolve()
        if result_dir.exists():
            raise ValueError(f"result directory already exists: {result_dir}")
        # Never allow the scheduler to write the repository's shared results.
        forbidden = (Path(__file__).resolve().parent / "results").resolve()
        parts = result_dir.parts
        has_shared_results = any(parts[i:i + 2] == ("optimization", "results")
                                 for i in range(len(parts) - 1))
        if result_dir == forbidden or forbidden in result_dir.parents or has_shared_results:
            raise ValueError(f"shared optimization/results is forbidden: {result_dir}")
        return result_dir

    def submit(self, *, command: list[str], cwd: Path, result_dir: Path,
               binds: list[Path], env: dict[str, str], timeout: float,
               metadata: dict | None = None,
               allow_duplicate: bool = False, priority: int = 0) -> dict:
        cwd = cwd.resolve()
        if not cwd.is_dir():
            raise ValueError(f"cwd is not a directory: {cwd}")
        if not command or not math.isfinite(timeout) or timeout <= 0:
            raise ValueError('command and a positive finite timeout are required')
        if isinstance(priority, bool) or not isinstance(priority, int):
            raise ValueError('priority must be an integer')
        allowed_env = ('PATH', 'LD_LIBRARY_PATH', 'PYTHONPATH', 'HOME', 'LANG',
                       'ASCEND_HOME_PATH', 'ASCEND_TOOLKIT_HOME', 'CAMODEL_HOME',
                       'CAMODEL_PATH', 'CANN_PATH', 'ASCEND_OPP_PATH',
                       'ASCEND_AICPU_PATH', 'ASCEND_SOC_VERSION', 'CAMODEL_LIB_DIR',
                       'OPENBLAS_NUM_THREADS', 'OMP_NUM_THREADS')
        if set(env) - set(allowed_env):
            raise ValueError('only documented runtime environment overrides are allowed')
        env = {**{key: os.environ[key] for key in allowed_env if key in os.environ}, **env}
        metadata = metadata or {}
        missing = sorted(REQUIRED_METADATA - metadata.keys())
        if missing:
            raise ValueError(f"metadata missing required fields: {', '.join(missing)}")
        for key in REQUIRED_METADATA:
            if not isinstance(metadata[key], (str, int, float, list, dict)) or metadata[key] in ("", None):
                raise ValueError(f"metadata field is empty or invalid: {key}")
        result_dir = self._validate_result_dir(result_dir)
        bound = []
        for path in binds:
            path = path.resolve()
            if any(part in ('gitlabcann', '.git', 'cookie') for part in path.parts):
                raise ValueError('credential/git directories cannot be bound')
            if not path.is_relative_to(cwd):
                raise ValueError('bound files must be inside candidate cwd')
            if not path.is_file():
                raise ValueError(f"bound file is missing: {path}")
            bound.append({"path": str(path), "sha256": sha256(path), "size": path.stat().st_size})
        bound_hashes = {x['sha256'] for x in bound}
        if metadata['source_sha256'] not in bound_hashes:
            raise ValueError('source_sha256 must identify a bound candidate file')
        if metadata['binary_sha256'] not in bound_hashes:
            raise ValueError('binary_sha256 must identify a bound executable')
        bound_paths = {Path(x['path']) for x in bound}
        for arg in command:
            candidate = Path(arg) if Path(arg).is_absolute() else cwd / arg
            if candidate.is_file() and candidate.resolve() not in bound_paths:
                raise ValueError(f'command file must be bound: {candidate}')
        identity = {"command": command, "cwd": str(cwd),
                    "binds": bound, "env": env, "timeout": timeout,
                    "metadata": metadata or {}, "priority": priority}
        spec_hash = hashlib.sha256(json.dumps(identity, sort_keys=True).encode()).hexdigest()
        now = time.time()
        with self._locked_queue() as data:
            for task in data["tasks"].values():
                if task["spec_hash"] == spec_hash and not allow_duplicate:
                    raise ValueError(f"duplicate task: {task['task_id']}")
                if task["result_dir"] == str(result_dir):
                    raise ValueError(f"result directory already reserved: {result_dir}")
            # Atomic reservation also prevents two independent queue roots from
            # selecting the same directory. Never adopt an existing directory.
            result_dir.mkdir(parents=True, exist_ok=False)
            task_id = f"{int(now * 1000)}-{uuid.uuid4().hex[:10]}"
            snapshot = self.snapshots / task_id
            snapshot.mkdir()
            snapshot_candidate = snapshot / 'candidate'
            # Explicit allowlist only: never recursively copy a worktree,
            # credentials, build caches, or historical experiment directories.
            snapshot_candidate.mkdir()
            copied = []
            for i, item in enumerate(bound):
                try:
                    relative = Path(item['path']).relative_to(cwd)
                except ValueError:
                    relative = Path('external') / f"{i}-{Path(item['path']).name}"
                if any(x in relative.parts for x in ('gitlabcann', '.git')):
                    raise ValueError('credential/git directories cannot be bound')
                target = snapshot_candidate / relative
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(item["path"], target)
                if sha256(target) != item['sha256']:
                    raise ValueError('file changed during submission')
                target.chmod(target.stat().st_mode & ~0o222)
                copied.append({**item, "snapshot": str(target), "snapshot_sha256": sha256(target)})
            frozen_command = []
            for arg in command:
                p = Path(arg)
                candidate = p if p.is_absolute() else cwd / p
                match = next((x for x in copied if Path(x['path']) == candidate), None)
                frozen_command.append(match['snapshot'] if match else arg)
            task = {"task_id": task_id, "spec_hash": spec_hash, "status": "queued",
                    "created_at": now, "updated_at": now, "command": command,
                    "cwd": str(cwd), "result_dir": str(result_dir), "binds": copied,
                    "env": env, "timeout": timeout, "metadata": metadata,
                    "priority": priority, "yield_requested": False,
                    "snapshot_dir": str(snapshot), "frozen_command": frozen_command,
                    "frozen_cwd": str(snapshot / 'candidate')}
            data["tasks"][task_id] = task
            # A high-value case arriving while a lower-value case is running
            # does not interrupt the simulator.  It only asks the current
            # Worker to yield after its case boundary.  The running task owns
            # the lease until its child exits; the next claim then selects the
            # higher-priority case and leaves the rest queued.
            running = [t for t in data["tasks"].values()
                       if t["status"] == "running" and t.get("priority", 0) < priority]
            for active in running:
                active["yield_requested"] = True
                active["updated_at"] = now
        return task

    def list_tasks(self) -> list[dict]:
        with self._locked_queue() as data:
            return list(data["tasks"].values())

    def submit_cases(self, *, cases: list[dict], result_dir: Path, **shared) -> list[dict]:
        """Enqueue explicit one-case commands; no command-line guessing/splitting.

        Each case supplies command and metadata (overlaid on shared metadata),
        and optionally priority. Already submitted cases remain recoverable if
        a later submission fails; this is not an atomic batch operation.
        """
        if not cases or not all(isinstance(case, dict) and case.get('command')
                                for case in cases):
            raise ValueError('cases must be a nonempty list of case command objects')
        tasks = []
        for index, case in enumerate(cases):
            options = {**shared, **case}
            options['metadata'] = {**shared.get('metadata', {}), **case.get('metadata', {})}
            options['result_dir'] = result_dir / f'case-{index:04d}'
            tasks.append(self.submit(**options))
        return tasks

    def cancel(self, task_id: str) -> dict:
        with self._locked_queue() as data:
            task = data["tasks"].get(task_id)
            if not task:
                raise ValueError(f"unknown task: {task_id}")
            if task["status"] != "queued":
                raise ValueError(f"only queued tasks can be cancelled: {task['status']}")
            task["status"] = "cancelled"
            task["updated_at"] = time.time()
            return task

    def pause(self, task_id: str) -> dict:
        """Ask the owning Worker to stop after this case, without signalling it."""
        with self._locked_queue() as data:
            task = data['tasks'].get(task_id)
            if not task or task['status'] != 'running':
                raise ValueError('pause requires a running task')
            task.update(pause_requested=True, yield_requested=True,
                        updated_at=time.time())
            return dict(task)

    def _claim(self) -> dict | None:
        with self._locked_queue() as data:
            for orphan in data['tasks'].values():
                if orphan['status'] == 'running':
                    orphan['status'] = 'failed'
                    orphan['error'] = 'worker exited; host lease is now available'
                    orphan['updated_at'] = time.time()
            queued = [t for t in data["tasks"].values() if t["status"] == "queued"]
            if not queued:
                return None
            task = min(queued, key=lambda x: (-x.get("priority", 0),
                                               x["created_at"], x["task_id"]))
            for item in task["binds"]:
                if (not Path(item['snapshot']).is_file() or
                        sha256(Path(item["snapshot"])) != item["snapshot_sha256"]):
                    task["status"] = "failed"
                    task["error"] = "immutable snapshot was modified"
                    task["updated_at"] = time.time()
                    return None
            task["status"] = "running"
            task["started_at"] = time.time()
            task["updated_at"] = task["started_at"]
            return dict(task)

    def worker_once(self) -> dict | None:
        try:
            with self.resource_lease() as fd:
                task = self._claim()
                if task is None:
                    return None
                return self._execute(task, fd)
        except RuntimeError as exc:
            return {"status": "idle", "busy": True, "error": str(exc)}

    def _set_status(self, task_id: str, status: str, **extra):
        with self._locked_queue() as data:
            task = data["tasks"][task_id]
            task.update(extra, status=status, updated_at=time.time())

    def _execute(self, task: dict, lease_fd: int) -> dict:
        result = Path(task["result_dir"])
        if any(result.iterdir()):
            self._set_status(task['task_id'], 'failed', error='result directory changed before execution')
            return {'task_id': task['task_id'], 'status': 'failed'}
        (result / "task.json").write_text(json.dumps(task, indent=2, sort_keys=True) + "\n")
        run_log = result / "run.log"
        env = dict(task["env"])
        env["CAMODEL_LEASE_FD"] = str(lease_fd)
        env['BENCHMARK_RESULTS_ROOT'] = str(result / 'benchmark')
        # Runtime housekeeping must not use the user's shared ~/ascend tree.
        env['ASCEND_WORK_PATH'] = str(result / 'ascend')
        env['ASCEND_PROCESS_LOG_PATH'] = str(result / 'ascend/log')
        (result / 'ascend/log').mkdir(parents=True, exist_ok=True)
        for key, name in [('TMPDIR', 'tmp'), ('CAMODEL_LOG_PATH', 'logs'), ('STARS_LOG_PATH', 'logs')]:
            (result / name).mkdir(exist_ok=True)
            env[key] = str(result / name)
        try:
            with run_log.open("w") as out:
                proc = subprocess.Popen(task["frozen_command"], cwd=task["frozen_cwd"], env=env,
                                        stdout=out, stderr=subprocess.STDOUT,
                                        start_new_session=True, pass_fds=(lease_fd,))
                try:
                    proc.wait(timeout=task['timeout'])
                except subprocess.TimeoutExpired:
                    os.killpg(proc.pid, signal.SIGKILL)
                    proc.wait()
                    raise
            status = "passed" if proc.returncode == 0 else "failed"
            extra = {"returncode": proc.returncode}
        except subprocess.TimeoutExpired:
            status, extra = "timeout", {"timeout_seconds": task["timeout"]}
        except Exception as exc:
            status, extra = "failed", {"error": repr(exc)}
        # Read the request after the child has exited.  This is deliberately a
        # case-boundary decision: no SIGSTOP/SIGTERM is sent to the simulator.
        with self._locked_queue() as data:
            current = data["tasks"][task["task_id"]]
            should_yield = bool(current.get("yield_requested"))
            pause_requested = bool(current.get('pause_requested'))
            current.update(status=status, yielded=should_yield,
                           updated_at=time.time(), **extra)
        return {"task_id": task["task_id"], "status": status,
                "yielded": should_yield, "pause_requested": pause_requested, **extra}


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--root", type=Path, default=Path(os.environ.get("CAMODEL_SCHEDULER_ROOT", "/tmp/opencode/camodel-scheduler")))
    sub = p.add_subparsers(dest="action", required=True)
    s = sub.add_parser("submit")
    s.add_argument("--cwd", type=Path, required=True)
    s.add_argument("--result-dir", type=Path, required=True)
    s.add_argument("--bind", type=Path, action="append", default=[])
    s.add_argument("--env", action="append", default=[], metavar="NAME=VALUE")
    s.add_argument("--timeout", type=float, default=1800)
    s.add_argument("--priority", type=int, default=0,
                   help="case priority; larger values run first")
    s.add_argument('--cases-json', type=Path,
                   help='list of explicit case command/metadata/priority objects; no trailing command')
    s.add_argument("--metadata", type=Path, help="JSON object with case/variant/golden identity")
    s.add_argument("--allow-duplicate", action="store_true")
    s.add_argument("command", nargs=argparse.REMAINDER)
    sub.add_parser("list")
    w = sub.add_parser("worker")
    w.add_argument("--once", action="store_true", help="process at most one queued task")
    w.add_argument("--loop", action="store_true", help="keep polling until interrupted")
    w.add_argument("--poll-interval", type=float, default=1.0)
    c = sub.add_parser("cancel")
    c.add_argument("task_id")
    pause = sub.add_parser('pause', help='stop Worker after its current case; never signal the child')
    pause.add_argument('task_id')
    args = p.parse_args(argv)
    scheduler = Scheduler(args.root)
    try:
        if args.action == "submit":
            command = args.command[1:] if args.command[:1] == ["--"] else args.command
            if bool(command) == bool(args.cases_json):
                raise ValueError("submit requires either a command after -- or --cases-json")
            env = {}
            for item in args.env:
                if "=" not in item:
                    raise ValueError(f"invalid --env: {item}")
                k, v = item.split("=", 1); env[k] = v
            metadata = json.loads(args.metadata.read_text()) if args.metadata else {}
            if not isinstance(metadata, dict):
                raise ValueError("--metadata JSON must contain an object")
            options = dict(cwd=args.cwd, result_dir=args.result_dir, binds=args.bind,
                           env=env, timeout=args.timeout, metadata=metadata,
                           allow_duplicate=args.allow_duplicate, priority=args.priority)
            if args.cases_json:
                cases = json.loads(args.cases_json.read_text())
                print(json.dumps(scheduler.submit_cases(cases=cases, **options), indent=2))
            else:
                print(json.dumps(scheduler.submit(command=command, **options), indent=2))
        elif args.action == "list":
            print(json.dumps(scheduler.list_tasks(), indent=2))
        elif args.action == "cancel":
            print(json.dumps(scheduler.cancel(args.task_id), indent=2))
        elif args.action == 'pause':
            print(json.dumps(scheduler.pause(args.task_id), indent=2))
        else:
            if args.loop and args.once:
                raise ValueError("worker accepts only one of --once and --loop")
            while True:
                result = scheduler.worker_once()
                print(json.dumps(result or {"status": "idle"}), flush=True)
                if not args.loop or (result and result.get('yielded')):
                    break
                time.sleep(args.poll_interval)
        return 0
    except (ValueError, OSError, json.JSONDecodeError) as exc:
        print(f"scheduler error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
