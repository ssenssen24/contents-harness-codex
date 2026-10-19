#!/usr/bin/env python3
"""Validate every run up to the last stage its state.json records as done (CI entry point)."""
import argparse
import json
import sys
from pathlib import Path

from validate_run import DONE, STAGES, Run


def claimed_stage(state):
    reached = None
    for stage in STAGES:
        if state['stages'][stage]['status'] not in DONE[stage]:
            break
        reached = stage
    return reached


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--project', type=Path, default=Path(__file__).resolve().parent.parent)
    args = parser.parse_args()
    failed = 0
    for state_path in sorted((args.project/'runs').glob('*/state.json')):
        run = state_path.parent
        try:
            stage = claimed_stage(json.loads(state_path.read_text()))
            if stage is None:
                print(f'SKIP {run.name}: 완료된 단계 없음')
                continue
            report = Run(run, args.project).validate(stage)
        except Exception as e:
            report = {'automatic_pass': False, 'errors': [{'check': 'input', 'message': str(e)}]}
            stage = '?'
        if report['automatic_pass']:
            print(f'PASS {run.name} --stage {stage}')
        else:
            failed += 1
            print(f'FAIL {run.name} --stage {stage}')
            for e in report['errors']:
                print(f'  - {e["check"]}: {e["message"]}')
    return 1 if failed else 0


if __name__ == '__main__':
    sys.exit(main())
