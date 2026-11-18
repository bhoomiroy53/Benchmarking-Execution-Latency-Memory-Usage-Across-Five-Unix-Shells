"""
make_figures.py - render the five manuscript figures from the verified analysis outputs.
Usage: python make_figures.py ANALYSIS_DIR FIGURE_DIR
All values are read from the CSVs written by analysis_core.analyze(); nothing is typed in.
Programmatic plots only (matplotlib); 300 DPI, width >= 1600 px, tight bounding boxes.
"""
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch
import numpy as np
import pandas as pd

SHELLS = ["bash", "dash", "zsh", "ksh", "fish"]
LABEL = {"bash": "bash", "dash": "dash", "zsh": "zsh", "ksh": "ksh93", "fish": "fish"}
COLOR = {"bash": "#2a78d6", "dash": "#eb6834", "zsh": "#1baf7a", "ksh": "#eda100", "fish": "#e87ba4"}
MARK = {"bash": "o", "dash": "s", "zsh": "^", "ksh": "D", "fish": "v"}
VARIANTS = ["A", "B", "C", "D"]
VNAME = {"A": "A external pipeline", "B": "B native built-ins", "C": "C batched concurrency", "D": "D fault-trapped"}
WNAME = {"w1": "Workload Suite 1 (log parsing)", "w2": "Workload Suite 2 (file system and processes)"}
INK, MUTED, GRID = "#1f1f1d", "#5f5e58", "#e1e0d9"

plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 9, "axes.edgecolor": "#c3c2b7",
                     "axes.labelcolor": INK, "xtick.color": MUTED, "ytick.color": MUTED,
                     "axes.spines.top": False, "axes.spines.right": False, "axes.grid": True,
                     "grid.color": GRID, "grid.linewidth": 0.6, "axes.axisbelow": True,
                     "legend.frameon": False, "savefig.dpi": 300})


def panel(ax, letter):
    ax.text(-0.12, 1.06, letter, transform=ax.transAxes, fontsize=12, fontweight="bold", color=INK, va="bottom")


def save(fig, path):
    fig.savefig(path, dpi=300, bbox_inches="tight", pad_inches=0.05, facecolor="white")
    plt.close(fig)


def fig1(out):
    fig, ax = plt.subplots(figsize=(8.6, 4.4))
    ax.set_xlim(0, 120); ax.set_ylim(0, 60); ax.axis("off")

    def box(x, y, w, h, title, body, fc):
        ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.3,rounding_size=1.2", fc=fc, ec="#8a897f", lw=0.8))
        ax.text(x + w / 2, y + h - 2.2, title, ha="center", va="top", fontsize=7.0, fontweight="bold", color=INK)
        ax.text(x + w / 2, y + h - 7.4, body, ha="center", va="top", fontsize=6.4, color=INK, linespacing=1.4)

    def arrow(x1, y1, x2, y2):
        ax.annotate("", xy=(x2, y2), xytext=(x1, y1), arrowprops=dict(arrowstyle="-|>", color="#5f5e58", lw=0.9))

    box(1, 33, 25, 25, 'Seeded corpus generator',
        'Suite 1: 1,250 access logs\n(200 to 600 records each)\nSuite 2: 1,250 directory trees\n(4 to 6 subtrees each)\n80:20 split, 250 evaluation', '#eaf2fc')
    box(1, 2, 25, 27, 'Fault-injection sandbox',
        '100 of 250 evaluation tasks\nmissing or unreadable input\ncorrupt record, helper exit\nSIGTERM, write failure\nclosed consumer pipe', '#fdeee8')
    box(32, 13, 27, 34, 'Five-shell harness',
        'bash, dash, zsh, ksh93, fish\nfour script variants, A to D\nfive seeds: 42, 101, 202,\n303 and 404\nrandomized interleaving\nstatic fork-exec launcher', '#e8f7f1')
    box(65, 33, 26, 25, 'Telemetry profiler',
        'wait4 rusage: wall, user\nand system time, context\nswitches, tree peak RSS\nptrace exit stop: VmHWM\nstrace, GNU time check', '#fdf5e0')
    box(65, 2, 26, 27, 'Outcome classifier',
        'exit status, stderr and\nBENCH-FAULT marker\noutput vs. reference\ndetection score 0 to 3\nconfusion matrix, ROC', '#fbeef3')
    box(97, 13, 22, 34, 'Verified results',
        'raw execution records\nMaster Verified\nResults Sheet\npaired t and\nWilcoxon tests\nHolm correction\ntables and figures', '#efedf9')
    arrow(26.6, 45, 31.6, 37); arrow(26.6, 15, 31.6, 23)
    arrow(59.6, 37, 64.6, 44); arrow(59.6, 23, 64.6, 16)
    arrow(91.6, 44, 96.6, 37); arrow(91.6, 16, 96.6, 23)
    save(fig, out / "Figure_1_Benchmarking_Architecture_Pipeline.png")


