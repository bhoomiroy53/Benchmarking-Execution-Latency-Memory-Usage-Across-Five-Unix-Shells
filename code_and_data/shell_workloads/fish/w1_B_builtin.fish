# Workload Suite 1, Variant B (fish translation): native built-ins only.
# read, switch, string and the math builtin; aggregation through variable
# indirection ($$name), mirroring the eval-based emulation of the POSIX source.
# Contract: IN OUT TMPD HELPER AWKDIR. No error handling by design.
set -gx BENCH_PID $fish_pid

set lines 0; set s2 0; set s3 0; set s4 0; set s5 0
set get 0; set post 0; set put 0; set del 0; set bytes 0; set maxlat 0
set r_auth 0; set r_items 0; set r_orders 0; set r_search 0; set r_users 0
$HELPER $IN | while read _ip _a _b _d _z meth path _p st by lat _rest
    set lines (math $lines + 1)
    switch $st
        case '2*'
            set s2 (math $s2 + 1)
        case '3*'
            set s3 (math $s3 + 1)
        case '4*'
            set s4 (math $s4 + 1)
        case '5*'
            set s5 (math $s5 + 1)
    end
    switch $meth
        case '"GET'
            set get (math $get + 1)
        case '"POST'
            set post (math $post + 1)
        case '"PUT'
            set put (math $put + 1)
        case '"DELETE'
            set del (math $del + 1)
    end
    set bytes (math $bytes + $by)
    if test $lat -gt $maxlat
        set maxlat $lat
    end
    set r (string replace -r '^/api/v1/([^/]*).*$' '$1' -- $path)
    switch $r
        case auth items orders search users
            set -l v r_$r
            set $v (math $$v + 1)
    end
end
printf 'lines=%s s2=%s s3=%s s4=%s s5=%s get=%s post=%s put=%s del=%s bytes=%s maxlat=%s r_auth=%s r_items=%s r_orders=%s r_search=%s r_users=%s\n' \
    "$lines" "$s2" "$s3" "$s4" "$s5" "$get" "$post" "$put" "$del" "$bytes" "$maxlat" \
    "$r_auth" "$r_items" "$r_orders" "$r_search" "$r_users" > $OUT
