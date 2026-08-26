#!/usr/bin/env python3
"""paperkit/labelmap.py — Λ·label·carrier: the concept/label/route index, and the contrast instrument.

A LABEL is a point in an orbit: it names a concept FROM THE CARRIER one was standing in.  "Current
divider", "bridge null", "pareto crossover" and "argmin" are four labels for one structure, coined
in four carriers.  So a concept has ONE identity and MANY labels, and the label records where it was
coined — which is why the map is `concept -> {carrier: label}` and not `label -> concept`.

This makes the map usable in two directions:

    lookup(term)     a foreign label -> (concept, carrier, the witness route that holds it)
    contrast(terms)  a foreign corpus -> what to REUSE and what to WEDGE

REUSE and WEDGE are the two outcomes that matter when ingesting a corpus.  A HIT means an existing
witness family already covers the idea, and the new material becomes another ARGUMENT to it (which
is what the graded key in routes.py is for).  A MISS means the idea is transverse and needs a wedge
against what is here.  Neither outcome is a judgement about the corpus; both are about THIS library's
current coverage.

CONTENT IS INJECTED, MECHANISM IS HERE.  The two mappings a caller supplies:

    concepts    {concept: {carrier: label}}   — the orbit of each concept
    routes_for  {concept: route}              — PARTIAL by design: a concept with no route is
                                                "unresolved", the third verdict, never a merge

WHY A CLASS AND NOT A FROZEN TABLE.  The index MUTATES: growing it is the normal operation (a corpus
is ingested, labels are added), and `collisions()` is meaningful only against a live index.  A
frozen structure would make the instrument unusable for the thing it exists to do.
"""
from __future__ import annotations

import re

_NORM = re.compile(r"[^a-z0-9]+")


def norm(s: str) -> str:
    return _NORM.sub(" ", s.lower()).strip()


class LabelMap:
    """concept <-> label <-> carrier, with the routes that hold each concept."""

    def __init__(self, concepts: dict | None = None, routes_for: dict | None = None):
        self.concepts = dict(concepts or {})
        self.routes_for = dict(routes_for or {})
        self.index = {}                      # normalised label -> (concept, carrier)
        for c, ls in self.concepts.items():
            for carrier, label in ls.items():
                self.index[norm(label)] = (c, carrier)

    def add(self, label: str, concept: str, carrier: str) -> None:
        """Grow the map.  The index is designed to GROW — this is the normal operation, not a
        repair, which is why the structure is mutable."""
        self.concepts.setdefault(concept, {})[carrier] = label
        self.index[norm(label)] = (concept, carrier)

    def lookup(self, term: str):
        """A foreign label -> (concept, carrier, route) or None.

        The match is on WHOLE WORDS, not substrings.  A substring rule matched `ratio` inside
        `bifibrational` and produced a hundred false hits — the instrument's own resolution limit,
        and the reason its first numbers were worthless.  Keep the rule."""
        t = norm(term)
        if t in self.index:
            c, carrier = self.index[t]
            return c, carrier, self.routes_for.get(c)
        tw = t.split()
        for lab, (c, carrier) in self.index.items():
            lw = lab.split()
            if lw and all(w in tw for w in lw):      # every label word, a WHOLE word of the term
                return c, carrier, self.routes_for.get(c)
        return None

    def contrast(self, terms):
        """A corpus's terms -> ({concept: [terms that hit it]}, [terms with no home])."""
        reuse, wedge = {}, []
        for t in terms:
            hit = self.lookup(t)
            (reuse.setdefault(hit[0], []).append(t) if hit else wedge.append(t))
        return reuse, wedge

    def collisions(self):
        """Labels landing on the SAME (concept, carrier) slot.

        A collision is not an error to annotate away — it is the DATUM.  Two labels at one slot mean
        EITHER that they are synonyms, OR that the concept is UNDER-PARAMETERISED and the carrier is
        not yet fine enough to separate them.  Which of the two holds is not declared; it is DERIVED,
        by running the witness families the labels point at and comparing what they compute (see
        discriminate).  A "meaning" field here would be a scalar tag standing in for that
        computation — the thing this design refuses."""
        slots = {}
        for label, slot in self.index.items():
            slots.setdefault(slot, []).append(label)
        return {k: v for k, v in slots.items() if len(v) > 1}

    def discriminate(self, label_a: str, label_b: str, run):
        """Derive whether two labels are ONE concept, by their WITNESSES.

        `run(route)` executes a witness route and returns its result; the verdict comes from the
        COMPUTATION, not from an annotation.  Returns (verdict, a_route, b_route) with verdict in
        {"one", "two", "unresolved"} — unresolved when either label carries no route, which is the
        not-runnable-here case and emphatically NOT a merge.

        `run` is injected, which is what keeps this module independent of any resolver: the natural
        wiring is `routes.dispatch`, but a caller may pass anything that maps a route to a value."""
        ha, hb = self.lookup(label_a), self.lookup(label_b)
        if not ha or not hb:
            return "unresolved", None, None
        ra, rb = ha[2], hb[2]
        if ra is None or rb is None:
            return "unresolved", ra, rb
        return ("one" if run(ra) == run(rb) else "two"), ra, rb

    def carriers_of(self, concept: str):
        """The carriers a concept has been named from — its orbit so far."""
        return sorted(self.concepts.get(concept, {}))

    def shared_middles(self):
        """Concepts sharing a CARRIER: candidates for a composition through it."""
        by = {}
        for c, ls in self.concepts.items():
            for carrier in ls:
                by.setdefault(carrier, []).append(c)
        return {k: v for k, v in by.items() if len(v) > 1}