def fig2(perf, out):
    fig, axes = plt.subplots(2, 1, figsize=(7.4, 6.4))
    for ax, wl, letter in zip(axes, ["w1", "w2"], "AB"):
        p = perf[perf.workload == wl]
        x = np.arange(len(VARIANTS))
        w = 0.16
        for i, sh in enumerate(SHELLS):
            q = p[p.shell == sh].set_index("variant").loc[VARIANTS]
            pos = x + (i - 2) * w
            ax.bar(pos, q.user_mean, w * 0.92, color=COLOR[sh], label=LABEL[sh])
            ax.bar(pos, q.sys_mean, w * 0.92, bottom=q.user_mean, color=COLOR[sh], alpha=0.45, hatch="////", edgecolor="white", lw=0)
            lower = np.minimum(q.wall_sd.values, q.wall_mean.values)   # clip the bar at zero latency
            ax.errorbar(pos, q.wall_mean, yerr=[lower, q.wall_sd.values], fmt="_", color=INK, ms=7, mew=1.4,
                        elinewidth=0.8, capsize=2)
        ax.set_xticks(x, [VNAME[v] for v in VARIANTS])
        ax.set_ylabel("Time per task (ms)")
        ax.set_ylim(bottom=0)
        ax.set_title(WNAME[wl], loc="left", fontsize=9.5, color=INK)
        panel(ax, letter)
    from matplotlib.patches import Patch
    from matplotlib.lines import Line2D
    h = [Patch(color=COLOR[s], label=LABEL[s]) for s in SHELLS]
    h += [Patch(facecolor="#bbbbbb", label="user CPU (solid)"), Patch(facecolor="#dddddd", hatch="////", edgecolor="white", label="system CPU (hatched)"),
          Line2D([0], [0], marker="_", color=INK, ls="", ms=9, mew=1.4, label="wall-clock mean ± SD")]
    fig.legend(handles=h, loc="lower center", ncol=4, fontsize=7.6, bbox_to_anchor=(0.5, -0.05))
    fig.tight_layout(rect=(0, 0.06, 1, 1))
    save(fig, out / "Figure_2_Execution_Latency_Comparison.png")


def fig3(perf, hwm, starthwm, strace, out):
    fig, axes = plt.subplots(1, 2, figsize=(7.6, 3.7))
    ax = axes[0]
    x = np.arange(len(SHELLS))
    w = 0.2
    sh = starthwm.set_index("shell").loc[SHELLS]["mean"] / 1024
    h1 = hwm[(hwm.workload == "w1") & (hwm.variant == "B")].set_index("shell").loc[SHELLS].hwm_kb_mean / 1024
    h2 = hwm[(hwm.workload == "w2") & (hwm.variant == "B")].set_index("shell").loc[SHELLS].hwm_kb_mean / 1024
    tp = perf[(perf.workload == "w1") & (perf.variant == "A")].set_index("shell").loc[SHELLS].rss_kb_mean / 1024
    series = [(sh, "#8a897f", "Interpreter, start-up only"), (h1, "#2a78d6", "Interpreter, Suite 1 Variant B"),
              (h2, "#1baf7a", "Interpreter, Suite 2 Variant B"), (tp, "#eb6834", "Task tree peak, Suite 1 Variant A")]
    for k, (vals, col, lab) in enumerate(series):
        ax.bar(x + (k - 1.5) * w, vals.values, w * 0.92, color=col, label=lab)
    ax.set_xticks(x, [LABEL[s] for s in SHELLS]); ax.set_ylabel("Peak resident set size (MB)")
    ax.legend(fontsize=6.4, loc="upper left")
    ax.set_ylim(0, max(tp.max(), h1.max()) * 1.45)
    panel(ax, "A")
    ax = axes[1]
    for k, v in enumerate(VARIANTS):
        vals = []
        for s in SHELLS:
            a1 = strace[(strace.workload == "w1") & (strace.shell == s) & (strace.variant == v)].process_creations_mean.iloc[0]
            a2 = strace[(strace.workload == "w2") & (strace.shell == s) & (strace.variant == v)].process_creations_mean.iloc[0]
            vals.append((a1 + a2) / 2)
        ax.bar(x + (k - 1.5) * w, vals, w * 0.92, color=["#2a78d6", "#eb6834", "#1baf7a", "#6250d6"][k], label=VNAME[v])
    ax.set_xticks(x, [LABEL[s] for s in SHELLS]); ax.set_ylabel("Process creations per task (count)")
    ax.set_ylim(0, ax.get_ylim()[1] * 1.35)
    ax.legend(fontsize=6.4, loc="upper center", ncol=2)
    panel(ax, "B")
    fig.tight_layout()
    save(fig, out / "Figure_3_Memory_Footprint_and_Fork_Overhead.png")


