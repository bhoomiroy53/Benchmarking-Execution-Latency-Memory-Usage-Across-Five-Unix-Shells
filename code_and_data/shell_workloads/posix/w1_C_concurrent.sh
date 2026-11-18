# Workload Suite 1, Variant C: buffered batch execution with named-pipe concurrency.
# The staged log is split into four line-balanced partitions; each partition is
# aggregated by one batched awk process running as a background job that reports
# its 16 counters through its own named pipe (FIFO); the parent merges natively.
# Contract: IN OUT TMPD HELPER AWKDIR. No error handling by design.
if [ -n "${ZSH_VERSION:-}" ]; then setopt SH_WORD_SPLIT NO_NOMATCH; fi
BENCH_PID=$$; export BENCH_PID

"$HELPER" "$IN" > "$TMPD/raw"
split -n l/4 -d "$TMPD/raw" "$TMPD/part."
for p in "$TMPD"/part.0?; do
  mkfifo "$p.fifo"
  awk -v out="$p.fifo" -f "$AWKDIR/w1_batch.awk" "$p" &
done
lines=0 s2=0 s3=0 s4=0 s5=0 get=0 post=0 put=0 del=0 bytes=0 maxlat=0
r_auth=0 r_items=0 r_orders=0 r_search=0 r_users=0
for p in "$TMPD"/part.0?; do
  read -r n a2 a3 a4 a5 g po pu de b mx ra ri ro rs ru < "$p.fifo"
  lines=$((lines + n)); s2=$((s2 + a2)); s3=$((s3 + a3)); s4=$((s4 + a4)); s5=$((s5 + a5))
  get=$((get + g)); post=$((post + po)); put=$((put + pu)); del=$((del + de))
  bytes=$((bytes + b))
  if [ "$mx" -gt "$maxlat" ]; then maxlat=$mx; fi
  r_auth=$((r_auth + ra)); r_items=$((r_items + ri)); r_orders=$((r_orders + ro))
  r_search=$((r_search + rs)); r_users=$((r_users + ru))
done
wait
printf 'lines=%s s2=%s s3=%s s4=%s s5=%s get=%s post=%s put=%s del=%s bytes=%s maxlat=%s r_auth=%s r_items=%s r_orders=%s r_search=%s r_users=%s\n' \
  "$lines" "$s2" "$s3" "$s4" "$s5" "$get" "$post" "$put" "$del" "$bytes" "$maxlat" \
  "$r_auth" "$r_items" "$r_orders" "$r_search" "$r_users" > "$OUT"
