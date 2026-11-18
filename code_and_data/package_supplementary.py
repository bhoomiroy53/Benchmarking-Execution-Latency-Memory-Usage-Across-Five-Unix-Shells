"""package_supplementary.py - build Master_Verified_Results_Sheet.xlsx (raw runs, seed log, verified values and
live Excel formulas), raw_telemetry_logs.json, and CJCS_Five_Unix_Shells_Supplementary_Package.zip."""
import hashlib
import json
import shutil
import zipfile
from pathlib import Path

import pandas as pd
from openpyxl import Workbook
from openpyxl.styles import Font
from openpyxl.utils.dataframe import dataframe_to_rows

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
AN, RAW, FIG, TAB = ROOT / "analysis", ROOT / "raw_staging", ROOT / "figures", ROOT / "tables"
ZIP = ROOT / "CJCS_Five_Unix_Shells_Supplementary_Package.zip"


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def master_xlsx():
    wb = Workbook()
    ws = wb.active
    ws.title = "Verified_values"
    m = pd.read_csv(AN / "Master_Verified_Results_Sheet.csv")
    for r in dataframe_to_rows(m, index=False, header=True):
        ws.append(r)
    for c in ws[1]:
        c.font = Font(bold=True)

    # live formulas: confusion metrics recomputed in Excel from the counts
    cls = pd.read_csv(AN / "classification_per_seed.csv")
    cls = cls[cls.partition == "eval"]
    wf = wb.create_sheet("Confusion_formulas")
    hdr = ["workload", "shell", "variant", "seed", "TP", "FP", "TN", "FN", "N (=SUM)", "Accuracy %", "Precision %",
           "Recall %", "F1 %", "Specificity %", "FPR %", "FNR % = FN/(TP+FN)", "AUC (computed in Python)"]
    wf.append(hdr)
    for c in wf[1]:
        c.font = Font(bold=True)
    for i, r in enumerate(cls.itertuples(), start=2):
        wf.append([r.workload, r.shell, r.variant, r.seed, r.TP, r.FP, r.TN, r.FN,
                   f"=SUM(E{i}:H{i})", f"=100*(E{i}+G{i})/I{i}", f"=IF(E{i}+F{i}=0,\"\",100*E{i}/(E{i}+F{i}))",
                   f"=100*E{i}/(E{i}+H{i})", f"=IF(E{i}=0,0,2*K{i}*L{i}/(K{i}+L{i}))", f"=100*G{i}/(G{i}+F{i})",
                   f"=100*F{i}/(F{i}+G{i})", f"=100*H{i}/(E{i}+H{i})", r.auc])

    # per-configuration latency recomputed from raw runs with AVERAGEIFS
    raw = pd.read_csv(RAW / "raw_runs.csv")
    wr = wb.create_sheet("Raw_eval_runs")
    cols = [c for c in raw.columns if c != "stderr_head"]
    wr.append(cols)
    for row in raw[cols].itertuples(index=False):
        wr.append(list(row))
    n = len(raw) + 1
    col = {c: chr(ord("A") + i) for i, c in enumerate(cols)}
    wl = wb.create_sheet("Latency_formulas")
    wl.append(["workload", "shell", "variant", "Mean wall ms (fault-free, AVERAGEIFS)", "Runs (COUNTIFS)",
               "Mean wall ms (Python)"])
    for c in wl[1]:
        c.font = Font(bold=True)
    perf = pd.read_csv(AN / "perf_summary.csv")
    rng = lambda c: f"Raw_eval_runs!${col[c]}$2:${col[c]}${n}"
    for i, r in enumerate(perf.itertuples(), start=2):
        crit = (f'{rng("workload")},A{i},{rng("shell")},B{i},{rng("variant")},C{i},{rng("is_faulty")},0')
        wl.append([r.workload, r.shell, r.variant, f"=AVERAGEIFS({rng('wall_ms')},{crit})",
                   f"=COUNTIFS({crit})", r.wall_mean])

    seeds = raw.groupby(["seed"]).agg(executions=("wall_ms", "size"), first_order=("order", "min"),
                                      last_order=("order", "max")).reset_index()
    wsd = wb.create_sheet("Seed_log")
    wsd.append(["seed", "executions", "first order index", "last order index", "role"])
    for r in seeds.itertuples():
        wsd.append([r.seed, r.executions, r.first_order, r.last_order, "evaluation repetition"])
    wsd.append([2026, "", "", "", "corpus generation and 80:20 split"])
    out = TAB / "Master_Verified_Results_Sheet.xlsx"
    wb.save(out)
    shutil.copy(AN / "Master_Verified_Results_Sheet.csv", TAB / "Master_Verified_Results_Sheet.csv")
    return out


def telemetry_index():
    files = sorted(p for p in RAW.iterdir() if p.is_file())
    idx = {"description": "Raw telemetry produced on Ubuntu 26.04.1 LTS (WSL2) by run_unix_shell_benchmark.py",
           "timeline_utc_2026_11_13": {
               "evaluation_segment_1": "about 07:04 to 07:14:19 (harness restart interrupted seed 101)",
               "development_partition_parallel": "07:14:19 to about 07:27 (four shards, non-timed use only)",
               "interpreter_hwm_pass": "07:14:19 to about 07:27 (ptrace exit stop)",
               "evaluation_segment_2": "07:42:52 to 08:12:35 (resumed, same binaries, order preserved)",
               "strace_and_gnu_time": "08:12:37 to 08:22:19"},
           "files": {}}
    for p in files:
        rows = sum(1 for _ in open(p, encoding="utf-8", errors="replace")) - 1 if p.suffix == ".csv" else None
        idx["files"][p.name] = {"bytes": p.stat().st_size, "sha256": sha(p), "rows": rows}
    out = HERE / "raw_telemetry_logs.json"
    out.write_text(json.dumps(idx, indent=2))
    shutil.copy(RAW / "environment_versions.json", HERE / "environment_versions.json")
    return out


def build_zip():
    if ZIP.exists():
        ZIP.unlink()
    skip_dirs = {"__pycache__"}
    with zipfile.ZipFile(ZIP, "w", zipfile.ZIP_DEFLATED) as z:
        for f in sorted(FIG.glob("*.png")):
            z.write(f, f"figures/{f.name}")
        for f in sorted(TAB.iterdir()):
            z.write(f, f"tables/{f.name}")
        for f in sorted(HERE.rglob("*")):
            if f.is_file() and not (set(f.parts) & skip_dirs) and f.name != "rusage_launcher":
                z.write(f, f"code_and_data/{f.relative_to(HERE).as_posix()}")
        for f in sorted(RAW.iterdir()):
            z.write(f, f"code_and_data/raw/{f.name}")
        for f in sorted(AN.iterdir()):
            z.write(f, f"code_and_data/analysis/{f.name}")
    return ZIP


if __name__ == "__main__":
    print("wrote", master_xlsx())
    print("wrote", telemetry_index())
    z = build_zip()
    with zipfile.ZipFile(z) as zz:
        names = zz.namelist()
    print("wrote", z, f"{z.stat().st_size / 1e6:.2f} MB,", len(names), "files")
