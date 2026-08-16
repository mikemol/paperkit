#!/bin/sh
# Ρ·render·format — select the render ROUTE (Ω·config): a consumer builds the paper's PDF deliverable
# via the intermediate format they want.  Every route terminates at the PDF node (graph.py), reached
# through a chosen intermediate — so this is a thin selector over `pdf.py --via <route>`, NOT a set of
# rival scripts.  Format is RENDER-LOCAL orchestration, not an engine concern: the engine projects
# paper.md format-agnostically and the render coalgebra renders it several ways, so a Param in the
# engine's registry would be a knob it does not own.
#
#   PAPERKIT_FORMAT=docx (default) → pdf.py --via docx  (md→docx→pdf, office UA-1: link/math/widen)
#   PAPERKIT_FORMAT=odf            → pdf.py --via odf   (md→odt→pdf,  office UA-1: link/math/widen)
#   PAPERKIT_FORMAT=latex          → pdf.py --via latex (md→latex→pdf, native UA-2: \DocumentMetadata)
#
# Each route is an independently gated warrant, so the paper is verified via every route regardless of
# this selector — it just picks which deliverable to BUILD.  The route names are graph.ROUTES; adding
# a node/edge (a beamer slide target) is a matrix entry, and this selector follows it.
#
#   PAPERKIT_FORMAT=latex sh checks/render.sh   # build the paper's PDF via the chosen route
#   sh checks/render.sh --selftest              # ⟨P,F,δ⟩: the selector dispatches on the format
set -eu

format="${PAPERKIT_FORMAT:-docx}"

if [ "${1:-}" = "--selftest" ]; then
    # ⟨P,F,δ⟩: the selector routes PAPERKIT_FORMAT onto a graph route.  P: docx/odf/latex map to the
    # matching --via.  F: an unknown format is refused, not silently defaulted.  δ: the one env var.
    ok=0
    [ "$(PAPERKIT_FORMAT=docx  sh "$0" --which)" = "docx"  ] || ok=1
    [ "$(PAPERKIT_FORMAT=odf   sh "$0" --which)" = "odf"   ] || ok=1
    [ "$(PAPERKIT_FORMAT=latex sh "$0" --which)" = "latex" ] || ok=1
    [ "$(sh "$0" --which)" = "docx" ] || ok=1                                # default is docx
    if PAPERKIT_FORMAT=bogus sh "$0" --which >/dev/null 2>&1; then ok=1; fi  # unknown → refused
    if [ "$ok" = 0 ]; then
        echo "  ok P: docx/odf/latex → pdf.py --via <route>, default docx"
        echo "  ok F: an unknown format is refused, not silently defaulted"
        echo "  ok δ: PAPERKIT_FORMAT is the one selector"
        echo "RENDER SELFTEST: PASS"
        exit 0
    fi
    echo "RENDER SELFTEST: FAIL" >&2
    exit 1
fi

# The format names ARE the graph's route keys (graph.ROUTES): docx|odf|latex.
case "$format" in
    docx|odf|latex) route="$format" ;;
    *) echo "render: unknown PAPERKIT_FORMAT=$format (expected docx|odf|latex)" >&2; exit 2 ;;
esac

# --which prints the selected route (for the selftest to assert the routing) without running it.
if [ "${1:-}" = "--which" ]; then
    echo "$route"
    exit 0
fi

exec python3 checks/pdf.py --via "$route"
