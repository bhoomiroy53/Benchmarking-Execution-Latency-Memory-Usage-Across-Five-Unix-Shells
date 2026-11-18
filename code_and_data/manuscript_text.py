"""manuscript_text.py - fixed prose for the Introduction and Materials and Methods.
Citations are written as {key}; build_manuscript.py numbers them in order of first appearance.
Values that come from the data are inserted from the verified results sheet at build time."""

TITLE = ("Comparative Benchmarking of Execution Latency and Memory Footprint Across Five Unix "
         "Command-Line Shell Interpreters Under System Automation Workloads")

CATEGORIES = "Operating Systems, Software Engineering, Computer Architecture"
KEYWORDS = ("Unix shell interpreters; shell script performance; execution latency benchmarking; "
            "peak resident memory; process creation overhead; fault injection testing; "
            "error handling reliability; system automation scripts")

INTRO = [
    "Unix shell interpreters remain the glue of system automation. Deployment hooks, log rotation, "
    "backup jobs, container entry points and continuous-integration steps are still written as shell "
    "scripts, and the interpreter chosen to run them affects both how fast a fleet of small jobs "
    "completes and how reliably failures surface. Several interpreters coexist on a typical Linux host: "
    "the GNU Bourne-Again Shell (bash), the Debian Almquist Shell (dash), the Z Shell (zsh), the "
    "KornShell (ksh93) and the Friendly Interactive Shell (fish). They differ in start-up cost, "
    "in how much work they perform inside the interpreter rather than in forked external programs, "
    "and in the error-handling facilities they offer, yet administrators usually select one by habit "
    "rather than by measurement.",

    "Shell scripts are recognized as both important and fragile software artifacts. Davis et al. {davis2014} "
    "built a fact extractor for bash scripts to support the migration of industrial script collections, "
    "and Tonon et al. {tonon2024} mined the historical shell operations of site reliability engineers to "
    "recommend commands, showing that shell work remains central to operations practice. Miller et al. "
    "{miller2022} re-applied random fuzz testing to Unix command-line utilities and still found utilities "
    "that crashed or hung, with unchecked return codes among the causes. Rahman et al. {rahman2019} "
    "identified seven security smells across 15,232 infrastructure-as-code scripts, Rahman and Williams "
    "{rahman2018} characterized defective configuration scripts used for continuous deployment, and Wu et al. "
    "{wu2020} found that smells are common in Dockerfiles, whose build steps are executed by a shell. "
    "These studies examine script content and defects; none of them measures how the interpreter itself "
    "behaves at run time.",

    "The cost of a shell script is dominated by process management. Gerofi et al. {gerofi2012} observed that "
    "operating system interfaces create one thread or process at a time and proposed a batched creation "
    "call, Condurache et al. {condurache2015} quantified the overhead of the mode switch that accompanies "
    "every system call, and Vicente et al. {vicente2011} reduced execution time by combining several system "
    "calls into compound calls. Interpreter overhead has been quantified for other languages: Ismail and Suh "
    "{ismail2018} decomposed the overheads of the Python interpreter, Southern and Renau {southern2016} measured "
    "the cost of deoptimization checks in a JavaScript engine, and Prechelt {prechelt2000} compared run time "
    "and memory consumption across seven languages including scripting languages. No comparable "
    "measurement exists for the interpreters that execute system automation scripts.",

    "Measurement methodology matters as much as the measurement. Weaver and McKee {weaver2008} and Weaver et al. "
    "{weaver2013} showed that even nominally deterministic hardware counters vary from run to run, De et al. "
    "{de2007} traced operating system jitter to timer interrupts and daemons, and Ferreira et al. "
    "{ferreira2008} showed that the effect of such noise depends on its frequency and duration. Iosup et al. "
    "{iosup2011} documented performance variability in production cloud services, and Papadopoulos et al. "
    "{papadopoulos2021} proposed methodological principles for reproducible performance evaluation and found "
    "that few published studies follow them. Virtualization adds a further layer: Felter et al. {felter2015}, "
    "Morabito et al. {morabito2015}, Xavier et al. {xavier2013} and Li et al. {li2017} compared hypervisor and "
    "container overheads and found them to vary by workload, and Kochberger et al. {kochberger2019} showed that "
    "the Windows Subsystem for Linux is observably different from a native Linux installation. A shell "
    "benchmark therefore needs repetitions, randomized execution order, documented seeds and a description "
    "of the execution platform.",

    "Reliability is the second dimension. Koopman and DeVale {koopman2000} found that POSIX operating systems "
    "returned error codes for only part of their exceptional inputs, Kao et al. {kao1993} traced the "
    "propagation of injected faults through a UNIX kernel, Marinescu and Candea {marinescu2009} injected "
    "faults at the boundary between applications and shared libraries, Duraes and Madeira {duraes2006} "
    "proposed the emulation of software faults from field data, and Bai et al. {bai2024} guided fault "
    "injection by the coverage of error-handling code. Shell scripts are a natural target for this "
    "approach, because a failing pipeline stage, a missing file or a delivered signal can leave a script "
    "running to completion with a successful exit status. Whether a given interpreter, together with a "
    "given scripting style, actually reports such faults to its caller has not been measured systematically.",

    "This study addresses that gap with a controlled, reproducible benchmark of five interpreters. Its "
    "contributions are fourfold. First, it measures start-up cost, wall-clock latency, CPU time, peak "
    "resident memory, context switches and process-creation counts for the five interpreters on two "
    "independent workload suites of 1,250 tasks each, with five seeded repetitions. Second, it isolates "
    "the contribution of the scripting paradigm through a four-variant component-level ablation: external "
    "pipelines, native built-ins, batched concurrency and a fault-trapped pipeline. Third, it injects six "
    "fault types per suite and evaluates fault trapping as a classification problem with confusion "
    "matrices, error rates and the area under the receiver operating characteristic curve. Fourth, it "
    "releases every script, the harness and the raw telemetry so that each number can be recomputed.",
]


