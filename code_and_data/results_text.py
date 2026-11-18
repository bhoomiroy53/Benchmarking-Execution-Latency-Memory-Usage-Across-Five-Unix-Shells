"""results_text.py - Results and Discussion, Conclusions and disclosures, generated from the analysis
CSVs through the lookup helpers of build_manuscript.py (passed in as module `M`)."""
import pandas as pd


def results_blocks(M):
    P, C, A, H, S, ST, STH, pv, pair, LBL = M.P, M.C, M.A, M.H, M.S, M.ST, M.STH, M.pv, M.pair, M.LBL
    wnum = M.wnum
    perf, pairs, hwm, abl, cls_e, tc, par, env = M.perf, M.pairs, M.hwm, M.abl, M.cls_e, M.tc, M.par, M.env
    B = []

    def add(kind, text=""):
        B.append((kind, text))

    add("major", "Start-up overhead and interpreter characteristics")
    add("p", "Table 1 lists the five interpreter builds, their checksums and their start-up cost. Running a single "
        f"no-op command took {ST('dash','wall_mean'):.2f} ms (SD {ST('dash','wall_sd'):.2f}) for dash, "
        f"{ST('bash','wall_mean'):.2f} ms (SD {ST('bash','wall_sd'):.2f}) for bash, {ST('ksh','wall_mean'):.2f} ms "
        f"(SD {ST('ksh','wall_sd'):.2f}) for ksh93, {ST('zsh','wall_mean'):.2f} ms (SD {ST('zsh','wall_sd'):.2f}) for zsh "
        f"and {ST('fish','wall_mean'):.2f} ms (SD {ST('fish','wall_sd'):.2f}) for fish, so fish started "
        f"{ST('fish','wall_mean')/ST('dash','wall_mean'):.2f} times slower than dash. The interpreter's own peak memory "
        f"at start-up followed a similar order: {STH('dash')/1024:.2f} MB for dash, {STH('ksh')/1024:.2f} MB for ksh93, "
        f"{STH('bash')/1024:.2f} MB for bash, {STH('zsh')/1024:.2f} MB for zsh and {STH('fish')/1024:.2f} MB for fish. "
        f"The fish binary ({env['shells']['fish']['size_bytes']/1e6:.2f} MB) is also the largest, because fish 4 is "
        "written in Rust and links its runtime statically. The dash build shipped with Ubuntu 26.04 accepts the "
        "pipefail option, which removes one traditional argument against dash for robust scripting.")

    add("major", "Workload composition and functional verification")
    dvc = pd.read_csv(M.AN / "dev_correctness.csv")
    add("p", "Table 2 gives the task distribution of both suites. Each evaluation partition holds 150 fault-free "
        "and 100 faulty tasks, with 16 or 17 tasks per fault type, and each development partition holds 600 "
        "fault-free and 400 faulty tasks. On the development partition all 40 interpreter, variant and suite "
        f"configurations produced the reference output for {dvc.out_correct.min():.2f}% of fault-free tasks, and on the "
        f"evaluation partition the rate was {perf.correct_rate.min():.2f}% for every configuration in all five "
        "repetitions. Every execution completed within the 30 s watchdog limit, so no measurement was censored. "
        "The functional equivalence of the 40 script implementations was therefore established before their "
        "costs were compared.")

    add("major", "Execution latency and throughput")
    b1 = perf[perf.workload == "w1"].sort_values("wall_mean").iloc[0]
    b2 = perf[perf.workload == "w2"].sort_values("wall_mean").iloc[0]
    nonsig = pairs[(pairs.metric == "wall_ms") & ((pairs.p_wilcoxon_holm >= 0.05) | (pairs.p_t_holm >= 0.05))]
    add("p", "Table 3 and Figure 2 report latency, CPU time and throughput for all 40 configurations. On Workload "
        f"Suite 1 the fastest configuration was {LBL[b1.shell]} with Variant {b1.variant}, at {b1.wall_mean:.2f} ms per "
        f"task (SD {b1.wall_sd:.2f}, 95% CI {b1.wall_ci_lo:.2f} to {b1.wall_ci_hi:.2f}), or {b1.tasks_per_s:.2f} tasks "
        f"per second. With the same native built-in script, dash needed {P('w1','dash','B','wall_mean'):.2f} ms, bash "
        f"{P('w1','bash','B','wall_mean'):.2f} ms, zsh {P('w1','zsh','B','wall_mean'):.2f} ms and fish "
        f"{P('w1','fish','B','wall_mean'):.2f} ms. The spread was far smaller with external pipelines, where most work "
        f"happens in the same external tools for every interpreter: Variant A ranged from {P('w1','fish','A','wall_mean'):.2f} ms "
        f"for fish and {P('w1','dash','A','wall_mean'):.2f} ms for dash to {P('w1','zsh','A','wall_mean'):.2f} ms for zsh. "
        f"On Workload Suite 2 the fastest configuration was {LBL[b2.shell]} with Variant {b2.variant}, at "
        f"{b2.wall_mean:.2f} ms (SD {b2.wall_sd:.2f}), and the native built-in variant took "
        f"{P('w2','ksh','B','wall_mean'):.2f} ms in ksh93, {P('w2','dash','B','wall_mean'):.2f} ms in dash, "
        f"{P('w2','bash','B','wall_mean'):.2f} ms in bash, {P('w2','zsh','B','wall_mean'):.2f} ms in zsh and "
        f"{P('w2','fish','B','wall_mean'):.2f} ms in fish.")
    exc = [f"{LBL[r.shell_a]} versus {LBL[r.shell_b]} on Suite {r.workload[1]}" for r in nonsig.itertuples()]
    allA = "all involved Variant A, where external tools dominate" if set(nonsig.variant) == {"A"} else "were"
    add("p", "The interpreter differences were statistically robust. Of the 80 paired interpreter comparisons of "
        f"wall-clock latency (10 pairs for each suite and variant), {80 - len(nonsig)} were significant after Holm "
        f"correction under both the paired t-test and the Wilcoxon signed-rank test. The {wnum(len(nonsig))} exceptions, "
        f"which failed at least one of the two tests, {allA}: " + ", ".join(exc[:-1]) + " and " + exc[-1] + ". For example, ksh93 was faster than dash on Suite 1 "
        f"Variant B by {abs(pair('w1','B','dash','ksh').mean_diff):.2f} ms per task (Holm-adjusted Wilcoxon p "
        f"{pv(pair('w1','B','dash','ksh').p_wilcoxon_holm)}), and dash was faster than bash by "
        f"{abs(pair('w1','B','bash','dash').mean_diff):.2f} ms (p {pv(pair('w1','B','bash','dash').p_wilcoxon_holm)}). The "
        "between-repetition standard deviation of configuration means, from "
        f"{perf.wall_between_rep_sd.min():.2f} ms to {perf.wall_between_rep_sd.max():.2f} ms, was small relative to the "
        "largest interpreter differences, which indicates that randomized interleaving kept drift and order effects "
        "below the effects of interest.")
    add("p", "The decomposition of Equation (1) explains the pattern. In Variant A the residual term T_io was negative, "
        f"for example {P('w1','bash','A','res_mean'):.2f} ms for bash on Suite 1, because the stages of each pipeline "
        "run concurrently and their CPU times add up to more than the elapsed time. In Variant B nearly all time is "
        "CPU time inside the interpreter, so interpreter efficiency is exposed directly: ksh93 spent "
        f"{P('w1','ksh','B','user_mean'):.2f} ms of user time and {P('w1','ksh','B','sys_mean'):.2f} ms of system time per "
        f"Suite 1 task, against {P('w1','bash','B','user_mean'):.2f} ms and {P('w1','bash','B','sys_mean'):.2f} ms for bash. "
        f"The high system time of bash, dash and zsh in Variant B ({P('w1','dash','B','sys_mean'):.2f} ms for dash) is "
        "consistent with the POSIX requirement that the read built-in must not consume input beyond the line it "
        "returns, which on a pipe these interpreters satisfy by reading one byte per system call; ksh93 avoided most "
        f"of this cost. In fish the system time reached {P('w1','fish','B','sys_mean'):.2f} ms per task, accompanied by "
        f"{P('w1','fish','B','nvcsw_mean'):,.2f} voluntary context switches, as discussed in the next subsection.")

    add("major", "Memory footprint, process creation and context switches")
    add("p", "Table 4 and Figure 3 separate two memory measures that are easily confused. The tree peak RSS, the "
        "quantity that getrusage reports for a waited-for process tree, lay between "
        f"{perf.rss_kb_mean.min()/1024:.2f} MB and {perf.rss_kb_mean.max()/1024:.2f} MB for every configuration. For the "
        "POSIX interpreters this value was set not by the interpreter but by the external tools, because the Rust "
        "coreutils of Ubuntu 26.04 are a single multi-call binary whose resident size exceeds that of bash, dash, "
        "zsh or ksh93. The interpreter's own peak memory, measured at the ptrace exit stop, was "
        f"{H('w1','dash','B')/1024:.2f} MB for dash, {H('w1','ksh','B')/1024:.2f} MB for ksh93, "
        f"{H('w1','bash','B')/1024:.2f} MB for bash, {H('w1','zsh','B')/1024:.2f} MB for zsh and "
        f"{H('w1','fish','B')/1024:.2f} MB for fish on Suite 1 Variant B, and it varied little across variants and "
        f"suites (from {hwm.hwm_kb_mean.min()/1024:.2f} MB to {hwm.hwm_kb_mean.max()/1024:.2f} MB overall). All 80 "
        "pairwise interpreter comparisons of this measure were significant after Holm correction. GNU time agreed "
        f"with the launcher's tree peak to within a mean absolute difference of {tc.rel_diff_pct.abs().mean():.2f}% "
        f"(maximum {tc.rel_diff_pct.abs().max():.2f}%) over {len(tc)} cross-check executions.")
    add("p", "Process creation followed the scripting paradigm rather than the interpreter. A Suite 1 task in "
        f"Variant A created {S('w1','bash','A'):.2f} processes in bash and {S('w1','ksh','A'):.2f} in ksh93, against "
        f"{S('w1','bash','B'):.2f} and {S('w1','ksh','B'):.2f} in Variant B, where only the fixed helper remained "
        f"external; Variant C needed {S('w1','bash','C'):.2f} in bash. On Suite 2, where Variant B captures one "
        "audit-helper result per subtree through command substitution, Variant B still created "
        f"{S('w2','bash','B'):.2f} processes per task in bash and {S('w2','fish','B'):.2f} in fish. Voluntary context "
        f"switches mirrored this structure for the POSIX interpreters, from {P('w1','ksh','B','nvcsw_mean'):.2f} per "
        f"Suite 1 task for ksh93 Variant B to {P('w1','zsh','A','nvcsw_mean'):.2f} for zsh Variant A. fish was the "
        f"outlier, with {P('w1','fish','B','nvcsw_mean'):,.2f} voluntary switches per Suite 1 task in Variant B while "
        f"creating {S('w1','fish','B'):.2f} processes and {S('w1','fish','B','thread_creations_mean'):.2f} threads. fish "
        "routes the output of every command substitution, including the result of its math built-in, through an "
        "internal pipe even when no process is created, so each arithmetic step costs blocking reads and writes; "
        "this is the most plausible source of both the context switches and the high system time, although the "
        "present instrumentation cannot attribute them to individual code paths. Memory efficiency in the sense of "
        "Equation (2) favored short-running configurations: the memory-delay product was lowest for ksh93 Variant B "
        f"on Suite 1 ({P('w1','ksh','B','mdp_mean'):.3f} MB s) and highest for fish Variant D "
        f"({P('w1','fish','D','mdp_mean'):.3f} MB s).")

    add("major", "Component-level ablation")
    dvb = abl[abl.contrast == "D_vs_B"]
    ns_db = dvb[dvb.p_t_holm >= 0.05]
    add("p", "Table 5 and Figure 4A isolate the scripting paradigm within each interpreter. Replacing external "
        "pipelines with native built-ins (B versus A) reduced latency in every POSIX interpreter on both suites, by "
        f"{-A('w1','zsh','B_vs_A','pct_change'):.2f}% for zsh to {-A('w1','ksh','B_vs_A','pct_change'):.2f}% for ksh93 on "
        f"Suite 1, a {A('w1','ksh','B_vs_A','speedup'):.2f}-fold speed-up for ksh93, and by "
        f"{-A('w2','zsh','B_vs_A','pct_change'):.2f}% to {-A('w2','ksh','B_vs_A','pct_change'):.2f}% on Suite 2 (all "
        "Holm-adjusted p below 0.001). In fish the same substitution increased latency by "
        f"{A('w1','fish','B_vs_A','pct_change'):.2f}% on Suite 1 and {A('w2','fish','B_vs_A','pct_change'):.2f}% on Suite 2, "
        "so the common advice to avoid external processes holds for the POSIX interpreters but is counterproductive "
        "in fish 4.2.1. Batched concurrency (C versus A) was the most consistent optimization, reducing latency by "
        f"{-A('w1','fish','C_vs_A','pct_change'):.2f}% to {-A('w1','bash','C_vs_A','pct_change'):.2f}% on Suite 1 and by "
        f"{-A('w2','fish','C_vs_A','pct_change'):.2f}% to {-A('w2','ksh','C_vs_A','pct_change'):.2f}% on Suite 2, because one "
        "batched awk process per partition replaces many short-lived tools and the partitions run in parallel on the "
        f"12 available hardware threads. The cost of fault trapping (D versus B) was small, from "
        f"{dvb["pct_change"].min():.2f}% to {dvb["pct_change"].max():.2f}% across interpreters and suites. It was not "
        "significant under the Holm-adjusted t-test for "
        + (lambda xs: xs[0] if len(xs) == 1 else ", ".join(xs[:-1]) + " and " + xs[-1])(
            [f"{LBL[r.shell]} on Suite {r.workload[1]}" for r in ns_db.itertuples()])
        + ", and it was largest for zsh, where per-record validation adds pattern matching to an already slower "
        "read loop.")

    add("major", "Fault-trapping reliability")
    add("p", "Table 6 and Figures 4B to 4D report the fault-trapping confusion matrices. No configuration raised a "
        "false alarm: all 150 fault-free tasks of each suite ended with status zero, so precision and specificity "
        "were 100.00% throughout and the comparison rests on recall. The matrices were identical for the five seeds, "
        "which indicates that the outcome of each fault was determined by the interpreter and script rather than by "
        f"timing. Without error handling, Variants A and C trapped {C('w1','bash','A','TP_mean'):.0f} of 100 faults on "
        f"Suite 1 and {C('w2','bash','A','TP_mean'):.0f} of 100 on Suite 2 in every interpreter (F1-score "
        f"{C('w1','bash','A','f1_mean'):.2f}% and {C('w2','bash','A','f1_mean'):.2f}%, false-negative rate "
        f"{C('w1','bash','A','fnr_mean'):.2f}% and {C('w2','bash','A','fnr_mean'):.2f}%). The trapped faults were exactly "
        "those that terminate the interpreter or fail its last command: the SIGTERM tasks, the write failures of "
        "Suite 1, whose output write is the last command of the script, and the consumer failures of Suite 2, whose "
        "sink is the last stage of the final pipeline. A missing or unreadable input, a corrupted record or a failing "
        "upstream helper passed silently, and the scripts reported plausible but wrong aggregates with exit status "
        "zero.")
    add("p", "Variant B exposed differences between interpreters even though the script contains no error handling. "
        "When a corrupted size field reached shell arithmetic, bash, dash, zsh and ksh93 aborted the script with an "
        "arithmetic error and a non-zero status, so Variant B trapped every corrupted-record fault on Suite 1 "
        f"(F1-score {C('w1','dash','B','f1_mean'):.2f}%), whereas the math built-in of fish printed an error and "
        f"continued (F1-score {C('w1','fish','B','f1_mean'):.2f}%). On Suite 2 a failed audit helper, whether its failure "
        "was injected directly or caused by an unreadable subtree, left an empty value in an arithmetic expansion; "
        "dash, zsh and ksh93 aborted, trapping {C('w2','dash','B','TP_mean'):.0f} of 100 "
        "faults, while bash printed a diagnostic, continued and exited with status zero, trapping "
        f"{C('w2','bash','B','TP_mean'):.0f}. These detections are side effects of expansion errors rather than designed "
        "protections, and they show how interpreter semantics can turn the same script into a fail-stop or a "
        "fail-silent program.")
    add("p", "The fault-trapped Variant D trapped all 100 faults in bash, dash, zsh and ksh93 on both suites "
        "(F1-score 100.00%, false-negative rate 0.00%). In fish, Variant D trapped "
        f"{C('w1','fish','D','TP_mean'):.0f} faults on Suite 1 and {C('w2','fish','D','TP_mean'):.0f} on Suite 2 (F1-score "
        f"{C('w1','fish','D','f1_mean'):.2f}% and {C('w2','fish','D','f1_mean'):.2f}%, false-negative rate "
        f"{C('w1','fish','D','fnr_mean'):.2f}% and {C('w2','fish','D','fnr_mean'):.2f}%). Every missed fault was a SIGTERM "
        "task. The fish signal handler ran, printed its diagnostic and called exit with status 143, and the script "
        "stopped, but fish 4.2.1 terminated with status zero, so the caller saw a successful run. A nine-line script "
        "in the supplementary package reproduces this behavior outside the benchmark. A process supervisor that "
        "relies on the exit status of a fish script would therefore record an interrupted job as successful.")
    rb = pd.read_csv(M.AN / "residual_output_rate.csv")
    rbv = lambda wl, s, v: float(rb[(rb.workload == wl) & (rb.shell == s) & (rb.variant == v)].out_exists.iloc[0])
    add("p", "Trapping a fault and cleaning up after it are not the same. Faulty executions of Variant A left a "
        f"regular output file behind in {rbv('w1','bash','A'):.2f}% of Suite 1 runs and {rbv('w2','bash','A'):.2f}% of "
        "Suite 2 runs, every one containing wrong aggregates. In Variant D of bash, dash, zsh and ksh93 this rate fell "
        f"to {rbv('w1','bash','D'):.2f}% on Suite 1 and {rbv('w2','bash','D'):.2f}% on Suite 2. The remaining Suite 1 "
        "residues were the upstream-helper failures: pipefail and set -e made the script exit with the helper's "
        "status 3, but only after the truncated aggregates had been written, and errexit terminates the script "
        "without invoking the diagnostic and rollback function. The fish translation, which inspects pipestatus "
        f"explicitly and calls that function, left no residue ({rbv('w1','fish','D'):.2f}%). Strict mode therefore "
        "propagates failures reliably, but rollback of partial output needs an explicit exit trap or explicit status "
        "checks.")
    add("p", "The ROC-AUC values in Table 6 and Figure 5A measure something different from recall. The detection score "
        "ranks executions by how much evidence of failure they leave, so a configuration that exits with status zero "
        "but prints a diagnostic on the standard error stream still separates faulty from fault-free runs. For this "
        f"reason several unprotected configurations reached a ROC-AUC of {C('w1','bash','B','auc_pooled'):.2f} although "
        f"their recall was only {C('w1','bash','B','recall_mean'):.2f}%: the failure was visible in the error stream but "
        f"was not propagated through the exit status. The lowest value, {cls_e.auc_pooled.min():.2f} for ksh93 Variants B "
        "and C on Suite 2, arose because ksh93 reported failed writes to /dev/full through its exit status only and "
        "printed nothing, so its silent write failures tied with fault-free runs. Variant D reached a ROC-AUC of 1.00 "
        "in all five interpreters, including fish, whose SIGTERM runs exited with status zero but carried the "
        "diagnostic line. ROC-AUC therefore shows that the evidence needed to detect every fault was present, while "
        "recall shows how much of it reached the caller; for automation driven by exit statuses, recall and the "
        "false-negative rate are the decisive metrics.")

    add("major", "Latency-memory trade-off and interpreter selection")
    f1 = par[(par.workload == "w1") & (par.pareto == 1)].sort_values("wall_mean")
    f2 = par[(par.workload == "w2") & (par.pareto == 1)].sort_values("wall_mean")

    def fr(f):
        items = [f"{LBL[r.shell]} Variant {r.variant}" for r in f.itertuples()]
        return items[0] if len(items) == 1 else ", ".join(items[:-1]) + " and " + items[-1]
    add("p", "Figure 5B plots mean latency against the interpreter's own peak memory. On Suite 1 the Pareto frontier "
        f"consists of {fr(f1)}, and on Suite 2 of {fr(f2)}. No interpreter was best on every axis, so selection should "
        "weigh several measured criteria rather than a single figure. For short, frequently started jobs such as "
        "hooks and container entry points, start-up time and memory dominate, and dash was the best choice with "
        f"{ST('dash','wall_mean'):.2f} ms start-up and {STH('dash')/1024:.2f} MB of memory. For data-processing scripts "
        "written with built-ins, ksh93 delivered the lowest latency on both suites at moderate memory, followed by "
        "dash. bash and zsh offer richer built-in data structures and interactive features, but they were slower "
        "than ksh93 and dash on the same POSIX code. fish had the highest start-up time, memory and built-in "
        "processing cost and, in the measured version, failed to propagate a handled signal, so it is better suited "
        "to interactive use than to unattended automation. Across interpreters, the choice of paradigm moved latency "
        "about as much as the choice of interpreter, and explicit fault trapping cost at most "
        f"{dvb["pct_change"].max():.2f}% of latency while lowering the false-negative rate of the bash Suite 1 script from "
        f"{C('w1','bash','B','fnr_mean'):.2f}% to 0.00%.")
    add("p", "These measurements extend prior work in two directions. The interpreter overhead studies of Ismail and "
        "Suh {ismail2018} and Prechelt {prechelt2000} compared general-purpose languages; for shell interpreters the "
        "present results show that the dominant cost is the interaction between scripting style and process "
        "management, the cost that Gerofi et al. {gerofi2012} sought to reduce at the operating-system level. The "
        "fault-injection studies of Koopman and DeVale {koopman2000} and Marinescu and Candea {marinescu2009} found "
        "that many failures are not reported through error codes; the shell results show the same weakness one "
        "layer higher, where unprotected scripts silently convert failures into wrong results with a successful exit "
        "status.")
    add("minor", "Limitations and Scope for Future Study")
    add("p", "All measurements were taken on one laptop inside a WSL2 virtual machine. Absolute latencies, and "
        "particularly process-creation costs, will differ on bare-metal servers, on other kernels and under "
        "concurrent load, and the host was not isolated from background Windows activity, although randomized "
        "interleaving and five repetitions bound its effect. The evaluation executions were collected in two "
        "uninterrupted segments on the same running system after a harness restart, with each seed's randomized "
        "order preserved. The external tools were the Rust coreutils of Ubuntu 26.04; GNU coreutils would change "
        "the absolute latency of Variants A and C and the tree peak memory, but not the interpreter-only "
        "measurements. Each interpreter was tested in one version, and the fish exit-status behavior was observed "
        "only in version 4.2.1. The workloads are synthetic, generated to resemble server logs and file trees; they "
        "exercise common automation patterns but cannot represent every production script. The fish scripts are "
        "translations rather than identical sources, so fish comparisons include translation choices. The "
        "development-partition executions ran in parallel and serve only as a functional-verification gate. "
        "Statements about larger fleets or longer jobs would be projections from per-task measurements and were not "
        "tested. Future work should repeat the benchmark on bare-metal hardware and other kernels, add GNU coreutils "
        "and BusyBox as alternative tool sets, include further interpreters and versions, and examine whether static "
        "analysis of scripts can flag the silent-failure patterns identified here.")
    return B


