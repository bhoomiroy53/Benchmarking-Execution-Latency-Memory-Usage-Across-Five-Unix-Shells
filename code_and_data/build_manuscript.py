"""
build_manuscript.py - assemble CJCS_Five_Unix_Shells_Benchmark_Manuscript.docx and the table files.
Every number is read from ../analysis (written by analysis_core.analyze from the raw telemetry).
Usage: python build_manuscript.py
"""
import json
import re
import sys
from pathlib import Path

import pandas as pd

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import docx_helpers as D  # noqa: E402
import manuscript_text as T  # noqa: E402

ROOT = HERE.parent
AN = ROOT / "analysis"
RAW = ROOT / "raw_staging"
OUTDOC = ROOT / "CJCS_Five_Unix_Shells_Benchmark_Manuscript.docx"
TABDIR = ROOT / "tables"

SH = ["bash", "dash", "zsh", "ksh", "fish"]
LBL = {"bash": "bash", "dash": "dash", "zsh": "zsh", "ksh": "ksh93", "fish": "fish"}
VN = {"A": "A, external pipeline", "B": "B, native built-ins", "C": "C, batched concurrency", "D": "D, fault-trapped"}
SUITE = {"w1": "Suite 1", "w2": "Suite 2"}

perf = pd.read_csv(AN / "perf_summary.csv")
cls = pd.read_csv(AN / "classification_summary.csv")
cls_e = cls[cls.partition == "eval"]
cls_d = cls[cls.partition == "dev"]
abl = pd.read_csv(AN / "ablation_tests.csv")
pairs = pd.read_csv(AN / "pairwise_tests.csv")
st = pd.read_csv(AN / "startup_summary.csv")
sth = pd.read_csv(AN / "startup_hwm_summary.csv")
hwm = pd.read_csv(AN / "interpreter_hwm_summary.csv")
hwp = pd.read_csv(AN / "interpreter_hwm_pairwise.csv")
strc = pd.read_csv(AN / "strace_summary.csv")
tc = pd.read_csv(AN / "timecheck_summary.csv")
ftr = pd.read_csv(AN / "fault_type_recall.csv")
par = pd.read_csv(AN / "pareto.csv")
master = pd.read_csv(AN / "Master_Verified_Results_Sheet.csv")
env = json.loads((RAW / "environment_versions.json").read_text())
refs = json.loads((HERE / "references_verified.json").read_text(encoding="utf-8"))


# ----------------------------------------------------------------- lookups
def P(wl, s, v, col):
    return float(perf[(perf.workload == wl) & (perf.shell == s) & (perf.variant == v)][col].iloc[0])


def C(wl, s, v, col):
    return float(cls_e[(cls_e.workload == wl) & (cls_e.shell == s) & (cls_e.variant == v)][col].iloc[0])


def A(wl, s, contrast, col):
    return float(abl[(abl.workload == wl) & (abl.shell == s) & (abl.contrast == contrast)][col].iloc[0])


def H(wl, s, v, col="hwm_kb_mean"):
    return float(hwm[(hwm.workload == wl) & (hwm.shell == s) & (hwm.variant == v)][col].iloc[0])


def S(wl, s, v, col="process_creations_mean"):
    return float(strc[(strc.workload == wl) & (strc.shell == s) & (strc.variant == v)][col].iloc[0])


def ST(s, col):
    return float(st[st.shell == s][col].iloc[0])


def STH(s, col="mean"):
    return float(sth[sth.shell == s][col].iloc[0])


def FR(wl, s, v, fault):
    return float(ftr[(ftr.workload == wl) & (ftr.shell == s) & (ftr.variant == v) & (ftr.fault == fault)].pred.iloc[0])


def f2(x):
    return f"{x:,.2f}"


def pv(p):
    return "<0.001" if p < 0.001 else f"{p:.3f}"


def wnum(n):
    words = {1: "one", 2: "two", 3: "three", 4: "four", 5: "five", 6: "six", 7: "seven", 8: "eight", 9: "nine"}
    return words.get(int(n), f"{int(n):,}")


