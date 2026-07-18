#!/usr/bin/env bash
# pre-commit hook: run trace hats regression test before every commit
# Install: cp $(dirname $0)/pre-commit .git/hooks/ && chmod +x .git/hooks/pre-commit
cd "$(git rev-parse --show-toplevel)"
python3 test_trace_hats.py
exit $?