def methods(env):
    """Materials and Methods paragraphs, as (kind, text) where kind is 'major', 'minor', 'lead:<label>' or 'p'."""
    sh = env["shells"]
    return [
        ("major", "Materials and methods"),
        ("p", "The study is a controlled laboratory benchmark. Five interpreters executed two families of "
              "synthetic but realistic system-automation tasks under four scripting paradigms, with injected "
              "faults on a fixed subset of tasks, five seeded repetitions and full telemetry capture. All "
              "steps are automated by a single Python harness, and the methods described here are kept separate "
              "from the results reported in the next section."),
        ("major", "Experimental setup"),
        ("lead:Hardware and operating system", "All measurements were taken on one laptop with an "
              f"{env['cpu_model']} processor (six cores, 12 hardware threads, 16 MiB L3 cache) running Windows 11 Home "
              f"with the Windows Subsystem for Linux, version 2 (WSL2). The Linux guest was {env['os_release']} with kernel "
              f"{env['kernel_release']}, 12 virtual CPUs and {int(env['mem_total'].split()[0]) / 1024 / 1024:.1f} GiB of memory "
              "visible to the guest. WSL2 runs a full Linux kernel inside a Hyper-V virtual machine, so the "
              "results describe this virtualized configuration rather than bare metal. All task inputs and "
              "scratch files were kept on the guest's native ext4 file system, never on the Windows-mounted "
              "drive, and the harness ran as an unprivileged user so that permission faults take effect."),
        ("lead:Interpreters", "The five interpreters were installed from the Ubuntu archive and invoked "
              f"non-interactively without user start-up files: bash {sh['bash']['version_string'].split()[3].split('(')[0]} "
              f"(package {sh['bash']['package_version']}), dash (package {sh['dash']['package_version']}), zsh 5.9 "
              f"(package {sh['zsh']['package_version']}, invoked with the -f option), ksh93u+m 1.0.10 (package "
              f"{sh['ksh']['package_version']}) and fish 4.2.1 (package {sh['fish']['package_version']}, invoked with "
              "--no-config). The SHA-256 checksum, size and package revision of every binary are recorded in the "
              "supplementary environment file and in Table 1. The external tools used by the scripts were the "
              f"Ubuntu defaults: {env['coreutils'].split(' ', 1)[1]} for cut, sort, wc, tr, split, head, tail and cat "
              f"(the Rust reimplementation that Ubuntu 26.04 installs in place of GNU coreutils), {env['grep']}, "
              f"{env['findutils']} and GNU Awk 5.3.2. The harness used Python {env['python']}, {env['strace'].replace(' -- version', '')} "
              "and a small C launcher compiled with GCC 15.2.0 as a static binary."),
        ("lead:Measurement instrumentation", "Each execution was started by a small statically linked C "
              "launcher that forks, executes the interpreter and collects its resource usage with the wait4 "
              "system call, which returns the getrusage record of the interpreter together with every descendant "
              "it waited for. The launcher reports wall-clock time from the monotonic clock, user and system CPU "
              "time in microseconds, voluntary and involuntary context switches and the peak resident set size "
              "(RSS). A launcher is necessary because Linux carries the pre-exec address space's peak RSS into "
              "the exec'd program; spawning interpreters directly from the 25 MB Python process would have reported "
              "the harness's memory instead of the interpreter's. The peak RSS returned by wait4 is that of the "
              "largest single process in the task's process tree, hereafter the tree peak. Because the tree peak "
              "is frequently set by an external tool rather than by the interpreter, a separate pass measured the "
              "interpreter process alone: the launcher traced the interpreter with ptrace, requesting only exit "
              "and exec events, and read the VmHWM field of /proc at the exit stop, before the kernel released "
              "the address space. Process-creation and execve counts were obtained by running a fixed subset of "
              "tasks under strace with the -f option, counting clone, clone3, fork and vfork calls that did not "
              "create threads. GNU time with the -v option was run on a further subset to cross-check the peak RSS "
              "reported by the launcher. The strace and ptrace passes perturb timing and were therefore never "
              "mixed with timed executions."),
        ("lead:Workload Suite 1", "The first suite models high-volume server log parsing and text-stream "
              "transformation. A seeded generator produced 1,250 access logs in the common combined format, each "
              "with 200 to 600 records and 502,818 records in total (49.7 MB). Each record holds a client address, "
              "a time stamp, a request method drawn from GET, POST, PUT and DELETE, a request path under one of five "
              "API resources, a status code, a response size and a latency in milliseconds. Every task reads one "
              "log through a fixed upstream helper that emulates a log-fetch tool and must report 16 aggregates: "
              "the record count, counts per status class, counts per method, the byte total, the maximum latency "
              "and counts per resource. The resource counts require associative aggregation, which the POSIX "
              "scripts emulate with eval-composed variable names and the fish scripts with variable indirection."),
        ("lead:Workload Suite 2", "The second suite models file-system traversal, process orchestration and "
              "fault recovery. The generator produced 1,250 directory trees, each with four to six top-level "
              "subtrees nested up to three levels deep, 102,128 files in total (24.7 MB) with 21 to 158 files per "
              "evaluation tree, of which about 12% are empty. Every task must count files, directories and empty "
              "files, find the maximum file depth, count files per extension, count lines across CSV files, run "
              "an external audit helper once per top-level subtree and deliver an 11-field report through an "
              "external sink process while appending to an audit log."),
        ("lead:Data partitions and seeds", "Within each suite the 1,250 tasks were split 80:20 by a seeded "
              "shuffle into a development partition of 1,000 tasks and an evaluation partition of 250 tasks. All "
              "statistics in this article come from the evaluation partition; the development partition was "
              "executed once, with seed 42, as a functional-verification gate. In each partition 40% of tasks "
              "received exactly one injected fault, giving 100 faulty and 150 fault-free evaluation tasks per "
              "suite. The corpus was generated with seed 2026. The evaluation partition was executed five times "
              "with seeds 42, 101, 202, 303 and 404. Each seed sets a fresh random interleaving of all "
              "interpreter, variant and task combinations, which removes systematic order effects, and it chooses "
              "the injection point of position-dependent faults."),
        ("lead:Fault injection", "Six fault types were injected per suite through the environment, the input "
              "or the fixed helper processes, never through the workload scripts. In Workload Suite 1 these were "
              "a missing input file, an unreadable input file, one corrupted record whose response-size field "
              "contains a letter, an upstream helper that exits with status 3 part-way through the stream, a "
              "SIGTERM sent to the interpreter part-way through the stream and an output path on /dev/full, which "
              "fails every write. In Workload Suite 2 they were a missing input root, an unreadable subtree, an "
              "audit helper that exits with status 3, a SIGTERM sent to the interpreter during auditing, an audit "
              "log on /dev/full and a sink consumer that closes its input and exits with status 1. The 100 faulty "
              "evaluation tasks were spread evenly over the six types, 16 or 17 tasks each."),
        ("minor", "Component-Level Ablation Variants"),
        ("p", "Each suite was implemented in four variants that isolate the scripting paradigm. Variant A, "
              "the external subshell and coreutils pipeline baseline, stages the input and computes each "
              "aggregate with a pipeline of external tools such as cut, grep, tr, sort, awk, find and xargs. "
              "Variant B, native shell built-ins and parameter expansion only, performs all parsing, counting and "
              "traversal inside the interpreter with read loops, case pattern matching, parameter expansion, "
              "arithmetic expansion, glob expansion and the test built-in, keeping only the fixed helper "
              "processes external. Variant C, buffered batch execution with named-pipe concurrency, splits the "
              "work into partitions, aggregates each partition with one batched awk process running as a "
              "background job, receives the partial results through one named pipe per job and merges them in "
              "the interpreter. Variant D, the complete optimized and fault-trapped pipeline, combines the native "
              "processing of Variant B with strict error handling: set -eu, pipefail where the interpreter "
              "supports it, validation of every input field, checked writes and helper exit statuses, traps for "
              "SIGTERM, SIGINT and SIGHUP, a uniform diagnostic line beginning with BENCH-FAULT and removal of "
              "partial output. Variants A to C contain no error handling by design. The four POSIX scripts per "
              "suite were executed unchanged by bash, dash, zsh and ksh93; zsh received two options, "
              "SH_WORD_SPLIT and NO_NOMATCH, set by the script itself, so that word splitting and unmatched globs "
              "follow POSIX rules. Because fish does not accept POSIX syntax, each script was translated to fish "
              "with the same external commands, the same order of operations and the same output format; fish has "
              "no errexit or pipefail options, so its Variant D implements the same protections with explicit "
              "status checks, the pipestatus variable and signal event handlers. The scripts range from 26 to 82 "
              "lines and are released in the supplementary package."),
        ("minor", "Performance Metrics"),
        ("p", "Wall-clock latency was decomposed as shown in Equation (1)."),
        ("eq1", ""),
        ("p", "In Equation (1), T_wall is the wall-clock time of one execution, T_user and T_sys are the user-mode "
              "and kernel-mode CPU times accumulated by the interpreter and every descendant it waited for, and "
              "T_io is the residual time spent blocked on input and output, waiting for the scheduler or waiting "
              "for children. T_io becomes negative when descendants run in parallel, because their CPU times then "
              "add up to more than the elapsed time. Memory efficiency was summarized by the memory-delay product "
              "of Equation (2)."),
        ("eq2", ""),
        ("p", "In Equation (2), MDP is the memory-delay product of one execution in megabyte-seconds, RSS_peak is "
              "the tree peak RSS in megabytes and T_wall is expressed in seconds; a lower MDP means that less "
              "memory is held for less time. Throughput was reported as tasks per second, the reciprocal of mean "
              "latency for sequential execution, and as megabytes of task input processed per second. Latency, "
              "CPU time, memory and context-switch statistics were computed over the 150 fault-free evaluation "
              "tasks of each suite, giving 750 executions per configuration, because faulty executions end "
              "early and would bias these measures."),
        ("minor", "Fault-Trapping Classification Metrics"),
        ("p", "Each evaluation execution was classified as a binary decision. Injected faults are positives. A "
              "fault counts as trapped when the interpreter exits with a non-zero status, including death by "
              "signal, so that a caller such as a scheduler or a continuous-integration runner can see the "
              "failure. A true positive (TP) is a faulty task that ended with a non-zero status, a false negative "
              "(FN) is a faulty task that ended with status zero, a true negative (TN) is a fault-free task that "
              "ended with status zero and a false positive (FP) is a fault-free task that ended with a non-zero "
              "status. Accuracy, precision, recall, F1-score, specificity and the false-positive rate were "
              "computed from these counts in the usual way, and the false-negative rate as in Equation (3)."),
        ("eq3", ""),
        ("p", "In Equation (3), FNR is the false-negative rate, the fraction of injected faults that the "
              "configuration let pass silently, and FN and TP are the counts defined above. To obtain a ranking "
              "score for the receiver operating characteristic (ROC) analysis, each execution also received an "
              "ordinal detection score: 3 for a non-zero exit with the BENCH-FAULT diagnostic, 2 for any other "
              "non-zero exit, 1 for a zero exit with diagnostic output on the standard error stream and 0 for a "
              "silent zero exit. The area under the ROC curve (ROC-AUC) was computed from this score as the "
              "Mann-Whitney probability that a faulty execution scores higher than a fault-free one, with ties "
              "counted as one half. AUC is preferred to accuracy as a summary of ranking quality, following Huang "
              "and Ling {huang2005}, and is reported alongside the confusion-matrix metrics, as recommended for "
              "comparative classifier studies by Lessmann et al. {lessmann2008}. Every confusion matrix sums to the "
              "250 evaluation tasks of one suite and one seed."),
        ("minor", "Statistical Analysis"),
        ("p", "Results are reported as mean and standard deviation (SD) over executions, together with the "
              "median and interquartile range (IQR). The 95% confidence interval (CI) of a mean was computed with "
              "the t distribution from the 150 task-level means, each averaged over the five repetitions, so that "
              "repeated executions of one task are not treated as independent. Interpreters and variants were "
              "compared with paired tests over the same 150 tasks. The paired t statistic is given by Equation (4)."),
        ("eq4", ""),
        ("p", "In Equation (4), t is the test statistic, d-bar is the mean of the n paired differences between two "
              "configurations on the same tasks, s_d is the sample standard deviation of those differences and "
              "n = 150 is the number of task pairs; under the null hypothesis t follows a t distribution with "
              "n - 1 degrees of freedom. Two-tailed p-values were obtained from the paired t-test and from the "
              "Wilcoxon signed-rank test, which does not assume normality. Within each family of comparisons, "
              "the 10 interpreter pairs for one suite and variant or the four ablation contrasts for one "
              "interpreter and suite, p-values were adjusted with the Holm procedure, and differences were "
              "considered significant at an adjusted p below 0.05. Classification metrics are reported as "
              "mean and SD over the five seeds. All statistics were computed with NumPy, SciPy and pandas by "
              "the analysis module of the harness, which writes every reported value to a single verified "
              "results sheet."),
        ("minor", "Use of Artificial Intelligence Tools"),
        ("p", "A large language model (Claude, Anthropic) was used to draft the benchmarking scripts, the "
              "analysis code and the text of this manuscript. The benchmarking itself was performed by "
              "deterministic scripts executed on the hardware described above; no language model was involved "
              "in producing, transforming or selecting any measurement. The authors reviewed the code, "
              "verified every reported number against the raw telemetry and take full responsibility for the "
              "content."),
    ]
