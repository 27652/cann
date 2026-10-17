#!/usr/bin/env python3
"""Reusable, fail-closed Fast Track for qualified research candidates.

Agents enroll qualified immutable snapshots.  The Coordinator is the only
process that invokes the CANNJudge client.  A POST is never repeated merely
because a worker or network request was interrupted: the job is reconciled by
submission ID first, and an unresolved job blocks later submissions.
"""
from __future__ import annotations

import argparse
import fcntl
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import time
import uuid
from decimal import Decimal, InvalidOperation

DEFAULT_PROJECT_FILES = (
    "CMakeLists.txt", "data_utils.h", "kernel.asc", "main.asc", "run.sh",
    "scripts/gen_data.py", "scripts/QuantMatmulReluQuant.py",
    "scripts/verify_result.py",
)
FORBIDDEN_PARTS = {".git", "build", "__pycache__", "gitlabcann", "cookie"}
PENDING_STATUSES = {"waiting", "pending", "judging", "running", "processing", "queued"}
TERMINAL_STATUSES = {"pass", "passed", "fail", "failed", "error", "complete", "completed"}


def digest(path: Path) -> str:
    """Hash one file or a deterministic relative-path/file-hash tree."""
    h = hashlib.sha256()
    if path.is_file():
        with path.open("rb") as stream:
            for block in iter(lambda: stream.read(1024 * 1024), b""):
                h.update(block)
    else:
        for item in sorted(path.rglob("*")):
            if item.is_file() and not any(part in FORBIDDEN_PARTS for part in item.parts):
                h.update(item.relative_to(path).as_posix().encode() + b"\0")
                h.update(digest(item).encode())
    return h.hexdigest()


def _json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def read_strict(path: Path) -> dict:
    data = _json(path)
    if not isinstance(data, dict):
        raise ValueError("strict result must be a JSON object")
    if (type(data.get("int32_mismatches")) is not int or
            data["int32_mismatches"] != 0 or data.get("int32_scale_ok") is not True):
        raise ValueError("strict INT32 result is not passing")
    return {
        "int32_mismatches": data["int32_mismatches"],
        "int32_scale_ok": data["int32_scale_ok"],
        "result_sha256": digest(path),
        "fingerprint": data.get("fingerprint", {}),
    }


def _safe_relative(name: str) -> bool:
    path = Path(name)
    return bool(name) and not path.is_absolute() and ".." not in path.parts and not any(
        part in FORBIDDEN_PARTS for part in path.parts)


def _project_files(metadata: dict) -> tuple[str, ...]:
    names = metadata.get("project_files", list(DEFAULT_PROJECT_FILES))
    if not isinstance(names, list) or not names or not all(isinstance(x, str) and _safe_relative(x) for x in names):
        raise ValueError("project_files must be a nonempty safe relative-path list")
    names = tuple(dict.fromkeys(names))
    if "kernel.asc" not in names:
        raise ValueError("project_files must include kernel.asc")
    return names


def _lock(root: Path, name="queue.lock", blocking=True):
    root.mkdir(parents=True, exist_ok=True, mode=0o700)
    try:
        root.chmod(0o700)
    except OSError:
        pass
    stream = (root / name).open("a+")
    flags = fcntl.LOCK_EX if blocking else fcntl.LOCK_EX | fcntl.LOCK_NB
    try:
        fcntl.flock(stream, flags)
    except BaseException:
        stream.close()
        raise
    return stream


def _load(root: Path) -> dict:
    path = root / "queue.json"
    if not path.exists():
        return {"schema_version": 2, "jobs": {}, "halted": False}
    data = _json(path)
    if data.get("schema_version") != 2 or not isinstance(data.get("jobs"), dict):
        raise ValueError("unsupported Fast Track queue schema")
    return data


def _save(root: Path, data: dict):
    fd, name = tempfile.mkstemp(prefix="queue.", dir=root)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as stream:
            json.dump(data, stream, indent=2, sort_keys=True)
            stream.write("\n")
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(name, root / "queue.json")
        (root / "queue.json").chmod(0o600)
    finally:
        if os.path.exists(name):
            os.unlink(name)


