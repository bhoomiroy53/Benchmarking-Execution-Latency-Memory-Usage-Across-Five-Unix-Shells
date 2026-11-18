#!/bin/dash
# logsrc.sh - fixed external upstream stage for Workload Suite 1.
# Streams one access-log file to stdout, emulating a log-fetch tool.
# It is always executed by /bin/dash, whichever shell runs the workload,
# so its cost is constant across interpreters.
#
# Usage: logsrc.sh FILE
# Fault-injection controls (set by the harness, never by the workload):
#   HFAULT=none  normal streaming (default)
#   HFAULT=exit  emit the first HFAULT_AT records, print a diagnostic, exit 3
#   HFAULT=term  emit HFAULT_AT records, send SIGTERM to $BENCH_PID (the
#                workload interpreter), then stream the remaining records
f=$1
case ${HFAULT:-none} in
  exit)
    head -n "$HFAULT_AT" -- "$f"
    echo "logsrc: upstream source failure after $HFAULT_AT records" >&2
    exit 3 ;;
  term)
    head -n "$HFAULT_AT" -- "$f"
    kill -TERM "$BENCH_PID" 2>/dev/null
    tail -n +"$((HFAULT_AT + 1))" -- "$f"
    exit 0 ;;
  *)
    exec cat -- "$f" ;;
esac