def cm_panel(ax, row, title):
    m = np.array([[row["TP_mean"], row["FN_mean"]], [row["FP_mean"], row["TN_mean"]]])
    ax.imshow(m, cmap="Blues", vmin=0, vmax=250)
    for (i, j), val in np.ndenumerate(m):
        ax.text(j, i, f"{val:.0f}" if float(val).is_integer() else f"{val:.1f}", ha="center", va="center",
                color="white" if val > 125 else INK, fontsize=9, fontweight="bold")
    ax.set_xticks([0, 1], ["trapped", "not trapped"]); ax.set_yticks([0, 1], ["faulty", "valid"])
    ax.set_xlabel("Interpreter outcome", fontsize=7.5); ax.set_ylabel("Ground truth", fontsize=7.5)
    ax.tick_params(labelsize=7); ax.grid(False)
    ax.set_title(title, fontsize=7.8, color=INK)


def fig4(perf, cls, out, cm_choice):
    fig = plt.figure(figsize=(7.6, 6.6))
    gs = fig.add_gridspec(2, 3, height_ratios=[1.05, 1])
    ax = fig.add_subplot(gs[0, :])
    x = np.arange(len(SHELLS) * 2)
    w = 0.2
    for k, v in enumerate(VARIANTS):
        vals = []
        for wl in ["w1", "w2"]:
            for s in SHELLS:
                a = perf[(perf.workload == wl) & (perf.shell == s) & (perf.variant == "A")].wall_mean.iloc[0]
                b = perf[(perf.workload == wl) & (perf.shell == s) & (perf.variant == v)].wall_mean.iloc[0]
                vals.append(100 * (b - a) / a)
        ax.bar(x + (k - 1.5) * w, vals, w * 0.92, color=["#2a78d6", "#eb6834", "#1baf7a", "#6250d6"][k], label=VNAME[v])
    ax.axhline(0, color="#c3c2b7", lw=0.8)
    ax.set_xticks(x, [f"{LABEL[s]}\nSuite {i // 5 + 1}" for i, s in enumerate(SHELLS * 2)], fontsize=7)
    ax.set_ylabel("Wall-clock change vs. Variant A (%)")
    ax.legend(fontsize=7, ncol=4, loc="upper center", bbox_to_anchor=(0.5, 1.16))
    panel(ax, "A")
    for idx, (letter, (wl, sh, v)) in enumerate(zip("BCD", cm_choice)):
        a2 = fig.add_subplot(gs[1, idx])
        row = cls[(cls.partition == "eval") & (cls.workload == wl) & (cls.shell == sh) & (cls.variant == v)].iloc[0]
        cm_panel(a2, row, f"{LABEL[sh]}, Variant {v}, Suite {wl[1]}\n(N = {row['N_mean']:.0f})")
        panel(a2, letter)
    fig.tight_layout()
    save(fig, out / "Figure_4_Ablation_and_Fault_Confusion_Matrices.png")


