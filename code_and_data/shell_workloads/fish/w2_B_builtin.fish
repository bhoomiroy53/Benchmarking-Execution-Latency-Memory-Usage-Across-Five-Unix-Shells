# Workload Suite 2, Variant B (fish translation): native built-ins only.
# Contract: IN OUT TMPD HELPER SINK AUDITLOG AWKDIR. No error handling by design.
set -gx BENCH_PID $fish_pid

set -g files 0; set -g dirs 0; set -g empty 0; set -g depth 0; set -g csvlines 0; set -g audit 0
set -g ext_csv 0; set -g ext_dat 0; set -g ext_json 0; set -g ext_log 0; set -g ext_txt 0

function walk
    for e in $argv[1]/*
        if test -d $e
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

set i 0
for d in $IN/*
    test -d $d; or continue
    set i (math $i + 1)
    set r ($HELPER $d $i)
    set audit (math $audit + (string replace -r '^.* ' '' -- $r))
end
walk $IN 1
printf '%s ok\n' $IN >> $AUDITLOG
printf 'files=%s dirs=%s empty=%s depth=%s ext_csv=%s ext_dat=%s ext_json=%s ext_log=%s ext_txt=%s csvlines=%s audit=%s\n' \
    "$files" "$dirs" "$empty" "$depth" "$ext_csv" "$ext_dat" "$ext_json" "$ext_log" "$ext_txt" "$csvlines" "$audit" \
    | $SINK $OUT
