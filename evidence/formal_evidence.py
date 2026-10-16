#!/usr/bin/env python3
"""Offline, fail-closed evidence recovery and promotion eligibility checker.

Never imports the network client or opens a session file. Eligibility does not
perform promotion: restoring/replacing a working tree is a separate operation.
"""
import argparse
from decimal import Decimal, InvalidOperation
import hashlib
import json
from pathlib import Path

CONTEST = '6a9a94b9bf41025d6012d4dd'
PROBLEM = '6a9a9ec4bf41025d6014adbe'
FILES = ('CMakeLists.txt', 'data_utils.h', 'kernel.asc', 'main.asc', 'run.sh',
         'scripts/gen_data.py', 'scripts/QuantMatmulReluQuant.py', 'scripts/verify_result.py')


def sha(data):
    return hashlib.sha256(data).hexdigest()


def require(condition, message):
    if not condition:
        raise ValueError(message)


def identifier(value):
    return value.get('_id') if isinstance(value, dict) else value


def number(value):
    require(not isinstance(value, bool) and value is not None, 'missing/invalid score')
    try:
        result = Decimal(str(value))
    except InvalidOperation as exc:
        raise ValueError('invalid score') from exc
    require(result.is_finite() and result >= 0, 'nonfinite/negative score')
    return result


def validate(record, root):
    require(isinstance(record, dict), 'invalid evidence record')
    require(record.get('schema_version') == 1, 'unknown evidence schema')
    sid = record.get('submission_id')
    require(isinstance(sid, str) and len(sid) == 24 and
            all(c in '0123456789abcdef' for c in sid), 'invalid submission ID')
    require(record.get('contest_id') == CONTEST and record.get('problem_id') == PROBLEM,
            'contest/problem mismatch')
    require(record.get('status') == 'Pass', 'submission not Pass')
    cases = record.get('testcases')
    require(isinstance(cases, list) and len(cases) == 15, 'expected exactly 15 testcases')
    require(all(isinstance(x, dict) for x in cases), 'invalid testcase record')
    ids = [x.get('testcase_id') for x in cases]
    require(all(isinstance(x, str) and x for x in ids) and len(set(ids)) == 15,
            'missing/duplicate testcase ID')
    require(all(x.get('testcase_status') == 'Pass' and
                x.get('precision_ratio') == 1 for x in cases), 'nonpassing testcase')
    score = record.get('score_evidence', {})
    require(isinstance(score, dict), 'invalid score evidence')
    require(score.get('submission_id') == sid and score.get('problem_id') == PROBLEM
            and score.get('status') == 'Pass' and score.get('source') == 'ranking',
            'score provenance/ID mismatch')
    value = number(score.get('value'))
    require(isinstance(record.get('scoring_context'), str) and record['scoring_context'],
            'unknown scoring context')
    files = record.get('files', {})
    require(isinstance(files, dict), 'invalid file manifest')
    require(set(files) == set(FILES), 'incomplete or unexpected submitted file set')
    root = Path(root).resolve()
    for name, digest in files.items():
        path = (root / name).resolve()
        require(path.is_relative_to(root) and path.is_file(), 'missing/unsafe source file')
        require(sha(path.read_bytes()) == digest, 'submitted content hash mismatch: ' + name)
    source_root = root.resolve()
    actual = {p.relative_to(source_root).as_posix() for p in source_root.rglob('*') if p.is_file()}
    require(actual == set(FILES), 'source tree has unexpected or missing files')
    return value


def eligibility(candidate, candidate_root, best, best_root):
    new = validate(candidate, candidate_root)
    old = validate(best, best_root)
    require(candidate['scoring_context'] == best['scoring_context'], 'scoring context mismatch')
    require(new > old, 'score does not strictly improve historical best')
    return {'eligible': True, 'submission_id': candidate['submission_id'],
            'score': str(new), 'previous_best_score': str(old),
            'action': 'decision-only; working tree not modified'}


