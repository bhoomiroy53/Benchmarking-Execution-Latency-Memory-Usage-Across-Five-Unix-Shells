# Workload Suite 1, Variant A: external subshell and coreutils pipeline baseline.
# One POSIX source executed unchanged by bash, dash, zsh and ksh93.
# Contract (environment set by the harness): IN OUT TMPD HELPER AWKDIR
# No error handling by design: this is the unprotected baseline.
if [ -n "${ZSH_VERSION:-}" ]; then setopt SH_WORD_SPLIT NO_NOMATCH; fi
BENCH_PID=$$; export BENCH_PID

"$HELPER" "$IN" > "$TMPD/raw"
R="$TMPD/raw"
lines=$(wc -l < "$R" | tr -d ' ')
s2=$(cut -d' ' -f9 < "$R" | grep -c '^2')
s3=$(cut -d' ' -f9 < "$R" | grep -c '^3')
s4=$(cut -d' ' -f9 < "$R" | grep -c '^4')
s5=$(cut -d' ' -f9 < "$R" | grep -c '^5')
get=$(cut -d' ' -f6 < "$R" | tr -d '"' | grep -cx GET)
post=$(cut -d' ' -f6 < "$R" | tr -d '"' | grep -cx POST)
put=$(cut -d' ' -f6 < "$R" | tr -d '"' | grep -cx PUT)
del=$(cut -d' ' -f6 < "$R" | tr -d '"' | grep -cx DELETE)
bytes=$(cut -d' ' -f10 < "$R" | awk '{s += $1} END {print s + 0}')
maxlat=$(cut -d' ' -f11 < "$R" | sort -n | tail -n 1)
r_auth=$(cut -d' ' -f7 < "$R" | cut -d/ -f4 | grep -cx auth)
r_items=$(cut -d' ' -f7 < "$R" | cut -d/ -f4 | grep -cx items)
r_orders=$(cut -d' ' -f7 < "$R" | cut -d/ -f4 | grep -cx orders)
r_search=$(cut -d' ' -f7 < "$R" | cut -d/ -f4 | grep -cx search)
r_users=$(cut -d' ' -f7 < "$R" | cut -d/ -f4 | grep -cx users)
printf 'lines=%s s2=%s s3=%s s4=%s s5=%s get=%s post=%s put=%s del=%s bytes=%s maxlat=%s r_auth=%s r_items=%s r_orders=%s r_search=%s r_users=%s\n' \
  "$lines" "$s2" "$s3" "$s4" "$s5" "$get" "$post" "$put" "$del" "$bytes" "$maxlat" \
  "$r_auth" "$r_items" "$r_orders" "$r_search" "$r_users" > "$OUT"
