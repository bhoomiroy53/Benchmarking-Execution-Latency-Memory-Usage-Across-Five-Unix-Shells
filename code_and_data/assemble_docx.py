"""assemble_docx.py - writes the manuscript .docx and the table files. Run: python assemble_docx.py"""
import re
import sys
from pathlib import Path

from docx.shared import Inches

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import build_manuscript as M  # noqa: E402
import docx_helpers as D  # noqa: E402
import manuscript_text as T  # noqa: E402
import results_text as R  # noqa: E402

FIG = M.ROOT / "figures"
FIGURES = {
    1: ("Figure_1_Benchmarking_Architecture_Pipeline.png", "Figure 1: Benchmarking architecture",
        "Seeded corpus generation and the fault-injection sandbox feed the five-shell execution harness, which runs "
        "every task under a static launcher; the telemetry profiler and the outcome classifier produce the raw "
        "records from which the verified results sheet, tables and figures are computed. RSS: resident set size; "
        "ROC: receiver operating characteristic."),
    2: ("Figure_2_Execution_Latency_Comparison.png", "Figure 2: Execution latency comparison",
        "Mean user CPU time (solid) and system CPU time (hatched) per task, with mean wall-clock latency and its "
        "standard deviation (black marker and error bar), for each interpreter and variant on Workload Suite 1 (A) "
        "and Workload Suite 2 (B); 750 executions per bar. CPU: central processing unit; ms: milliseconds; SD: "
        "standard deviation."),
    3: ("Figure_3_Memory_Footprint_and_Fork_Overhead.png", "Figure 3: Memory footprint and process-creation overhead",
        "(A) Peak resident set size of the interpreter process alone at start-up and on Variant B of each suite, "
        "and the peak of the whole task process tree on Suite 1 Variant A. (B) Process creations per task from "
        "strace, averaged over both suites, per interpreter and variant. MB: megabytes."),
    4: ("Figure_4_Ablation_and_Fault_Confusion_Matrices.png", "Figure 4: Ablation latency changes and fault-trapping confusion matrices",
        "(A) Change in mean wall-clock latency of each variant relative to Variant A per interpreter and suite. "
        "(B to D) Fault-trapping confusion matrices on Suite 1 for bash Variant A (B), bash Variant D (C) and fish "
        "Variant D (D); each matrix sums to N = 250 evaluation tasks and was identical for all five seeds."),
    5: ("Figure_5_ROC_AUC_and_Latency_Memory_Pareto.png", "Figure 5: ROC curves and latency-memory Pareto frontier",
        "(A) Receiver operating characteristic curves of the ordinal detection score for Variant D of each "
        "interpreter and suite, with the area under the curve matching Table 6. (B) Mean wall-clock latency against "
        "the interpreter's own peak resident set size for all 40 configurations; filled markers Suite 1, open "
        "markers Suite 2; stepped lines mark the Pareto frontiers. AUC: area under the curve; MB: megabytes; ms: "
        "milliseconds; ROC: receiver operating characteristic; S1, S2: Suite 1, Suite 2."),
}
# insert after the first paragraph that starts with this text
TABLE_AFTER = {1: "Table 1 lists", 2: "Table 2 gives", 3: "Table 3 and Figure 2", 4: "Table 4 and Figure 3",
               5: "Table 5 and Figure 4A", 6: "Table 6 and Figures 4B"}
FIG_AFTER = {1: "The study is a controlled", 2: "Table 3 and Figure 2", 3: "Table 4 and Figure 3",
             4: "Table 5 and Figure 4A", 5: "The ROC-AUC values"}


