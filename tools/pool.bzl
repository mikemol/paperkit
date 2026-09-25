"""Ζ·render·pool — the ONE owner of the executor-pool name a `toolchain` warrant runs in.

The pool is a luthen-observability Deployment running paperkit's OWN executor image
(image/executor/Containerfile: the vendor executor base + pandoc, TeX Live, LibreOffice, poppler,
tesseract, veraPDF, the pk_render python deps).  The generator (bibtex.bzl) stamps it onto every
toolchain-tier target as `exec_properties = {"Pool": …}`; the rule (verb.bzl) reads the same name
so neither side can drift from the other.  `sandbox` and `local` never name a pool: they run in
the unnamed default pool, whose thin image is what makes the mutation sweep cheap.

The name is a constant, not a build setting: there is exactly one such pool and it is selected
by tier, not by invocation.  If a second toolchain image ever exists, this becomes a dict keyed
by tier (or by warrant), still here.
"""

TOOLCHAIN_POOL = "paperkit"
