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
 * Two modes:
 *   sched-batch -- <cmd> [args...]   tune SELF, then exec <cmd>            (per-action, Phase 2)
 *   sched-batch --pid <PID>          tune an EXISTING task then exit; its
 *                                    later-forked children inherit          (server-tune, Phase 1)
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
        tune((pid_t)strtol(argv[2], NULL, 10));   /* Phase 1: tune an existing task, exit */
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
