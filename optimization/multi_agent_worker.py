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


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', required=True, type=Path)
    parser.add_argument('--max-seconds', type=float, default=3600)
    parser.add_argument('--poll-interval', type=float, default=2)
    args = parser.parse_args()
    if args.max_seconds <= 0 or args.poll_interval <= 0:
        parser.error('time limits must be positive')
    scheduler = Scheduler(args.root)
    deadline = time.monotonic() + args.max_seconds
    while time.monotonic() < deadline:
        result = scheduler.worker_once()
        if result is not None:
            print(json.dumps(result), flush=True)
            if result.get('pause_requested'):
                break
        if result is None or result.get('busy'):
            time.sleep(args.poll_interval)


if __name__ == '__main__':
    main()