def _with_queue(root: Path, callback):
    with _lock(root) as stream:
        data = _load(root)
        result = callback(data)
        _save(root, data)
        fcntl.flock(stream, fcntl.LOCK_UN)
        return result


def enroll(project: Path, strict: Path, root: Path, candidate_id: str, metadata: dict) -> dict:
    """Validate and atomically enroll one candidate snapshot."""
    project, strict, root = project.resolve(), strict.resolve(), root.resolve()
    if not project.is_dir() or not strict.is_file():
        raise ValueError("project and strict result are required")
    if not candidate_id or not candidate_id.replace("-", "").replace("_", "").replace(".", "").isalnum():
        raise ValueError("invalid candidate ID")
    if any(part in FORBIDDEN_PARTS for part in project.parts):
        raise ValueError("invalid candidate project path")
    if not isinstance(metadata, dict):
        raise ValueError("metadata must be an object")
    allowed = {"candidate_id", "source_sha256", "binary_sha256", "build_fingerprint",
               "strict_result_sha256", "environment_fingerprint", "binary_path", "risks",
               "project_files"}
    extra = set(metadata) - allowed
    if extra:
        raise ValueError("unsupported metadata fields: " + ",".join(sorted(extra)))

    names = _project_files(metadata)
    files = {}
    for name in names:
        path = (project / name).resolve()
        if not path.is_relative_to(project) or not path.is_file():
            raise ValueError("missing/unsafe project file: " + name)
        files[name] = digest(path)
    source = files["kernel.asc"]
    strict_info = read_strict(strict)
    binary = metadata.get("binary_sha256")
    if not isinstance(binary, str) or len(binary) != 64 or any(c not in "0123456789abcdef" for c in binary):
        raise ValueError("metadata.binary_sha256 is required")
    if metadata.get("source_sha256") not in (None, source):
        raise ValueError("source_sha256 does not match project")
    binary_path = Path(metadata.get("binary_path", "")).resolve()
    if (any(part in {".git", "gitlabcann", "cookie"} for part in binary_path.parts) or
            not binary_path.is_file() or digest(binary_path) != binary):
        raise ValueError("missing or mismatched compiled binary")
    build = metadata.get("build_fingerprint")
    if (not isinstance(build, dict) or build.get("returncode") != 0 or
            build.get("files") != files or build.get("binary_sha256") != binary or
            build.get("payload_enabled") is not True):
        raise ValueError("build fingerprint must bind project files, binary and payload activation")
    fp = strict_info["fingerprint"]
    if (not isinstance(fp, dict) or fp.get("source_sha256") != source or
            fp.get("binary_sha256") != binary or not fp.get("environment")):
        raise ValueError("strict result source/binary/environment identity mismatch")
    if not isinstance(metadata.get("risks"), list):
        raise ValueError("explicit risks list is required (may be empty)")

    project_hash = hashlib.sha256(json.dumps(files, sort_keys=True).encode()).hexdigest()

    def create(data):
        for job in data["jobs"].values():
            if job.get("candidate_id") == candidate_id or job.get("project_sha256") == project_hash:
                raise ValueError("duplicate candidate or source snapshot")
        job_id = f"{int(time.time() * 1000)}-{uuid.uuid4().hex[:10]}"
        snapshot = root / "snapshots" / job_id
        snapshot.mkdir(parents=True, exist_ok=False)
        try:
            for name, expected in files.items():
                target = snapshot / "project" / name
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(project / name, target)
                if digest(target) != expected:
                    raise ValueError("project changed during snapshot")
                target.chmod(0o400)
            shutil.copy2(strict, snapshot / "strict-result.json")
            if digest(snapshot / "strict-result.json") != strict_info["result_sha256"]:
                raise ValueError("strict result changed during snapshot")
            shutil.copy2(binary_path, snapshot / "compiled-binary")
            if digest(snapshot / "compiled-binary") != binary:
                raise ValueError("binary changed during snapshot")
        except BaseException:
            shutil.rmtree(snapshot, ignore_errors=True)
            raise
        job = {
            "job_id": job_id, "candidate_id": candidate_id, "source_sha256": source,
            "binary_sha256": binary, "files": files, "project_sha256": project_hash,
            "strict": strict_info, "metadata": metadata, "snapshot": str(snapshot),
            "status": "queued", "created_at": time.time(), "official": True,
        }
        data["jobs"][job_id] = job
        return job

    return _with_queue(root, create)


