/* Ζ·sched-batch — set SCHED_BATCH + nice + a long EEVDF slice on a task, best-effort.
 *
 * paperkit's Δ grid runs many concurrent CPU-bound python cells; under the default short
 * fair-class slice they preempt each other constantly (measured: ~30% sys, 15-20k ctx-switch/s,
 * run-queue 2-3x cores).  SCHED_BATCH stops the scheduler waking/preempting a cell for
 * interactivity; nice 19 yields to the IDE (cells run on spare CPU); the long sched_runtime
 * SLICE lets a scheduled cell run a LONG uninterrupted stretch, NOT preempted merely because a
 * peer is runnable — so preemption churn (the sys/ctx-switch cost) collapses.  Per-task,
 * UNPRIVILEGED (SCHED_BATCH + nice-down + the fair-class slice need no CAP_SYS_NICE for a
 * same-user task).  chrt CANNOT set the fair-class slice (its -T is DEADLINE-only), hence the raw
 * sched_setattr.  Adapted from ~/github/substrate/scripts/sched-batch.rs — paperkit owns this copy
 * (portability: no dependency on substrate's path or on rustc; cc is more universally present).
 *
 * Modes:
 *   sched-batch -- <cmd> [args...]   tune SELF, then exec <cmd>            (per-action, Phase 2 — durable)
 *   sched-batch --pid <PID>          tune one task (its main thread) then exit
 *   sched-batch --all-threads <PID>  tune EVERY thread of <PID> then exit  (bazel server pool)
 *
 * Scheduling is PER-THREAD: sched_setattr(tgid) tunes only the MAIN thread, so a multi-threaded
 * server (bazel) that forks actions from its WORKER threads leaves those cells untuned.
 * --all-threads iterates /proc/<PID>/task to tune the whole pool; a cell forked from any of them
 * then inherits.  This is PARTIAL and DECAYS: threads the server spawns AFTER the tune are untuned,
 * so their cells are untuned — the durable fix is the per-action `-- <cmd>` self-tune (Phase 2),
 * where each cell tunes itself at exec regardless of which thread forked it.
 *
 * Env (optional): PK_SCHED_NICE (default 19) · PK_SCHED_SLICE_MS (default 100, kernel-clamped) ·
 *                 PK_SCHED_OFF (set -> skip tuning; mode `--` still execs, `--pid` is a no-op).
 * Best-effort: any sched_setattr failure (old kernel / container / unsupported arch) is IGNORED.
 *
 *   cc -O2 -o tools/sched-batch tools/sched-batch.c
 */
#define _GNU_SOURCE
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
#include <sys/syscall.h>
#include <stdint.h>
#include <dirent.h>

/* sched_setattr's struct — stable ABI; not always in libc headers, so declared here. */
struct sched_attr {
    uint32_t size;
    uint32_t sched_policy;
    uint64_t sched_flags;
    int32_t  sched_nice;
    uint32_t sched_priority;
    uint64_t sched_runtime;   /* EEVDF: requested per-task slice (ns) for fair-class tasks */
    uint64_t sched_deadline;
    uint64_t sched_period;
};

#ifndef SCHED_BATCH
#define SCHED_BATCH 3
#endif

static void tune(pid_t pid) {
    if (getenv("PK_SCHED_OFF")) return;
    long nice = 19, slice_ms = 100;
    const char *e;
    if ((e = getenv("PK_SCHED_NICE")))     nice = strtol(e, NULL, 10);
    if ((e = getenv("PK_SCHED_SLICE_MS"))) slice_ms = strtol(e, NULL, 10);
    struct sched_attr a;
    memset(&a, 0, sizeof(a));
    a.size = sizeof(a);
    a.sched_policy = SCHED_BATCH;
    a.sched_nice = (int32_t)nice;
    a.sched_runtime = (uint64_t)slice_ms * 1000000ull;  /* ms -> ns */
    /* pid 0 = self.  Return ignored — tuning is best-effort. */
    syscall(__NR_sched_setattr, pid, &a, 0u);
}

int main(int argc, char **argv) {
    if (argc >= 3 && strcmp(argv[1], "--pid") == 0) {
        tune((pid_t)strtol(argv[2], NULL, 10));   /* tune one task's main thread, exit */
        return 0;
    }
    if (argc >= 3 && strcmp(argv[1], "--all-threads") == 0) {
        /* per-thread: tune EVERY thread of the pid so cells forked from any worker inherit */
        char path[64];
        snprintf(path, sizeof(path), "/proc/%s/task", argv[2]);
        DIR *d = opendir(path);
        if (d) {
            struct dirent *e;
            while ((e = readdir(d))) {
                if (e->d_name[0] < '0' || e->d_name[0] > '9') continue;   /* skip . .. */
                tune((pid_t)strtol(e->d_name, NULL, 10));
            }
            closedir(d);
        }
        return 0;
    }
    int i = 1;
    if (i < argc && strcmp(argv[i], "--") == 0) i++;
    if (i >= argc) {
        fprintf(stderr, "sched-batch: usage: sched-batch [--pid PID] | -- <cmd> [args...]\n");
        return 2;
    }
    tune(0);                                       /* Phase 2: tune self, then exec */
    execvp(argv[i], &argv[i]);
    fprintf(stderr, "sched-batch: exec %s: ", argv[i]);
    perror(NULL);
    return 127;
}
