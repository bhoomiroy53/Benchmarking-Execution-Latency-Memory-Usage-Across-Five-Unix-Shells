#!/usr/bin/env python3
"""
run_unix_shell_benchmark.py - reproducible benchmark of five Unix shell interpreters
(bash, dash, zsh, ksh93, fish) under two system-automation workload suites, four
scripting-paradigm variants, five seeded repetitions and controlled fault injection.

Subcommands (run in this order on Linux; `analyze` also runs on any OS with
numpy/scipy/pandas installed):

  env        record kernel, CPU, memory, package revisions and SHA-256 of every binary
  gen        generate both workload corpora and the task manifest (seeded, deterministic)
  check      smoke-test every shell x variant on a few tasks and print diffs
  startup    measure interpreter start-up cost (shell -c ':'), 200 runs per shell
  run        execute workload tasks:  --partition dev|eval  --seeds ...
  strace     count process-creation and execve system calls on a fixed task subset
  timecheck  cross-check wait4() peak RSS against GNU time -v on a task subset
  analyze    compute every statistic and write Master_Verified_Results_Sheet.csv
  all        env, gen, startup, run dev (seed 42), run eval (5 seeds), strace, timecheck

The run-time part uses only the Python standard library. Measurements come from
os.wait4(), which returns the getrusage() record of the terminated interpreter
including every descendant it waited for.
"""
import argparse
import csv
import hashlib
import json
import os
import platform
import random
import re
import shutil
import signal
import subprocess
import sys
import threading
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
WORKLOAD_DIR = HERE / "shell_workloads"
LAUNCHER = HERE / "rusage_launcher"          # gcc -O2 -static -o rusage_launcher rusage_launcher.c
DEFAULT_WORK = Path(os.environ.get("CJCS_WORK", str(Path.home() / "cjcs_bench")))

CORPUS_SEED = 2026
REP_SEEDS = [42, 101, 202, 303, 404]
N_TASKS = 1250
N_EVAL = 250                       # 80:20 split -> 1000 development, 250 evaluation
FAULT_FRACTION = 0.40              # 100 of 250 evaluation tasks receive one injected fault
TIMEOUT_S = 30.0
STARTUP_RUNS = 200
STRACE_TASKS = 20
TIMECHECK_TASKS = 10

SHELL_ORDER = ["bash", "dash", "zsh", "ksh", "fish"]
VARIANTS = ["A", "B", "C", "D"]
VARIANT_FILES = {"A": "A_external", "B": "B_builtin", "C": "C_concurrent", "D": "D_trapped"}
WORKLOADS = ["w1", "w2"]
FAULTS = {
    "w1": ["missing_input", "unreadable_input", "corrupt_record", "helper_exit", "signal_term", "write_failure"],
    "w2": ["missing_root", "unreadable_subdir", "helper_exit", "signal_term", "write_failure", "consumer_failure"],
}

# interpreter name -> (candidate binaries, extra arguments, dialect, Debian package)
SHELL_SPECS = {
    "bash": (["bash"], [], "posix", "bash"),
    "dash": (["dash"], [], "posix", "dash"),
    "zsh":  (["zsh"], ["-f"], "posix", "zsh"),
    "ksh":  (["ksh93", "ksh"], [], "posix", "ksh"),
    "fish": (["fish"], ["--no-config"], "fish", "fish"),
}

RUN_FIELDS = ["partition", "workload", "shell", "variant", "task", "seed", "order", "fault",
              "is_faulty", "wall_ms", "user_ms", "sys_ms", "maxrss_kb", "nvcsw", "nivcsw",
              "exit_code", "timed_out", "stderr_bytes", "fault_marker", "out_exists",
              "out_correct", "in_bytes", "stderr_head"]


