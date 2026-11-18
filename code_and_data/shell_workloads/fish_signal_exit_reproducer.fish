function h --on-signal TERM
    echo "handler start" >&2
    exit 143
end
kill -TERM $fish_pid
sleep 0.2
echo "after kill, still running" >&2
command sleep 0.2
echo "end of script" >&2