def list_jobs(root: Path) -> list[dict]:
    with _lock(root) as stream:
        jobs = list(_load(root)["jobs"].values())
        fcntl.flock(stream, fcntl.LOCK_UN)
        return jobs


def _submission_id(job: dict, result_dir: Path | None = None) -> str | None:
    if isinstance(job.get("submission_id"), str) and job["submission_id"]:
        return job["submission_id"]
    if result_dir:
        for path in (result_dir / "result.json", result_dir / "result.submit.json"):
            if path.is_file():
                try:
                    data = _json(path)
                except (OSError, ValueError, json.JSONDecodeError):
                    continue
                for key in ("submission_id", "submissionId", "_id", "id"):
                    value = data.get(key) if isinstance(data, dict) else None
                    if isinstance(value, dict):
                        value = value.get("_id") or value.get("id")
                    if value:
                        return str(value)
                nested = data.get('data', {}) if isinstance(data, dict) else {}
                if isinstance(nested, dict):
                    for key in ('submissionId', '_id', 'id'):
                        if nested.get(key):
                            return str(nested[key])
    return None


def _manifest_ok(job: dict, result_dir: Path) -> dict:
    path = result_dir / "result.manifest.json"
    if not path.is_file():
        raise ValueError("missing preflight payload manifest")
    data = _json(path)
    uploaded = data.get("files") if isinstance(data, dict) else None
    if not isinstance(uploaded, dict) or not uploaded:
        raise ValueError("invalid payload manifest")
    if any(name not in job["files"] or value.get("sha256") != job["files"][name]
           for name, value in uploaded.items() if isinstance(value, dict)):
        raise ValueError("payload manifest identity mismatch")
    if any(not isinstance(value, dict) for value in uploaded.values()):
        raise ValueError("invalid payload manifest entry")
    return {"path": str(path), "sha256": digest(path), "files": uploaded}


def _formal_state(path: Path, expected_submission: str | None) -> dict:
    if not path.is_file():
        return {"state": "uncertain", "reason": "missing result JSON"}
    data = _json(path)
    if not isinstance(data, dict):
        return {"state": "uncertain", "reason": "result is not an object"}
    embedded_sid = _submission_id({}, path.parent)
    sid = embedded_sid or expected_submission
    if expected_submission and embedded_sid and embedded_sid != expected_submission:
        return {"state": "uncertain", "reason": "submission ID changed", "submission_id": embedded_sid}
    status = str(data.get("status", "")).lower()
    if not sid or len(sid) != 24 or any(c not in '0123456789abcdef' for c in sid):
        return {"state": "uncertain", "reason": "missing/invalid submission ID"}
    if status in PENDING_STATUSES:
        return {"state": "submitted", "submission_id": sid}
    if status not in TERMINAL_STATUSES:
        return {"state": "uncertain", "reason": "unknown result status", "status": status}
    cases = data.get("result", data.get("testcases"))
    if status in {"pass", "passed"}:
        if not isinstance(cases, list) or len(cases) != 15:
            return {"state": "uncertain", "reason": "Pass result is not 15 testcases", "submission_id": sid}
        if not all(isinstance(case, dict) and case.get("testcase_status") == "Pass" and
                   case.get("precision_ratio") == 1 for case in cases):
            return {"state": "uncertain", "reason": "Pass result contains a nonpassing testcase", "submission_id": sid}
        ids = [case.get('testcase_id') for case in cases]
        if any(not isinstance(value, str) or not value for value in ids) or len(set(ids)) != 15:
            return {'state': 'uncertain', 'reason': 'missing/duplicate testcase IDs', 'submission_id': sid}
        state = "evaluated_pass"
    else:
        state = "evaluated_fail"
    return {"state": state, "submission_id": sid,
            "testcase_count": len(cases) if isinstance(cases, list) else None,
            "status": data.get("status")}