def conclusions(M):
    P, ST, STH = M.P, M.ST, M.STH
    return [
        "Five Unix shell interpreters were benchmarked on two workload suites with four scripting variants, five "
        "seeded repetitions and controlled fault injection, and every reported value was recomputed from the raw "
        f"telemetry. dash started fastest ({ST('dash','wall_mean'):.2f} ms) with the smallest memory footprint "
        f"({STH('dash')/1024:.2f} MB), ksh93 executed native built-in scripts fastest ({P('w1','ksh','B','wall_mean'):.2f} ms "
        "per log-parsing task), and fish was the slowest and largest interpreter. The scripting paradigm changed "
        "latency about as much as the interpreter did: native built-ins helped every POSIX interpreter and slowed "
        "fish, and batched concurrency helped all five.",
        "Unprotected scripts let most injected faults pass with a successful exit status in every interpreter. A "
        "fault-trapped script with strict mode, validation, checked writes and signal traps trapped every fault in "
        "bash, dash, zsh and ksh93 at a latency cost of a few percent, and in fish it missed only the "
        "signal-terminated runs, because fish exited with status zero after handling SIGTERM. Interpreter selection "
        "for system automation should therefore weigh start-up cost, built-in efficiency, memory and exit-status "
        "propagation together, and automation scripts should trap faults explicitly whichever interpreter runs them.",
    ]


