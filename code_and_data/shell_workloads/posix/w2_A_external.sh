# Workload Suite 2, Variant A: external subshell and coreutils pipeline baseline.
# Recursive traversal and metadata audit through find, grep, cut, sort, xargs,
# cat, wc and awk; one audit helper process per top-level subdirectory; the
# report is delivered through the external sink consumer.
# Contract: IN OUT TMPD HELPER SINK AUDITLOG AWKDIR. No error handling by design.
if [ -n "${ZSH_VERSION:-}" ]; then setopt SH_WORD_SPLIT NO_NOMATCH; fi
BENCH_PID=$$; export BENCH_PID

i=0
for d in "$IN"/*; do
  [ -d "$d" ] || continue
  i=$((i + 1))
  "$HELPER" "$d" "$i"
done > "$TMPD/audit.txt"
L="$TMPD/list.txt"
find "$IN" -mindepth 1 -printf '%y %d %s %p\n' > "$L"
files=$(grep -c '^f ' "$L")
dirs=$(grep -c '^d ' "$L")
empty=$(grep -c '^f [0-9]* 0 ' "$L")
depth=$(grep '^f ' "$L" | cut -d' ' -f2 | sort -n | tail -n 1)
ext_csv=$(grep -c '^f .*\.csv$' "$L")
ext_dat=$(grep -c '^f .*\.dat$' "$L")
ext_json=$(grep -c '^f .*\.json$' "$L")
ext_log=$(grep -c '^f .*\.log$' "$L")
ext_txt=$(grep -c '^f .*\.txt$' "$L")
csvlines=$(grep '^f .*\.csv$' "$L" | cut -d' ' -f4 | xargs -r cat | wc -l)
audit=$(awk '{s += $3} END {print s + 0}' "$TMPD/audit.txt")
printf '%s ok\n' "$IN" >> "$AUDITLOG"
printf 'files=%s dirs=%s empty=%s depth=%s ext_csv=%s ext_dat=%s ext_json=%s ext_log=%s ext_txt=%s csvlines=%s audit=%s\n' \
  "$files" "$dirs" "$empty" "$depth" "$ext_csv" "$ext_dat" "$ext_json" "$ext_log" "$ext_txt" "$csvlines" "$audit" \
  | "$SINK" "$OUT"