def _summary(job: dict, result_dir: Path, state: dict, manifest: dict) -> dict:
    result = _json(result_dir / "result.json")
    cases = result.get("result", result.get("testcases", [])) or []
    return {
        "schema_version": 1, "job_id": job["job_id"], "candidate_id": job["candidate_id"],
        "submission_id": state.get("submission_id"), "status": state["state"],
        "testcases": [{"testcase_id": x.get("testcase_id"),
                       "testcase_status": x.get("testcase_status"),
                       "precision_ratio": x.get("precision_ratio")} for x in cases
                      if isinstance(x, dict)],
        "payload_manifest": manifest, "result_sha256": digest(result_dir / "result.json"),
        "score_evidence": state.get("score_evidence"),
        "evaluated_at": time.time(),
    }


def archive(job: dict, result_dir: Path, state: dict, destination: Path):
    """Persist allowlisted evidence and actual uploaded bytes, never raw replies."""
    manifest = _json(result_dir / 'result.manifest.json')
    summary = _json(result_dir / 'official-summary.json')
    sid = state['submission_id']
    destination.mkdir(parents=True, exist_ok=True, mode=0o700)
    bundle = destination / sid
    if bundle.exists():
        existing = _json(bundle / 'evidence.json')
        if existing.get('submission_id') != summary.get('submission_id') or existing.get('result_sha256') != summary.get('result_sha256'):
            raise ValueError('refusing to replace existing evidence')
        return str(bundle)
    staging = Path(tempfile.mkdtemp(prefix='.pending-', dir=destination))
    for name, entry in manifest['files'].items():
        if not _safe_relative(name) or name not in job['files']:
            raise ValueError('unsafe archive payload')
        source = Path(job['snapshot']) / 'project' / name
        if digest(source) != entry['sha256']:
            raise ValueError('archive source identity mismatch')
        target = staging / 'source' / name
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, target)
    summary.update(risks=job['metadata']['risks'], source_sha256=job['source_sha256'],
                   binary_sha256=job['binary_sha256'])
    (staging / 'evidence.json').write_text(json.dumps(summary, indent=2) + '\n')
    os.rename(staging, bundle)
    return str(bundle)


def _ranking_score(cli: Path, job: dict, result_dir: Path, manifest: dict,
                   ranking_query: str, session: Path | None = None) -> dict:
    sid = _submission_id(job, result_dir)
    problem_id = manifest.get("problem_id")
    if not sid or not problem_id:
        return {"state": "awaiting_score", "reason": "missing submission/problem ID"}
    output = result_dir / "result.ranking.json"
    command = ["python3", str(cli), "ranking", "--problem-id", str(problem_id),
               "--submission-id", sid, "--output", str(output)]
    if session:
        command[2:2] = ["--session", str(session)]
    if ranking_query:
        command += ["--query", ranking_query]
    try:
        proc = subprocess.run(command, text=True, stdout=subprocess.PIPE,
                              stderr=subprocess.STDOUT, timeout=600)
        (result_dir / "ranking.log").write_text(proc.stdout)
    except Exception as exc:
        return {"state": "awaiting_score", "reason": type(exc).__name__}
    if proc.returncode != 0 or not output.is_file():
        return {"state": "awaiting_score", "reason": "ranking query unavailable"}
    ranking = _json(output)
    if ranking.get("requested_submission_id") != sid or ranking.get("problem_id") != problem_id:
        return {"state": "uncertain", "reason": "ranking query identity mismatch"}
    matches = [row for row in ranking.get("metrics", [])
               if row.get("submission_id") == sid and row.get("status") == "Pass" and
               row.get("score") is not None]
    if len(matches) != 1:
        return {"state": "awaiting_score", "reason": "no unique score for this submission"}
    score = matches[0]["score"]
    try:
        score_value = Decimal(str(score))
    except (TypeError, ValueError, InvalidOperation):
        return {"state": "uncertain", "reason": "invalid ranking score"}
    if isinstance(score, bool) or not score_value.is_finite() or score_value < 0:
        return {"state": "uncertain", "reason": "invalid ranking score"}
    return {"state": "evaluated_pass", "submission_id": sid,
            "score_evidence": {"source": "ranking", "submission_id": sid,
                               "problem_id": problem_id, "status": "Pass",
                               "value": str(score), "ranking_sha256": digest(output)}}


