"""
analysis_core.py - statistical verification for run_unix_shell_benchmark.py.

Reads the raw telemetry produced on Linux (raw_runs.csv, startup_runs.csv,
strace_counts.csv, timecheck.csv) and writes every derived quantity used in the
manuscript to one long-format file, Master_Verified_Results_Sheet.csv, plus
helper CSVs consumed by make_figures.py and build_manuscript.py.

Definitions (match the manuscript equations):
  T_res  = T_wall - (T_user + T_sys)                       (residual / off-CPU time, Eq. 1)
  MDP    = RSS_MB * T_wall_s                                (memory-delay product, Eq. 2)
  FNR    = FN / (TP + FN)                                   (Eq. 3)
  t      = mean(d) / (sd(d) / sqrt(n)),  d = paired task-level differences  (Eq. 4)
  detection score s: 3 = non-zero exit with BENCH-FAULT diagnostic, 2 = non-zero exit
  (including death by signal or watchdog), 1 = zero exit with stderr output,
  0 = zero exit and silent.  Predicted positive (fault trapped) <=> s >= 2.
"""
from itertools import combinations
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats

SHELLS = ["bash", "dash", "zsh", "ksh", "fish"]
VARIANTS = ["A", "B", "C", "D"]
WORKLOADS = ["w1", "w2"]


def holm(pvals):
    p = np.asarray(pvals, dtype=float)
    order = np.argsort(p)
    m = len(p)
    adj = np.empty(m)
    running = 0.0
    for rank, idx in enumerate(order):
        running = max(running, min(1.0, (m - rank) * p[idx]))
        adj[idx] = running
    return adj


def score_frame(df):
    nonzero = df["exit_code"] != 0
    s = np.where(nonzero & (df["fault_marker"] == 1), 3,
        np.where(nonzero, 2, np.where(df["stderr_bytes"] > 0, 1, 0)))
    df = df.copy()
    df["score"] = s
    df["pred"] = (s >= 2).astype(int)
    return df


def auc_from_scores(y, s):
    y = np.asarray(y)
    s = np.asarray(s, dtype=float)
    pos, neg = s[y == 1], s[y == 0]
    if len(pos) == 0 or len(neg) == 0:
        return float("nan")
    gt = (pos[:, None] > neg[None, :]).sum()
    eq = (pos[:, None] == neg[None, :]).sum()
    return float((gt + 0.5 * eq) / (len(pos) * len(neg)))


def roc_points(y, s):
    y = np.asarray(y)
    s = np.asarray(s)
    pts = []
    for th in [4, 3, 2, 1, 0]:
        pred = s >= th
        tp = int(((pred) & (y == 1)).sum()); fn = int(((~pred) & (y == 1)).sum())
        fp = int(((pred) & (y == 0)).sum()); tn = int(((~pred) & (y == 0)).sum())
        pts.append({"threshold": th, "tpr": tp / max(tp + fn, 1), "fpr": fp / max(fp + tn, 1)})
    return pts


def cls_metrics(y, pred):
    y = np.asarray(y); pred = np.asarray(pred)
    tp = int(((pred == 1) & (y == 1)).sum()); fn = int(((pred == 0) & (y == 1)).sum())
    fp = int(((pred == 1) & (y == 0)).sum()); tn = int(((pred == 0) & (y == 0)).sum())
    n = tp + fn + fp + tn
    prec = tp / (tp + fp) if tp + fp else float("nan")
    rec = tp / (tp + fn) if tp + fn else float("nan")
    f1 = 2 * prec * rec / (prec + rec) if (tp + fp) and (tp + fn) and (prec + rec) else 0.0
    return {"TP": tp, "FP": fp, "TN": tn, "FN": fn, "N": n,
            "accuracy": 100 * (tp + tn) / n, "precision": 100 * prec if prec == prec else float("nan"),
            "recall": 100 * rec, "f1": 100 * f1,
            "specificity": 100 * tn / (tn + fp) if tn + fp else float("nan"),
            "fpr": 100 * fp / (fp + tn) if fp + tn else float("nan"),
            "fnr": 100 * fn / (tp + fn) if tp + fn else float("nan")}


