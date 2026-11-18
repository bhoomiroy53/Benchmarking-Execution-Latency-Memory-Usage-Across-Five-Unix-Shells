# Five Unix shell interpreters: latency, memory footprint and fault trapping

Reproduction package for the manuscript *Comparative Benchmarking of Execution Latency and
Memory Footprint Across Five Unix Command-Line Shell Interpreters Under System Automation
Workloads*. Every number in the manuscript, its tables and its figures comes from
`tables/Master_Verified_Results_Sheet.csv`, which `analyze` regenerates from the raw
telemetry in this folder.

## Contents

| Path | What it is |
|---|---|
| `run_unix_shell_benchmark.py` | Harness: environment capture, corpus generation, fault injection, execution, strace, GNU time cross-check, analysis entry point |
| `analysis_core.py` | Statistics: summaries, 95% confidence intervals, paired t and Wilcoxon tests with Holm correction, confusion matrices, ROC-AUC, Pareto frontier |
| `make_figures.py` | Renders Figures 1 to 5 from the analysis CSVs |
| `build_manuscript.py`, `results_text.py`, `manuscript_text.py`, `assemble_docx.py`, `docx_helpers.py` | Build the manuscript .docx and the table CSV/XLSX files from the analysis CSVs |
| `rusage_launcher.c` | Static measurement launcher (wait4 rusage; `--hwm` ptrace exit-stop VmHWM) |
| `package_supplementary.py` | Master results workbook with live Excel formulas, telemetry index, supplementary zip |
| `shell_workloads/posix/` | One POSIX source per workload and variant; run unchanged by bash, dash, zsh and ksh93 |
| `shell_workloads/fish/` | fish translations of the same eight scripts |
| `shell_workloads/helpers/` | Fixed external stages (`logsrc.sh`, `audit.sh`, `sink.sh`) executed by `/bin/dash` for every interpreter; they carry the fault-injection switches |
| `shell_workloads/awk/` | Batched aggregators used by Variant C |
| `shell_workloads/fish_signal_exit_reproducer.fish` | Minimal reproducer for the fish 4.2.1 behavior reported in the paper (exit status 0 after `exit 143` inside an `--on-signal` handler) |
| `environment_versions.json` | Kernel, CPU, memory, package revisions, SHA-256 of every interpreter binary and every workload script |
| `raw_telemetry_logs.json` | Index of the raw telemetry files and their SHA-256 checksums |
| `raw/` | `raw_runs.csv` (every execution), `startup_runs.csv`, `strace_counts.csv`, `timecheck.csv`, `manifest.json` (tasks, partitions, faults, expected outputs) |

## Reproduce on Linux

Tested on Ubuntu 26.04.1 LTS under WSL2 (kernel 6.18.58.1-microsoft-standard-WSL2). Run it as a
**non-root** user; permission-denied faults have no effect for root. Keep the work directory on
a native Linux filesystem, not on `/mnt/c`.

```bash
sudo apt-get install -y bash dash zsh ksh fish strace time gawk python3
python3 run_unix_shell_benchmark.py env          # environment_versions.json
python3 run_unix_shell_benchmark.py gen          # 2 x 1,250 tasks, seed 2026, 80:20 split
python3 run_unix_shell_benchmark.py check        # functional smoke test of all 40 configurations
python3 run_unix_shell_benchmark.py startup      # 200 start-up runs per interpreter
python3 run_unix_shell_benchmark.py run --partition eval            # seeds 42 101 202 303 404
python3 run_unix_shell_benchmark.py run --partition dev --seeds 42  # development partition
python3 run_unix_shell_benchmark.py strace
python3 run_unix_shell_benchmark.py timecheck
```

The work directory defaults to `~/cjcs_bench` (override with `--work` or `CJCS_WORK`).
`run` is resumable: it skips executions already in `results/raw_runs.csv`. On the reference
machine the evaluation partition (50,000 executions) took about 40 minutes.

## Recompute every statistic, table and figure (any OS)

Needs Python 3 with numpy, scipy, pandas, matplotlib, pillow, openpyxl and python-docx.
Do not run with `python -I`; the scripts import their sibling modules.

```bash
python run_unix_shell_benchmark.py analyze --results raw --out analysis
python make_figures.py analysis figures
python assemble_docx.py
python package_supplementary.py
```

## Measurement notes

Every execution is started through `rusage_launcher` (static C, `gcc -O2 -static`). The launcher forks, runs the
interpreter and calls `wait4()`. It reports wall-clock time from the monotonic clock, user and system CPU time in
microseconds, context switches and `ru_maxrss` (the peak RSS of the largest single process in the interpreter's
waited-for tree, called the "tree peak"). A launcher is needed because Linux carries the pre-exec address space's
peak RSS into the exec'd program. Spawning interpreters straight from the ~25 MB Python harness reported the
harness's memory instead. That first run was discarded and is not part of the package.

`rusage_launcher --hwm` (subcommand `shellmem`) traces the interpreter with ptrace exit and exec events only, and
reads `VmHWM` from `/proc/PID/status` at the exit stop: the interpreter's own peak RSS. It perturbs timing, so it
runs as a separate pass. The `--hwm` branch was added to the launcher after the timed executions. The timing branch
is unchanged, and the timed runs used a build of the earlier source, whose non-hwm code path is identical.

Run order on the reference machine (UTC, 2026-11-13):
- start-up timing;
- evaluation seeds 42 and part of 101 (interrupted by a harness restart);
- development partition (four parallel shards, `--shard i/4`, `CJCS_TAG` per process) and `shellmem`, in parallel;
- the rest of the evaluation partition, alone on the machine (`run` resumes and skips finished executions, keeping
  each seed's shuffled order);
- strace (one process per interpreter, `--shells`), then `timecheck`.

`raw_telemetry_logs.json` records the timeline and the checksum of every raw file.

Detection score per execution:
- 3: non-zero exit with the `BENCH-FAULT` diagnostic;
- 2: non-zero exit, including death by signal;
- 1: zero exit with diagnostics on stderr;
- 0: zero exit and silent.

A fault counts as trapped when the score is 2 or higher.

Rebuild the documents (Windows or Linux): `python make_figures.py ../analysis ../figures`, then
`python assemble_docx.py`, then `python package_supplementary.py`.