def _apply_result(job: dict, result_dir: Path, cli: Path, ranking_query: str,
                  session: Path | None = None) -> dict:
    expected = _submission_id(job, result_dir)
    state = _formal_state(result_dir / "result.json", expected)
    if state["state"] in {"submitted", "uncertain"}:
        return state
    manifest = _manifest_ok(job, result_dir)
    if state["state"] == "evaluated_pass":
        score = _ranking_score(cli, job, result_dir, _json(result_dir / "result.manifest.json"), ranking_query, session)
        if score["state"] != "evaluated_pass":
            return score
        state.update(score)
    summary = _summary(job, result_dir, state, manifest)
    (result_dir / "official-summary.json").write_text(json.dumps(summary, indent=2) + "\n")
    return {**state, "summary_path": str(result_dir / "official-summary.json")}


def _set_job(root: Path, job_id: str, **updates):
    def update(data):
        data["jobs"][job_id].update(updates)
    return _with_queue(root, update)


def _claim_queued(root: Path) -> dict | None:
    def claim(data):
        # A worker crash after POST must never turn into an automatic resubmit.
        for job in data["jobs"].values():
            if job["status"] == "running":
                job["status"] = "uncertain"
                job["error"] = "worker interrupted; reconcile by submission ID"
        for job in sorted(data["jobs"].values(), key=lambda x: (x["created_at"], x["job_id"])):
            if job["status"] == "queued":
                job["status"] = "running"
                return dict(job)
        return None
    return _with_queue(root, claim)


def _result_command(cli: Path, submission_id: str, result: Path,
                    session: Path | None = None) -> list[str]:
    prefix = ["python3", str(cli)]
    if session:
        prefix += ["--session", str(session)]
    return prefix + ["result", submission_id, "--output", str(result),
            "--wait", "30", "--timeout", "1800"]


def _submit_command(cli: Path, project: Path, result: Path, expected: Path,
                    project_args: list[str], session: Path | None = None) -> list[str]:
    filtered = []
    skip = False
    for value in project_args:
        if skip:
            skip = False
            continue
        if value == '--ranking-query':
            skip = True
            continue
        filtered.append(value)
    prefix = ["python3", str(cli)]
    if session:
        prefix += ["--session", str(session)]
    return prefix + ["submit", str(project), "--output", str(result),
            "--expected-project", str(expected), "--wait", "30", "--timeout", "1800",
             *filtered]


def _reconcile_one(root: Path, cli: Path, job: dict, result_dir: Path,
                   ranking_query: str, session: Path | None = None) -> dict:
    sid = _submission_id(job, result_dir)
    if not sid:
        return {"state": "uncertain", "reason": "no submission ID; resubmission is forbidden"}
    result = result_dir / "result.json"
    state = _formal_state(result, sid)
    if state["state"] == "submitted" or not result.is_file():
        try:
            proc = subprocess.run(_result_command(cli, sid, result, session), text=True,
                                  stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                  timeout=86400)
            (result_dir / "reconcile.log").write_text(proc.stdout)
        except Exception as exc:
            return {"state": "uncertain", "reason": type(exc).__name__, "submission_id": sid}
        if proc.returncode != 0:
            return {"state": "uncertain", "reason": f"result returncode={proc.returncode}", "submission_id": sid}
        state = _formal_state(result, sid)
    if state["state"] in {"evaluated_pass", "evaluated_fail"}:
        return state
    return state