def fig5(roc, cls, perf, out):
    fig, axes = plt.subplots(1, 2, figsize=(7.6, 3.7))
    ax = axes[0]
    for wl, ls in [("w1", "-"), ("w2", "--")]:
        for s in SHELLS:
            r = roc[(roc.workload == wl) & (roc.shell == s) & (roc.variant == "D")].sort_values("fpr")
            auc = cls[(cls.partition == "eval") & (cls.workload == wl) & (cls.shell == s) & (cls.variant == "D")].auc_pooled.iloc[0]
            ax.plot(r.fpr, r.tpr, ls=ls, color=COLOR[s], lw=1.4, marker=MARK[s], ms=5 if wl == "w1" else 3.5,
                    mfc=COLOR[s] if wl == "w1" else "white", alpha=0.9,
                    label=f"{LABEL[s]} S{wl[1]} (AUC {auc:.2f})")
    ax.plot([0, 1], [0, 1], color="#c3c2b7", lw=0.8, ls=":")
    ax.set_xlabel("False-positive rate"); ax.set_ylabel("True-positive rate")
    ax.set_xlim(-0.02, 1.02); ax.set_ylim(-0.02, 1.02)
    ax.legend(fontsize=5.8, loc="lower right", ncol=2, columnspacing=0.8)
    ax.set_title("Variant D detection-score ROC (curves coincide)", fontsize=8.5, loc="left")
    panel(ax, "A")
    ax = axes[1]
    par = pd.read_csv(PARETO_CSV)
    for wl, fill in [("w1", True), ("w2", False)]:
        p = par[par.workload == wl]
        for s in SHELLS:
            q = p[p.shell == s]
            ax.scatter(q.wall_mean, q.rss_kb_mean / 1024, s=28, marker=MARK[s], color=COLOR[s] if fill else "white",
                       edgecolor=COLOR[s], lw=1.2, zorder=3, label=f"{LABEL[s]}" if wl == "w1" else None)
    for wl, ls in [("w1", "-"), ("w2", "--")]:
        f = par[(par.workload == wl) & (par.pareto == 1)].sort_values("wall_mean")
        ax.step(f.wall_mean, f.rss_kb_mean / 1024, where="post", color=INK, lw=0.9, ls=ls, zorder=2,
                label=f"Pareto frontier, Suite {wl[1]}")
        for r in f.itertuples():
            ax.annotate(f"{LABEL[r.shell]}-{r.variant}", (r.wall_mean, r.rss_kb_mean / 1024), fontsize=6,
                        xytext=(3, 3 if wl == "w1" else -8), textcoords="offset points", color=MUTED)
    ax.set_xscale("log")
    ax.set_xlabel("Mean wall-clock latency per task (ms, log scale)"); ax.set_ylabel("Interpreter peak RSS (MB)")
    ax.legend(fontsize=6, loc="center right")
    ax.set_title("Latency-memory trade-off (filled: Suite 1, open: Suite 2)", fontsize=8.5, loc="left")
    panel(ax, "B")
    fig.tight_layout()
    save(fig, out / "Figure_5_ROC_AUC_and_Latency_Memory_Pareto.png")


def main(analysis_dir, fig_dir, cm_choice):
    global PARETO_CSV
    a, out = Path(analysis_dir), Path(fig_dir)
    PARETO_CSV = a / "pareto.csv"
    out.mkdir(parents=True, exist_ok=True)
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    perf = pd.read_csv(a / "perf_summary.csv")
    cls = pd.read_csv(a / "classification_summary.csv")
    fig1(out)
    fig2(perf, out)
    fig3(perf, pd.read_csv(a / "interpreter_hwm_summary.csv"), pd.read_csv(a / "startup_hwm_summary.csv"),
         pd.read_csv(a / "strace_summary.csv"), out)
    fig4(perf, cls, out, cm_choice)
    fig5(pd.read_csv(a / "roc_points.csv"), cls, perf, out)
    from PIL import Image
    for f in sorted(out.glob("*.png")):
        im = Image.open(f)
        print(f.name, im.size, f"{f.stat().st_size / 1e6:.2f} MB")


if __name__ == "__main__":
    choice = [("w1", "bash", "A"), ("w1", "bash", "D"), ("w1", "fish", "D")]
    if len(sys.argv) > 3:
        choice = [tuple(x.split(":")) for x in sys.argv[3].split(",")]
    main(sys.argv[1], sys.argv[2], choice)