def ci95(x):
    x = np.asarray(x, dtype=float)
    n = len(x)
    m = x.mean()
    h = stats.t.ppf(0.975, n - 1) * x.std(ddof=1) / np.sqrt(n) if n > 1 else float("nan")
    return m - h, m + h


def analyze(results_dir, out_dir):
    results_dir, out_dir = Path(results_dir), Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    parts = [results_dir / "raw_runs.csv"] + sorted(results_dir.glob("raw_runs_dev_shard*.csv"))
    raw = pd.concat([pd.read_csv(p) for p in parts if p.exists()], ignore_index=True)
    raw = score_frame(raw)
    raw["res_ms"] = raw["wall_ms"] - raw["user_ms"] - raw["sys_ms"]
    raw["rss_mb"] = raw["maxrss_kb"] / 1024.0
    raw["mdp"] = raw["rss_mb"] * raw["wall_ms"] / 1000.0
    master = []

    def put(section, metric, value, unit="", workload="", shell="", variant="", n="", note=""):
        master.append({"section": section, "workload": workload, "shell": shell, "variant": variant,
                       "metric": metric, "value": value, "unit": unit, "n": n, "note": note})

    ev = raw[raw.partition == "eval"]
    dev = raw[raw.partition == "dev"]

    # ---------------- run accounting
    for part, d in [("eval", ev), ("dev", dev)]:
        put("accounting", f"runs_{part}", len(d), "runs")
        put("accounting", f"timeouts_{part}", int(d.timed_out.sum()), "runs")
    for wl in WORKLOADS:
        e = ev[(ev.workload == wl) & (ev.shell == "bash") & (ev.variant == "A") & (ev.seed == ev.seed.min())]
        put("accounting", "eval_tasks", e.task.nunique(), "tasks", wl)
        put("accounting", "eval_faulty_tasks", int(e.is_faulty.sum()), "tasks", wl)
        put("accounting", "eval_valid_tasks", int((1 - e.is_faulty).sum()), "tasks", wl)
        for f, c in e.groupby("fault").size().items():
            put("accounting", f"eval_fault_{f}", int(c), "tasks", wl)
        dd = dev[(dev.workload == wl) & (dev.shell == "bash") & (dev.variant == "A")]
        put("accounting", "dev_tasks", dd.task.nunique(), "tasks", wl)

    # ---------------- performance on fault-free evaluation tasks
    valid = ev[ev.is_faulty == 0]
    perf_rows = []
    taskmeans = {}
    for (wl, sh, v), g in valid.groupby(["workload", "shell", "variant"]):
        tm = g.groupby("task")[["wall_ms", "user_ms", "sys_ms", "maxrss_kb", "nvcsw", "nivcsw", "res_ms"]].mean()
        taskmeans[(wl, sh, v)] = tm
        rep = g.groupby("seed")["wall_ms"].mean()
        lo, hi = ci95(tm["wall_ms"])
        row = {"workload": wl, "shell": sh, "variant": v, "n_runs": len(g), "n_tasks": len(tm),
               "wall_mean": g.wall_ms.mean(), "wall_sd": g.wall_ms.std(ddof=1), "wall_median": g.wall_ms.median(),
               "wall_q1": g.wall_ms.quantile(.25), "wall_q3": g.wall_ms.quantile(.75),
               "wall_ci_lo": lo, "wall_ci_hi": hi, "wall_between_rep_sd": rep.std(ddof=1),
               "user_mean": g.user_ms.mean(), "user_sd": g.user_ms.std(ddof=1),
               "sys_mean": g.sys_ms.mean(), "sys_sd": g.sys_ms.std(ddof=1),
               "res_mean": g.res_ms.mean(), "res_sd": g.res_ms.std(ddof=1),
               "rss_kb_mean": g.maxrss_kb.mean(), "rss_kb_sd": g.maxrss_kb.std(ddof=1),
               "rss_mb_mean": g.rss_mb.mean(), "mdp_mean": g.mdp.mean(), "mdp_sd": g.mdp.std(ddof=1),
               "nvcsw_mean": g.nvcsw.mean(), "nivcsw_mean": g.nivcsw.mean(),
               "tasks_per_s": 1000.0 / g.wall_ms.mean(),
               "mb_per_s": (g.in_bytes.mean() / 1e6) / (g.wall_ms.mean() / 1000.0),
               "correct_rate": 100 * g.out_correct.astype(float).mean()}
        perf_rows.append(row)
        for k, val in row.items():
            if k not in ("workload", "shell", "variant"):
                put("performance", k, val, "", wl, sh, v, len(g))
    perf = pd.DataFrame(perf_rows)
    perf.to_csv(out_dir / "perf_summary.csv", index=False)

    # ---------------- pairwise cross-interpreter tests (paired by task)
    pair_rows = []
    for wl in WORKLOADS:
        for v in VARIANTS:
            for metric in ["wall_ms", "maxrss_kb"]:
                fam = []
                for a, b in combinations(SHELLS, 2):
                    xa, xb = taskmeans[(wl, a, v)][metric], taskmeans[(wl, b, v)][metric]
                    idx = xa.index.intersection(xb.index)
                    d = (xa[idx] - xb[idx]).values
                    t, p_t = stats.ttest_rel(xa[idx], xb[idx])
                    try:
                        _, p_w = stats.wilcoxon(xa[idx], xb[idx])
                    except ValueError:
                        p_w = float("nan")
                    lo, hi = ci95(d)
                    fam.append({"workload": wl, "variant": v, "metric": metric, "shell_a": a, "shell_b": b,
                                "n_tasks": len(idx), "mean_a": xa[idx].mean(), "mean_b": xb[idx].mean(),
                                "mean_diff": d.mean(), "diff_ci_lo": lo, "diff_ci_hi": hi,
                                "t": t, "p_t": p_t, "p_wilcoxon": p_w})
                adj_t = holm([r["p_t"] for r in fam]); adj_w = holm([r["p_wilcoxon"] for r in fam])
                for r, at, aw in zip(fam, adj_t, adj_w):
                    r["p_t_holm"], r["p_wilcoxon_holm"] = at, aw
                pair_rows += fam
    pairs = pd.DataFrame(pair_rows)
    pairs.to_csv(out_dir / "pairwise_tests.csv", index=False)
    for r in pair_rows:
        tag = f"{r['shell_a']}_vs_{r['shell_b']}"
        for k in ["mean_diff", "t", "p_t", "p_wilcoxon", "p_t_holm", "p_wilcoxon_holm"]:
            put("pairwise", f"{r['metric']}:{tag}:{k}", r[k], "", r["workload"], "", r["variant"], r["n_tasks"])

    # ---------------- component-level ablation tests (paired by task, within shell)
    abl_rows = []
    for wl in WORKLOADS:
        for sh in SHELLS:
            fam = []
            for a, b in [("B", "A"), ("C", "A"), ("D", "A"), ("D", "B")]:
                xa, xb = taskmeans[(wl, sh, a)]["wall_ms"], taskmeans[(wl, sh, b)]["wall_ms"]
                idx = xa.index.intersection(xb.index)
                t, p_t = stats.ttest_rel(xa[idx], xb[idx])
                try:
                    _, p_w = stats.wilcoxon(xa[idx], xb[idx])
                except ValueError:
                    p_w = float("nan")
                fam.append({"workload": wl, "shell": sh, "contrast": f"{a}_vs_{b}", "n_tasks": len(idx),
                            "mean_a": xa[idx].mean(), "mean_b": xb[idx].mean(),
                            "pct_change": 100 * (xa[idx].mean() - xb[idx].mean()) / xb[idx].mean(),
                            "speedup": xb[idx].mean() / xa[idx].mean(), "t": t, "p_t": p_t, "p_wilcoxon": p_w})
            for r, at, aw in zip(fam, holm([r["p_t"] for r in fam]), holm([r["p_wilcoxon"] for r in fam])):
                r["p_t_holm"], r["p_wilcoxon_holm"] = at, aw
            abl_rows += fam
    abl = pd.DataFrame(abl_rows)
    abl.to_csv(out_dir / "ablation_tests.csv", index=False)
    for r in abl_rows:
        for k in ["pct_change", "speedup", "t", "p_t", "p_wilcoxon", "p_t_holm", "p_wilcoxon_holm"]:
            put("ablation", f"{r['contrast']}:{k}", r[k], "", r["workload"], r["shell"], "", r["n_tasks"])

    # ---------------- fault-trapping classification
    cls_rows, cls_seed_rows, roc_rows = [], [], []
    for part, d in [("eval", ev), ("dev", dev)]:
        for (wl, sh, v), g in d.groupby(["workload", "shell", "variant"]):
            per_seed = []
            for seed, gs in g.groupby("seed"):
                mtr = cls_metrics(gs.is_faulty, gs.pred)
                mtr["auc"] = auc_from_scores(gs.is_faulty, gs.score)
                mtr.update({"partition": part, "workload": wl, "shell": sh, "variant": v, "seed": seed})
                per_seed.append(mtr)
                cls_seed_rows.append(mtr)
            ps = pd.DataFrame(per_seed)
            row = {"partition": part, "workload": wl, "shell": sh, "variant": v, "n_seeds": len(ps)}
            for k in ["TP", "FP", "TN", "FN", "N", "accuracy", "precision", "recall", "f1", "specificity", "fpr", "fnr", "auc"]:
                row[f"{k}_mean"] = ps[k].mean()
                row[f"{k}_sd"] = ps[k].std(ddof=1) if len(ps) > 1 else 0.0
            row["auc_pooled"] = auc_from_scores(g.is_faulty, g.score)
            row["identical_across_seeds"] = int(all(ps[k].nunique() == 1 for k in ["TP", "FP", "TN", "FN"]))
            cls_rows.append(row)
            if part == "eval":
                for pt in roc_points(g.is_faulty, g.score):
                    pt.update({"workload": wl, "shell": sh, "variant": v})
                    roc_rows.append(pt)
                for k, val in row.items():
                    if k not in ("partition", "workload", "shell", "variant"):
                        put("classification", k, val, "", wl, sh, v, int(row["N_mean"]))
                # per fault type detection rate (pooled over seeds)
                for f, gf in g[g.is_faulty == 1].groupby("fault"):
                    put("fault_type_recall", f"recall_{f}", 100 * gf.pred.mean(), "%", wl, sh, v, len(gf))
                put("fault_type_fpr", "valid_false_alarm_rate", 100 * g[g.is_faulty == 0].pred.mean(), "%", wl, sh, v,
                    int((g.is_faulty == 0).sum()))
    pd.DataFrame(cls_rows).to_csv(out_dir / "classification_summary.csv", index=False)
    pd.DataFrame(cls_seed_rows).to_csv(out_dir / "classification_per_seed.csv", index=False)
    pd.DataFrame(roc_rows).to_csv(out_dir / "roc_points.csv", index=False)
    ft = ev[ev.is_faulty == 1].groupby(["workload", "shell", "variant", "fault"])["pred"].mean().mul(100).reset_index()
    ft.to_csv(out_dir / "fault_type_recall.csv", index=False)
    # residual-artifact (rollback) rate: faulty runs that left a regular output file behind
    rb = ev[ev.is_faulty == 1].groupby(["workload", "shell", "variant"])["out_exists"].mean().mul(100).reset_index()
    rb.to_csv(out_dir / "residual_output_rate.csv", index=False)
    for _, r in rb.iterrows():
        put("rollback", "faulty_runs_leaving_output_pct", r.out_exists, "%", r.workload, r.shell, r.variant)

    # ---------------- development (validation) partition functional verification
    dv = dev[dev.is_faulty == 0] if len(dev) else dev.iloc[0:0]
    if not len(dv):
        dv = pd.DataFrame(columns=["workload", "shell", "variant", "out_correct"])
    dv = dv.groupby(["workload", "shell", "variant"])["out_correct"].apply(
        lambda s: 100 * s.astype(float).mean()).reset_index()
    dv.to_csv(out_dir / "dev_correctness.csv", index=False)
    for _, r in dv.iterrows():
        put("dev_verification", "valid_output_correct_pct", r.out_correct, "%", r.workload, r.shell, r.variant)

    # ---------------- start-up, strace, GNU time cross-check
    st = pd.read_csv(results_dir / "startup_runs.csv")
    srows = []
    for sh, g in st.groupby("shell"):
        lo, hi = ci95(g.wall_ms)
        srows.append({"shell": sh, "n": len(g), "wall_mean": g.wall_ms.mean(), "wall_sd": g.wall_ms.std(ddof=1),
                      "wall_median": g.wall_ms.median(), "wall_ci_lo": lo, "wall_ci_hi": hi,
                      "user_mean": g.user_ms.mean(), "sys_mean": g.sys_ms.mean(),
                      "rss_kb_mean": g.maxrss_kb.mean(), "rss_kb_sd": g.maxrss_kb.std(ddof=1)})
    sdf = pd.DataFrame(srows)
    sdf.to_csv(out_dir / "startup_summary.csv", index=False)
    for r in srows:
        for k, val in r.items():
            if k != "shell":
                put("startup", k, val, "", "", r["shell"], "", r["n"])
    # interpreter-only peak RSS (ptrace exit-stop VmHWM pass)
    if (results_dir / "interpreter_hwm.csv").exists():
        hw = pd.read_csv(results_dir / "interpreter_hwm.csv")
        put("interp_memory", "hwm_runs_with_output_correct_pct", 100 * hw.out_correct.astype(float).mean(), "%", n=len(hw))
        put("interp_memory", "hwm_runs_where_interpreter_exec_replaced", int((hw.tracee_execs > 0).sum()), "runs", n=len(hw))
        hrows = []
        for (wl, sh, v), g in hw.groupby(["workload", "shell", "variant"]):
            lo, hi = ci95(g.interp_hwm_kb)
            row = {"workload": wl, "shell": sh, "variant": v, "n": len(g), "hwm_kb_mean": g.interp_hwm_kb.mean(),
                   "hwm_kb_sd": g.interp_hwm_kb.std(ddof=1), "hwm_kb_median": g.interp_hwm_kb.median(),
                   "hwm_kb_ci_lo": lo, "hwm_kb_ci_hi": hi, "hwm_mb_mean": g.interp_hwm_kb.mean() / 1024}
            hrows.append(row)
            for k in ["hwm_kb_mean", "hwm_kb_sd", "hwm_kb_median", "hwm_kb_ci_lo", "hwm_kb_ci_hi", "hwm_mb_mean"]:
                put("interp_memory", k, row[k], "KB" if "kb" in k else "MB", wl, sh, v, len(g))
        hdf = pd.DataFrame(hrows)
        hdf.to_csv(out_dir / "interpreter_hwm_summary.csv", index=False)
        prow = []
        for wl in WORKLOADS:
            for v in VARIANTS:
                fam = []
                for a, b in combinations(SHELLS, 2):
                    xa = hw[(hw.workload == wl) & (hw.shell == a) & (hw.variant == v)].set_index("task").interp_hwm_kb
                    xb = hw[(hw.workload == wl) & (hw.shell == b) & (hw.variant == v)].set_index("task").interp_hwm_kb
                    idx = xa.index.intersection(xb.index)
                    t, p_t = stats.ttest_rel(xa[idx], xb[idx])
                    try:
                        _, p_w = stats.wilcoxon(xa[idx], xb[idx])
                    except ValueError:
                        p_w = float("nan")
                    fam.append({"workload": wl, "variant": v, "shell_a": a, "shell_b": b, "n_tasks": len(idx),
                                "mean_diff_kb": (xa[idx] - xb[idx]).mean(), "t": t, "p_t": p_t, "p_wilcoxon": p_w})
                for r, at, aw in zip(fam, holm([r["p_t"] for r in fam]), holm([r["p_wilcoxon"] for r in fam])):
                    r["p_t_holm"], r["p_wilcoxon_holm"] = at, aw
                prow += fam
        pd.DataFrame(prow).to_csv(out_dir / "interpreter_hwm_pairwise.csv", index=False)
        for r in prow:
            for k in ["mean_diff_kb", "p_t_holm", "p_wilcoxon_holm"]:
                put("interp_memory_pairwise", f"{r['shell_a']}_vs_{r['shell_b']}:{k}", r[k], "", r["workload"], "", r["variant"], r["n_tasks"])
    if (results_dir / "startup_hwm.csv").exists():
        sh_ = pd.read_csv(results_dir / "startup_hwm.csv")
        sg = sh_.groupby("shell").interp_hwm_kb.agg(["mean", "std", "count"]).reset_index()
        sg.to_csv(out_dir / "startup_hwm_summary.csv", index=False)
        for r in sg.itertuples():
            put("startup", "interp_hwm_kb_mean", r.mean, "KB", "", r.shell, "", r.count)
            put("startup", "interp_hwm_kb_sd", r.std, "KB", "", r.shell, "", r.count)

    if not list(results_dir.glob("strace_counts*.csv")):
        print("strace/timecheck not yet available; partial analysis")
        m = pd.DataFrame(master); m.to_csv(out_dir / "Master_Verified_Results_Sheet.csv", index=False); return m
    sc = pd.concat([pd.read_csv(p) for p in sorted(results_dir.glob("strace_counts*.csv"))], ignore_index=True)
    scs = sc.groupby(["workload", "shell", "variant"])[["process_creations", "thread_creations", "execve_ok", "execve_failed"]].agg(["mean", "std"])
    scs.columns = ["_".join(c) for c in scs.columns]
    scs = scs.reset_index()
    scs.to_csv(out_dir / "strace_summary.csv", index=False)
    for _, r in scs.iterrows():
        for k in ["process_creations_mean", "process_creations_std", "thread_creations_mean", "execve_ok_mean", "execve_failed_mean"]:
            put("syscalls", k, r[k], "per task", r.workload, r.shell, r.variant, int(sc[(sc.workload == r.workload) & (sc.shell == r.shell) & (sc.variant == r.variant)].shape[0]))
    tc = pd.read_csv(results_dir / "timecheck.csv")
    tc["rel_diff_pct"] = 100 * (tc.gnu_time_maxrss_kb - tc.wait4_maxrss_kb) / tc.wait4_maxrss_kb
    tc.to_csv(out_dir / "timecheck_summary.csv", index=False)
    put("instrumentation", "gnu_time_vs_wait4_rss_mean_abs_rel_diff", tc.rel_diff_pct.abs().mean(), "%", "w1", "", "B", len(tc))
    put("instrumentation", "gnu_time_vs_wait4_rss_max_abs_rel_diff", tc.rel_diff_pct.abs().max(), "%", "w1", "", "B", len(tc))

    # ---------------- Pareto frontier (latency vs memory), per workload
    par = []
    hsum = out_dir / "interpreter_hwm_summary.csv"
    for wl in WORKLOADS:
        p = perf[perf.workload == wl][["shell", "variant", "wall_mean", "rss_kb_mean"]].copy()
        if hsum.exists():   # the frontier uses the interpreter's own peak RSS, not the tree peak
            hs = pd.read_csv(hsum)
            hs = hs[hs.workload == wl][["shell", "variant", "hwm_kb_mean"]]
            p = p.merge(hs, on=["shell", "variant"])
            p["tree_rss_kb_mean"] = p["rss_kb_mean"]
            p["rss_kb_mean"] = p["hwm_kb_mean"]
        p["pareto"] = [int(not ((p.wall_mean <= r.wall_mean) & (p.rss_kb_mean <= r.rss_kb_mean) &
                               ((p.wall_mean < r.wall_mean) | (p.rss_kb_mean < r.rss_kb_mean))).any())
                       for r in p.itertuples()]
        p["workload"] = wl
        par.append(p)
        for r in p.itertuples():
            put("pareto", "on_frontier", r.pareto, "", wl, r.shell, r.variant)
    pd.concat(par).to_csv(out_dir / "pareto.csv", index=False)

    m = pd.DataFrame(master)
    m.to_csv(out_dir / "Master_Verified_Results_Sheet.csv", index=False)
    print(f"analysis complete: {len(m)} verified values -> {out_dir / 'Master_Verified_Results_Sheet.csv'}")
    return m