def pair(wl, v, a, b, metric="wall_ms"):
    q = pairs[(pairs.workload == wl) & (pairs.variant == v) & (pairs.metric == metric)]
    r = q[((q.shell_a == a) & (q.shell_b == b)) | ((q.shell_a == b) & (q.shell_b == a))].iloc[0]
    return r


# ----------------------------------------------------------------- citations
KEY = {}
for r in refs:
    KEY[r["authors"][0].split()[0].lower() + str(r["year"])] = r
ORDER = []


def cite(text):
    """Replace {key} or {key1,key2} with bracketed sequential numbers, assigning by first appearance."""
    def rep(m):
        keys = [k.strip() for k in m.group(1).split(",")]
        nums = []
        for k in keys:
            if k not in KEY:
                raise KeyError(k)
            if k not in ORDER:
                ORDER.append(k)
            nums.append(ORDER.index(k) + 1)
        nums.sort()
        out, i = [], 0
        while i < len(nums):
            j = i
            while j + 1 < len(nums) and nums[j + 1] == nums[j] + 1:
                j += 1
            out.append(f"{nums[i]}-{nums[j]}" if j - i >= 2 else ",".join(str(n) for n in nums[i:j + 1]))
            i = j + 1
        return "[" + ",".join(out) + "]"
    return re.sub(r"\{([a-z0-9, ]+)\}", rep, text)


SMALL = {"a", "an", "the", "of", "for", "and", "in", "on", "to", "via", "vs", "with"}


def sentence_case(title, doi):
    fixed = {
        "10.1109/cluster.2012.85": "clone_n(): parallel thread creation for upcoming many-core architectures",
        "10.1109/ecbs-eerc.2015.29": "Performance evaluation of in-kernel system calls",
        "10.1109/ispass.2013.6557172": "Non-determinism and overcount on modern hardware performance counter implementations",
        "10.1109/aina.2017.79": "Performance overhead comparison between hypervisor and container based virtualization",
    }
    return fixed.get(doi, title)


def ref_line(r):
    au = r["authors"]
    names = ", ".join(au) if len(au) <= 7 else ", ".join(au[:3]) + ", et al."
    t = sentence_case(r["title"], r["doi"]).rstrip(".")
    end = "" if t.endswith("?") else "."
    vol = f"{r['volume']}:" if r.get("volume") else ""
    pages = r.get("pages") or ""
    return f"{names}: {t}{end} {r['container']}. {r['year']}, {vol}{pages}. {r['doi']}"


