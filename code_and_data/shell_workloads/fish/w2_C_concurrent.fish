# Workload Suite 2, Variant C (fish translation): per-subtree batched jobs reporting via FIFOs.
# Contract: IN OUT TMPD HELPER SINK AUDITLOG AWKDIR. No error handling by design.
set -gx BENCH_PID $fish_pid

set i 0
for d in $IN/*
    test -d $d; or continue
    set i (math $i + 1)
    mkfifo $TMPD/j$i.fifo
    $HELPER $d $i > $TMPD/a$i.txt &
    find $d -printf '%y %d %s %p\n' | awk -v out=$TMPD/j$i.fifo -f $AWKDIR/w2_batch.awk &
end
set files 0; set dirs 0; set empty 0; set depth 0; set csvlines 0; set audit 0
set ext_csv 0; set ext_dat 0; set ext_json 0; set ext_log 0; set ext_txt 0
set j 0
while test $j -lt $i
    set j (math $j + 1)
    read -l line < $TMPD/j$j.fifo
    set -l f (string split ' ' -- $line)
    set files (math $files + $f[1]); set dirs (math $dirs + $f[2]); set empty (math $empty + $f[3])
    if test $f[4] -gt $depth
        set depth $f[4]
    end
    set ext_csv (math $ext_csv + $f[5]); set ext_dat (math $ext_dat + $f[6]); set ext_json (math $ext_json + $f[7])
    set ext_log (math $ext_log + $f[8]); set ext_txt (math $ext_txt + $f[9]); set csvlines (math $csvlines + $f[10])
end
wait
set j 0
while test $j -lt $i
    set j (math $j + 1)
    read -l aline < $TMPD/a$j.txt
    set -l a (string split ' ' -- $aline)
    set audit (math $audit + $a[3])
end
printf '%s ok\n' $IN >> $AUDITLOG
printf 'files=%s dirs=%s empty=%s depth=%s ext_csv=%s ext_dat=%s ext_json=%s ext_log=%s ext_txt=%s csvlines=%s audit=%s\n' \
    "$files" "$dirs" "$empty" "$depth" "$ext_csv" "$ext_dat" "$ext_json" "$ext_log" "$ext_txt" "$csvlines" "$audit" \
    | $SINK $OUT
