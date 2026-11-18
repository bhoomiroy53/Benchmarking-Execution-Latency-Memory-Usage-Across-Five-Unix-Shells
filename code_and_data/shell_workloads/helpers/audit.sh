#!/bin/dash
# audit.sh - fixed external audit stage for Workload Suite 2.
# Invoked once per top-level subdirectory; prints "ok <dir> <direct-entry-count>".
# Always executed by /bin/dash, so its cost is constant across interpreters.
#
# Usage: audit.sh DIR INDEX
# Fault-injection controls (set by the harness):
#   HFAULT=exit  invocation number HFAULT_AT prints a diagnostic and exits 3
#   HFAULT=term  invocation number HFAULT_AT sends SIGTERM to $BENCH_PID
d=$1
i=$2
case ${HFAULT:-none} in
  exit)
    if [ "$i" = "$HFAULT_AT" ]; then
      echo "audit: policy check failed for $d" >&2
      exit 3
    fi ;;
  term)
    if [ "$i" = "$HFAULT_AT" ]; then
      kill -TERM "$BENCH_PID" 2>/dev/null
    fi ;;
esac
entries=$(ls -A -- "$d") || { echo "audit: cannot list $d" >&2; exit 2; }
n=0
for _e in $entries; do n=$((n + 1)); done
printf 'ok %s %s\n' "$d" "$n"
