# Paperkit — Rendering: paper.md → docx, Gated to Agree

*On-demand: the paper renders to a Word document, and the document is gated to PRESENT the verified paper faithfully — presentation agreement extends prose≡projection down the render stack.*

## The Render Coalgebra: Format Nodes and Conversion Edges

The render pipeline is a COALGEBRA tracked as data — format OBJECTS (md, docx, odt, latex, pdf) and conversion MORPHISMS (pandoc from markdown, the office suite between docx/odt/pdf, lualatex from latex) live as an explicit many-to-many adjacency matrix with ONE owner, and the format-node producers and the pdf router DERIVE their edges from it rather than each hardcoding a tool — so every declared morphism's tool is present (the graph cannot claim an edge the toolchain cannot perform) and every route to the terminal PDF composes real edges, and a new node or edge (a slide-deck target) is added in ONE place [@rnd-graph]. And the docx format is a first-class NODE — md becomes a Word document by the pandoc morphism the graph declares (asserted against the matrix, not hardcoded), from the ONE resolved source every node shares (each internal warrant inlined as its verification marker, the title carried from paper.toml through pandoc's core metadata), a well-formed OOXML package that pandoc reads back — terminal-capable (a consumer may want the .docx itself) or the intermediate the docx-to-pdf route reads [@rnd-docx]. And the OpenDocument format is a first-class NODE too — md becomes a valid .odt (a package carrying content.xml and the OpenDocument-text mimetype) by the same pandoc morphism from the same resolved source; ODF is LibreOffice's NATIVE format, the object the office edges already pass through, so surfacing it as its own node makes the hidden intermediate a terminal-capable deliverable a consumer may render or route on to a PDF [@rnd-odf]. And a SECOND matrix over the same format objects is owned as data — capability by FORMAT: which render target AFFORDS which accessibility or fidelity capability (native math, link and math alternatives, PDF/UA conformance, per-row accessible table rules, and the rest), each cell stating whether the format carries it BY CONSTRUCTION, only AFTER a post-processing pass, or is TOOLCHAIN-EXCEPTED (a named exception, never a silent gap), and naming the warrant that demonstrates it — so a capability's reach across formats lives in ONE place, every demonstrated cell is backed by a passing warrant, and the PDF/UA row agrees with the render coalgebra's own per-edge accessibility field: the conversion graph and the capability grid are two faces of one owned coalgebra, composing into the capabilities-by-formats-by-conversions whole [@rnd-matrix]. And the THIRD axis completes the cube as a category — a conversion edge is a MORPHISM ON THE CAPABILITY SPACE, mapping a capability to what it BECOMES across that edge, and the cell records that IMAGE rather than a bare survives-or-not: an edge may PRESERVE a capability, ESTABLISH one its post-processing creates, drop one the destination cannot carry, or TWIST one into a DIFFERENT capability the destination affords instead — editable native math crossing the office export becomes a tagged formula with alternate text, faithful to the eye and to a word processor but no longer editable, so it arrives at the PDF under a different name than it left the document, the categorical twist a survival predicate would have discarded; and the action DERIVES from the two owned faces plus the genuine twists declared where the endpoints cannot express them, so a route delivers each capability under the name it arrives as and the whole is one owned coalgebra — the graph is the base category, the capabilities a fibration over it, and each conversion edge its action on the fibre [@rnd-cube].

## Emit: paper.md → docx

The paper renders to a Word document — pandoc turns paper.md into a valid .docx (a well-formed OOXML package that pandoc can read back), the first presentation beyond markdown [@rnd-emit].

## Presentation Agreement

The rendered document PRESENTS the verified paper: the plain text a reader sees in the .docx is byte-for-byte the plain text of paper.md, so the render preserves the content — presentation agreement extends prose≡projection down the render stack, from the gated source to the delivered document [@rnd-agree].

## Output Integrity & Fidelity

The rendered document is structurally sound: word/document.xml is well-formed OOXML, and every section of the paper is presented as a real Word heading whose text matches — the structure survives the render, never flattened into body text [@rnd-wf]. And the reader's view is faithful: rendered all the way to a PDF, every non-ASCII glyph the paper uses survives into the text layer with no missing-glyph tofu, and every heading is present there — what the consumer copies, searches, or hears through a screen reader is the paper, not a broken rendering [@rnd-fidelity]. And the paper's EQUATIONS transport as native Office Math (OMML), not pixels — the effective-grade clamp, the emergence increment and the coherence disjointness render from the claim prose's inline math into editable, well-formed $<$m:oMath$>$ elements that scale and stay in the text layer, with no equation leaked to a rasterized image and no math delimiter surviving as literal text; and the presentation-agreement check DELEGATES the equations to this OMML owner rather than compare their plain-text flattenings (which differ across the two render paths), so the cross-path difference is REGISTERED against a bounded set of glyph variants and witnessed to stay within it, not erased — the hardest document-fidelity case demonstrated on the paper's own content (mat260's OMML doctrine) [@rnd-omml]. And a wide equation in a TABLE cell is sized to fit rather than clipped — an OMML run cannot wrap (LibreOffice never breaks inside it, and renders it at a fixed base size that ignores the run's own size hints, so column WIDTH is the only lever), and a formula wider than its fixed column paints past the margin and is truncated, so before the export each table's columns are sized to their MEASURED rendered ink and a cell that still would not fit under that sizing is named rather than silently clipped — the ink measured with the same rasterizer the reader sees, not estimated from a character count (mat260's measured-column-width, whose CLIPS verdict is first-pass under column sizing, a wider page or a broken equation left untried) [@rnd-widen].

## Visual Fidelity (the rendered pixels)

The reader's EYE sees the paper, not just a screen reader: rendered to a PDF and rasterized to images, OCR recovers the paper's text from the pixels themselves — a font or render regression that turned the body to tofu would crater that recovery, so the visual layer is gated, not only the text layer [@rnd-ocr]. And every font in the rendered PDF is EMBEDDED, so it draws identically on a machine that lacks the font — no silent substitution to a glyph the author never saw [@rnd-fonts].

## Citations: Warrants Inline, Sources Referenced

The paper's two kinds of citation RESOLVE in the render: an internal warrant becomes an inline machine-checked marker (cite_split, before pandoc), an external source renders author-date with a References list (–citeproc over references.bib), and no bracketed citation marker is left as bare text — a render-time projection that leaves the gated paper.md untouched [@rnd-bib]. Which of these a citation MATERIALIZES as is the projector's render TARGET — pandoc emits an inline citeproc marker, web an intra-page anchor, footnote a document-end provenance note, and plain surfaces NO citation marker at all: a clean SUBMISSION view that presents the same verified prose with the machinery removed, while the claim-DAG stays the author-side gate [@rnd-plain].

## The PDF Deliverable

The paper renders END-TO-END to a PDF deliverable — cite_split, then citeproc, then docx, then PDF: the human-readable artifact a reader actually receives — gated to be complete and polished: no citation is left as a bare marker, the References list renders, and the paper's content is present in the PDF [@rnd-pdf]. And the deliverable is exported as a tagged PDF/UA over the office suite's UNO scripting bridge rather than its command-line conversion — the bridge sets the PDF/UA export flags and refreshes each document index, since the command-line path exports a plain PDF and never populates a table-of-contents field, and it owns the office process explicitly (a private pipe, a deadline, and a kill if it will not exit) so that sre-troubleshooting's first attempt, a document macro that hung the build with no output, becomes a LOUD bounded failure instead of a silent stall — the export path falls back to the plain conversion where no scripting-bridge interpreter is present, so the deliverable still renders [@rnd-index].

## Figures: Vector and Legible

A generated figure renders into the document as a Word-native VECTOR — SVG converted to EMF (libreoffice), embedded by pandoc, and carried through to the PDF without ever being rasterized — so it stays crisp at any zoom, with no pixelation for a reader who magnifies the page [@rnd-fig-vector]; the figure's legend SURVIVES into the rendered PDF text layer — every label selectable, searchable, and screen-readable rather than locked inside the pixels — the accessibility of the report's Okabe-Ito claim-DAG figure, preserved through the render [@rnd-fig-legible].

## Accessibility: PDF/UA by Construction