def recover(result_path, ranking_path, hashes_path, destination, context):
    """Extract only known public result fields and previously indexed source paths."""
    raw_bytes = Path(result_path).read_bytes()
    rank_bytes = Path(ranking_path).read_bytes()
    raw, rank = json.loads(raw_bytes), json.loads(rank_bytes)
    expected = {}
    for line in Path(hashes_path).read_text().splitlines():
        digest, name = line.split()
        expected[name] = digest
    require(set(expected) == set(FILES), 'unexpected recovery allowlist')
    contents = {}
    for entry in raw['files']:
        name = entry['path']
        require(name in expected and name not in contents, 'unexpected/duplicate submitted path')
        data = entry['content'].encode('utf-8')
        require(sha(data) == expected[name], 'historical source hash mismatch: ' + name)
        contents[name] = data
    require(set(contents) == set(FILES), 'incomplete historical source')
    sid = identifier(raw.get('_id'))
    matching = [x for x in rank['metrics'] if x.get('submission_id') == sid]
    require(len(matching) == 1 and rank.get('requested_submission_id') == sid,
            'ranking does not uniquely match submission')
    metric = matching[0]
    record = dict(schema_version=1, submission_id=sid,
                  contest_id=identifier(raw.get('contest')), problem_id=identifier(raw.get('problem_id')),
                  status=raw.get('status'), scoring_context=context,
                  testcases=[{k: x.get(k) for k in ('testcase_id', 'testcase_status', 'precision_ratio',
                                                   'time', 'best_time', 'score')} for x in raw['result']],
                  score_evidence=dict(source='ranking', submission_id=metric.get('submission_id'),
                                      problem_id=rank.get('problem_id'), status=metric.get('status'),
                                      value=str(metric.get('score')), queried_at=rank.get('queried_at')),
                  files=expected, provenance=dict(result_sha256=sha(raw_bytes), ranking_sha256=sha(rank_bytes)))
    destination = Path(destination)
    require(not destination.exists(), 'refusing to overwrite existing bundle')
    # Validate all metadata before creating any persistent files.
    import tempfile
    with tempfile.TemporaryDirectory(prefix='formal-', dir='/tmp/opencode') as tmp:
        for name, data in contents.items():
            p = Path(tmp) / name
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_bytes(data)
        validate(record, tmp)
    destination.mkdir(parents=True, mode=0o700)
    for name, data in contents.items():
        p = destination / 'source' / name
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes(data)
    (destination / 'evidence.json').write_text(json.dumps(record, indent=2) + '\n')
    return {'submission_id': sid, 'score': str(validate(record, destination / 'source')),
            'testcases_passed': 15, 'source_files': len(contents)}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest='command', required=True)
    r = commands.add_parser('recover')
    for name in ('result', 'ranking', 'hashes', 'destination', 'scoring-context'):
        r.add_argument('--' + name, required=True)
    v = commands.add_parser('validate')
    v.add_argument('bundle', type=Path)
    p = commands.add_parser('decide')
    p.add_argument('candidate', type=Path)
    p.add_argument('--best', required=True, type=Path)
    args = parser.parse_args()
    try:
        if args.command == 'recover':
            output = recover(args.result, args.ranking, args.hashes, args.destination, args.scoring_context)
        elif args.command == 'validate':
            record = json.loads((args.bundle / 'evidence.json').read_text())
            output = {'valid': True, 'score': str(validate(record, args.bundle / 'source'))}
        else:
            output = eligibility(json.loads((args.candidate / 'evidence.json').read_text()),
                                 args.candidate / 'source',
                                 json.loads((args.best / 'evidence.json').read_text()), args.best / 'source')
        print(json.dumps(output))
    except (ValueError, KeyError, TypeError, OSError) as exc:
        print(json.dumps({'valid': False, 'eligible': False, 'reason': str(exc)}))
        return 1
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
