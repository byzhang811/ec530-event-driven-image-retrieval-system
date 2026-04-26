#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
LOG_DIR="$ROOT_DIR/artifacts/logs"

mkdir -p "$LOG_DIR"

cd "$ROOT_DIR"

echo "==> [1/4] Redis status check"
{
  echo '$ brew services start redis'
  brew services start redis
  echo
  echo '$ redis-cli ping'
  redis-cli ping
  echo
  echo '$ brew services list | rg "^redis\\s"'
  brew services list | rg '^redis\s'
} | tee "$LOG_DIR/01_redis_status.log"

echo "==> [2/4] Unit test run"
{
  echo '$ python3 -m pytest -q'
  python3 -m pytest -q
} | tee "$LOG_DIR/02_pytest.log"

echo "==> [3/4] In-memory demo run"
{
  echo '$ python3 scripts/run_demo.py --broker memory'
  python3 scripts/run_demo.py --broker memory
} | tee "$LOG_DIR/03_demo_memory.log"

echo "==> [4/4] Redis demo run"
{
  echo '$ python3 scripts/run_demo.py --broker redis'
  python3 scripts/run_demo.py --broker redis
} | tee "$LOG_DIR/04_demo_redis.log"

echo "All checks completed. Logs saved under: $LOG_DIR"
