// Ζ·sched-batch — set SCHED_BATCH + nice + a long EEVDF slice on a task, best-effort.
//
// paperkit's Δ grid runs many concurrent CPU-bound python cells; under the default fair-class slice
// (MEASURED at 2.8ms) they preempt each other constantly — ~30% sys, 15-20k ctx-switch/s, run-queue
// 2-3x cores (a third of the CPU spent switching, and under zswap the refault churn from short slices
// is codec CPU too, so short slices also inflate swap TRAFFIC si/so).  SCHED_BATCH stops the scheduler
// preempting a cell for interactivity; nice 19 yields to the IDE; the long sched_runtime SLICE lets a
// scheduled cell run a LONG uninterrupted stretch — so preemption AND refault churn collapse.  Per-task,
// UNPRIVILEGED (SCHED_BATCH + nice-down + the fair-class slice need no CAP_SYS_NICE for a same-user task).
// chrt CANNOT set the fair-class slice (its -T is DEADLINE-only), hence raw sched_setattr.
//
// Rust, single-file (no cargo, no crates): the toolchain is provisioned by mise (already a paperkit hook
// dep — `mise exec -- bazel`), so rustc is as reachable as bazel.  Adapted from
// ~/github/substrate/scripts/sched-batch.rs — paperkit owns this copy, and picks the syscall number by
// target_arch (substrate's bare 314 is x86_64-only) so it is arch-correct where we know the number and
// best-effort (exec untuned) where we don't.
//   rustc -O -o tools/sched-batch tools/sched-batch.rs
//
// Modes:
//   sched-batch -- <cmd> [args...]   tune SELF, then exec <cmd>            (per-action, Phase 2 — durable)
//   sched-batch --pid <PID>          tune one task (its MAIN thread) then exit
//   sched-batch --all-threads <PID>  tune EVERY thread of <PID> then exit  (bazel server pool)
//
// Scheduling is PER-THREAD: sched_setattr(tgid) tunes only the MAIN thread, so a multi-threaded server
// (bazel) that forks actions from its WORKER threads leaves those cells untuned.  --all-threads iterates
// /proc/<PID>/task to tune the whole pool; PARTIAL + DECAYING (threads spawned after are untuned), so the
// durable fix is the per-action `-- <cmd>` self-tune where each cell tunes itself at exec.
//
// Env (optional): PK_SCHED_NICE (default 19) · PK_SCHED_SLICE_MS (default 100, kernel-clamped) ·
//                 PK_SCHED_OFF (set -> skip tuning; `--` still execs, `--pid`/`--all-threads` no-op).
// Best-effort: any sched_setattr failure (old kernel / container / unknown arch) is IGNORED.

use std::env;
use std::fs;
use std::os::raw::c_long;
use std::os::unix::process::CommandExt;
use std::process::Command;

#[repr(C)]
struct SchedAttr {
    size: u32,
    policy: u32,
    flags: u64,
    nice: i32,
    priority: u32,
    runtime: u64, // EEVDF: requested per-task slice (ns) for fair-class tasks
    deadline: u64,
    period: u64,
}

extern "C" {
    fn syscall(num: c_long, ...) -> c_long;
}

// sched_setattr syscall number, per arch (best-effort: None -> skip the syscall, still exec).
#[cfg(target_arch = "x86_64")]
const SYS_SCHED_SETATTR: Option<c_long> = Some(314);
#[cfg(target_arch = "aarch64")]
const SYS_SCHED_SETATTR: Option<c_long> = Some(274);
#[cfg(not(any(target_arch = "x86_64", target_arch = "aarch64")))]
const SYS_SCHED_SETATTR: Option<c_long> = None;

const SCHED_BATCH: u32 = 3;

fn tune(pid: c_long) {
    if env::var_os("PK_SCHED_OFF").is_some() {
        return;
    }
    let nr = match SYS_SCHED_SETATTR {
        Some(n) => n,
        None => return, // unknown arch: best-effort, leave scheduling as-is
    };
    let nice: i32 = env::var("PK_SCHED_NICE").ok().and_then(|s| s.parse().ok()).unwrap_or(19);
    let slice_ms: u64 = env::var("PK_SCHED_SLICE_MS").ok().and_then(|s| s.parse().ok()).unwrap_or(100);
    let a = SchedAttr {
        size: std::mem::size_of::<SchedAttr>() as u32,
        policy: SCHED_BATCH,
        flags: 0,
        nice,
        priority: 0,
        runtime: slice_ms.saturating_mul(1_000_000), // ms -> ns
        deadline: 0,
        period: 0,
    };
    // sched_setattr(pid, &attr, flags=0) — return ignored (tuning is best-effort).
    unsafe {
        syscall(nr, pid, &a as *const SchedAttr, 0 as c_long);
    }
}

fn main() {
    let args: Vec<String> = env::args().collect();

    if args.len() >= 3 && args[1] == "--pid" {
        tune(args[2].parse::<c_long>().unwrap_or(0)); // one task's main thread, exit
        return;
    }
    if args.len() >= 3 && args[1] == "--all-threads" {
        // per-thread: tune EVERY thread of the pid so cells forked from any worker inherit
        if let Ok(entries) = fs::read_dir(format!("/proc/{}/task", args[2])) {
            for e in entries.flatten() {
                if let Ok(tid) = e.file_name().to_string_lossy().parse::<c_long>() {
                    tune(tid);
                }
            }
        }
        return;
    }

    let mut i = 1;
    if i < args.len() && args[i] == "--" {
        i += 1;
    }
    if i >= args.len() {
        eprintln!("sched-batch: usage: sched-batch [--pid PID | --all-threads PID] | -- <cmd> [args...]");
        std::process::exit(2);
    }
    tune(0); // self, then exec
    let err = Command::new(&args[i]).args(&args[i + 1..]).exec();
    eprintln!("sched-batch: exec {}: {}", args[i], err);
    std::process::exit(127);
}
