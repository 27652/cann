#!/usr/bin/env python3
"""Bounded Coordinator-owned Worker; reclaims after cooperative case yields.

Uses the existing Scheduler and its canonical host lease. Research Agents only
submit; this process is the single queue consumer for an integration run.
"""
import argparse
import json
from pathlib import Path
import time

from camodel_scheduler import Scheduler
from fast_track import list_jobs, worker as formal_worker


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', required=True, type=Path)
    parser.add_argument('--max-seconds', type=float, default=3600)
    parser.add_argument('--poll-interval', type=float, default=2)
    parser.add_argument('--fast-track-root', type=Path, default=Path('/tmp/opencode/fast-track/queue'))
    parser.add_argument('--fast-track-ranking-query', default=None)
    parser.add_argument('--fast-track-output', type=Path, default=Path('/tmp/opencode/fast-track/results'))
    parser.add_argument('--formal-cli', type=Path, default=Path('gitlabcann/cannjudge_cli.py'))
    args = parser.parse_args()
    if args.max_seconds <= 0 or args.poll_interval <= 0:
        parser.error('time limits must be positive')
    scheduler = Scheduler(args.root)
    deadline = time.monotonic() + args.max_seconds
    formal_halted = False
    next_formal_check = 0.0
    while time.monotonic() < deadline:
        result = scheduler.worker_once()
        if result is not None:
            print(json.dumps(result), flush=True)
            if result.get('pause_requested'):
                break
        if (not formal_halted and time.monotonic() >= next_formal_check):
            next_formal_check = time.monotonic() + 60
            outstanding = [job for job in list_jobs(args.fast_track_root)
                           if job['status'] in {'queued', 'running', 'submitted', 'uncertain', 'awaiting_score'}]
            if outstanding:
                formal = formal_worker(
                    args.fast_track_root, args.formal_cli, args.fast_track_output,
                    ['--ranking-query', args.fast_track_ranking_query],
                    evidence_root=Path('evidence/formal/fast-track'))
                print(json.dumps({'fast_track': formal}), flush=True)
                formal_halted = any(item['status'] in {'rejected', 'uncertain', 'submitted', 'awaiting_score'}
                                    for item in formal)
        if result is None or result.get('busy'):
            time.sleep(args.poll_interval)


if __name__ == '__main__':
    main()
