# Workload Suite 2, Variant D: complete optimized and fault-trapped pipeline.
# Native traversal (as Variant B) plus set -eu, pipefail where supported,
# readability checks before descent, checked helper status and output format,
# checked audit-log and sink delivery, signal traps and rollback.
# Contract: IN OUT TMPD HELPER SINK AUDITLOG AWKDIR.
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

files=0 dirs=0 empty=0 depth=0 csvlines=0 audit=0
ext_csv=0 ext_dat=0 ext_json=0 ext_log=0 ext_txt=0

walk() {
  for e in "$1"/*; do
    [ -e "$e" ] || continue
    if [ -d "$e" ]; then
      if [ ! -r "$e" ] || [ ! -x "$e" ]; then fail "unreadable directory $e" 66; fi
      dirs=$((dirs + 1))
      walk "$e" $(($2 + 1))
    else
      files=$((files + 1))
      if [ "$2" -gt "$depth" ]; then depth=$2; fi
      [ -s "$e" ] || empty=$((empty + 1))
      case $e in
        *.csv)
          ext_csv=$((ext_csv + 1))
          if [ ! -r "$e" ]; then fail "unreadable file $e" 66; fi
          while IFS= read -r _l; do csvlines=$((csvlines + 1)); done < "$e" ;;
        *.dat) ext_dat=$((ext_dat + 1)) ;;
        *.json) ext_json=$((ext_json + 1)) ;;
        *.log) ext_log=$((ext_log + 1)) ;;
        *.txt) ext_txt=$((ext_txt + 1)) ;;
      esac
    fi
  done
}

if [ ! -d "$IN" ] || [ ! -r "$IN" ] || [ ! -x "$IN" ]; then fail "input root missing or unreadable" 66; fi
i=0
for d in "$IN"/*; do
  [ -d "$d" ] || continue
  i=$((i + 1))
  r=$("$HELPER" "$d" "$i") || fail "audit helper failed for $d" 70
  case $r in
    "ok "*) ;;
    *) fail "malformed audit output for $d" 70 ;;
  esac
  n=${r##* }
  case $n in ''|*[!0-9]*) fail "malformed audit count for $d" 70 ;; esac
  audit=$((audit + n))
done
if [ "$i" -eq 0 ]; then fail "no subdirectories found under input root" 66; fi
walk "$IN" 1
printf '%s ok\n' "$IN" >> "$AUDITLOG" || fail "audit log write failed" 74
printf 'files=%s dirs=%s empty=%s depth=%s ext_csv=%s ext_dat=%s ext_json=%s ext_log=%s ext_txt=%s csvlines=%s audit=%s\n' \
  "$files" "$dirs" "$empty" "$depth" "$ext_csv" "$ext_dat" "$ext_json" "$ext_log" "$ext_txt" "$csvlines" "$audit" \
  | "$SINK" "$OUT" || fail "report delivery to sink failed" 74