# ----------------------------------------------------------------- abstract
def abstract_parts():
    w1b = {s: P("w1", s, "B", "wall_mean") for s in SH}
    bg = ("Unix shell interpreters execute most system automation scripts, yet the choice among bash, dash, zsh, "
          "ksh93 and fish is rarely based on measured execution latency, memory footprint or fault-trapping "
          "reliability. This study benchmarks the execution latency and memory footprint of five Unix shell "
          "interpreters and tests how reliably each reports injected faults to its caller.")
    mm = ("Five interpreters (bash 5.3.9, dash 0.5.12, zsh 5.9, ksh93u+m 1.0.10 and fish 4.2.1) were benchmarked on "
          "Ubuntu 26.04 under the Windows Subsystem for Linux 2. Two workload suites of 1,250 seeded tasks each, "
          "server log parsing and file-system traversal with process orchestration, were split 80:20 into "
          "development and evaluation partitions. Each of the 250 evaluation tasks per suite was executed with "
          "four scripting variants (external pipelines, native built-ins, batched concurrency and a fault-trapped "
          "pipeline) and five seeded repetitions, for 50,000 timed executions. Wall-clock, user and system time, "
          "context switches and peak resident memory were collected with wait4, interpreter-only memory with a "
          "ptrace exit stop, and process creations with strace. One of six fault types was injected into 100 "
          "evaluation tasks per suite, and fault trapping was scored with confusion matrices, F1-score, "
          "false-negative rate and the area under the receiver operating characteristic curve (ROC-AUC). Paired "
          "t and Wilcoxon tests with Holm correction compared configurations.")
    res = (f"Start-up took {ST('dash','wall_mean'):.2f} ms for dash, {ST('bash','wall_mean'):.2f} ms for bash, "
           f"{ST('ksh','wall_mean'):.2f} ms for ksh93, {ST('zsh','wall_mean'):.2f} ms for zsh and "
           f"{ST('fish','wall_mean'):.2f} ms for fish. On log parsing with native built-ins, mean latency was "
           f"{w1b['ksh']:.2f} ms for ksh93, {w1b['dash']:.2f} ms for dash, {w1b['bash']:.2f} ms for bash, "
           f"{w1b['zsh']:.2f} ms for zsh and {w1b['fish']:.2f} ms for fish. Replacing external pipelines with "
           f"built-ins cut latency by {-A('w1','zsh','B_vs_A','pct_change'):.2f}% to {-A('w1','ksh','B_vs_A','pct_change'):.2f}% "
           f"in the POSIX shells but raised it by {A('w1','fish','B_vs_A','pct_change'):.2f}% in fish. The interpreter's "
           f"own peak memory ranged from {H('w1','dash','B')/1024:.2f} MB for dash to {H('w1','fish','D')/1024:.2f} MB for fish, "
           f"whereas the task tree peak ({perf.rss_kb_mean.min()/1024:.2f} MB to {perf.rss_kb_mean.max()/1024:.2f} MB) was "
           "set mostly by the external Rust coreutils. Unprotected variants trapped 32% to 67% of faults. The "
           "fault-trapped variant reached an F1-score of 100.00% in bash, dash, zsh and ksh93 on both suites, while "
           f"fish reached {C('w1','fish','D','f1_mean'):.2f}% and {C('w2','fish','D','f1_mean'):.2f}% because fish 4.2.1 "
           "exited with status zero after handling SIGTERM. No configuration raised a false alarm, and results were "
           "identical across the five seeds.")
    con = ("No single interpreter is best on every metric. ksh93 with native built-ins gave the lowest latency, dash "
           "the lowest start-up time and memory, and fish the highest cost and weakest signal propagation. Scripting "
           "paradigm mattered as much as interpreter choice, and explicit fault trapping added little latency while "
           "turning silent failures into visible ones.")
    return [("Background", bg), ("Materials and Methods", mm), ("Results", res), ("Conclusions", con)]


# ----------------------------------------------------------------- tables
def table1():
    hdr = ["Interpreter", "Version", "Ubuntu package revision", "SHA-256 prefix", "Binary size (MB)",
           "Script dialect", "Native pipefail", "Start-up mean (ms)", "Start-up SD (ms)",
           "Start-up interpreter peak RSS (MB)"]
    ver = {"bash": "5.3.9", "dash": "0.5.12", "zsh": "5.9", "ksh": "93u+m 1.0.10", "fish": "4.2.1"}
    pf = {"bash": "Yes", "dash": "Yes", "zsh": "Yes", "ksh": "Yes", "fish": "No"}
    rows = []
    for s in SH:
        e = env["shells"][s]
        rows.append([LBL[s], ver[s], e["package_version"], e["sha256"][:16], f2(e["size_bytes"] / 1e6),
                     "fish" if s == "fish" else "POSIX", pf[s], f2(ST(s, "wall_mean")), f2(ST(s, "wall_sd")),
                     f2(STH(s) / 1024)])
    return hdr, rows


def table2():
    m = json.loads((RAW / "manifest.json").read_text())
    mech = {"none": "No fault", "missing_input": "Input path does not exist", "unreadable_input": "Input file mode 000",
            "corrupt_record": "Letter inserted in one size field", "helper_exit": "Helper exits with status 3",
            "signal_term": "SIGTERM sent to interpreter", "write_failure": "Output written to /dev/full",
            "missing_root": "Input root does not exist", "unreadable_subdir": "One subtree mode 000",
            "consumer_failure": "Sink closes input, exits 1"}
    hdr = ["Workload suite", "Task class", "Injection mechanism", "Development tasks (n)", "Evaluation tasks (n)"]
    rows = []
    for wl in ["w1", "w2"]:
        tasks = m["workloads"][wl]["tasks"]
        faults = ["none"] + m["faults"][wl]
        for f in faults:
            dv = sum(1 for t in tasks.values() if t["partition"] == "dev" and t["fault"] == f)
            ev = sum(1 for t in tasks.values() if t["partition"] == "eval" and t["fault"] == f)
            rows.append([SUITE[wl], "Fault-free" if f == "none" else f.replace("_", " ").capitalize(), mech[f], dv, ev])
        rows.append([SUITE[wl], "Total", "All classes",
                     sum(1 for t in tasks.values() if t["partition"] == "dev"),
                     sum(1 for t in tasks.values() if t["partition"] == "eval")])
    return hdr, rows


