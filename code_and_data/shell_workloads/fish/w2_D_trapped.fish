# Workload Suite 2, Variant D (fish translation): validated, status-checked, signal-trapped.
# Contract: IN OUT TMPD HELPER SINK AUDITLOG AWKDIR.
set -gx BENCH_PID $fish_pid

function fail
    printf 'BENCH-FAULT %s\n' $argv[1] >&2
    if test -f $OUT
        rm -f $OUT
    end
    exit $argv[2]
end
function __bench_term --on-signal TERM
    fail "signal TERM" 143
end
function __bench_int --on-signal INT
    fail "signal INT" 130
end
function __bench_hup --on-signal HUP
    fail "signal HUP" 129
end

set -g files 0; set -g dirs 0; set -g empty 0; set -g depth 0; set -g csvlines 0; set -g audit 0
set -g ext_csv 0; set -g ext_dat 0; set -g ext_json 0; set -g ext_log 0; set -g ext_txt 0

function walk
    for e in $argv[1]/*
        if test -d $e
            if not test -r $e -a -x $e
                fail "unreadable directory $e" 66
            end
            set dirs (math $dirs + 1)
            walk $e (math $argv[2] + 1)
        else
            set files (math $files + 1)
            if test $argv[2] -gt $depth
                set depth $argv[2]
            end
            test -s $e; or set empty (math $empty + 1)
            switch $e
                case '*.csv'
                    set ext_csv (math $ext_csv + 1)
                    if not test -r $e
                        fail "unreadable file $e" 66
                    end
                    while read -l _l
                        set csvlines (math $csvlines + 1)
                    end < $e
                case '*.dat'
                    set ext_dat (math $ext_dat + 1)
                case '*.json'
                    set ext_json (math $ext_json + 1)
                case '*.log'
                    set ext_log (math $ext_log + 1)
                case '*.txt'
                    set ext_txt (math $ext_txt + 1)
            end
        end
    end
end

if not test -d "$IN" -a -r "$IN" -a -x "$IN"
    fail "input root missing or unreadable" 66
end
set i 0
for d in $IN/*
    test -d $d; or continue
    set i (math $i + 1)
    set r ($HELPER $d $i); or fail "audit helper failed for $d" 70
    string match -q 'ok *' -- $r; or fail "malformed audit output for $d" 70
    set -l n (string replace -r '^.* ' '' -- $r)
    string match -qr '^[0-9]+$' -- $n; or fail "malformed audit count for $d" 70
    set audit (math $audit + $n)
end
if test $i -eq 0
    fail "no subdirectories found under input root" 66
end
walk $IN 1
printf '%s ok\n' $IN >> $AUDITLOG; or fail "audit log write failed" 74
printf 'files=%s dirs=%s empty=%s depth=%s ext_csv=%s ext_dat=%s ext_json=%s ext_log=%s ext_txt=%s csvlines=%s audit=%s\n' \
    "$files" "$dirs" "$empty" "$depth" "$ext_csv" "$ext_dat" "$ext_json" "$ext_log" "$ext_txt" "$csvlines" "$audit" \
    | $SINK $OUT
or fail "report delivery to sink failed" 74