Every link annotation in the deliverable carries a text description — a pass over the finished PDF reads the words whose boxes OVERLAP each undescribed link's rectangle and writes them back as that link's description, on the reasoning that the words a sighted reader sees are what a screen reader should hear, so a citation link announces its destination rather than a bare "link" (PDF/UA 7.18.1 and 7.18.5) — adopted from sre-troubleshooting, carrying its half-description fix forward: selection is by BOX OVERLAP not word centre, so two adjacent citations that extract as one word are both described [@rnd-link-alt]. And every equation carries a text alternative so the math is accessible — the office export tags each formula as a Formula structure element but sets no alternate text, which a screen reader announces as nothing (PDF/UA 7.7), so a post-export pass writes each equation's own LaTeX source, the recoverable structure, as the Formula's alt text in document order, refusing loudly if the formula and equation counts disagree rather than describing a partial set (mat230's per-formula math-alternative doctrine, on the office route) [@rnd-math-alt]. So paperkit's OWN paper is PDF/UA-1 conformant BY CONSTRUCTION — the deliverable is built as the pdf check builds it (the title carried from paper.toml through pandoc metadata, the export driven in PDF/UA mode so LibreOffice sets the pdfuaid schema, DisplayDocTitle and dc:title AT THE LAYER THAT OWNS THEM, then link and equation descriptions restored), and veraPDF validates it at UA-1 with zero failed checks over a Tagged PDF including its equations, gating on the flavour the producer targets (LibreOffice emits UA-1 and declares pdfuaid part 1) — what was an opt-in measurement a downstream deliverable pointed at is now a live warrant of the render project's own output, earned rather than asserted [@rnd-a11y].

## The LaTeX Format: Tagged PDF/UA-2

And the SAME verified paper renders through a SECOND format — a LaTeX pipeline beside the docx one, for a reader who wants latex and PDF where another wants docx and PDF — pandoc turns the projected prose into a LaTeX body, the engine assembles it under a tagged-PDF preamble with a per-codepoint font fallback so a prose glyph the main font lacks is covered rather than dropped, and lualatex compiles it to a tagged PDF, so one claim-DAG reaches two delivered formats and neither degrades the other [@rnd-latex]. And the LaTeX format is held to AT LEAST the docx format's accessibility, and better — paperkit's own paper renders through it to a PDF that veraPDF validates at PDF/UA-2 with zero failed checks, a LATER standard than the docx route's UA-1, reached BY CONSTRUCTION (native document tagging, not post-export surgery) with every equation carrying an ASSOCIATED MathML file rather than a stamped alt string, so the math is recoverable structure a screen reader reads; and because a zero-failure UA-2 verdict forbids a .notdef glyph, the conformance gate SUBSUMES the missing-glyph tofu check the arbitrary-prose format needs — the recipe vendored from mat230 (its minimal tagged preamble, pinned to its validated TeX Live), the arbitrary-prose font fallback authored for paperkit's own route [@rnd-a11y-latex]. And WHICH route a consumer builds their PDF through is one selector, resolved the paperkit way (Ω·config) — an environment knob picks a graph ROUTE (docx, odf, or latex), each terminating at the PDF node through its own intermediate, defaulting to docx and REFUSING an unknown value rather than silently falling back, and it lives in the render project rather than the engine registry because the engine projects the paper format-agnostically and never branches on the format, so a knob there would be one the engine does not own — the routes stay independently gated regardless, so the selector chooses what to BUILD, never what to VERIFY [@rnd-format].

## Use of Colour: The Rule Pattern Carries the Structure

And every table in the LaTeX deliverable carries its binary row structure in the RULE PATTERN, a redundant non-colour cue — the rule between two rows is chosen by the cycle order of that boundary (the 2-adic valuation of the row index, which bit rolls over there) and drawn as a self-similar dot-dash motif, so a reader who cannot perceive colour still recovers the counting structure (WCAG 2.2 use-of-colour, the producing side); the rules are applied BY CONSTRUCTION to every rendered table, and a table is exempt only through a NAMED marker that the deliverable records rather than a silent absence, so the paper's own formula table is ruled with no author effort and the exception stays legible — the capability vendored from mat230 as the target-independent generator it should have been (uncapped, encoding any unsigned row count, with tex, html and markdown readings), not its order-capped reified form [@rnd-ruler]. And the deliverable is audited so colour is never the SOLE cue — every table row that uses a meaning colour must also carry a weight cue (a bold command) in that same row, so a distinction the colour was carrying survives for a reader who cannot perceive it (WCAG 2.2 use-of-colour, the verifying side that pairs with the ruler-sequence producing side) — a sufficient-condition auditor over the LaTeX source, vendored from mat230 so the one accessibility criterion is covered from both ends [@rnd-colour].

## Accessibility Conformance: A Self-Attesting VPAT

And the accessibility STANDARDS themselves are modeled as sourced, versioned data — the 86 WCAG 2.2 success criteria (completeness proven by checkable arithmetic, not a trusted number: WCAG 2.1's 78 plus the 9 added in 2.2 less the one removed), the Revised Section 508 incorporation of WCAG 2.0 A and AA, and the EN 301 549 non-web clauses, each tracing to its primary source, with the version skew modeled explicitly because a criterion new in 2.2 is out of 508 scope and out of EN's 2.1 scope BY VERSION, not by choice — a conformance claim rests on a verified model of the law, not a hand-guessed one [@rnd-wcag-model]. And the entailment LOGIC that decides admissibility is itself falsifiability-graded, not merely trusted — the pure regulatory core (a Supports is admissible only when its backing proof reads pass; a red proof drops it; an unverifiable one is disclosed conservatively) runs HERMETICALLY with the veraPDF verdicts stubbed, so paperkit's own mutation sweep grades it: corrupt the rule that a failed proof cannot back a Supports and the ⟨P,F,δ⟩ selftest reds, which is what makes the regulatory soundness architecturally enforced rather than self-certified [@rnd-wcag-entail-core]. And the entailment is then discharged against the REAL deliverable — a Supports verdict is admissible only when a warrant's own falsification arm reds on that criterion's violation, or when the deliverable passes the standard's own validator (veraPDF for PDF/UA, whose verdict this check CONSUMES from the render warrant that runs it once rather than re-running it), so the falsifiability that grades every paperkit claim becomes the entailment evidence a regulatory claim needs; a broken proof cannot back a Supports, and a criterion whose entailment is unproven is disclosed conservatively rather than claimed — the warrant-adequacy gap closed at the regulatory tier, under-claiming by construction because a false Supports is a false legal claim [@rnd-wcag-entail]. And paperkit's own accessibility conformance is DISCLOSED as a self-attesting report — a VPAT International conformance statement (WCAG 2.2 by level, Section 508, and EN 301 549), generated as a projection of the standards model and the proven entailment verdicts, per render route, so the two deliverables disclose their genuine difference (the office route reaches PDF/UA-1, the LaTeX route the later PDF/UA-2) and every Supports carries in its remarks the warrant that entails it — the engine's own thesis, that a document is a projection of a verified claim-DAG, applied to the highest-stakes claim a document makes about itself, so the conformance statement and its machine-checked proof are one object gated fresh [@rnd-wcag].

<!-- paperkit:raw -->
<!-- GENERATED by checks/wcag.py from wcag_model.py + wcag_entail.py — do not edit; regenerate: python3 checks/wcag.py --emit -->

# paperkit — Accessibility Conformance Report (VPAT® International)

# Accessibility Conformance Report — docx route

International Edition (VPAT®-style ACR): WCAG 2.2, Revised Section 508, and EN 301 549.

**Deliverable / technologies relied upon:** paperkit's paper rendered through the docx route to a tagged PDF (UA-1). Conformance is stated per route because the routes differ (the office route reaches PDF/UA-1, the LaTeX route PDF/UA-2).

**Attestation basis:** this report is a paperkit projection of a verified claim-DAG. Each "Supports" is entailed by a warrant whose ⟨P,F,δ⟩ F-arm reds on the criterion's violation, or by veraPDF (the PDF/UA validator); an unproven criterion is never "Supports". The report is gated fresh, so the conformance claim and its machine-checked proof are one object.

**Standards versions:** WCAG 2.2 (W3C Rec 2024-12-12); Revised Section 508 (WCAG 2.0 A/AA); EN 301 549 V3.2.1 (WCAG 2.1). The version skew is disclosed per report.

## WCAG 2.2 Report

### Table 1: Success Criteria, Level A

| Criteria | Conformance Level | Remarks and Explanations |
| --- | --- | --- |
| 1.1.1 Non-text Content | Partially Supports | rnd-math-alt entails this — only part of the criterion is proven (farm), not the whole; a full claim needs coverage the tool cannot confirm |
| 1.2.1 Audio-only and Video-only (Prerecorded) | Not Applicable | does not apply to a static, non-interactive print PDF |
| 1.2.2 Captions (Prerecorded) | Not Applicable | does not apply to a static, non-interactive print PDF |
| 1.2.3 Audio Description or Media Alternative (Prerecorded) | Not Applicable | does not apply to a static, non-interactive print PDF |
| 1.3.1 Info and Relationships | Partially Supports | rnd-a11y (veraPDF): UA validates the structure tree, but veraPDF cannot confirm EVERY visual relationship was tagged (completeness is a human PDF/UA checkpoint) — only part of the criterion is proven (oracle), not the whole; a full claim needs coverage the tool cannot confirm |
| 1.3.2 Meaningful Sequence | Partially Supports | rnd-a11y (veraPDF): UA validates a reading order exists, but not that it matches the visual sequence (correctness is a human checkpoint) — only part of the criterion is proven (oracle), not the whole; a full claim needs coverage the tool cannot confirm |
| 1.3.3 Sensory Characteristics | Does Not Support | no warrant entails this criterion for this deliverable (a known gap) |
| 1.4.1 Use of Color | Does Not Support | no warrant entails this criterion for this deliverable (a known gap) |
| 1.4.2 Audio Control | Not Applicable | does not apply to a static, non-interactive print PDF |
| 2.1.1 Keyboard | Not Applicable | does not apply to a static, non-interactive print PDF |
| 2.1.2 No Keyboard Trap | Not Applicable | does not apply to a static, non-interactive print PDF |
| 2.1.4 Character Key Shortcuts | Not Applicable | does not apply to a static, non-interactive print PDF |
| 2.2.1 Timing Adjustable | Not Applicable | does not apply to a static, non-interactive print PDF |
| 2.2.2 Pause, Stop, Hide | Not Applicable | does not apply to a static, non-interactive print PDF |
| 2.3.1 Three Flashes or Below Threshold | Not Applicable | does not apply to a static, non-interactive print PDF |
| 2.4.1 Bypass Blocks | Not Applicable | does not apply to a static, non-interactive print PDF |
| 2.4.2 Page Titled | Partially Supports | rnd-a11y (veraPDF): UA validates a title EXISTS and DisplayDocTitle, but veraPDF cannot confirm it DESCRIBES topic/purpose (the SC's bar) — presence is not descriptiveness — only part of the criterion is proven (oracle), not the whole; a full claim needs coverage the tool cannot confirm |
| 2.4.3 Focus Order | Not Applicable | does not apply to a static, non-interactive print PDF |
| 2.4.4 Link Purpose (In Context) | Partially Supports | rnd-link-alt entails this — only part of the criterion is proven (farm), not the whole; a full claim needs coverage the tool cannot confirm |
| 2.5.1 Pointer Gestures | Not Applicable | does not apply to a static, non-interactive print PDF |
| 2.5.2 Pointer Cancellation | Not Applicable | does not apply to a static, non-interactive print PDF |
| 2.5.3 Label in Name | Not Applicable | does not apply to a static, non-interactive print PDF |
| 2.5.4 Motion Actuation | Not Applicable | does not apply to a static, non-interactive print PDF |
| 3.1.1 Language of Page | Supports | rnd-a11y (veraPDF): UA requires (and veraPDF checks) the document's primary language be set (oracle) |
| 3.2.1 On Focus | Not Applicable | does not apply to a static, non-interactive print PDF |
| 3.2.2 On Input | Not Applicable | does not apply to a static, non-interactive print PDF |
| 3.2.6 Consistent Help | Not Applicable | does not apply to a static, non-interactive print PDF |
| 3.3.1 Error Identification | Not Applicable | does not apply to a static, non-interactive print PDF |
| 3.3.2 Labels or Instructions | Not Applicable | does not apply to a static, non-interactive print PDF |
| 3.3.7 Redundant Entry | Not Applicable | does not apply to a static, non-interactive print PDF |
| 4.1.2 Name, Role, Value | Does Not Support | no warrant entails this criterion for this deliverable (a known gap) |

### Table 2: Success Criteria, Level AA

| Criteria | Conformance Level | Remarks and Explanations |
| --- | --- | --- |
| 1.2.4 Captions (Live) | Not Applicable | does not apply to a static, non-interactive print PDF |
| 1.2.5 Audio Description (Prerecorded) | Not Applicable | does not apply to a static, non-interactive print PDF |
| 1.3.4 Orientation | Not Applicable | does not apply to a static, non-interactive print PDF |
| 1.3.5 Identify Input Purpose | Not Applicable | does not apply to a static, non-interactive print PDF |
| 1.4.3 Contrast (Minimum) | Does Not Support | no warrant entails this criterion for this deliverable (a known gap) |
| 1.4.4 Resize Text | Not Applicable | does not apply to a static, non-interactive print PDF |
| 1.4.5 Images of Text | Partially Supports | rnd-fig-legible addresses this but its entailment is not proven for a full claim |
| 1.4.10 Reflow | Not Applicable | does not apply to a static, non-interactive print PDF |
| 1.4.11 Non-text Contrast | Does Not Support | no warrant entails this criterion for this deliverable (a known gap) |
| 1.4.12 Text Spacing | Not Applicable | does not apply to a static, non-interactive print PDF |
| 1.4.13 Content on Hover or Focus | Not Applicable | does not apply to a static, non-interactive print PDF |
| 2.4.5 Multiple Ways | Not Applicable | does not apply to a static, non-interactive print PDF |
| 2.4.6 Headings and Labels | Partially Supports | rnd-a11y (veraPDF): UA validates tagged headings, but not that EVERY visual heading was tagged as one (completeness is a human checkpoint) — only part of the criterion is proven (oracle), not the whole; a full claim needs coverage the tool cannot confirm |
| 2.4.7 Focus Visible | Not Applicable | does not apply to a static, non-interactive print PDF |
| 2.4.11 Focus Not Obscured (Minimum) | Not Applicable | does not apply to a static, non-interactive print PDF |
| 2.5.7 Dragging Movements | Not Applicable | does not apply to a static, non-interactive print PDF |
| 2.5.8 Target Size (Minimum) | Not Applicable | does not apply to a static, non-interactive print PDF |
| 3.1.2 Language of Parts | Not Applicable | does not apply to a static, non-interactive print PDF |
| 3.2.3 Consistent Navigation | Not Applicable | does not apply to a static, non-interactive print PDF |
| 3.2.4 Consistent Identification | Not Applicable | does not apply to a static, non-interactive print PDF |
| 3.3.3 Error Suggestion | Not Applicable | does not apply to a static, non-interactive print PDF |
| 3.3.4 Error Prevention (Legal, Financial, Data) | Not Applicable | does not apply to a static, non-interactive print PDF |
| 3.3.8 Accessible Authentication (Minimum) | Not Applicable | does not apply to a static, non-interactive print PDF |
| 4.1.3 Status Messages | Not Applicable | does not apply to a static, non-interactive print PDF |

### Table 3: Success Criteria, Level AAA

| Criteria | Conformance Level | Remarks and Explanations |
| --- | --- | --- |
| 1.2.6 Sign Language (Prerecorded) | Not Applicable | does not apply to a static, non-interactive print PDF |
| 1.2.7 Extended Audio Description (Prerecorded) | Not Applicable | does not apply to a static, non-interactive print PDF |
| 1.2.8 Media Alternative (Prerecorded) | Not Applicable | does not apply to a static, non-interactive print PDF |
| 1.2.9 Audio-only (Live) | Not Applicable | does not apply to a static, non-interactive print PDF |
| 1.3.6 Identify Purpose | Does Not Support | no warrant entails this criterion for this deliverable (a known gap) |
| 1.4.6 Contrast (Enhanced) | Does Not Support | no warrant entails this criterion for this deliverable (a known gap) |
| 1.4.7 Low or No Background Audio | Not Applicable | does not apply to a static, non-interactive print PDF |
| 1.4.8 Visual Presentation | Does Not Support | no warrant entails this criterion for this deliverable (a known gap) |
| 1.4.9 Images of Text (No Exception) | Does Not Support | no warrant entails this criterion for this deliverable (a known gap) |
| 2.1.3 Keyboard (No Exception) | Not Applicable | does not apply to a static, non-interactive print PDF |
| 2.2.3 No Timing | Not Applicable | does not apply to a static, non-interactive print PDF |
| 2.2.4 Interruptions | Not Applicable | does not apply to a static, non-interactive print PDF |
| 2.2.5 Re-authenticating | Not Applicable | does not apply to a static, non-interactive print PDF |
| 2.2.6 Timeouts | Not Applicable | does not apply to a static, non-interactive print PDF |
| 2.3.2 Three Flashes | Not Applicable | does not apply to a static, non-interactive print PDF |
| 2.3.3 Animation from Interactions | Not Applicable | does not apply to a static, non-interactive print PDF |
| 2.4.8 Location | Not Applicable | does not apply to a static, non-interactive print PDF |
| 2.4.9 Link Purpose (Link Only) | Does Not Support | no warrant entails this criterion for this deliverable (a known gap) |
| 2.4.10 Section Headings | Does Not Support | no warrant entails this criterion for this deliverable (a known gap) |
| 2.4.12 Focus Not Obscured (Enhanced) | Not Applicable | does not apply to a static, non-interactive print PDF |
| 2.4.13 Focus Appearance | Not Applicable | does not apply to a static, non-interactive print PDF |
| 2.5.5 Target Size (Enhanced) | Not Applicable | does not apply to a static, non-interactive print PDF |
| 2.5.6 Concurrent Input Mechanisms | Not Applicable | does not apply to a static, non-interactive print PDF |
| 3.1.3 Unusual Words | Does Not Support | no warrant entails this criterion for this deliverable (a known gap) |
| 3.1.4 Abbreviations | Does Not Support | no warrant entails this criterion for this deliverable (a known gap) |
| 3.1.5 Reading Level | Does Not Support | no warrant entails this criterion for this deliverable (a known gap) |
| 3.1.6 Pronunciation | Does Not Support | no warrant entails this criterion for this deliverable (a known gap) |
| 3.2.5 Change on Request | Not Applicable | does not apply to a static, non-interactive print PDF |
| 3.3.5 Help | Not Applicable | does not apply to a static, non-interactive print PDF |
| 3.3.6 Error Prevention (All) | Not Applicable | does not apply to a static, non-interactive print PDF |
| 3.3.9 Accessible Authentication (Enhanced) | Not Applicable | does not apply to a static, non-interactive print PDF |

## Revised Section 508 Report

Section 508 incorporates WCAG 2.0 Level A and AA by reference. Criteria introduced after WCAG 2.0 are outside 508 scope by version (disclosed below, not scored as 508).

| Criteria | Conformance Level | Remarks and Explanations |
| --- | --- | --- |
| 1.1.1 Non-text Content (A) | Partially Supports | rnd-math-alt entails this — only part of the criterion is proven (farm), not the whole; a full claim needs coverage the tool cannot confirm |
| 1.2.1 Audio-only and Video-only (Prerecorded) (A) | Not Applicable | does not apply to a static, non-interactive print PDF |
| 1.2.2 Captions (Prerecorded) (A) | Not Applicable | does not apply to a static, non-interactive print PDF |
| 1.2.3 Audio Description or Media Alternative (Prerecorded) (A) | Not Applicable | does not apply to a static, non-interactive print PDF |
| 1.2.4 Captions (Live) (AA) | Not Applicable | does not apply to a static, non-interactive print PDF |
| 1.2.5 Audio Description (Prerecorded) (AA) | Not Applicable | does not apply to a static, non-interactive print PDF |
| 1.3.1 Info and Relationships (A) | Partially Supports | rnd-a11y (veraPDF): UA validates the structure tree, but veraPDF cannot confirm EVERY visual relationship was tagged (completeness is a human PDF/UA checkpoint) — only part of the criterion is proven (oracle), not the whole; a full claim needs coverage the tool cannot confirm |
| 1.3.2 Meaningful Sequence (A) | Partially Supports | rnd-a11y (veraPDF): UA validates a reading order exists, but not that it matches the visual sequence (correctness is a human checkpoint) — only part of the criterion is proven (oracle), not the whole; a full claim needs coverage the tool cannot confirm |
| 1.3.3 Sensory Characteristics (A) | Does Not Support | no warrant entails this criterion for this deliverable (a known gap) |
| 1.4.1 Use of Color (A) | Does Not Support | no warrant entails this criterion for this deliverable (a known gap) |
| 1.4.2 Audio Control (A) | Not Applicable | does not apply to a static, non-interactive print PDF |
| 1.4.3 Contrast (Minimum) (AA) | Does Not Support | no warrant entails this criterion for this deliverable (a known gap) |
| 1.4.4 Resize Text (AA) | Not Applicable | does not apply to a static, non-interactive print PDF |
| 1.4.5 Images of Text (AA) | Partially Supports | rnd-fig-legible addresses this but its entailment is not proven for a full claim |
| 2.1.1 Keyboard (A) | Not Applicable | does not apply to a static, non-interactive print PDF |
| 2.1.2 No Keyboard Trap (A) | Not Applicable | does not apply to a static, non-interactive print PDF |
| 2.2.1 Timing Adjustable (A) | Not Applicable | does not apply to a static, non-interactive print PDF |
| 2.2.2 Pause, Stop, Hide (A) | Not Applicable | does not apply to a static, non-interactive print PDF |
| 2.3.1 Three Flashes or Below Threshold (A) | Not Applicable | does not apply to a static, non-interactive print PDF |
| 2.4.1 Bypass Blocks (A) | Not Applicable | does not apply to a static, non-interactive print PDF |
| 2.4.2 Page Titled (A) | Partially Supports | rnd-a11y (veraPDF): UA validates a title EXISTS and DisplayDocTitle, but veraPDF cannot confirm it DESCRIBES topic/purpose (the SC's bar) — presence is not descriptiveness — only part of the criterion is proven (oracle), not the whole; a full claim needs coverage the tool cannot confirm |
| 2.4.3 Focus Order (A) | Not Applicable | does not apply to a static, non-interactive print PDF |
| 2.4.4 Link Purpose (In Context) (A) | Partially Supports | rnd-link-alt entails this — only part of the criterion is proven (farm), not the whole; a full claim needs coverage the tool cannot confirm |
| 2.4.5 Multiple Ways (AA) | Not Applicable | does not apply to a static, non-interactive print PDF |
| 2.4.6 Headings and Labels (AA) | Partially Supports | rnd-a11y (veraPDF): UA validates tagged headings, but not that EVERY visual heading was tagged as one (completeness is a human checkpoint) — only part of the criterion is proven (oracle), not the whole; a full claim needs coverage the tool cannot confirm |
| 2.4.7 Focus Visible (AA) | Not Applicable | does not apply to a static, non-interactive print PDF |
| 3.1.1 Language of Page (A) | Supports | rnd-a11y (veraPDF): UA requires (and veraPDF checks) the document's primary language be set (oracle) |
| 3.1.2 Language of Parts (AA) | Not Applicable | does not apply to a static, non-interactive print PDF |
| 3.2.1 On Focus (A) | Not Applicable | does not apply to a static, non-interactive print PDF |
| 3.2.2 On Input (A) | Not Applicable | does not apply to a static, non-interactive print PDF |
| 3.2.3 Consistent Navigation (AA) | Not Applicable | does not apply to a static, non-interactive print PDF |
| 3.2.4 Consistent Identification (AA) | Not Applicable | does not apply to a static, non-interactive print PDF |
| 3.3.1 Error Identification (A) | Not Applicable | does not apply to a static, non-interactive print PDF |
| 3.3.2 Labels or Instructions (A) | Not Applicable | does not apply to a static, non-interactive print PDF |
| 3.3.3 Error Suggestion (AA) | Not Applicable | does not apply to a static, non-interactive print PDF |
| 3.3.4 Error Prevention (Legal, Financial, Data) (AA) | Not Applicable | does not apply to a static, non-interactive print PDF |
| 4.1.2 Name, Role, Value (A) | Does Not Support | no warrant entails this criterion for this deliverable (a known gap) |

## EN 301 549 V3.2.1 Report (Chapter 10, Non-web Documents)

EN 301 549 V3.2.1 references WCAG 2.1. Chapter 10 maps each adopted criterion to clause 10.x; criteria new in WCAG 2.2 have no clause in this version (out of scope by version).

| EN Clause | Criteria | Status | Remarks and Explanations |
| --- | --- | --- | --- |
| 10.1.1.1 | 1.1.1 Non-text Content | Partially Supports | rnd-math-alt entails this — only part of the criterion is proven (farm), not the whole; a full claim needs coverage the tool cannot confirm |
| 10.1.2.1 | 1.2.1 Audio-only and Video-only (Prerecorded) | Not Applicable | does not apply to a static, non-interactive print PDF |
| 10.1.2.2 | 1.2.2 Captions (Prerecorded) | Not Applicable | does not apply to a static, non-interactive print PDF |
| 10.1.2.3 | 1.2.3 Audio Description or Media Alternative (Prerecorded) | Not Applicable | does not apply to a static, non-interactive print PDF |
| 10.1.2.4 | 1.2.4 Captions (Live) | Not Applicable | does not apply to a static, non-interactive print PDF |
| 10.1.2.5 | 1.2.5 Audio Description (Prerecorded) | Not Applicable | does not apply to a static, non-interactive print PDF |
| 10.1.2.6 | 1.2.6 Sign Language (Prerecorded) | Void | not applicable to non-web documents per EN |
| 10.1.2.7 | 1.2.7 Extended Audio Description (Prerecorded) | Void | not applicable to non-web documents per EN |
| 10.1.2.8 | 1.2.8 Media Alternative (Prerecorded) | Void | not applicable to non-web documents per EN |
| 10.1.2.9 | 1.2.9 Audio-only (Live) | Void | not applicable to non-web documents per EN |
| 10.1.3.1 | 1.3.1 Info and Relationships | Partially Supports | rnd-a11y (veraPDF): UA validates the structure tree, but veraPDF cannot confirm EVERY visual relationship was tagged (completeness is a human PDF/UA checkpoint) — only part of the criterion is proven (oracle), not the whole; a full claim needs coverage the tool cannot confirm |
| 10.1.3.2 | 1.3.2 Meaningful Sequence | Partially Supports | rnd-a11y (veraPDF): UA validates a reading order exists, but not that it matches the visual sequence (correctness is a human checkpoint) — only part of the criterion is proven (oracle), not the whole; a full claim needs coverage the tool cannot confirm |
| 10.1.3.3 | 1.3.3 Sensory Characteristics | Does Not Support | no warrant entails this criterion for this deliverable (a known gap) |
| 10.1.3.4 | 1.3.4 Orientation | Not Applicable | does not apply to a static, non-interactive print PDF |
| 10.1.3.5 | 1.3.5 Identify Input Purpose | Not Applicable | does not apply to a static, non-interactive print PDF |
| 10.1.3.6 | 1.3.6 Identify Purpose | Void | not applicable to non-web documents per EN |
| 10.1.4.1 | 1.4.1 Use of Color | Does Not Support | no warrant entails this criterion for this deliverable (a known gap) |
| 10.1.4.2 | 1.4.2 Audio Control | Not Applicable | does not apply to a static, non-interactive print PDF |
| 10.1.4.3 | 1.4.3 Contrast (Minimum) | Does Not Support | no warrant entails this criterion for this deliverable (a known gap) |
| 10.1.4.4 | 1.4.4 Resize Text | Not Applicable | does not apply to a static, non-interactive print PDF |
| 10.1.4.5 | 1.4.5 Images of Text | Partially Supports | rnd-fig-legible addresses this but its entailment is not proven for a full claim |
| 10.1.4.6 | 1.4.6 Contrast (Enhanced) | Void | not applicable to non-web documents per EN |
| 10.1.4.7 | 1.4.7 Low or No Background Audio | Void | not applicable to non-web documents per EN |
| 10.1.4.8 | 1.4.8 Visual Presentation | Void | not applicable to non-web documents per EN |
| 10.1.4.9 | 1.4.9 Images of Text (No Exception) | Void | not applicable to non-web documents per EN |
| 10.1.4.10 | 1.4.10 Reflow | Not Applicable | does not apply to a static, non-interactive print PDF |
| 10.1.4.11 | 1.4.11 Non-text Contrast | Does Not Support | no warrant entails this criterion for this deliverable (a known gap) |
| 10.1.4.12 | 1.4.12 Text Spacing | Not Applicable | does not apply to a static, non-interactive print PDF |
| 10.1.4.13 | 1.4.13 Content on Hover or Focus | Not Applicable | does not apply to a static, non-interactive print PDF |
| 10.2.1.1 | 2.1.1 Keyboard | Not Applicable | does not apply to a static, non-interactive print PDF |
| 10.2.1.2 | 2.1.2 No Keyboard Trap | Not Applicable | does not apply to a static, non-interactive print PDF |
| 10.2.1.3 | 2.1.3 Keyboard (No Exception) | Void | not applicable to non-web documents per EN |
| 10.2.1.4 | 2.1.4 Character Key Shortcuts | Not Applicable | does not apply to a static, non-interactive print PDF |
| 10.2.2.1 | 2.2.1 Timing Adjustable | Not Applicable | does not apply to a static, non-interactive print PDF |
| 10.2.2.2 | 2.2.2 Pause, Stop, Hide | Not Applicable | does not apply to a static, non-interactive print PDF |
| 10.2.2.3 | 2.2.3 No Timing | Void | not applicable to non-web documents per EN |
| 10.2.2.4 | 2.2.4 Interruptions | Void | not applicable to non-web documents per EN |
| 10.2.2.5 | 2.2.5 Re-authenticating | Void | not applicable to non-web documents per EN |
| 10.2.2.6 | 2.2.6 Timeouts | Void | not applicable to non-web documents per EN |
| 10.2.3.1 | 2.3.1 Three Flashes or Below Threshold | Not Applicable | does not apply to a static, non-interactive print PDF |
| 10.2.3.2 | 2.3.2 Three Flashes | Void | not applicable to non-web documents per EN |
| 10.2.3.3 | 2.3.3 Animation from Interactions | Void | not applicable to non-web documents per EN |
| 10.2.4.1 | 2.4.1 Bypass Blocks | Void | not applicable to non-web documents per EN |
| 10.2.4.2 | 2.4.2 Page Titled | Partially Supports | rnd-a11y (veraPDF): UA validates a title EXISTS and DisplayDocTitle, but veraPDF cannot confirm it DESCRIBES topic/purpose (the SC's bar) — presence is not descriptiveness — only part of the criterion is proven (oracle), not the whole; a full claim needs coverage the tool cannot confirm |
| 10.2.4.3 | 2.4.3 Focus Order | Not Applicable | does not apply to a static, non-interactive print PDF |
| 10.2.4.4 | 2.4.4 Link Purpose (In Context) | Partially Supports | rnd-link-alt entails this — only part of the criterion is proven (farm), not the whole; a full claim needs coverage the tool cannot confirm |
| 10.2.4.5 | 2.4.5 Multiple Ways | Void | not applicable to non-web documents per EN |
| 10.2.4.6 | 2.4.6 Headings and Labels | Partially Supports | rnd-a11y (veraPDF): UA validates tagged headings, but not that EVERY visual heading was tagged as one (completeness is a human checkpoint) — only part of the criterion is proven (oracle), not the whole; a full claim needs coverage the tool cannot confirm |
| 10.2.4.7 | 2.4.7 Focus Visible | Not Applicable | does not apply to a static, non-interactive print PDF |
| 10.2.4.8 | 2.4.8 Location | Void | not applicable to non-web documents per EN |
| 10.2.4.9 | 2.4.9 Link Purpose (Link Only) | Void | not applicable to non-web documents per EN |
| 10.2.4.10 | 2.4.10 Section Headings | Void | not applicable to non-web documents per EN |
| — | 2.4.11 Focus Not Obscured (Minimum) | Out of scope (post-2.1) | not in EN 301 549 V3.2.1 |
| — | 2.4.12 Focus Not Obscured (Enhanced) | Out of scope (post-2.1) | not in EN 301 549 V3.2.1 |
| — | 2.4.13 Focus Appearance | Out of scope (post-2.1) | not in EN 301 549 V3.2.1 |
| 10.2.5.1 | 2.5.1 Pointer Gestures | Not Applicable | does not apply to a static, non-interactive print PDF |
| 10.2.5.2 | 2.5.2 Pointer Cancellation | Not Applicable | does not apply to a static, non-interactive print PDF |
| 10.2.5.3 | 2.5.3 Label in Name | Not Applicable | does not apply to a static, non-interactive print PDF |
| 10.2.5.4 | 2.5.4 Motion Actuation | Not Applicable | does not apply to a static, non-interactive print PDF |
| 10.2.5.5 | 2.5.5 Target Size (Enhanced) | Void | not applicable to non-web documents per EN |
| 10.2.5.6 | 2.5.6 Concurrent Input Mechanisms | Void | not applicable to non-web documents per EN |
| — | 2.5.7 Dragging Movements | Out of scope (post-2.1) | not in EN 301 549 V3.2.1 |
| — | 2.5.8 Target Size (Minimum) | Out of scope (post-2.1) | not in EN 301 549 V3.2.1 |
| 10.3.1.1 | 3.1.1 Language of Page | Supports | rnd-a11y (veraPDF): UA requires (and veraPDF checks) the document's primary language be set (oracle) |
| 10.3.1.2 | 3.1.2 Language of Parts | Not Applicable | does not apply to a static, non-interactive print PDF |
| 10.3.1.3 | 3.1.3 Unusual Words | Void | not applicable to non-web documents per EN |
| 10.3.1.4 | 3.1.4 Abbreviations | Void | not applicable to non-web documents per EN |
| 10.3.1.5 | 3.1.5 Reading Level | Void | not applicable to non-web documents per EN |
| 10.3.1.6 | 3.1.6 Pronunciation | Void | not applicable to non-web documents per EN |
| 10.3.2.1 | 3.2.1 On Focus | Not Applicable | does not apply to a static, non-interactive print PDF |
| 10.3.2.2 | 3.2.2 On Input | Not Applicable | does not apply to a static, non-interactive print PDF |
| 10.3.2.3 | 3.2.3 Consistent Navigation | Void | not applicable to non-web documents per EN |
| 10.3.2.4 | 3.2.4 Consistent Identification | Void | not applicable to non-web documents per EN |
| 10.3.2.5 | 3.2.5 Change on Request | Void | not applicable to non-web documents per EN |
| — | 3.2.6 Consistent Help | Out of scope (post-2.1) | not in EN 301 549 V3.2.1 |
| 10.3.3.1 | 3.3.1 Error Identification | Not Applicable | does not apply to a static, non-interactive print PDF |
| 10.3.3.2 | 3.3.2 Labels or Instructions | Not Applicable | does not apply to a static, non-interactive print PDF |
| 10.3.3.3 | 3.3.3 Error Suggestion | Not Applicable | does not apply to a static, non-interactive print PDF |
| 10.3.3.4 | 3.3.4 Error Prevention (Legal, Financial, Data) | Not Applicable | does not apply to a static, non-interactive print PDF |
| 10.3.3.5 | 3.3.5 Help | Void | not applicable to non-web documents per EN |
| 10.3.3.6 | 3.3.6 Error Prevention (All) | Void | not applicable to non-web documents per EN |
| — | 3.3.7 Redundant Entry | Out of scope (post-2.1) | not in EN 301 549 V3.2.1 |
| — | 3.3.8 Accessible Authentication (Minimum) | Out of scope (post-2.1) | not in EN 301 549 V3.2.1 |
| — | 3.3.9 Accessible Authentication (Enhanced) | Out of scope (post-2.1) | not in EN 301 549 V3.2.1 |
| 10.4.1.2 | 4.1.2 Name, Role, Value | Does Not Support | no warrant entails this criterion for this deliverable (a known gap) |
| 10.4.1.3 | 4.1.3 Status Messages | Not Applicable | does not apply to a static, non-interactive print PDF |

## Sources

- W3C Recommendation, Web Content Accessibility Guidelines (WCAG) 2.2, 2024-12-12 (https://www.w3.org/TR/WCAG22/)
- Revised Section 508 Standards, US Access Board 2017, 36 CFR Part 1194 — incorporates WCAG 2.0 Level A and AA by reference (E207); no published per-SC crosswalk (column DERIVED)
- ETSI EN 301 549 V3.2.1 (2021-03), Chapter 10 (Non-web documents) — references WCAG 2.1; clause = 10.<SC> for adopted rows, Void/absent as recorded (https://www.etsi.org/deliver/etsi_en/301500_301599/301549/03.02.01_60/en_301549v030201p.pdf)
- ISO 14289 (PDF/UA) tagging requirements ↔ WCAG, per the PDF/UA-WCAG correspondence (Matterhorn Protocol / PDF Association guidance); only the directly-established correspondences are claimed here


---

# Accessibility Conformance Report — latex route

International Edition (VPAT®-style ACR): WCAG 2.2, Revised Section 508, and EN 301 549.

**Deliverable / technologies relied upon:** paperkit's paper rendered through the latex route to a tagged PDF (UA-2). Conformance is stated per route because the routes differ (the office route reaches PDF/UA-1, the LaTeX route PDF/UA-2).

**Attestation basis:** this report is a paperkit projection of a verified claim-DAG. Each "Supports" is entailed by a warrant whose ⟨P,F,δ⟩ F-arm reds on the criterion's violation, or by veraPDF (the PDF/UA validator); an unproven criterion is never "Supports". The report is gated fresh, so the conformance claim and its machine-checked proof are one object.

**Standards versions:** WCAG 2.2 (W3C Rec 2024-12-12); Revised Section 508 (WCAG 2.0 A/AA); EN 301 549 V3.2.1 (WCAG 2.1). The version skew is disclosed per report.

## WCAG 2.2 Report

### Table 1: Success Criteria, Level A

| Criteria | Conformance Level | Remarks and Explanations |
| --- | --- | --- |
| 1.1.1 Non-text Content | Supports | rnd-a11y-latex (veraPDF): veraPDF confirms /Alt PRESENT; on docx it is the raw-LaTeX source (not an equivalent a screen reader can speak) → fragment, on latex it is recoverable MathML (/AF) → full (oracle) |
| 1.2.1 Audio-only and Video-only (Prerecorded) | Not Applicable | does not apply to a static, non-interactive print PDF |
| 1.2.2 Captions (Prerecorded) | Not Applicable | does not apply to a static, non-interactive print PDF |
| 1.2.3 Audio Description or Media Alternative (Prerecorded) | Not Applicable | does not apply to a static, non-interactive print PDF |
| 1.3.1 Info and Relationships | Partially Supports | rnd-a11y-latex (veraPDF): UA validates the structure tree, but veraPDF cannot confirm EVERY visual relationship was tagged (completeness is a human PDF/UA checkpoint) — only part of the criterion is proven (oracle), not the whole; a full claim needs coverage the tool cannot confirm |
| 1.3.2 Meaningful Sequence | Partially Supports | rnd-a11y-latex (veraPDF): UA validates a reading order exists, but not that it matches the visual sequence (correctness is a human checkpoint) — only part of the criterion is proven (oracle), not the whole; a full claim needs coverage the tool cannot confirm |
| 1.3.3 Sensory Characteristics | Does Not Support | no warrant entails this criterion for this deliverable (a known gap) |
| 1.4.1 Use of Color | Partially Supports | rnd-ruler entails this — only part of the criterion is proven (farm), not the whole; a full claim needs coverage the tool cannot confirm |
| 1.4.2 Audio Control | Not Applicable | does not apply to a static, non-interactive print PDF |
| 2.1.1 Keyboard | Not Applicable | does not apply to a static, non-interactive print PDF |
| 2.1.2 No Keyboard Trap | Not Applicable | does not apply to a static, non-interactive print PDF |
| 2.1.4 Character Key Shortcuts | Not Applicable | does not apply to a static, non-interactive print PDF |
| 2.2.1 Timing Adjustable | Not Applicable | does not apply to a static, non-interactive print PDF |
| 2.2.2 Pause, Stop, Hide | Not Applicable | does not apply to a static, non-interactive print PDF |
| 2.3.1 Three Flashes or Below Threshold | Not Applicable | does not apply to a static, non-interactive print PDF |
| 2.4.1 Bypass Blocks | Not Applicable | does not apply to a static, non-interactive print PDF |
| 2.4.2 Page Titled | Partially Supports | rnd-a11y-latex (veraPDF): UA validates a title EXISTS and DisplayDocTitle, but veraPDF cannot confirm it DESCRIBES topic/purpose (the SC's bar) — presence is not descriptiveness — only part of the criterion is proven (oracle), not the whole; a full claim needs coverage the tool cannot confirm |
| 2.4.3 Focus Order | Not Applicable | does not apply to a static, non-interactive print PDF |
| 2.4.4 Link Purpose (In Context) | Does Not Support | no warrant entails this criterion for this deliverable (a known gap) |
| 2.5.1 Pointer Gestures | Not Applicable | does not apply to a static, non-interactive print PDF |
| 2.5.2 Pointer Cancellation | Not Applicable | does not apply to a static, non-interactive print PDF |
| 2.5.3 Label in Name | Not Applicable | does not apply to a static, non-interactive print PDF |
| 2.5.4 Motion Actuation | Not Applicable | does not apply to a static, non-interactive print PDF |
| 3.1.1 Language of Page | Supports | rnd-a11y-latex (veraPDF): UA requires (and veraPDF checks) the document's primary language be set (oracle) |
| 3.2.1 On Focus | Not Applicable | does not apply to a static, non-interactive print PDF |
| 3.2.2 On Input | Not Applicable | does not apply to a static, non-interactive print PDF |
| 3.2.6 Consistent Help | Not Applicable | does not apply to a static, non-interactive print PDF |
| 3.3.1 Error Identification | Not Applicable | does not apply to a static, non-interactive print PDF |
| 3.3.2 Labels or Instructions | Not Applicable | does not apply to a static, non-interactive print PDF |
| 3.3.7 Redundant Entry | Not Applicable | does not apply to a static, non-interactive print PDF |
| 4.1.2 Name, Role, Value | Does Not Support | no warrant entails this criterion for this deliverable (a known gap) |

### Table 2: Success Criteria, Level AA

| Criteria | Conformance Level | Remarks and Explanations |
| --- | --- | --- |
| 1.2.4 Captions (Live) | Not Applicable | does not apply to a static, non-interactive print PDF |
| 1.2.5 Audio Description (Prerecorded) | Not Applicable | does not apply to a static, non-interactive print PDF |
| 1.3.4 Orientation | Not Applicable | does not apply to a static, non-interactive print PDF |
| 1.3.5 Identify Input Purpose | Not Applicable | does not apply to a static, non-interactive print PDF |
| 1.4.3 Contrast (Minimum) | Does Not Support | no warrant entails this criterion for this deliverable (a known gap) |
| 1.4.4 Resize Text | Not Applicable | does not apply to a static, non-interactive print PDF |
| 1.4.5 Images of Text | Does Not Support | no warrant entails this criterion for this deliverable (a known gap) |
| 1.4.10 Reflow | Not Applicable | does not apply to a static, non-interactive print PDF |
| 1.4.11 Non-text Contrast | Does Not Support | no warrant entails this criterion for this deliverable (a known gap) |
| 1.4.12 Text Spacing | Not Applicable | does not apply to a static, non-interactive print PDF |
| 1.4.13 Content on Hover or Focus | Not Applicable | does not apply to a static, non-interactive print PDF |
| 2.4.5 Multiple Ways | Not Applicable | does not apply to a static, non-interactive print PDF |
| 2.4.6 Headings and Labels | Partially Supports | rnd-a11y-latex (veraPDF): UA validates tagged headings, but not that EVERY visual heading was tagged as one (completeness is a human checkpoint) — only part of the criterion is proven (oracle), not the whole; a full claim needs coverage the tool cannot confirm |
| 2.4.7 Focus Visible | Not Applicable | does not apply to a static, non-interactive print PDF |
| 2.4.11 Focus Not Obscured (Minimum) | Not Applicable | does not apply to a static, non-interactive print PDF |
| 2.5.7 Dragging Movements | Not Applicable | does not apply to a static, non-interactive print PDF |
| 2.5.8 Target Size (Minimum) | Not Applicable | does not apply to a static, non-interactive print PDF |
| 3.1.2 Language of Parts | Not Applicable | does not apply to a static, non-interactive print PDF |
| 3.2.3 Consistent Navigation | Not Applicable | does not apply to a static, non-interactive print PDF |
| 3.2.4 Consistent Identification | Not Applicable | does not apply to a static, non-interactive print PDF |
| 3.3.3 Error Suggestion | Not Applicable | does not apply to a static, non-interactive print PDF |
| 3.3.4 Error Prevention (Legal, Financial, Data) | Not Applicable | does not apply to a static, non-interactive print PDF |
| 3.3.8 Accessible Authentication (Minimum) | Not Applicable | does not apply to a static, non-interactive print PDF |
| 4.1.3 Status Messages | Not Applicable | does not apply to a static, non-interactive print PDF |

### Table 3: Success Criteria, Level AAA

| Criteria | Conformance Level | Remarks and Explanations |
| --- | --- | --- |
| 1.2.6 Sign Language (Prerecorded) | Not Applicable | does not apply to a static, non-interactive print PDF |
| 1.2.7 Extended Audio Description (Prerecorded) | Not Applicable | does not apply to a static, non-interactive print PDF |
| 1.2.8 Media Alternative (Prerecorded) | Not Applicable | does not apply to a static, non-interactive print PDF |
| 1.2.9 Audio-only (Live) | Not Applicable | does not apply to a static, non-interactive print PDF |
| 1.3.6 Identify Purpose | Does Not Support | no warrant entails this criterion for this deliverable (a known gap) |
| 1.4.6 Contrast (Enhanced) | Does Not Support | no warrant entails this criterion for this deliverable (a known gap) |
| 1.4.7 Low or No Background Audio | Not Applicable | does not apply to a static, non-interactive print PDF |
| 1.4.8 Visual Presentation | Does Not Support | no warrant entails this criterion for this deliverable (a known gap) |
| 1.4.9 Images of Text (No Exception) | Does Not Support | no warrant entails this criterion for this deliverable (a known gap) |
| 2.1.3 Keyboard (No Exception) | Not Applicable | does not apply to a static, non-interactive print PDF |
| 2.2.3 No Timing | Not Applicable | does not apply to a static, non-interactive print PDF |
| 2.2.4 Interruptions | Not Applicable | does not apply to a static, non-interactive print PDF |
| 2.2.5 Re-authenticating | Not Applicable | does not apply to a static, non-interactive print PDF |
| 2.2.6 Timeouts | Not Applicable | does not apply to a static, non-interactive print PDF |
| 2.3.2 Three Flashes | Not Applicable | does not apply to a static, non-interactive print PDF |
| 2.3.3 Animation from Interactions | Not Applicable | does not apply to a static, non-interactive print PDF |
| 2.4.8 Location | Not Applicable | does not apply to a static, non-interactive print PDF |
| 2.4.9 Link Purpose (Link Only) | Does Not Support | no warrant entails this criterion for this deliverable (a known gap) |
| 2.4.10 Section Headings | Does Not Support | no warrant entails this criterion for this deliverable (a known gap) |
| 2.4.12 Focus Not Obscured (Enhanced) | Not Applicable | does not apply to a static, non-interactive print PDF |
| 2.4.13 Focus Appearance | Not Applicable | does not apply to a static, non-interactive print PDF |
| 2.5.5 Target Size (Enhanced) | Not Applicable | does not apply to a static, non-interactive print PDF |
| 2.5.6 Concurrent Input Mechanisms | Not Applicable | does not apply to a static, non-interactive print PDF |
| 3.1.3 Unusual Words | Does Not Support | no warrant entails this criterion for this deliverable (a known gap) |
| 3.1.4 Abbreviations | Does Not Support | no warrant entails this criterion for this deliverable (a known gap) |
| 3.1.5 Reading Level | Does Not Support | no warrant entails this criterion for this deliverable (a known gap) |
| 3.1.6 Pronunciation | Does Not Support | no warrant entails this criterion for this deliverable (a known gap) |
| 3.2.5 Change on Request | Not Applicable | does not apply to a static, non-interactive print PDF |
| 3.3.5 Help | Not Applicable | does not apply to a static, non-interactive print PDF |
| 3.3.6 Error Prevention (All) | Not Applicable | does not apply to a static, non-interactive print PDF |
| 3.3.9 Accessible Authentication (Enhanced) | Not Applicable | does not apply to a static, non-interactive print PDF |

## Revised Section 508 Report

Section 508 incorporates WCAG 2.0 Level A and AA by reference. Criteria introduced after WCAG 2.0 are outside 508 scope by version (disclosed below, not scored as 508).

| Criteria | Conformance Level | Remarks and Explanations |
| --- | --- | --- |
| 1.1.1 Non-text Content (A) | Supports | rnd-a11y-latex (veraPDF): veraPDF confirms /Alt PRESENT; on docx it is the raw-LaTeX source (not an equivalent a screen reader can speak) → fragment, on latex it is recoverable MathML (/AF) → full (oracle) |
| 1.2.1 Audio-only and Video-only (Prerecorded) (A) | Not Applicable | does not apply to a static, non-interactive print PDF |
| 1.2.2 Captions (Prerecorded) (A) | Not Applicable | does not apply to a static, non-interactive print PDF |
| 1.2.3 Audio Description or Media Alternative (Prerecorded) (A) | Not Applicable | does not apply to a static, non-interactive print PDF |
| 1.2.4 Captions (Live) (AA) | Not Applicable | does not apply to a static, non-interactive print PDF |
| 1.2.5 Audio Description (Prerecorded) (AA) | Not Applicable | does not apply to a static, non-interactive print PDF |
| 1.3.1 Info and Relationships (A) | Partially Supports | rnd-a11y-latex (veraPDF): UA validates the structure tree, but veraPDF cannot confirm EVERY visual relationship was tagged (completeness is a human PDF/UA checkpoint) — only part of the criterion is proven (oracle), not the whole; a full claim needs coverage the tool cannot confirm |
| 1.3.2 Meaningful Sequence (A) | Partially Supports | rnd-a11y-latex (veraPDF): UA validates a reading order exists, but not that it matches the visual sequence (correctness is a human checkpoint) — only part of the criterion is proven (oracle), not the whole; a full claim needs coverage the tool cannot confirm |
| 1.3.3 Sensory Characteristics (A) | Does Not Support | no warrant entails this criterion for this deliverable (a known gap) |
| 1.4.1 Use of Color (A) | Partially Supports | rnd-ruler entails this — only part of the criterion is proven (farm), not the whole; a full claim needs coverage the tool cannot confirm |
| 1.4.2 Audio Control (A) | Not Applicable | does not apply to a static, non-interactive print PDF |
| 1.4.3 Contrast (Minimum) (AA) | Does Not Support | no warrant entails this criterion for this deliverable (a known gap) |
| 1.4.4 Resize Text (AA) | Not Applicable | does not apply to a static, non-interactive print PDF |
| 1.4.5 Images of Text (AA) | Does Not Support | no warrant entails this criterion for this deliverable (a known gap) |
| 2.1.1 Keyboard (A) | Not Applicable | does not apply to a static, non-interactive print PDF |
| 2.1.2 No Keyboard Trap (A) | Not Applicable | does not apply to a static, non-interactive print PDF |
| 2.2.1 Timing Adjustable (A) | Not Applicable | does not apply to a static, non-interactive print PDF |
| 2.2.2 Pause, Stop, Hide (A) | Not Applicable | does not apply to a static, non-interactive print PDF |
| 2.3.1 Three Flashes or Below Threshold (A) | Not Applicable | does not apply to a static, non-interactive print PDF |
| 2.4.1 Bypass Blocks (A) | Not Applicable | does not apply to a static, non-interactive print PDF |
| 2.4.2 Page Titled (A) | Partially Supports | rnd-a11y-latex (veraPDF): UA validates a title EXISTS and DisplayDocTitle, but veraPDF cannot confirm it DESCRIBES topic/purpose (the SC's bar) — presence is not descriptiveness — only part of the criterion is proven (oracle), not the whole; a full claim needs coverage the tool cannot confirm |
| 2.4.3 Focus Order (A) | Not Applicable | does not apply to a static, non-interactive print PDF |
| 2.4.4 Link Purpose (In Context) (A) | Does Not Support | no warrant entails this criterion for this deliverable (a known gap) |
| 2.4.5 Multiple Ways (AA) | Not Applicable | does not apply to a static, non-interactive print PDF |
| 2.4.6 Headings and Labels (AA) | Partially Supports | rnd-a11y-latex (veraPDF): UA validates tagged headings, but not that EVERY visual heading was tagged as one (completeness is a human checkpoint) — only part of the criterion is proven (oracle), not the whole; a full claim needs coverage the tool cannot confirm |
| 2.4.7 Focus Visible (AA) | Not Applicable | does not apply to a static, non-interactive print PDF |
| 3.1.1 Language of Page (A) | Supports | rnd-a11y-latex (veraPDF): UA requires (and veraPDF checks) the document's primary language be set (oracle) |
| 3.1.2 Language of Parts (AA) | Not Applicable | does not apply to a static, non-interactive print PDF |
| 3.2.1 On Focus (A) | Not Applicable | does not apply to a static, non-interactive print PDF |
| 3.2.2 On Input (A) | Not Applicable | does not apply to a static, non-interactive print PDF |
| 3.2.3 Consistent Navigation (AA) | Not Applicable | does not apply to a static, non-interactive print PDF |
| 3.2.4 Consistent Identification (AA) | Not Applicable | does not apply to a static, non-interactive print PDF |
| 3.3.1 Error Identification (A) | Not Applicable | does not apply to a static, non-interactive print PDF |
| 3.3.2 Labels or Instructions (A) | Not Applicable | does not apply to a static, non-interactive print PDF |
| 3.3.3 Error Suggestion (AA) | Not Applicable | does not apply to a static, non-interactive print PDF |
| 3.3.4 Error Prevention (Legal, Financial, Data) (AA) | Not Applicable | does not apply to a static, non-interactive print PDF |
| 4.1.2 Name, Role, Value (A) | Does Not Support | no warrant entails this criterion for this deliverable (a known gap) |

## EN 301 549 V3.2.1 Report (Chapter 10, Non-web Documents)

EN 301 549 V3.2.1 references WCAG 2.1. Chapter 10 maps each adopted criterion to clause 10.x; criteria new in WCAG 2.2 have no clause in this version (out of scope by version).

| EN Clause | Criteria | Status | Remarks and Explanations |
| --- | --- | --- | --- |
| 10.1.1.1 | 1.1.1 Non-text Content | Supports | rnd-a11y-latex (veraPDF): veraPDF confirms /Alt PRESENT; on docx it is the raw-LaTeX source (not an equivalent a screen reader can speak) → fragment, on latex it is recoverable MathML (/AF) → full (oracle) |
| 10.1.2.1 | 1.2.1 Audio-only and Video-only (Prerecorded) | Not Applicable | does not apply to a static, non-interactive print PDF |
| 10.1.2.2 | 1.2.2 Captions (Prerecorded) | Not Applicable | does not apply to a static, non-interactive print PDF |
| 10.1.2.3 | 1.2.3 Audio Description or Media Alternative (Prerecorded) | Not Applicable | does not apply to a static, non-interactive print PDF |
| 10.1.2.4 | 1.2.4 Captions (Live) | Not Applicable | does not apply to a static, non-interactive print PDF |
| 10.1.2.5 | 1.2.5 Audio Description (Prerecorded) | Not Applicable | does not apply to a static, non-interactive print PDF |
| 10.1.2.6 | 1.2.6 Sign Language (Prerecorded) | Void | not applicable to non-web documents per EN |
| 10.1.2.7 | 1.2.7 Extended Audio Description (Prerecorded) | Void | not applicable to non-web documents per EN |
| 10.1.2.8 | 1.2.8 Media Alternative (Prerecorded) | Void | not applicable to non-web documents per EN |
| 10.1.2.9 | 1.2.9 Audio-only (Live) | Void | not applicable to non-web documents per EN |
| 10.1.3.1 | 1.3.1 Info and Relationships | Partially Supports | rnd-a11y-latex (veraPDF): UA validates the structure tree, but veraPDF cannot confirm EVERY visual relationship was tagged (completeness is a human PDF/UA checkpoint) — only part of the criterion is proven (oracle), not the whole; a full claim needs coverage the tool cannot confirm |
| 10.1.3.2 | 1.3.2 Meaningful Sequence | Partially Supports | rnd-a11y-latex (veraPDF): UA validates a reading order exists, but not that it matches the visual sequence (correctness is a human checkpoint) — only part of the criterion is proven (oracle), not the whole; a full claim needs coverage the tool cannot confirm |
| 10.1.3.3 | 1.3.3 Sensory Characteristics | Does Not Support | no warrant entails this criterion for this deliverable (a known gap) |
| 10.1.3.4 | 1.3.4 Orientation | Not Applicable | does not apply to a static, non-interactive print PDF |
| 10.1.3.5 | 1.3.5 Identify Input Purpose | Not Applicable | does not apply to a static, non-interactive print PDF |
| 10.1.3.6 | 1.3.6 Identify Purpose | Void | not applicable to non-web documents per EN |
| 10.1.4.1 | 1.4.1 Use of Color | Partially Supports | rnd-ruler entails this — only part of the criterion is proven (farm), not the whole; a full claim needs coverage the tool cannot confirm |
| 10.1.4.2 | 1.4.2 Audio Control | Not Applicable | does not apply to a static, non-interactive print PDF |
| 10.1.4.3 | 1.4.3 Contrast (Minimum) | Does Not Support | no warrant entails this criterion for this deliverable (a known gap) |
| 10.1.4.4 | 1.4.4 Resize Text | Not Applicable | does not apply to a static, non-interactive print PDF |
| 10.1.4.5 | 1.4.5 Images of Text | Does Not Support | no warrant entails this criterion for this deliverable (a known gap) |
| 10.1.4.6 | 1.4.6 Contrast (Enhanced) | Void | not applicable to non-web documents per EN |
| 10.1.4.7 | 1.4.7 Low or No Background Audio | Void | not applicable to non-web documents per EN |
| 10.1.4.8 | 1.4.8 Visual Presentation | Void | not applicable to non-web documents per EN |
| 10.1.4.9 | 1.4.9 Images of Text (No Exception) | Void | not applicable to non-web documents per EN |
| 10.1.4.10 | 1.4.10 Reflow | Not Applicable | does not apply to a static, non-interactive print PDF |
| 10.1.4.11 | 1.4.11 Non-text Contrast | Does Not Support | no warrant entails this criterion for this deliverable (a known gap) |
| 10.1.4.12 | 1.4.12 Text Spacing | Not Applicable | does not apply to a static, non-interactive print PDF |
| 10.1.4.13 | 1.4.13 Content on Hover or Focus | Not Applicable | does not apply to a static, non-interactive print PDF |
| 10.2.1.1 | 2.1.1 Keyboard | Not Applicable | does not apply to a static, non-interactive print PDF |
| 10.2.1.2 | 2.1.2 No Keyboard Trap | Not Applicable | does not apply to a static, non-interactive print PDF |
| 10.2.1.3 | 2.1.3 Keyboard (No Exception) | Void | not applicable to non-web documents per EN |
| 10.2.1.4 | 2.1.4 Character Key Shortcuts | Not Applicable | does not apply to a static, non-interactive print PDF |
| 10.2.2.1 | 2.2.1 Timing Adjustable | Not Applicable | does not apply to a static, non-interactive print PDF |
| 10.2.2.2 | 2.2.2 Pause, Stop, Hide | Not Applicable | does not apply to a static, non-interactive print PDF |
| 10.2.2.3 | 2.2.3 No Timing | Void | not applicable to non-web documents per EN |
| 10.2.2.4 | 2.2.4 Interruptions | Void | not applicable to non-web documents per EN |
| 10.2.2.5 | 2.2.5 Re-authenticating | Void | not applicable to non-web documents per EN |
| 10.2.2.6 | 2.2.6 Timeouts | Void | not applicable to non-web documents per EN |
| 10.2.3.1 | 2.3.1 Three Flashes or Below Threshold | Not Applicable | does not apply to a static, non-interactive print PDF |
| 10.2.3.2 | 2.3.2 Three Flashes | Void | not applicable to non-web documents per EN |
| 10.2.3.3 | 2.3.3 Animation from Interactions | Void | not applicable to non-web documents per EN |
| 10.2.4.1 | 2.4.1 Bypass Blocks | Void | not applicable to non-web documents per EN |
| 10.2.4.2 | 2.4.2 Page Titled | Partially Supports | rnd-a11y-latex (veraPDF): UA validates a title EXISTS and DisplayDocTitle, but veraPDF cannot confirm it DESCRIBES topic/purpose (the SC's bar) — presence is not descriptiveness — only part of the criterion is proven (oracle), not the whole; a full claim needs coverage the tool cannot confirm |
| 10.2.4.3 | 2.4.3 Focus Order | Not Applicable | does not apply to a static, non-interactive print PDF |
| 10.2.4.4 | 2.4.4 Link Purpose (In Context) | Does Not Support | no warrant entails this criterion for this deliverable (a known gap) |
| 10.2.4.5 | 2.4.5 Multiple Ways | Void | not applicable to non-web documents per EN |
| 10.2.4.6 | 2.4.6 Headings and Labels | Partially Supports | rnd-a11y-latex (veraPDF): UA validates tagged headings, but not that EVERY visual heading was tagged as one (completeness is a human checkpoint) — only part of the criterion is proven (oracle), not the whole; a full claim needs coverage the tool cannot confirm |
| 10.2.4.7 | 2.4.7 Focus Visible | Not Applicable | does not apply to a static, non-interactive print PDF |
| 10.2.4.8 | 2.4.8 Location | Void | not applicable to non-web documents per EN |
| 10.2.4.9 | 2.4.9 Link Purpose (Link Only) | Void | not applicable to non-web documents per EN |
| 10.2.4.10 | 2.4.10 Section Headings | Void | not applicable to non-web documents per EN |
| — | 2.4.11 Focus Not Obscured (Minimum) | Out of scope (post-2.1) | not in EN 301 549 V3.2.1 |
| — | 2.4.12 Focus Not Obscured (Enhanced) | Out of scope (post-2.1) | not in EN 301 549 V3.2.1 |
| — | 2.4.13 Focus Appearance | Out of scope (post-2.1) | not in EN 301 549 V3.2.1 |
| 10.2.5.1 | 2.5.1 Pointer Gestures | Not Applicable | does not apply to a static, non-interactive print PDF |
| 10.2.5.2 | 2.5.2 Pointer Cancellation | Not Applicable | does not apply to a static, non-interactive print PDF |
| 10.2.5.3 | 2.5.3 Label in Name | Not Applicable | does not apply to a static, non-interactive print PDF |
| 10.2.5.4 | 2.5.4 Motion Actuation | Not Applicable | does not apply to a static, non-interactive print PDF |
| 10.2.5.5 | 2.5.5 Target Size (Enhanced) | Void | not applicable to non-web documents per EN |
| 10.2.5.6 | 2.5.6 Concurrent Input Mechanisms | Void | not applicable to non-web documents per EN |
| — | 2.5.7 Dragging Movements | Out of scope (post-2.1) | not in EN 301 549 V3.2.1 |
| — | 2.5.8 Target Size (Minimum) | Out of scope (post-2.1) | not in EN 301 549 V3.2.1 |
| 10.3.1.1 | 3.1.1 Language of Page | Supports | rnd-a11y-latex (veraPDF): UA requires (and veraPDF checks) the document's primary language be set (oracle) |
| 10.3.1.2 | 3.1.2 Language of Parts | Not Applicable | does not apply to a static, non-interactive print PDF |
| 10.3.1.3 | 3.1.3 Unusual Words | Void | not applicable to non-web documents per EN |
| 10.3.1.4 | 3.1.4 Abbreviations | Void | not applicable to non-web documents per EN |
| 10.3.1.5 | 3.1.5 Reading Level | Void | not applicable to non-web documents per EN |
| 10.3.1.6 | 3.1.6 Pronunciation | Void | not applicable to non-web documents per EN |
| 10.3.2.1 | 3.2.1 On Focus | Not Applicable | does not apply to a static, non-interactive print PDF |
| 10.3.2.2 | 3.2.2 On Input | Not Applicable | does not apply to a static, non-interactive print PDF |
| 10.3.2.3 | 3.2.3 Consistent Navigation | Void | not applicable to non-web documents per EN |
| 10.3.2.4 | 3.2.4 Consistent Identification | Void | not applicable to non-web documents per EN |
| 10.3.2.5 | 3.2.5 Change on Request | Void | not applicable to non-web documents per EN |
| — | 3.2.6 Consistent Help | Out of scope (post-2.1) | not in EN 301 549 V3.2.1 |
| 10.3.3.1 | 3.3.1 Error Identification | Not Applicable | does not apply to a static, non-interactive print PDF |
| 10.3.3.2 | 3.3.2 Labels or Instructions | Not Applicable | does not apply to a static, non-interactive print PDF |
| 10.3.3.3 | 3.3.3 Error Suggestion | Not Applicable | does not apply to a static, non-interactive print PDF |
| 10.3.3.4 | 3.3.4 Error Prevention (Legal, Financial, Data) | Not Applicable | does not apply to a static, non-interactive print PDF |
| 10.3.3.5 | 3.3.5 Help | Void | not applicable to non-web documents per EN |
| 10.3.3.6 | 3.3.6 Error Prevention (All) | Void | not applicable to non-web documents per EN |
| — | 3.3.7 Redundant Entry | Out of scope (post-2.1) | not in EN 301 549 V3.2.1 |
| — | 3.3.8 Accessible Authentication (Minimum) | Out of scope (post-2.1) | not in EN 301 549 V3.2.1 |
| — | 3.3.9 Accessible Authentication (Enhanced) | Out of scope (post-2.1) | not in EN 301 549 V3.2.1 |
| 10.4.1.2 | 4.1.2 Name, Role, Value | Does Not Support | no warrant entails this criterion for this deliverable (a known gap) |
| 10.4.1.3 | 4.1.3 Status Messages | Not Applicable | does not apply to a static, non-interactive print PDF |

## Sources

- W3C Recommendation, Web Content Accessibility Guidelines (WCAG) 2.2, 2024-12-12 (https://www.w3.org/TR/WCAG22/)
- Revised Section 508 Standards, US Access Board 2017, 36 CFR Part 1194 — incorporates WCAG 2.0 Level A and AA by reference (E207); no published per-SC crosswalk (column DERIVED)
- ETSI EN 301 549 V3.2.1 (2021-03), Chapter 10 (Non-web documents) — references WCAG 2.1; clause = 10.<SC> for adopted rows, Void/absent as recorded (https://www.etsi.org/deliver/etsi_en/301500_301599/301549/03.02.01_60/en_301549v030201p.pdf)
- ISO 14289 (PDF/UA) tagging requirements ↔ WCAG, per the PDF/UA-WCAG correspondence (Matterhorn Protocol / PDF Association guidance); only the directly-established correspondences are claimed here


---
<!-- /paperkit:raw -->