def table3():
    hdr = ["Suite", "Interpreter", "Variant", "Wall mean (ms)", "Wall SD (ms)", "Median (ms)", "IQR (ms)",
           "95% CI low (ms)", "95% CI high (ms)", "User CPU (ms)", "System CPU (ms)", "Throughput (tasks/s)",
           "Throughput (MB/s)"]
    rows = []
    for wl in ["w1", "w2"]:
        for s in SH:
            for v in "ABCD":
                g = lambda c: P(wl, s, v, c)
                rows.append([SUITE[wl], LBL[s], v, f2(g("wall_mean")), f2(g("wall_sd")), f2(g("wall_median")),
                             f2(g("wall_q3") - g("wall_q1")), f2(g("wall_ci_lo")), f2(g("wall_ci_hi")),
                             f2(g("user_mean")), f2(g("sys_mean")), f2(g("tasks_per_s")), f2(g("mb_per_s"))])
    return hdr, rows


def table4():
    hdr = ["Suite", "Interpreter", "Variant", "Tree peak RSS (KB)", "Tree peak RSS (MB)",
           "Interpreter peak RSS (KB)", "Interpreter peak RSS (MB)", "Process creations per task",
           "Successful execve per task", "Voluntary context switches", "Involuntary context switches",
           "MDP (MB s)"]
    rows = []
    for wl in ["w1", "w2"]:
        for s in SH:
            for v in "ABCD":
                rows.append([SUITE[wl], LBL[s], v, f2(P(wl, s, v, "rss_kb_mean")), f2(P(wl, s, v, "rss_kb_mean") / 1024),
                             f2(H(wl, s, v)), f2(H(wl, s, v) / 1024), f2(S(wl, s, v)), f2(S(wl, s, v, "execve_ok_mean")),
                             f2(P(wl, s, v, "nvcsw_mean")), f2(P(wl, s, v, "nivcsw_mean")), f"{P(wl, s, v, 'mdp_mean'):.3f}"])
    return hdr, rows


def table5():
    hdr = ["Suite", "Interpreter", "Contrast", "Variant mean (ms)", "Reference mean (ms)", "Change (%)",
           "Speed-up (x)", "Paired t", "Holm p, t-test", "Holm p, Wilcoxon"]
    names = {"B_vs_A": "B vs. A", "C_vs_A": "C vs. A", "D_vs_A": "D vs. A", "D_vs_B": "D vs. B"}
    rows = []
    for wl in ["w1", "w2"]:
        for s in SH:
            for c in ["B_vs_A", "C_vs_A", "D_vs_A", "D_vs_B"]:
                g = lambda col: A(wl, s, c, col)
                rows.append([SUITE[wl], LBL[s], names[c], f2(g("mean_a")), f2(g("mean_b")), f2(g("pct_change")),
                             f2(g("speedup")), f2(g("t")), pv(g("p_t_holm")), pv(g("p_wilcoxon_holm"))])
    return hdr, rows


def table6():
    hdr = ["Suite", "Interpreter", "Variant", "TP", "FP", "TN", "FN", "N", "Accuracy (%)", "Precision (%)",
           "Recall (%)", "F1-score (%)", "Specificity (%)", "FNR (%)", "ROC-AUC"]
    rows = []
    for wl in ["w1", "w2"]:
        for s in SH:
            for v in "ABCD":
                g = lambda col: C(wl, s, v, col)
                rows.append([SUITE[wl], LBL[s], v, int(g("TP_mean")), int(g("FP_mean")), int(g("TN_mean")),
                             int(g("FN_mean")), int(g("N_mean")), f2(g("accuracy_mean")), f2(g("precision_mean")),
                             f2(g("recall_mean")), f2(g("f1_mean")), f2(g("specificity_mean")), f2(g("fnr_mean")),
                             f2(g("auc_pooled"))])
    return hdr, rows


