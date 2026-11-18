# Workload Suite 2, Variant B: native shell built-ins only.
# Recursive traversal by a shell function over glob expansions, metadata tests
# with the test builtin, CSV line counting with read loops, and audit-helper
# output captured by command substitution (one subshell per subdirectory).
# Contract: IN OUT TMPD HELPER SINK AUDITLOG AWKDIR. No error handling by design.
if [ -n "${ZSH_VERSION:-}" ]; then setopt SH_WORD_SPLIT NO_NOMATCH; fi
BENCH_PID=$$; export BENCH_PID

files=0 dirs=0 empty=0 depth=0 csvlines=0 audit=0
ext_csv=0 ext_dat=0 ext_json=0 ext_log=0 ext_txt=0

walk() {
  for e in "$1"/*; do
    [ -e "$e" ] || continue
    if [ -d "$e" ]; then
      dirs=$((dirs + 1))
      walk "$e" $(($2 + 1))
    else
      files=$((files + 1))
      if [ "$2" -gt "$depth" ]; then depth=$2; fi
      [ -s "$e" ] || empty=$((empty + 1))
      case $e in
        *.csv)
          ext_csv=$((ext_csv + 1))
          while IFS= read -r _l; do csvlines=$((csvlines + 1)); done < "$e" ;;
        *.dat) ext_dat=$((ext_dat + 1)) ;;
        *.json) ext_json=$((ext_json + 1)) ;;
        *.log) ext_log=$((ext_log + 1)) ;;
        *.txt) ext_txt=$((ext_txt + 1)) ;;
      esac
    fi
  done
}

i=0
for d in "$IN"/*; do
  [ -d "$d" ] || continue
  i=$((i + 1))
  r=$("$HELPER" "$d" "$i")
  audit=$((audit + ${r##* }))
done
walk "$IN" 1
printf '%s ok\n' "$IN" >> "$AUDITLOG"
printf 'files=%s dirs=%s empty=%s depth=%s ext_csv=%s ext_dat=%s ext_json=%s ext_log=%s ext_txt=%s csvlines=%s audit=%s\n' \
  "$files" "$dirs" "$empty" "$depth" "$ext_csv" "$ext_dat" "$ext_json" "$ext_log" "$ext_txt" "$csvlines" "$audit" \
  | "$SINK" "$OUT"