def eqs():
    m = D
    return {
        "eq1": [m.sub(m.mr("T"), m.mr("wall", False)), m.mr(" = ", False), m.sub(m.mr("T"), m.mr("user", False)),
                m.mr(" + ", False), m.sub(m.mr("T"), m.mr("sys", False)), m.mr(" + ", False),
                m.sub(m.mr("T"), m.mr("io", False))],
        "eq2": [m.mr("MDP", False), m.mr(" = ", False), m.sub(m.mr("RSS", False), m.mr("peak", False)),
                m.mr(" × ", False), m.sub(m.mr("T"), m.mr("wall", False))],
        "eq3": [m.mr("FNR", False), m.mr(" = ", False),
                m.frac(m.mr("FN", False), [m.mr("TP", False), m.mr(" + ", False), m.mr("FN", False)])],
        "eq4": [m.mr("t"), m.mr(" = ", False),
                m.frac(m.bar(m.mr("d")), m.frac(m.sub(m.mr("s"), m.mr("d")), m.sqrt(m.mr("n"))))],
    }


def place_media(doc, text, placed):
    for k, start in TABLE_AFTER.items():
        if k not in placed["t"] and text.startswith(start):
            cap, fn, legend = M.TABLES[k - 1]
            hdr, rows = fn()
            D.table(doc, cap, hdr, rows, legend, font=7 if len(hdr) > 10 else 8)
            placed["t"].add(k)
    for k, start in FIG_AFTER.items():
        if k not in placed["f"] and text.startswith(start):
            fname, cap, legend = FIGURES[k]
            D.para(doc, cap, bold=True, space_after=6)
            doc.add_picture(str(FIG / fname), width=Inches(6.3))
            D.para(doc, legend, size=9)
            placed["f"].add(k)


def emit(doc, kind, text, placed, E):
    if kind == "major":
        D.major(doc, text)
    elif kind == "minor":
        D.minor(doc, text)
    elif kind.startswith("lead:"):
        D.lead(doc, kind[5:], M.cite(text))
        place_media(doc, text, placed)
    elif kind.startswith("eq"):
        D.equation(doc, E[kind], int(kind[2]))
    else:
        D.para(doc, M.cite(text))
        place_media(doc, text, placed)


def main():
    E = eqs()
    doc = D.new_document()
    placed = {"t": set(), "f": set()}
    D.title(doc, T.TITLE)
    p = D.para(doc, "AUTHOR ONE, AUTHOR TWO, AUTHOR THREE (placeholders: replace with author names, affiliations and "
               "the corresponding author before submission)", italic=True)
    for r in p.runs:
        r.font.highlight_color = 7  # yellow
    D.major(doc, "Abstract")
    for head, body in M.abstract_parts():
        D.rich(doc, [(head + ": ", "b"), (body, "")])
    D.rich(doc, [("Categories: ", "b"), (T.CATEGORIES, "")])
    D.rich(doc, [("Keywords: ", "b"), (T.KEYWORDS, "")])
    D.major(doc, "Introduction")
    for para in T.INTRO:
        D.para(doc, M.cite(para))
    meth = T.methods(M.env)
    meth[1] = ("p", meth[1][1] + " Figure 1 summarizes the harness and its data flow.")
    for kind, text in meth:
        if kind == "major" and text == "Materials and methods":
            D.major(doc, "Materials and Methods")
            continue
        emit(doc, kind, text, placed, E)
    D.major(doc, "Results and Discussion")
    for kind, text in R.results_blocks(M):
        emit(doc, kind, text, placed, E)
    D.major(doc, "Conclusions")
    for para in R.conclusions(M):
        D.para(doc, para)
    D.major(doc, "References")
    for i, key in enumerate(M.ORDER, start=1):
        D.para(doc, f"{i}. " + M.ref_line(M.KEY[key]), space_after=6)
    D.major(doc, "Additional Information")
    for head, body in R.disclosures():
        D.rich(doc, [(head + ": ", "b"), (body, "")])
    missing_t = set(range(1, 7)) - placed["t"]
    missing_f = set(range(1, 6)) - placed["f"]
    assert not missing_t and not missing_f, (missing_t, missing_f)
    assert len(M.ORDER) == len(M.KEY), set(M.KEY) - set(M.ORDER)
    doc.save(M.OUTDOC)
    M.export_tables()
    print("wrote", M.OUTDOC, "with", len(M.ORDER), "references")


if __name__ == "__main__":
    main()
