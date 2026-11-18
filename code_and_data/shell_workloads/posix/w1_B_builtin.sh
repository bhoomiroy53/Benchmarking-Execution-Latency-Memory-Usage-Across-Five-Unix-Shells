# Workload Suite 1, Variant B: native shell built-ins and parameter expansion only.
# The only external process is the fixed upstream helper; all parsing, counting
# and aggregation use read, case, parameter expansion and shell arithmetic.
# Associative aggregation is emulated with eval-composed variable names
# (POSIX sh has no associative arrays), guarded by a case whitelist.
# Contract: IN OUT TMPD HELPER AWKDIR. No error handling by design.
if [ -n "${ZSH_VERSION:-}" ]; then setopt SH_WORD_SPLIT NO_NOMATCH; fi
BENCH_PID=$$; export BENCH_PID

lines=0 s2=0 s3=0 s4=0 s5=0 get=0 post=0 put=0 del=0 bytes=0 maxlat=0
r_auth=0 r_items=0 r_orders=0 r_search=0 r_users=0
"$HELPER" "$IN" | {
  while read -r _ip _a _b _d _z meth path _p st by lat _rest; do
    lines=$((lines + 1))
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
    esac
    bytes=$((bytes + by))
    if [ "$lat" -gt "$maxlat" ]; then maxlat=$lat; fi
    r=${path#/api/v1/}
    r=${r%%/*}
    case $r in
      auth|items|orders|search|users) eval "r_$r=\$((r_$r + 1))" ;;
    esac
  done
  printf 'lines=%s s2=%s s3=%s s4=%s s5=%s get=%s post=%s put=%s del=%s bytes=%s maxlat=%s r_auth=%s r_items=%s r_orders=%s r_search=%s r_users=%s\n' \
    "$lines" "$s2" "$s3" "$s4" "$s5" "$get" "$post" "$put" "$del" "$bytes" "$maxlat" \
    "$r_auth" "$r_items" "$r_orders" "$r_search" "$r_users" > "$OUT"
}
