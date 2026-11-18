# Workload Suite 2, Variant A (fish translation): external coreutils pipeline baseline.
# Contract: IN OUT TMPD HELPER SINK AUDITLOG AWKDIR. No error handling by design.
set -gx BENCH_PID $fish_pid

set i 0
for d in $IN/*
    test -d $d; or continue
    set i (math $i + 1)
    $HELPER $d $i
end > $TMPD/audit.txt
set L $TMPD/list.txt
find $IN -mindepth 1 -printf '%y %d %s %p\n' > $L
set files (grep -c '^f ' $L)
set dirs (grep -c '^d ' $L)
set empty (grep -c '^f [0-9]* 0 ' $L)
set depth (grep '^f ' $L | cut -d' ' -f2 | sort -n | tail -n 1)
set ext_csv (grep -c '^f .*\.csv$' $L)
set ext_dat (grep -c '^f .*\.dat$' $L)
set ext_json (grep -c '^f .*\.json$' $L)
set ext_log (grep -c '^f .*\.log$' $L)
set ext_txt (grep -c '^f .*\.txt$' $L)
set csvlines (grep '^f .*\.csv$' $L | cut -d' ' -f4 | xargs -r cat | wc -l)
set audit (awk '{s += $3} END {print s + 0}' $TMPD/audit.txt)
printf '%s ok\n' $IN >> $AUDITLOG
printf 'files=%s dirs=%s empty=%s depth=%s ext_csv=%s ext_dat=%s ext_json=%s ext_log=%s ext_txt=%s csvlines=%s audit=%s\n' \
    "$files" "$dirs" "$empty" "$depth" "$ext_csv" "$ext_dat" "$ext_json" "$ext_log" "$ext_txt" "$csvlines" "$audit" \
    | $SINK $OUT