def disclosures():
    return [
        ("Data Availability", "All data in this study are synthetic and were produced by the seeded generator "
         "included in the supplementary package (CJCS_Five_Unix_Shells_Supplementary_Package.zip). The package "
         "contains the task manifest with expected outputs, every raw execution record (50,000 evaluation and 40,000 "
         "development executions), the start-up, strace, ptrace and GNU time records, the verified results sheet and "
         "all tables and figures. A public repository URL or DOI has not yet been assigned; the authors will deposit "
         "the package in a public repository before publication and add its persistent identifier here."),
        ("Code Availability", "The harness, analysis, figure and manuscript-building scripts and every executed shell, "
         "fish, awk and helper script are included in the supplementary package in the exact versions that produced "
         "the reported results, and their SHA-256 checksums are recorded in environment_versions.json. The "
         "measurement launcher gained a second, ptrace-based memory mode after the timed executions; its timing path "
         "is unchanged, and the README documents this sequence."),
        ("AI Disclosure", "A large language model (Claude, Anthropic) assisted with writing the benchmarking and "
         "analysis code and with drafting and language editing of the manuscript, as stated in the Materials and "
         "Methods. All measurements were produced by deterministic scripts on the stated hardware, and no language "
         "model generated, modified or selected data. The authors verified the code, the results and the references "
         "and are accountable for the work. All figures are programmatic plots or diagrams produced with matplotlib; "
         "no generative image tool was used."),
        ("Ethics Statement", "This study used only synthetic system workloads generated by software. It involved no "
         "human participants, human data or animals, and ethics approval was therefore not required."),
        ("Author Contributions", "AUTHOR ONE: concept and design, acquisition and analysis of data, drafting of the "
         "manuscript, critical review for important intellectual content, final approval and accountability. AUTHOR "
         "TWO: design, interpretation of data, critical review for important intellectual content, final approval and "
         "accountability. AUTHOR THREE: analysis and interpretation of data, critical review for important "
         "intellectual content, final approval and accountability. All authors meet the four ICMJE criteria for "
         "authorship."),
        ("Competing Interests", "The authors declare no financial or non-financial competing interests. The study "
         "received no specific funding."),
    ]
