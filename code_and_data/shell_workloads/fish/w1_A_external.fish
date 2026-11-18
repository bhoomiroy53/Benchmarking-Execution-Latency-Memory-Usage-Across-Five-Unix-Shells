# Workload Suite 1, Variant A (fish translation): external coreutils pipeline baseline.
# Same external commands, same order and same output as posix/w1_A_external.sh.
# Contract: IN OUT TMPD HELPER AWKDIR. No error handling by design.
set -gx BENCH_PID $fish_pid

$HELPER $IN > $TMPD/raw
set R $TMPD/raw
set lines (wc -l < $R | tr -d ' ')
set s2 (cut -d' ' -f9 < $R | grep -c '^2')
set s3 (cut -d' ' -f9 < $R | grep -c '^3')
set s4 (cut -d' ' -f9 < $R | grep -c '^4')
set s5 (cut -d' ' -f9 < $R | grep -c '^5')
set get (cut -d' ' -f6 < $R | tr -d '"' | grep -cx GET)
set post (cut -d' ' -f6 < $R | tr -d '"' | grep -cx POST)
set put (cut -d' ' -f6 < $R | tr -d '"' | grep -cx PUT)
set del (cut -d' ' -f6 < $R | tr -d '"' | grep -cx DELETE)
set bytes (cut -d' ' -f10 < $R | awk '{s += $1} END {print s + 0}')
set maxlat (cut -d' ' -f11 < $R | sort -n | tail -n 1)
set r_auth (cut -d' ' -f7 < $R | cut -d/ -f4 | grep -cx auth)
set r_items (cut -d' ' -f7 < $R | cut -d/ -f4 | grep -cx items)
set r_orders (cut -d' ' -f7 < $R | cut -d/ -f4 | grep -cx orders)
set r_search (cut -d' ' -f7 < $R | cut -d/ -f4 | grep -cx search)
set r_users (cut -d' ' -f7 < $R | cut -d/ -f4 | grep -cx users)
printf 'lines=%s s2=%s s3=%s s4=%s s5=%s get=%s post=%s put=%s del=%s bytes=%s maxlat=%s r_auth=%s r_items=%s r_orders=%s r_search=%s r_users=%s\n' \
    "$lines" "$s2" "$s3" "$s4" "$s5" "$get" "$post" "$put" "$del" "$bytes" "$maxlat" \
    "$r_auth" "$r_items" "$r_orders" "$r_search" "$r_users" > $OUT