def _worker(root: Path, cli: Path, output: Path, project_args: list[str],
            ranking_query: str | None, submit=True, evidence_root=None,
            session: Path | None = None) -> list[dict]:
    results = []
    # Reconcile all outstanding jobs before considering a new POST.
    for job in list_jobs(root):
        if job["status"] not in {"running", "submitted", "uncertain", "awaiting_score"}:
            continue
        result_dir = Path(job.get("result_dir", ""))
        state = _reconcile_one(root, cli, job, result_dir, ranking_query, session) if result_dir.is_dir() else {
            "state": "uncertain", "reason": "missing result directory"}
        if state["state"] in {"evaluated_pass", "evaluated_fail"}:
            try:
                if state.get('submission_id'):
                    job['submission_id'] = state['submission_id']
                state = {**state, **_apply_result(job, result_dir, cli, ranking_query, session)}
                if evidence_root and state['state'] in {'evaluated_pass', 'evaluated_fail'}:
                    archive(job, result_dir, state, evidence_root)
            except (ValueError, OSError, json.JSONDecodeError) as exc:
                state = {"state": "uncertain", "reason": str(exc)}
        if state["state"] in {"uncertain", "submitted", "awaiting_score"}:
            _set_job(root, job["job_id"], status=state["state"], error=state.get("reason"), halted=True)
            return [{"job_id": job["job_id"], "status": state["state"], "error": state.get("reason")}]
        _set_job(root, job["job_id"], status=state["state"], submission_id=state.get("submission_id"),
                 summary_path=state.get("summary_path"), error=None)

    if not submit:
        return results
    while True:
        job = _claim_queued(root)
        if job is None:
            _with_queue(root, lambda data: data.update(halted=False))
            return results
        snap = Path(job["snapshot"])
        result_dir = output / job["job_id"]
        try:
            if (any(digest(snap / "project" / name) != expected for name, expected in job["files"].items()) or
                    digest(snap / "compiled-binary") != job["binary_sha256"] or
                    digest(snap / "strict-result.json") != job["strict"]["result_sha256"]):
                raise ValueError("snapshot integrity check failed")
            result_dir.mkdir(parents=True, exist_ok=False, mode=0o700)
            expected = result_dir / "expected-project.json"
            expected.write_text(json.dumps(job["files"], sort_keys=True) + "\n")
            _set_job(root, job["job_id"], result_dir=str(result_dir))
            proc = subprocess.run(_submit_command(cli, snap / "project", result_dir / "result.json",
                                                  expected, project_args, session), text=True,
                                  stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=86400)
            (result_dir / "worker.log").write_text(proc.stdout)
            if proc.returncode != 0:
                state = {"state": "uncertain", "reason": f"submit returncode={proc.returncode}"}
            else:
                state = _formal_state(result_dir / "result.json", None)
                if state["state"] in {"evaluated_pass", "evaluated_fail"}:
                    sid = state.get('submission_id')
                    _set_job(root, job["job_id"], submission_id=sid)
                    job['submission_id'] = sid
                    state = {**state, **_apply_result(job, result_dir, cli, ranking_query, session)}
                    if evidence_root and state['state'] in {'evaluated_pass', 'evaluated_fail'}:
                        archive(job, result_dir, state, evidence_root)
                elif state["state"] == "submitted":
                    state["reason"] = "submission accepted but result is not terminal"
                else:
                    state["reason"] = state.get("reason", "submission result is unavailable")
        except (OSError, ValueError, json.JSONDecodeError, subprocess.SubprocessError) as exc:
            state = {"state": "uncertain", "reason": str(exc)}
        updates = {"status": state["state"], "error": state.get("reason"),
                   "submission_id": state.get("submission_id") or job.get('submission_id') or _submission_id({}, result_dir),
                   "finished_at": time.time()}
        if state["state"] in {"submitted", "uncertain", "awaiting_score"}:
            updates["halted"] = True
            _set_job(root, job["job_id"], **updates)
            results.append({"job_id": job["job_id"], "status": state["state"], "error": state.get("reason")})
            return results
        _set_job(root, job["job_id"], **updates, summary_path=state.get("summary_path"))
        results.append({"job_id": job["job_id"], "status": state["state"], "error": None})