# ----------------------------------------------------------------------------- utilities
def sh(cmd):
    try:
        return subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=60).stdout.strip()
    except Exception as exc:  # pragma: no cover - environment probing only
        return f"unavailable ({exc})"


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for block in iter(lambda: fh.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def resolve_shells():
    out = {}
    for name in SHELL_ORDER:
        cands, args, dialect, pkg = SHELL_SPECS[name]
        path = None
        for c in cands:
            path = shutil.which(c)
            if path:
                break
        if not path:
            sys.exit(f"interpreter {name} not found; install with: sudo apt-get install -y {pkg}")
        out[name] = {"path": path, "real": os.path.realpath(path), "args": args, "dialect": dialect, "pkg": pkg}
    return out


def script_for(shells, shell, workload, variant):
    d = shells[shell]["dialect"]
    ext = "fish" if d == "fish" else "sh"
    return WORKLOAD_DIR / d / f"{workload}_{VARIANT_FILES[variant]}.{ext}"


def work_paths(work):
    return {"corpus": work / "corpus", "tmp": work / "tmp", "home": work / "home",
            "results": work / "results", "manifest": work / "corpus" / "manifest.json"}


# ----------------------------------------------------------------------------- env
def cmd_env(args):
    work = Path(args.work)
    P = work_paths(work)
    P["results"].mkdir(parents=True, exist_ok=True)
    shells = resolve_shells()
    meminfo = Path("/proc/meminfo").read_text().splitlines()
    cpu = {}
    for line in Path("/proc/cpuinfo").read_text().splitlines():
        if ":" in line:
            k, v = [x.strip() for x in line.split(":", 1)]
            if k in ("model name", "cpu MHz", "cache size", "flags") and k not in cpu:
                cpu[k] = v if k != "flags" else ("hypervisor" in v.split())
    env = {
        "captured_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "kernel_release": platform.release(),
        "uname_a": sh("uname -a"),
        "os_release": sh(". /etc/os-release && echo \"$PRETTY_NAME\""),
        "wsl": "microsoft" in platform.release().lower(),
        "cpu_model": cpu.get("model name"),
        "cpu_mhz_reported": cpu.get("cpu MHz"),
        "cpu_cache": cpu.get("cache size"),
        "cpu_hypervisor_flag": cpu.get("flags"),
        "logical_cpus": os.cpu_count(),
        "mem_total": next((l.split(":", 1)[1].strip() for l in meminfo if l.startswith("MemTotal")), None),
        "lscpu": sh("lscpu"),
        "python": sys.version.split()[0],
        "coreutils": sh("cut --version | head -n 1"),
        "grep": sh("grep --version | head -n 1"),
        "findutils": sh("find --version | head -n 1"),
        "awk": sh("readlink -f \"$(command -v awk)\"") + " | " + sh("awk -W version 2>&1 | head -n 1"),
        "strace": sh("strace -V | head -n 1"),
        "gnu_time": sh("/usr/bin/time --version 2>&1 | head -n 1"),
        "workdir": str(work),
        "workdir_filesystem": sh(f"stat -f -c %T '{work}'"),
        "running_as_root": os.geteuid() == 0,
        "shells": {},
        "workload_scripts": {},
    }
    version_cmd = {
        "bash": "{p} --version | head -n 1",
        "dash": "dpkg-query -W -f='${{Version}}' dash",
        "zsh": "{p} --version",
        "ksh": "{p} -c 'echo ${{.sh.version}}'",
        "fish": "{p} --version",
    }
    for name, s in shells.items():
        pkg_owner = sh(f"dpkg -S '{s['real']}' 2>/dev/null | head -n 1 | cut -d: -f1")
        env["shells"][name] = {
            "invocation": " ".join([s["path"], *s["args"]]),
            "binary": s["real"],
            "version_string": sh(version_cmd[name].format(p=s["path"])),
            "package": pkg_owner or s["pkg"],
            "package_version": sh(f"dpkg-query -W -f='${{Version}}' {pkg_owner or s['pkg']}"),
            "sha256": sha256(s["real"]),
            "size_bytes": os.path.getsize(s["real"]),
            "dialect": s["dialect"],
        }
    for f in sorted(WORKLOAD_DIR.rglob("*")):
        if f.is_file():
            txt = f.read_text()
            env["workload_scripts"][str(f.relative_to(WORKLOAD_DIR))] = {
                "sha256": sha256(f), "lines": txt.count("\n"), "bytes": f.stat().st_size}
    env["harness_sha256"] = sha256(Path(__file__))
    env["launcher_source_sha256"] = sha256(HERE / "rusage_launcher.c")
    env["gcc"] = sh("gcc --version | head -n 1")
    out = P["results"] / "environment_versions.json"
    out.write_text(json.dumps(env, indent=2))
    print(json.dumps({k: env[k] for k in ("kernel_release", "os_release", "cpu_model", "logical_cpus", "mem_total")}, indent=2))
    for n, s in env["shells"].items():
        print(f"{n:5s} {s['version_string']!r:60s} {s['package_version']}")
    print("wrote", out)


# ----------------------------------------------------------------------------- corpus
METHODS = [("GET", 70), ("POST", 18), ("PUT", 7), ("DELETE", 5)]
STATUSES = [(200, 62), (201, 10), (204, 8), (301, 3), (304, 4), (400, 3), (401, 2), (403, 1), (404, 4), (500, 1.5), (502, 1), (503, 0.5)]
RESOURCES = ["auth", "items", "orders", "search", "users"]
EXTS = [("csv", 25), ("json", 20), ("log", 20), ("txt", 20), ("dat", 15)]


def wchoice(rng, items):
    vals, weights = zip(*items)
    return rng.choices(vals, weights=weights, k=1)[0]


def w1_expected_from_lines(lines):
    c = dict(lines=0, s2=0, s3=0, s4=0, s5=0, get=0, post=0, put=0, delete=0, bytes=0, maxlat=0,
             r_auth=0, r_items=0, r_orders=0, r_search=0, r_users=0)
    for ln in lines:
        f = ln.split(" ")
        c["lines"] += 1
        c["s" + f[8][0]] += 1
        c[{"\"GET": "get", "\"POST": "post", "\"PUT": "put", "\"DELETE": "delete"}[f[5]]] += 1
        c["bytes"] += int(f[9])
        c["maxlat"] = max(c["maxlat"], int(f[10]))
        c["r_" + f[6].split("/")[3]] += 1
    return ("lines={lines} s2={s2} s3={s3} s4={s4} s5={s5} get={get} post={post} put={put} del={delete} "
            "bytes={bytes} maxlat={maxlat} r_auth={r_auth} r_items={r_items} r_orders={r_orders} "
            "r_search={r_search} r_users={r_users}").format(**c)


def gen_w1(task, path):
    rng = random.Random(f"{CORPUS_SEED}-w1-{task}")
    n = rng.randint(200, 600)
    t0 = rng.randint(0, 86000 - n * 2)
    out = []
    for i in range(n):
        ip = f"10.{rng.randint(0, 255)}.{rng.randint(0, 255)}.{rng.randint(1, 254)}"
        ts = t0 + i * 2 + rng.randint(0, 1)
        hh, mm, ss = ts // 3600, (ts % 3600) // 60, ts % 60
        res = rng.choice(RESOURCES)
        p = f"/api/v1/{res}/{rng.randint(1, 99999)}"
        if rng.random() < 0.3:
            p += f"?page={rng.randint(1, 50)}"
        out.append(f"{ip} - - [13/Nov/2026:{hh:02d}:{mm:02d}:{ss:02d} +0000] \"{wchoice(rng, METHODS)} {p} HTTP/1.1\" "
                   f"{wchoice(rng, STATUSES)} {rng.randint(100, 60000)} {rng.randint(1, 2500)}")
    path.write_text("\n".join(out) + "\n")
    return {"records": n, "bytes": path.stat().st_size, "expected": w1_expected_from_lines(out)}


def w2_expected(root):
    files = dirs = empty = depth = csvlines = 0
    ext = {e: 0 for e, _ in EXTS}
    for cur, dnames, fnames in os.walk(root):
        rel = Path(cur).relative_to(root)
        lvl = 0 if str(rel) == "." else len(rel.parts)
        dirs += len(dnames)
        for fn in fnames:
            fp = Path(cur) / fn
            files += 1
            depth = max(depth, lvl + 1)
            if fp.stat().st_size == 0:
                empty += 1
            e = fn.rsplit(".", 1)[1]
            ext[e] += 1
            if e == "csv":
                csvlines += fp.read_bytes().count(b"\n")
    audit = sum(len(os.listdir(root / s)) for s in sorted(os.listdir(root)) if (root / s).is_dir())
    return (f"files={files} dirs={dirs} empty={empty} depth={depth} ext_csv={ext['csv']} ext_dat={ext['dat']} "
            f"ext_json={ext['json']} ext_log={ext['log']} ext_txt={ext['txt']} csvlines={csvlines} audit={audit}")


def gen_w2(task, root):
    rng = random.Random(f"{CORPUS_SEED}-w2-{task}")
    if root.exists():
        shutil.rmtree(root)
    root.mkdir(parents=True)
    k = rng.randint(4, 6)
    counter = [0]

    def fill(d, level):
        for _ in range(rng.randint(3, 8)):
            counter[0] += 1
            e = wchoice(rng, EXTS)
            fp = d / f"f{counter[0]:03d}.{e}"
            if rng.random() < 0.12:
                fp.write_bytes(b"")
            elif e == "csv":
                rows = ["id,host,value,status"] + [f"{j},h{rng.randint(1, 40)},{rng.randint(0, 9999)},{rng.choice(['ok', 'warn', 'fail'])}"
                                                   for j in range(rng.randint(5, 40))]
                fp.write_text("\n".join(rows) + "\n")
            elif e == "json":
                fp.write_text(json.dumps({"id": counter[0], "owner": f"svc{rng.randint(1, 30)}", "size": rng.randint(1, 10 ** 6)}) + "\n")
            else:
                fp.write_text("".join(f"line {j} value={rng.randint(0, 10 ** 6)}\n" for j in range(rng.randint(1, 30))))
        if level < 3:
            for j in range(rng.randint(0, 2)):
                sub = d / f"d{level}{j}"
                sub.mkdir()
                fill(sub, level + 1)

    for s in range(1, k + 1):
        sd = root / f"s{s}"
        sd.mkdir()
        fill(sd, 1)
    nbytes = sum(f.stat().st_size for f in root.rglob("*") if f.is_file())
    nfiles = sum(1 for f in root.rglob("*") if f.is_file())
    return {"subdirs": k, "files": nfiles, "bytes": nbytes, "expected": w2_expected(root)}


def cmd_gen(args):
    work = Path(args.work)
    P = work_paths(work)
    (P["corpus"] / "w1").mkdir(parents=True, exist_ok=True)
    (P["corpus"] / "w2").mkdir(parents=True, exist_ok=True)
    manifest = {"corpus_seed": CORPUS_SEED, "n_tasks": N_TASKS, "n_eval": N_EVAL, "fault_fraction": FAULT_FRACTION,
                "faults": FAULTS, "workloads": {}}
    for wl in WORKLOADS:
        tasks = {}
        for t in range(N_TASKS):
            if wl == "w1":
                info = gen_w1(t, P["corpus"] / "w1" / f"task_{t:04d}.log")
            else:
                info = gen_w2(t, P["corpus"] / "w2" / f"task_{t:04d}")
            tasks[t] = info
            if t % 250 == 249:
                print(f"{wl}: generated {t + 1}/{N_TASKS}")
        ids = list(range(N_TASKS))
        random.Random(f"{CORPUS_SEED}-split-{wl}").shuffle(ids)
        parts = {"dev": sorted(ids[:N_TASKS - N_EVAL]), "eval": sorted(ids[N_TASKS - N_EVAL:])}
        fault_of = {}
        for pname, pids in parts.items():
            rng = random.Random(f"{CORPUS_SEED}-faults-{wl}-{pname}")
            nf = round(len(pids) * FAULT_FRACTION)
            faulty = sorted(rng.sample(pids, nf))
            for j, t in enumerate(faulty):
                fault_of[t] = FAULTS[wl][j % len(FAULTS[wl])]
        for t in tasks:
            tasks[t]["partition"] = "eval" if t in parts["eval"] else "dev"
            tasks[t]["fault"] = fault_of.get(t, "none")
        manifest["workloads"][wl] = {"partitions": parts, "tasks": {str(k): v for k, v in tasks.items()}}
    P["manifest"].write_text(json.dumps(manifest))
    for wl in WORKLOADS:
        m = manifest["workloads"][wl]
        ev = [m["tasks"][str(t)] for t in m["partitions"]["eval"]]
        print(wl, "eval faults:", {f: sum(1 for x in ev if x["fault"] == f) for f in ["none", *FAULTS[wl]]})
    print("wrote", P["manifest"])


# ----------------------------------------------------------------------------- execution core
class Runner:
    def __init__(self, work):
        self.work = Path(work)
        self.P = work_paths(self.work)
        self.shells = resolve_shells()
        self.manifest = json.loads(self.P["manifest"].read_text())
        # per-process scratch area, so parallel non-timed passes never share files
        self.P["tmp"] = self.P["tmp"] / os.environ.get("CJCS_TAG", "main")
        self.P["tmp"].mkdir(parents=True, exist_ok=True)
        self.P["home"].mkdir(parents=True, exist_ok=True)
        if not LAUNCHER.exists():
            subprocess.run(["gcc", "-O2", "-static", "-o", str(LAUNCHER), str(HERE / "rusage_launcher.c")], check=True)
        self.helpers = WORKLOAD_DIR / "helpers"
        for h in self.helpers.iterdir():
            h.chmod(0o755)
        if os.geteuid() == 0:
            sys.exit("refusing to run as root: permission-denied faults would not take effect")

    def task_info(self, wl, task):
        return self.manifest["workloads"][wl]["tasks"][str(task)]

    def prepare(self, wl, task, seed, tmpd, force_valid=False):
        """Build environment and fault materials for one run; returns (env, restore_fn, expected)."""
        info = self.task_info(wl, task)
        fault = "none" if force_valid else info["fault"]
        rng = random.Random(f"{seed}-{wl}-{task}")
        env = {"PATH": "/usr/local/bin:/usr/bin:/bin", "LC_ALL": "C", "HOME": str(self.P["home"]),
               "XDG_CONFIG_HOME": str(self.P["home"] / ".config"), "XDG_DATA_HOME": str(self.P["home"] / ".local"),
               "TMPD": str(tmpd), "OUT": str(tmpd / "out.txt"), "AWKDIR": str(WORKLOAD_DIR / "awk"),
               "HFAULT": "none", "HFAULT_AT": "0", "SFAULT": "none"}
        restore = None
        if wl == "w1":
            src = self.P["corpus"] / "w1" / f"task_{task:04d}.log"
            env["IN"] = str(src)
            env["HELPER"] = str(self.helpers / "logsrc.sh")
            n = info["records"]
            if fault == "missing_input":
                env["IN"] = str(tmpd / "missing.log")
            elif fault == "unreadable_input":
                dst = tmpd / "in.log"
                shutil.copyfile(src, dst)
                dst.chmod(0)
                env["IN"] = str(dst)
            elif fault == "corrupt_record":
                lines = src.read_text().splitlines()
                k = rng.randrange(n)
                f = lines[k].split(" ")
                f[9] = f[9][0] + "O" + f[9][2:]        # e.g. 51234 -> 5O234 (letter O)
                lines[k] = " ".join(f)
                dst = tmpd / "in.log"
                dst.write_text("\n".join(lines) + "\n")
                env["IN"] = str(dst)
            elif fault == "helper_exit":
                env["HFAULT"], env["HFAULT_AT"] = "exit", str(rng.randint(1, n - 1))
            elif fault == "signal_term":
                env["HFAULT"], env["HFAULT_AT"] = "term", str(rng.randint(1, n - 1))
            elif fault == "write_failure":
                env["OUT"] = "/dev/full"
        else:
            root = self.P["corpus"] / "w2" / f"task_{task:04d}"
            env["IN"] = str(root)
            env["HELPER"] = str(self.helpers / "audit.sh")
            env["SINK"] = str(self.helpers / "sink.sh")
            env["AUDITLOG"] = str(tmpd / "audit.log")
            k = info["subdirs"]
            if fault == "missing_root":
                env["IN"] = str(tmpd / "missing_root")
            elif fault == "unreadable_subdir":
                victim = root / f"s{rng.randint(1, k)}"
                victim.chmod(0)
                restore = lambda v=victim: v.chmod(0o755)
            elif fault == "helper_exit":
                env["HFAULT"], env["HFAULT_AT"] = "exit", str(rng.randint(1, k))
            elif fault == "signal_term":
                env["HFAULT"], env["HFAULT_AT"] = "term", str(rng.randint(1, k))
            elif fault == "write_failure":
                env["AUDITLOG"] = "/dev/full"
            elif fault == "consumer_failure":
                env["SFAULT"] = "close"
        return env, restore, fault, info

    def spawn(self, argv, env, errpath, hwm=False):
        """Run argv under the static rusage launcher (see rusage_launcher.c for why).
        hwm=True adds the ptrace exit-stop reading of the interpreter's own VmHWM."""
        res = self.P["tmp"] / "rusage.txt"
        if res.exists():
            res.unlink()
        fa = [(os.POSIX_SPAWN_OPEN, 0, "/dev/null", os.O_RDONLY, 0),
              (os.POSIX_SPAWN_OPEN, 1, "/dev/null", os.O_WRONLY, 0),
              (os.POSIX_SPAWN_OPEN, 2, str(errpath), os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o644)]
        timed_out = [False]
        t0 = time.perf_counter_ns()
        largv = [str(LAUNCHER), *(["--hwm"] if hwm else []), str(res), *argv]
        pid = os.posix_spawn(largv[0], largv, env, file_actions=fa, setpgroup=0)

        def kill():
            timed_out[0] = True
            try:
                os.killpg(pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
        timer = threading.Timer(TIMEOUT_S, kill)
        timer.start()
        _, status, ru = os.wait4(pid, 0)
        t1 = time.perf_counter_ns()
        timer.cancel()
        try:                                   # reap orphaned background jobs, if any
            os.killpg(pid, signal.SIGKILL)
        except (ProcessLookupError, PermissionError):
            pass
        if timed_out[0] or not res.exists():
            return {"wall_ms": (t1 - t0) / 1e6, "user_ms": float("nan"), "sys_ms": float("nan"),
                    "maxrss_kb": float("nan"), "nvcsw": float("nan"), "nivcsw": float("nan"),
                    "exit_code": -9, "timed_out": 1}
        fields = res.read_text().split()
        w, ut, st, rss, nv, ni, raw = fields[:7]
        out = {"wall_ms": int(w) / 1e6, "user_ms": int(ut) / 1e3, "sys_ms": int(st) / 1e3,
               "maxrss_kb": int(rss), "nvcsw": int(nv), "nivcsw": int(ni),
               "exit_code": os.waitstatus_to_exitcode(int(raw)), "timed_out": 0}
        if hwm:
            out["interp_hwm_kb"], out["tracee_execs"] = int(fields[7]), int(fields[8])
        return out

    def argv(self, shell, wl, variant):
        s = self.shells[shell]
        return [s["path"], *s["args"], str(script_for(self.shells, shell, wl, variant))]

    def run_one(self, wl, shell, variant, task, seed, force_valid=False, wrapper=None, hwm=False):
        tmpd = self.P["tmp"] / "run"
        if tmpd.exists():
            subprocess.run(["chmod", "-R", "u+rwx", str(tmpd)], check=False)
            shutil.rmtree(tmpd)
        tmpd.mkdir()
        env, restore, fault, info = self.prepare(wl, task, seed, tmpd, force_valid)
        errpath = self.P["tmp"] / "stderr.txt"
        argv = self.argv(shell, wl, variant)
        if wrapper:
            argv = wrapper + argv
        try:
            m = self.spawn(argv, env, errpath, hwm=hwm)
        finally:
            if restore:
                restore()
        err = errpath.read_bytes()
        out = Path(env["OUT"])
        out_exists = out.is_file()
        correct = ""
        if fault == "none":
            correct = int(out_exists and out.read_text().strip() == info["expected"])
        m.update({"fault": fault, "is_faulty": int(fault != "none"), "stderr_bytes": len(err),
                  "fault_marker": int(b"BENCH-FAULT" in err), "out_exists": int(out_exists),
                  "out_correct": correct, "in_bytes": info["bytes"],
                  "stderr_head": err[:240].decode("utf-8", "replace").replace("\n", " | ").replace("\r", " ")})
        return m, err


def cmd_check(args):
    r = Runner(args.work)
    bad = 0
    for wl in WORKLOADS:
        tasks = r.manifest["workloads"][wl]["partitions"]["dev"][:3]
        for shell in SHELL_ORDER:
            for v in VARIANTS:
                for t in tasks:
                    m, err = r.run_one(wl, shell, v, t, 42, force_valid=True)
                    ok = m["out_correct"] == 1 and m["exit_code"] == 0
                    bad += not ok
                    if not ok or args.verbose:
                        got = (r.P["tmp"] / "run" / "out.txt")
                        print(f"{'OK ' if ok else 'BAD'} {wl} {shell:4s} {v} task {t} exit={m['exit_code']} "
                              f"wall={m['wall_ms']:.1f}ms\n   expected: {r.task_info(wl, t)['expected']}\n"
                              f"   got:      {got.read_text().strip() if got.exists() else '<no output>'}\n"
                              f"   stderr:   {err[:300]!r}")
                print(f"{wl} {shell:4s} {v}: done")
        # one pass over every fault type with seed 42
        for f in FAULTS[wl]:
            t = next(int(k) for k, x in r.manifest["workloads"][wl]["tasks"].items() if x["fault"] == f and x["partition"] == "dev")
            for shell in SHELL_ORDER:
                row = []
                for v in VARIANTS:
                    m, err = r.run_one(wl, shell, v, t, 42)
                    row.append(f"{v}:exit={m['exit_code']},err={m['stderr_bytes']},mk={m['fault_marker']},to={m['timed_out']}")
                print(f"FAULT {wl} {f:18s} {shell:4s} " + "  ".join(row))
    print("failures:", bad)


def load_done(path):
    done = set()
    if path.exists():
        with open(path, newline="") as fh:
            for row in csv.DictReader(fh):
                done.add((row["partition"], row["workload"], row["shell"], row["variant"], row["task"], row["seed"]))
    return done


def cmd_run(args):
    r = Runner(args.work)
    r.P["results"].mkdir(parents=True, exist_ok=True)
    shard_i, shard_n = (int(x) for x in args.shard.split("/")) if args.shard else (0, 1)
    out = r.P["results"] / ("raw_runs.csv" if shard_n == 1 else f"raw_runs_{args.partition}_shard{shard_i}.csv")
    done = load_done(out)
    new = not out.exists()
    fh = open(out, "a", newline="")
    w = csv.DictWriter(fh, fieldnames=RUN_FIELDS)
    if new:
        w.writeheader()
    for seed in args.seeds:
        jobs = []
        for wl in args.workloads:
            for k, t in enumerate(r.manifest["workloads"][wl]["partitions"][args.partition]):
                if k % shard_n != shard_i:
                    continue
                for shell in SHELL_ORDER:
                    for v in VARIANTS:
                        jobs.append((wl, shell, v, t))
        random.Random(seed).shuffle(jobs)          # randomized interleaving removes order bias
        t_start = time.time()
        for i, (wl, shell, v, t) in enumerate(jobs):
            key = (args.partition, wl, shell, v, str(t), str(seed))
            if key in done:
                continue
            m, _ = r.run_one(wl, shell, v, t, seed)
            m.update({"partition": args.partition, "workload": wl, "shell": shell, "variant": v,
                      "task": t, "seed": seed, "order": i})
            w.writerow(m)
            if i % 500 == 0:
                fh.flush()
                el = time.time() - t_start
                print(f"[{args.partition} seed {seed}] {i}/{len(jobs)}  elapsed {el / 60:.1f} min", flush=True)
        fh.flush()
    fh.close()
    print("wrote", out)


def cmd_startup(args):
    r = Runner(args.work)
    r.P["results"].mkdir(parents=True, exist_ok=True)
    jobs = [s for s in SHELL_ORDER for _ in range(STARTUP_RUNS)]
    random.Random(REP_SEEDS[0]).shuffle(jobs)
    rows = []
    env = {"PATH": "/usr/local/bin:/usr/bin:/bin", "LC_ALL": "C", "HOME": str(r.P["home"]),
           "XDG_CONFIG_HOME": str(r.P["home"] / ".config"), "XDG_DATA_HOME": str(r.P["home"] / ".local")}
    for i, s in enumerate(jobs):
        sp = r.shells[s]
        argv = [sp["path"], *sp["args"], "-c", "true" if sp["dialect"] == "fish" else ":"]
        m = r.spawn(argv, env, r.P["tmp"] / "stderr.txt")
        m.update({"shell": s, "order": i})
        rows.append(m)
    with open(r.P["results"] / "startup_runs.csv", "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)
    print("wrote startup_runs.csv")


CLONE_RE = re.compile(r"^\d+\s+(clone3?|fork|vfork)\(")
EXEC_RE = re.compile(r"^\d+\s+execve\(")


def cmd_strace(args):
    r = Runner(args.work)
    if not shutil.which("strace"):
        sys.exit("strace not installed")
    rows = []
    for wl in WORKLOADS:
        m = r.manifest["workloads"][wl]
        valid = [t for t in m["partitions"]["eval"] if m["tasks"][str(t)]["fault"] == "none"][:STRACE_TASKS]
        for shell in [x for x in SHELL_ORDER if not getattr(args, "shells", []) or x in args.shells]:
            for v in VARIANTS:
                for t in valid:
                    trace = r.P["tmp"] / "strace.txt"
                    wrapper = ["/usr/bin/strace", "-f", "-qq", "-o", str(trace), "-e", "trace=clone,clone3,fork,vfork,execve"]
                    _, _ = r.run_one(wl, shell, v, t, REP_SEEDS[0], force_valid=True, wrapper=wrapper)
                    procs = threads = execs = exec_fail = 0
                    for line in trace.read_text(errors="replace").splitlines():
                        if "resumed>" in line:
                            if "execve resumed>" in line and re.search(r"=\s*-1", line):
                                execs -= 1          # an unfinished execve that later failed
                                exec_fail += 1
                            continue
                        if CLONE_RE.match(line):
                            if "CLONE_THREAD" in line:
                                threads += 1
                            else:
                                procs += 1
                        elif EXEC_RE.match(line):
                            if re.search(r"\)\s*=\s*0\s*$", line) or "<unfinished" in line:
                                execs += 1
                            else:
                                exec_fail += 1
                    # the first execve is strace starting the interpreter itself
                    rows.append({"workload": wl, "shell": shell, "variant": v, "task": t,
                                 "process_creations": procs, "thread_creations": threads,
                                 "execve_ok": max(execs - 1, 0), "execve_failed": exec_fail})
                print(f"strace {wl} {shell} {v} done", flush=True)
    name = "strace_counts.csv" if not getattr(args, "shells", []) else f"strace_counts_{'_'.join(args.shells)}.csv"
    with open(r.P["results"] / name, "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)
    print("wrote", name)


def cmd_shellmem(args):
    """Interpreter-only peak RSS (VmHWM at the ptrace exit-stop) on every fault-free
    evaluation task, seed 42, all 40 configurations. Separate from the timed runs."""
    r = Runner(args.work)
    rows = []
    jobs = []
    for wl in WORKLOADS:
        m = r.manifest["workloads"][wl]
        for t in m["partitions"]["eval"]:
            if m["tasks"][str(t)]["fault"] == "none":
                for shell in SHELL_ORDER:
                    for v in VARIANTS:
                        jobs.append((wl, shell, v, t))
    random.Random(REP_SEEDS[0]).shuffle(jobs)
    for i, (wl, shell, v, t) in enumerate(jobs):
        res, _ = r.run_one(wl, shell, v, t, REP_SEEDS[0], force_valid=True, hwm=True)
        rows.append({"workload": wl, "shell": shell, "variant": v, "task": t,
                     "interp_hwm_kb": res.get("interp_hwm_kb"), "tracee_execs": res.get("tracee_execs"),
                     "tree_maxrss_kb": res["maxrss_kb"], "exit_code": res["exit_code"],
                     "out_correct": res["out_correct"]})
        if i % 1000 == 0:
            print(f"shellmem {i}/{len(jobs)}", flush=True)
    with open(r.P["results"] / "interpreter_hwm.csv", "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)
    # start-up only (shell -c ':'), 50 runs per interpreter
    srows = []
    env = {"PATH": "/usr/local/bin:/usr/bin:/bin", "LC_ALL": "C", "HOME": str(r.P["home"])}
    for s in SHELL_ORDER:
        sp = r.shells[s]
        for _ in range(50):
            m = r.spawn([sp["path"], *sp["args"], "-c", "true" if sp["dialect"] == "fish" else ":"], env,
                        r.P["tmp"] / "stderr.txt", hwm=True)
            srows.append({"shell": s, "interp_hwm_kb": m["interp_hwm_kb"], "tree_maxrss_kb": m["maxrss_kb"]})
    with open(r.P["results"] / "startup_hwm.csv", "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(srows[0].keys()))
        w.writeheader()
        w.writerows(srows)
    print("wrote interpreter_hwm.csv and startup_hwm.csv")


def cmd_timecheck(args):
    r = Runner(args.work)
    rows = []
    m = r.manifest["workloads"]["w1"]
    valid = [t for t in m["partitions"]["eval"] if m["tasks"][str(t)]["fault"] == "none"][:TIMECHECK_TASKS]
    for shell in SHELL_ORDER:
        for t in valid:
            tv = r.P["tmp"] / "time_v.txt"
            res, _ = r.run_one("w1", shell, "B", t, REP_SEEDS[0], force_valid=True,
                               wrapper=["/usr/bin/time", "-v", "-o", str(tv)])
            txt = tv.read_text()
            gnu = int(re.search(r"Maximum resident set size \(kbytes\): (\d+)", txt).group(1))
            direct, _ = r.run_one("w1", shell, "B", t, REP_SEEDS[0], force_valid=True)
            rows.append({"shell": shell, "task": t, "gnu_time_maxrss_kb": gnu, "wait4_maxrss_kb": direct["maxrss_kb"]})
    with open(r.P["results"] / "timecheck.csv", "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)
    print("wrote timecheck.csv")


def cmd_all(args):
    cmd_env(args)
    if not work_paths(Path(args.work))["manifest"].exists():
        cmd_gen(args)
    cmd_startup(args)
    a = argparse.Namespace(**vars(args))
    a.partition, a.seeds, a.workloads = "dev", [REP_SEEDS[0]], WORKLOADS
    cmd_run(a)
    a.partition, a.seeds = "eval", REP_SEEDS
    cmd_run(a)
    cmd_strace(args)
    cmd_timecheck(args)


# ----------------------------------------------------------------------------- analysis
def cmd_analyze(args):
    sys.path.insert(0, str(HERE))
    from analysis_core import analyze  # noqa: E402  (kept separate: needs numpy/scipy/pandas)
    analyze(Path(args.results), Path(args.out))


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--work", default=str(DEFAULT_WORK))
    sub = ap.add_subparsers(dest="cmd", required=True)
    for name in ["env", "gen", "startup", "timecheck", "shellmem", "all"]:
        sub.add_parser(name)
    stp = sub.add_parser("strace")
    stp.add_argument("--shells", nargs="*", default=[])
    c = sub.add_parser("check")
    c.add_argument("--verbose", action="store_true")
    rp = sub.add_parser("run")
    rp.add_argument("--partition", choices=["dev", "eval"], default="eval")
    rp.add_argument("--seeds", type=int, nargs="+", default=REP_SEEDS)
    rp.add_argument("--workloads", nargs="+", default=WORKLOADS)
    rp.add_argument("--shard", default="", help="i/n: run every n-th task starting at i (non-timed passes only)")
    an = sub.add_parser("analyze")
    an.add_argument("--results", required=True)
    an.add_argument("--out", required=True)
    args = ap.parse_args()
    {"env": cmd_env, "gen": cmd_gen, "check": cmd_check, "run": cmd_run, "startup": cmd_startup,
     "strace": cmd_strace, "timecheck": cmd_timecheck, "shellmem": cmd_shellmem, "all": cmd_all, "analyze": cmd_analyze}[args.cmd](args)


if __name__ == "__main__":
    main()
