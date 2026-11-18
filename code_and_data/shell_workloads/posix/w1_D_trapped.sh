# Workload Suite 1, Variant D: complete optimized and fault-trapped pipeline.
# Native built-in processing (as Variant B) plus strict mode (set -eu), pipefail
# where the interpreter supports it, record validation, checked writes, signal
# traps, a uniform BENCH-FAULT diagnostic, and rollback of partial output.
# Contract: IN OUT TMPD HELPER AWKDIR.
if [ -n "${ZSH_VERSION:-}" ]; then setopt SH_WORD_SPLIT NO_NOMATCH; fi
BENCH_PID=$$; export BENCH_PID
set -eu
if (set -o pipefail) 2>/dev/null; then set -o pipefail; fi

fail() {
  printf 'BENCH-FAULT %s\n' "$1" >&2
  if [ -f "$OUT" ]; then rm -f "$OUT"; fi
  exit "$2"
}
trap 'fail "signal TERM" 143' TERM
trap 'fail "signal INT" 130' INT
trap 'fail "signal HUP" 129' HUP

if [ ! -f "$IN" ] || [ ! -r "$IN" ]; then fail "input missing or unreadable" 66; fi

lines=0 s2=0 s3=0 s4=0 s5=0 get=0 post=0 put=0 del=0 bytes=0 maxlat=0
r_auth=0 r_items=0 r_orders=0 r_search=0 r_users=0
"$HELPER" "$IN" | {
  while read -r _ip _a _b _d _z meth path _p st by lat _rest; do
    lines=$((lines + 1))
    case $st in [1-5][0-9][0-9]) ;; *) fail "corrupt status field at record $lines" 65 ;; esac
    case $by in ''|*[!0-9]*) fail "corrupt bytes field at record $lines" 65 ;; esac
    case $lat in ''|*[!0-9]*) fail "corrupt latency field at record $lines" 65 ;; esac
    case $st in
      2*) s2=$((s2 + 1)) ;;
      3*) s3=$((s3 + 1)) ;;
      4*) s4=$((s4 + 1)) ;;
      5*) s5=$((s5 + 1)) ;;
    esac
    case $meth in
      '"GET') get=$((get + 1)) ;;
      '"POST') post=$((post + 1)) ;;
      '"PUT') put=$((put + 1)) ;;
      '"DELETE') del=$((del + 1)) ;;
      *) fail "corrupt method field at record $lines" 65 ;;
    esac
    bytes=$((bytes + by))
    if [ "$lat" -gt "$maxlat" ]; then maxlat=$lat; fi
    r=${path#/api/v1/}
    r=${r%%/*}
    case $r in
      auth|items|orders|search|users) eval "r_$r=\$((r_$r + 1))" ;;
      *) fail "corrupt path field at record $lines" 65 ;;
    esac
  done
  printf 'lines=%s s2=%s s3=%s s4=%s s5=%s get=%s post=%s put=%s del=%s bytes=%s maxlat=%s r_auth=%s r_items=%s r_orders=%s r_search=%s r_users=%s\n' \
    "$lines" "$s2" "$s3" "$s4" "$s5" "$get" "$post" "$put" "$del" "$bytes" "$maxlat" \
    "$r_auth" "$r_items" "$r_orders" "$r_search" "$r_users" > "$OUT" || fail "output write failed" 74
}