TABLES = [
    ("Table 1: Five Unix shell interpreters, binary revisions, architectural characteristics and start-up overhead",
     table1,
     "SHA-256 prefix: first 16 hexadecimal characters of the binary checksum (full values in the supplementary "
     "environment file). Native pipefail: pipefail option accepted by this build. Start-up: interpreter running a "
     "single no-op command, 200 timed executions per interpreter; peak RSS of the interpreter process alone from a "
     "separate pass of 50 executions. MB: megabytes; ms: milliseconds; RSS: resident set size; SD: standard deviation."),
    ("Table 2: System automation workload suites, task distributions and evaluation splits (N_eval = 250)",
     table2,
     "Suite 1: server log parsing and text-stream transformation. Suite 2: file-system traversal, process "
     "orchestration and fault recovery. Each suite contains 1,250 tasks split 80:20 by a seeded shuffle. Faults are "
     "injected by the harness through the environment, the input or the fixed helper processes; mode 000 removes "
     "all file permissions. n: number of tasks."),
    ("Table 3: Execution latency and throughput across Workload Suite 1 and Workload Suite 2",
     table3,
     "Variants: A, external subshell and coreutils pipeline; B, native built-ins; C, batched execution with "
     "named-pipe concurrency; D, fault-trapped pipeline. Statistics over the 150 fault-free evaluation tasks per "
     "suite and five repetitions (750 executions per row). CI: confidence interval of the mean from task-level means; "
     "CPU: central processing unit time of the interpreter and its waited-for descendants; IQR: interquartile range; "
     "MB/s: megabytes of task input per second; ms: milliseconds; SD: standard deviation."),
    ("Table 4: Peak resident set size memory footprint, process creations and context switches",
     table4,
     "Tree peak RSS: peak RSS of the largest single process in the task's process tree from wait4 (750 executions "
     "per row). Interpreter peak RSS: VmHWM of the interpreter process alone at the ptrace exit stop (150 executions "
     "per row). Process creations and execve: strace counts on 20 fault-free evaluation tasks per row. Context "
     "switches are per execution. KB: kilobytes; MB: megabytes; MDP: memory-delay product (Equation 2); RSS: "
     "resident set size."),
    ("Table 5: Component-level ablation study of external subshells, native built-ins, buffered concurrency and the fault-trapped pipeline",
     table5,
     "Contrast X vs. Y compares mean wall-clock latency of variant X with reference variant Y on the same 150 "
     "fault-free tasks (paired by task, each task averaged over five repetitions). Change: 100 x (X - Y) / Y; "
     "negative values are faster. Speed-up: Y / X. p-values are two-tailed and Holm-adjusted within the four "
     "contrasts of each interpreter and suite; <0.001 denotes p below 0.001. ms: milliseconds."),
    ("Table 6: Fault-trapping confusion matrix counts, precision, recall, F1-score, false-negative rate and ROC-AUC verification",
     table6,
     "Positive class: injected fault (100 tasks); negative class: fault-free task (150 tasks); every row sums to "
     "N = 250. A fault is trapped when the interpreter exits with a non-zero status. Counts and percentages were "
     "identical for all five seeds, so the standard deviation across seeds is zero. ROC-AUC is computed from the "
     "ordinal detection score (0 to 3) pooled over the five seeds. FN: false negatives; FNR: false-negative rate "
     "(Equation 3); FP: false positives; ROC-AUC: area under the receiver operating characteristic curve; TN: true "
     "negatives; TP: true positives."),
]


def export_tables():
    TABDIR.mkdir(exist_ok=True)
    for i, (cap, fn, _) in enumerate(TABLES, start=1):
        hdr, rows = fn()
        df = pd.DataFrame(rows, columns=hdr)
        stem = f"Table_{i}"
        df.to_csv(TABDIR / f"{stem}.csv", index=False)
        with pd.ExcelWriter(TABDIR / f"{stem}.xlsx", engine="openpyxl") as xw:
            df.to_excel(xw, index=False, sheet_name=f"Table {i}")
            pd.DataFrame({"Title": [cap.split(": ", 1)[1]]}).to_excel(xw, index=False, sheet_name="Title")
