# Workload Suite 1, Variant C (fish translation): batched awk jobs reporting via FIFOs.
# Contract: IN OUT TMPD HELPER AWKDIR. No error handling by design.
set -gx BENCH_PID $fish_pid

$HELPER $IN > $TMPD/raw
split -n l/4 -d $TMPD/raw $TMPD/part.
set parts $TMPD/part.0*
for p in $parts
    mkfifo $p.fifo
    awk -v out=$p.fifo -f $AWKDIR/w1_batch.awk $p &
end
set lines 0; set s2 0; set s3 0; set s4 0; set s5 0
set get 0; set post 0; set put 0; set del 0; set bytes 0; set maxlat 0
set r_auth 0; set r_items 0; set r_orders 0; set r_search 0; set r_users 0
for p in $parts
    read -l line < $p.fifo
    set -l f (string split ' ' -- $line)
    set lines (math $lines + $f[1]); set s2 (math $s2 + $f[2]); set s3 (math $s3 + $f[3])
    set s4 (math $s4 + $f[4]); set s5 (math $s5 + $f[5])
    set get (math $get + $f[6]); set post (math $post + $f[7]); set put (math $put + $f[8])
    set del (math $del + $f[9]); set bytes (math $bytes + $f[10])
    if test $f[11] -gt $maxlat
        set maxlat $f[11]
    end
    set r_auth (math $r_auth + $f[12]); set r_items (math $r_items + $f[13])
    set r_orders (math $r_orders + $f[14]); set r_search (math $r_search + $f[15])
    set r_users (math $r_users + $f[16])
end
wait
printf 'lines=%s s2=%s s3=%s s4=%s s5=%s get=%s post=%s put=%s del=%s bytes=%s maxlat=%s r_auth=%s r_items=%s r_orders=%s r_search=%s r_users=%s\n' \
    "$lines" "$s2" "$s3" "$s4" "$s5" "$get" "$post" "$put" "$del" "$bytes" "$maxlat" \
    "$r_auth" "$r_items" "$r_orders" "$r_search" "$r_users" > $OUT
