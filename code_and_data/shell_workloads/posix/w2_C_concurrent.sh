# Workload Suite 2, Variant C: buffered batch execution with named-pipe concurrency.
# Each top-level subdirectory becomes one background job: a single find listing
# piped into one batched awk aggregator that reports through its own FIFO, plus
# one background audit-helper job; the parent merges the partial counters.
# Contract: IN OUT TMPD HELPER SINK AUDITLOG AWKDIR. No error handling by design.
if [ -n "${ZSH_VERSION:-}" ]; then setopt SH_WORD_SPLIT NO_NOMATCH; fi
BENCH_PID=$$; export BENCH_PID

i=0
for d in "$IN"/*; do
  [ -d "$d" ] || continue
  i=$((i + 1))
  mkfifo "$TMPD/j$i.fifo"
  "$HELPER" "$d" "$i" > "$TMPD/a$i.txt" &
  find "$d" -printf '%y %d %s %p\n' | awk -v out="$TMPD/j$i.fifo" -f "$AWKDIR/w2_batch.awk" &
done
files=0 dirs=0 empty=0 depth=0 csvlines=0 audit=0
ext_csv=0 ext_dat=0 ext_json=0 ext_log=0 ext_txt=0
j=0
while [ "$j" -lt "$i" ]; do
  j=$((j + 1))
  read -r f dd e mx c da js lg tx cl < "$TMPD/j$j.fifo"
  files=$((files + f)); dirs=$((dirs + dd)); empty=$((empty + e))
  if [ "$mx" -gt "$depth" ]; then depth=$mx; fi
  ext_csv=$((ext_csv + c)); ext_dat=$((ext_dat + da)); ext_json=$((ext_json + js))
  ext_log=$((ext_log + lg)); ext_txt=$((ext_txt + tx)); csvlines=$((csvlines + cl))
done
wait
j=0
while [ "$j" -lt "$i" ]; do
  j=$((j + 1))
  read -r _st _nm n < "$TMPD/a$j.txt"
  audit=$((audit + n))
done
printf '%s ok\n' "$IN" >> "$AUDITLOG"
printf 'files=%s dirs=%s empty=%s depth=%s ext_csv=%s ext_dat=%s ext_json=%s ext_log=%s ext_txt=%s csvlines=%s audit=%s\n' \
  "$files" "$dirs" "$empty" "$depth" "$ext_csv" "$ext_dat" "$ext_json" "$ext_log" "$ext_txt" "$csvlines" "$audit" \
  | "$SINK" "$OUT"
