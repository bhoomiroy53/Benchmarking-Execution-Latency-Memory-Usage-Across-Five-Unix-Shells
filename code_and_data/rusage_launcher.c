/*
 * rusage_launcher.c - minimal measurement launcher for run_unix_shell_benchmark.py
 *
 * Usage: rusage_launcher [--hwm] RESULT_FILE PROGRAM [ARGS...]
 *
 * Why it exists: Linux carries the pre-exec address space's peak RSS into the
 * ru_maxrss of the exec'd program. When a large parent (the Python harness,
 * ~25 MB) spawns an interpreter with posix_spawn/vfork, the interpreter's
 * reported peak RSS is the parent's. This launcher is a small static process:
 * it fork()s a child whose pre-exec image is only the launcher itself, execs
 * the target, and reports wait4() resource usage with microsecond precision.
 * ru_maxrss then is the peak RSS of the largest single process in the
 * interpreter's waited-for process tree ("tree peak").
 *
 * --hwm (separate measurement pass, not used for timing): the child is traced
 * with ptrace using only PTRACE_O_TRACEEXIT/TRACEEXEC. At the exit-stop, before
 * the kernel tears down the address space, the launcher reads VmHWM from
 * /proc/PID/status: the peak RSS of the interpreter process alone. Forked
 * children are not traced. Signals are re-injected unchanged.
 *
 * RESULT_FILE receives one line:
 *   wall_ns utime_us stime_us maxrss_kb nvcsw nivcsw raw_wait_status interp_hwm_kb tracee_execs
 * (interp_hwm_kb = -1 and tracee_execs = -1 without --hwm)
 * Build: gcc -O2 -static -o rusage_launcher rusage_launcher.c
 */
#define _GNU_SOURCE
#include <signal.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>
#include <unistd.h>
#include <sys/ptrace.h>
#include <sys/resource.h>
#include <sys/time.h>
#include <sys/types.h>
#include <sys/wait.h>

static long read_hwm(pid_t pid) {
    char path[64], line[256];
    snprintf(path, sizeof path, "/proc/%d/status", (int)pid);
    FILE *f = fopen(path, "r");
    if (!f) return -2;
    long kb = -3;
    while (fgets(line, sizeof line, f))
        if (strncmp(line, "VmHWM:", 6) == 0) { kb = strtol(line + 6, NULL, 10); break; }
    fclose(f);
    return kb;
}

int main(int argc, char **argv) {
    int hwm_mode = 0, a = 1;
    if (argc > 1 && strcmp(argv[1], "--hwm") == 0) { hwm_mode = 1; a = 2; }
    if (argc < a + 2) {
        fprintf(stderr, "usage: %s [--hwm] RESULT_FILE PROGRAM [ARGS...]\n", argv[0]);
        return 64;
    }
    const char *result = argv[a];
    char **prog = argv + a + 1;
    struct timespec t0, t1;
    clock_gettime(CLOCK_MONOTONIC, &t0);
    pid_t pid = fork();
    if (pid < 0) { perror("fork"); return 71; }
    if (pid == 0) {
        if (hwm_mode) ptrace(PTRACE_TRACEME, 0, NULL, NULL);
        execv(prog[0], prog);
        perror("execv");
        _exit(127);
    }
    int status = 0;
    struct rusage ru;
    long hwm = -1, execs = -1;
    if (!hwm_mode) {
        while (wait4(pid, &status, 0, &ru) < 0) { }
    } else {
        execs = 0;
        int first = 1;
        for (;;) {
            if (wait4(pid, &status, 0, &ru) < 0) continue;
            if (WIFEXITED(status) || WIFSIGNALED(status)) break;
            if (!WIFSTOPPED(status)) continue;
            int sig = WSTOPSIG(status), ev = status >> 16, inject = 0;
            if (first && sig == SIGTRAP) {              /* stop after the initial execve */
                first = 0;
                ptrace(PTRACE_SETOPTIONS, pid, NULL,
                       (void *)(long)(PTRACE_O_TRACEEXIT | PTRACE_O_TRACEEXEC | PTRACE_O_EXITKILL));
            } else if (sig == SIGTRAP && ev == PTRACE_EVENT_EXIT) {
                hwm = read_hwm(pid);
            } else if (sig == SIGTRAP && ev == PTRACE_EVENT_EXEC) {
                execs++;                                 /* interpreter replaced itself */
            } else {
                inject = sig;                            /* ordinary signal: deliver it */
            }
            ptrace(PTRACE_CONT, pid, NULL, (void *)(long)inject);
        }
    }
    clock_gettime(CLOCK_MONOTONIC, &t1);
    long long wall = (long long)(t1.tv_sec - t0.tv_sec) * 1000000000LL + (t1.tv_nsec - t0.tv_nsec);
    FILE *f = fopen(result, "w");
    if (!f) { perror("fopen"); return 73; }
    fprintf(f, "%lld %lld %lld %ld %ld %ld %d %ld %ld\n", wall,
            (long long)ru.ru_utime.tv_sec * 1000000LL + ru.ru_utime.tv_usec,
            (long long)ru.ru_stime.tv_sec * 1000000LL + ru.ru_stime.tv_usec,
            ru.ru_maxrss, ru.ru_nvcsw, ru.ru_nivcsw, status, hwm, execs);
    fclose(f);
    return 0;
}
