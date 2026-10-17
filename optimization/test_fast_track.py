import json
import hashlib
import tempfile
import unittest
import importlib.util
from types import SimpleNamespace
from unittest.mock import patch, Mock
from pathlib import Path

from fast_track import digest, enroll, read_strict, worker, _formal_state, _submit_command, _result_command, _ranking_score


class FastTrackTests(unittest.TestCase):
    def test_explicit_session_is_global_cli_option(self):
        session = Path('/unused/session-file')
        submit = _submit_command(Path('cli'), Path('project'), Path('result'),
                                 Path('expected'), [], session)
        result = _result_command(Path('cli'), 'submission', Path('result'), session)
        for command, action in ((submit, 'submit'), (result, 'result')):
            self.assertEqual(command[:5], ['python3', 'cli', '--session', str(session), action])
        with tempfile.TemporaryDirectory() as temp:
            with patch('fast_track._submission_id', return_value='submission'), \
                 patch('fast_track.subprocess.run', return_value=SimpleNamespace(returncode=1)) as run:
                _ranking_score(Path('cli'), {}, Path(temp), {'problem_id': 'problem'}, 'team', session)
                self.assertEqual(run.call_args.args[0][:5],
                                 ['python3', 'cli', '--session', str(session), 'ranking'])

    def test_real_cli_rejects_changed_payload_before_post(self):
        spec = importlib.util.spec_from_file_location('fast_track_cli_test',
            Path(__file__).resolve().parents[1] / 'gitlabcann/cannjudge_cli.py')
        cli = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(cli)
        with tempfile.TemporaryDirectory() as temp:
            base = Path(temp)
            (base / 'kernel.asc').write_text('changed')
            expected = base / 'expected.json'
            expected.write_text(json.dumps({'kernel.asc': 'a' * 64}))
            args = SimpleNamespace(user_id='test', contest='contest', problem='problem',
                                   project=str(base), expected_project=str(expected),
                                   output=str(base / 'result.json'))
            client = Mock()
            client.request.return_value = {'data': {'files': [{'path': 'kernel.asc', 'editable': True}]}}
            with patch.object(cli, 'get_problem', return_value=({}, {}, {'_id': 'problem'})):
                with self.assertRaisesRegex(RuntimeError, 'identity mismatch'):
                    cli.submit(client, args)
            self.assertEqual(client.request.call_count, 1)  # template GET only

    def test_result_identity_and_duplicate_cases_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / 'result.json'
            path.write_text(json.dumps({'_id': 'a' * 24, 'status': 'Pass', 'result': [
                {'testcase_id': 'same', 'testcase_status': 'Pass', 'precision_ratio': 1}
                for _ in range(15)]}))
            self.assertEqual(_formal_state(path, 'b' * 24)['state'], 'uncertain')
            self.assertEqual(_formal_state(path, 'a' * 24)['state'], 'uncertain')

    def test_submit_command_keeps_identity_guard_not_ranking_query(self):
        command = _submit_command(Path('cli'), Path('project'), Path('result'), Path('expected'),
                                  ['--contest', 'contest', '--ranking-query', 'team'])
        self.assertIn('--expected-project', command)
        self.assertNotIn('team', command)
        self.assertIn('contest', command)

    def _project(self, base):
        project = base / "project"; project.mkdir()
        for name in ('CMakeLists.txt', 'data_utils.h', 'kernel.asc', 'main.asc', 'run.sh',
                     'scripts/gen_data.py', 'scripts/QuantMatmulReluQuant.py', 'scripts/verify_result.py'):
            path = project / name; path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(name)
        return project

    def _qualified(self, base):
        project = self._project(base)
        binary = base / 'binary'; binary.write_bytes(b'binary')
        files = {name: hashlib.sha256((project / name).read_bytes()).hexdigest()
                 for name in ('CMakeLists.txt', 'data_utils.h', 'kernel.asc', 'main.asc',
                              'run.sh', 'scripts/gen_data.py', 'scripts/QuantMatmulReluQuant.py',
                              'scripts/verify_result.py')}
        strict = base / 'strict.json'
        strict.write_text(json.dumps({'int32_mismatches': 0, 'int32_scale_ok': True,
                                      'fingerprint': {'source_sha256': files['kernel.asc'],
                                                      'binary_sha256': hashlib.sha256(b'binary').hexdigest(),
                                                      'environment': {'soc': 'host'}}}))
        metadata = {'binary_sha256': hashlib.sha256(b'binary').hexdigest(),
                    'binary_path': str(binary), 'risks': [],
                    'build_fingerprint': {'returncode': 0, 'files': files,
                                           'binary_sha256': hashlib.sha256(b'binary').hexdigest(),
                                           'payload_enabled': True}}
        return project, strict, metadata

    def test_enroll_freezes_and_deduplicates(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp) / "queue"; project, strict, metadata = self._qualified(Path(temp))
            job = enroll(project, strict, root, "c1", metadata)
            self.assertEqual(job["status"], "queued")
            self.assertEqual(digest(Path(job["snapshot"]) / "project/kernel.asc"), job["source_sha256"])
            with self.assertRaisesRegex(ValueError, "duplicate"):
                enroll(project, strict, root, "c1-again", metadata)

    def test_rejects_non_strict_and_unapproved_metadata(self):
        with tempfile.TemporaryDirectory() as temp:
            project = self._project(Path(temp))
            strict = Path(temp) / "strict.json"
            strict.write_text(json.dumps({"int32_mismatches": 1, "int32_scale_ok": False}))
            with self.assertRaisesRegex(ValueError, "strict"):
                enroll(project, strict, Path(temp) / "queue", "c1", {"binary_sha256": "a" * 64})
            strict.write_text(json.dumps({"int32_mismatches": 0, "int32_scale_ok": True}))
            with self.assertRaisesRegex(ValueError, "unsupported"):
                enroll(project, strict, Path(temp) / "queue", "c1", {"binary_sha256": "a" * 64, "cookie": "x"})

    def test_worker_submits_snapshot_without_network(self):
        with tempfile.TemporaryDirectory() as temp:
            base = Path(temp)
            root = base / "queue"
            project, strict, metadata = self._qualified(base)
            enroll(project, strict, root, "c1", metadata)
            cli = base / "fake_cli.py"
            cli.write_text(
                "import json,sys\n"
                "out=sys.argv[sys.argv.index('--output')+1]\n"
                "open(out, 'w').write(json.dumps({'status':'queued','submissionId':'0123456789abcdef01234567'}))\n")
            result = worker(root, cli, base / "results", ['--ranking-query', 'test-team'])
            self.assertEqual(result[0]["status"], "submitted")
            self.assertEqual(json.loads((base / "queue/queue.json").read_text())["jobs"]
                             [result[0]["job_id"]]["status"], "submitted")
            # A second invocation reconciles, never repeats submit.
            cli.write_text("raise SystemExit(3)\n")
            again = worker(root, cli, base / 'results', ['--ranking-query', 'test-team'])
            self.assertEqual(again[0]['status'], 'uncertain')
            self.assertEqual(len(list((base / 'results').iterdir())), 1)

    def test_terminal_pass_archives_and_drains_two_candidates(self):
        with tempfile.TemporaryDirectory() as temp:
            base = Path(temp); root = base / 'queue'
            for i in range(2):
                folder = base / str(i); folder.mkdir()
                project, strict, metadata = self._qualified(folder)
                (project / 'main.asc').write_text(str(i))
                metadata['build_fingerprint']['files']['main.asc'] = digest(project / 'main.asc')
                enroll(project, strict, root, 'c' + str(i), metadata)
            cli = base / 'fake.py'
            cli.write_text('''import json,sys
from pathlib import Path
a=sys.argv; out=Path(a[a.index('--output')+1]); sid='0123456789abcdef01234567'
if a[1]=='submit':
    sid=('1' if Path(a[2]+'/main.asc').read_text()=='1' else '0')*24
    files=json.loads(Path(a[a.index('--expected-project')+1]).read_text())
    out.with_suffix('.manifest.json').write_text(json.dumps({'problem_id':'problem', 'files':{k:{'sha256':v} for k,v in files.items()}}))
    out.write_text(json.dumps({'_id':sid,'status':'Pass','result':[{'testcase_id':str(i),'testcase_status':'Pass','precision_ratio':1} for i in range(15)]}))
else:
    sid=a[a.index('--submission-id')+1]
    out.write_text(json.dumps({'problem_id':'problem','requested_submission_id':sid,'metrics':[{'submission_id':sid,'status':'Pass','score':7.1}]}))
''')
            results = worker(root, cli, base / 'results', ['--ranking-query', 'test'],
                             evidence_root=base / 'evidence')
            self.assertEqual([r['status'] for r in results], ['evaluated_pass'] * 2)
            self.assertEqual(len(list((base / 'evidence').glob('*/evidence.json'))), 2)

    def test_tampered_snapshot_and_missing_identity_fail_closed(self):
        with tempfile.TemporaryDirectory() as temp:
            base = Path(temp); project, strict, metadata = self._qualified(base)
            job = enroll(project, strict, base / 'queue', 'c1', metadata)
            path = Path(job['snapshot']) / 'project/kernel.asc'
            path.chmod(0o600); path.write_text('tampered')
            results = worker(base / 'queue', base / 'nonexistent.py', base / 'results',
                             ['--ranking-query', 'test'])
            self.assertEqual(results[0]['status'], 'uncertain')
            self.assertFalse((base / 'results').exists())


if __name__ == "__main__":
    unittest.main()
