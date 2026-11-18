#!/bin/dash
# sink.sh - fixed downstream consumer for Workload Suite 2 (report uploader).
# Usage: producer | sink.sh OUTFILE
# Fault-injection control (set by the harness):
#   SFAULT=close  the consumer closes its input without reading and exits 1
#                 (closed-pipe / unavailable-consumer fault)
case ${SFAULT:-none} in
  close)
    echo "sink: downstream consumer unavailable" >&2
    exit 1 ;;
esac
exec cat > "$1"