def worker(root: Path, cli: Path, output: Path, project_args: list[str], submit=True,
            evidence_root=None, session: Path | None = None) -> list[dict]:
    """Drain terminal jobs and submit qualified candidates serially."""
    root, cli, output = root.resolve(), cli.resolve(), output.resolve()
    root.mkdir(parents=True, exist_ok=True, mode=0o700)
    try:
        guard = _lock(root, "worker.lock", blocking=False)
    except BlockingIOError:
        return [{"status": "busy"}]
    try:
        ranking_query = None
        for index, arg in enumerate(project_args[:-1]):
            if arg == "--ranking-query":
                ranking_query = project_args[index + 1]
        try:
            host_guard = _lock(Path('/tmp/opencode/fast-track'), 'formal-host.lock', blocking=False)
        except BlockingIOError:
            return [{'status': 'busy'}]
        with host_guard:
            return _worker(root, cli, output, project_args, ranking_query, submit=submit,
                           evidence_root=evidence_root, session=session)
    finally:
        fcntl.flock(guard, fcntl.LOCK_UN)
        guard.close()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path("/tmp/opencode/fast-track/queue"))
    sub = parser.add_subparsers(dest="action", required=True)
    e = sub.add_parser("enroll")
    e.add_argument("--project", type=Path, required=True)
    e.add_argument("--strict-result", type=Path, required=True)
    e.add_argument("--candidate-id", required=True)
    e.add_argument("--metadata", type=Path, required=True)
    sub.add_parser("list")
    for name in ('worker', 'serve'):
        w = sub.add_parser(name)
        w.add_argument("--cli", type=Path, default=Path("gitlabcann/cannjudge_cli.py"))
        w.add_argument("--output", type=Path, default=Path("/tmp/opencode/fast-track/results"))
        w.add_argument("--contest")
        w.add_argument("--problem")
        w.add_argument("--ranking-query", required=True)
        w.add_argument("--session", type=Path,
                       help="受控 CLI 会话文件；内容不会被读取、打印或写入日志")
        w.add_argument('--evidence-root', type=Path, default=Path('evidence/formal/fast-track'))
        if name == 'serve':
            w.add_argument('--max-seconds', type=float, default=3600)
            w.add_argument('--poll-interval', type=float, default=60)
    r = sub.add_parser("reconcile")
    r.add_argument("--cli", type=Path, default=Path("gitlabcann/cannjudge_cli.py"))
    r.add_argument("--output", type=Path, default=Path("/tmp/opencode/fast-track/results"))
    r.add_argument('--ranking-query', required=True)
    r.add_argument('--session', type=Path,
                   help="受控 CLI 会话文件；内容不会被读取、打印或写入日志")
    r.add_argument('--evidence-root', type=Path, default=Path('evidence/formal/fast-track'))
    args = parser.parse_args()
    try:
        if args.action == "enroll":
            metadata = _json(args.metadata)
            print(json.dumps(enroll(args.project, args.strict_result, args.root,
                                     args.candidate_id, metadata), indent=2))
        elif args.action == "list":
            print(json.dumps(list_jobs(args.root), indent=2))
        else:
            if args.action == "reconcile":
                print(json.dumps(worker(args.root, args.cli, args.output,
                                        ['--ranking-query', args.ranking_query], submit=False,
                                        evidence_root=args.evidence_root,
                                        session=args.session), indent=2))
            else:
                extra = []
                for key in ("contest", "problem", "ranking_query"):
                    value = getattr(args, key)
                    if value:
                        extra += ["--" + key.replace("_", "-"), value]
                if args.action == 'serve':
                    if args.max_seconds <= 0 or args.poll_interval < 30:
                        raise ValueError('serve requires positive duration and poll interval >= 30 seconds')
                    deadline = time.monotonic() + args.max_seconds
                    while time.monotonic() < deadline:
                        result = worker(args.root, args.cli, args.output, extra,
                                        evidence_root=args.evidence_root,
                                        session=args.session)
                        print(json.dumps(result), flush=True)
                        # Unknown acceptance, expired sessions and missing score
                        # require explicit operator reconciliation, never a loop.
                        if any(item['status'] in {'uncertain', 'awaiting_score', 'submitted', 'rejected'} for item in result):
                            return 1
                        time.sleep(min(args.poll_interval, max(0, deadline - time.monotonic())))
                else:
                    print(json.dumps(worker(args.root, args.cli, args.output, extra,
                                            evidence_root=args.evidence_root,
                                            session=args.session), indent=2))
        return 0
    except (ValueError, OSError, json.JSONDecodeError, subprocess.SubprocessError) as exc:
        print(json.dumps({"ok": False, "error": str(exc)}))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
