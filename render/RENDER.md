# Paperkit — Rendering: paper.md → docx, Gated to Agree

*On-demand: the paper renders to a Word document, and the document is gated to PRESENT the verified paper faithfully — presentation agreement extends prose≡projection down the render stack.*

## Emit: paper.md → docx

The paper renders to a Word document — pandoc turns paper.md into a valid .docx (a well-formed OOXML package that pandoc can read back), the first presentation beyond markdown [@rnd-emit].

## Presentation Agreement

The rendered document PRESENTS the verified paper: the plain text a reader sees in the .docx is byte-for-byte the plain text of paper.md, so the render preserves the content — presentation agreement extends prose≡projection down the render stack, from the gated source to the delivered document [@rnd-agree].

## Output Integrity & Fidelity

The rendered document is structurally sound: word/document.xml is well-formed OOXML, and every section of the paper is presented as a real Word heading whose text matches — the structure survives the render, never flattened into body text [@rnd-wf]. And the reader's view is faithful: rendered all the way to a PDF, every non-ASCII glyph the paper uses survives into the text layer with no missing-glyph tofu, and every heading is present there — what the consumer copies, searches, or hears through a screen reader is the paper, not a broken rendering [@rnd-fidelity].

## Visual Fidelity (the rendered pixels)

The reader's EYE sees the paper, not just a screen reader: rendered to a PDF and rasterized to images, OCR recovers the paper's text from the pixels themselves — a font or render regression that turned the body to tofu would crater that recovery, so the visual layer is gated, not only the text layer [@rnd-ocr]. And every font in the rendered PDF is EMBEDDED, so it draws identically on a machine that lacks the font — no silent substitution to a glyph the author never saw [@rnd-fonts].

## Citations: Warrants Inline, Sources Referenced

The paper's two kinds of citation RESOLVE in the render: an internal warrant becomes an inline machine-checked marker (cite_split, before pandoc), an external source renders author-date with a References list (–citeproc over references.bib), and no bracketed citation marker is left as bare text — a render-time projection that leaves the gated paper.md untouched [@rnd-bib]. Which of these a citation MATERIALIZES as is the projector's render TARGET — pandoc emits an inline citeproc marker, web an intra-page anchor, footnote a document-end provenance note, and plain surfaces NO citation marker at all: a clean SUBMISSION view that presents the same verified prose with the machinery removed, while the claim-DAG stays the author-side gate [@rnd-plain].

## The PDF Deliverable

The paper renders END-TO-END to a PDF deliverable — cite_split, then citeproc, then docx, then PDF: the human-readable artifact a reader actually receives — gated to be complete and polished: no citation is left as a bare marker, the References list renders, and the paper's content is present in the PDF [@rnd-pdf]. And a document index or table of contents is refreshed by driving the export over the office suite's UNO scripting bridge on a PRIVATE SOCKET, held to a deadline and killed if it will not exit, because the headless command-line conversion never populates the index field — adopted from sre-troubleshooting, carrying forward the fix for its first attempt (a document macro that hung the build with no output): the socket path and the deadline-kill turn a hang into a LOUD bounded failure rather than a silent stall — the mechanism is proven on the bridge itself; paperkit's current paper carries no index field, so this warrant is dormant on the present deliverable and live for a downstream paper that has a table of contents [@rnd-index].

## Figures: Vector and Legible

A generated figure renders into the document as a Word-native VECTOR — SVG converted to EMF (libreoffice), embedded by pandoc, and carried through to the PDF without ever being rasterized — so it stays crisp at any zoom, with no pixelation for a reader who magnifies the page [@rnd-fig-vector]; the figure's legend SURVIVES into the rendered PDF text layer — every label selectable, searchable, and screen-readable rather than locked inside the pixels — the accessibility of the report's Okabe-Ito claim-DAG figure, preserved through the render [@rnd-fig-legible]. And a figure's edges survive the vector conversion — the SVG viewport is PADDED by a symmetric margin before the SVG-to-EMF step, because that step shaves each edge and clips titles and legends flush against the drawing's bounding box, so the boundary the clipper trims is empty space and the drawing keeps its full extent — adopted from sre-troubleshooting's third render workaround, classified by mat230's audit-table frame as RENDER FIDELITY and NOT a WCAG criterion, so it lives with the figure checks and never in the accessibility gate [@rnd-fig-pad].

## Accessibility: PDF/UA by Construction

Every link annotation in the deliverable carries a text description — a pass over the finished PDF reads the words whose boxes OVERLAP each undescribed link's rectangle and writes them back as that link's description, on the reasoning that the words a sighted reader sees are what a screen reader should hear, so a citation link announces its destination rather than a bare "link" (PDF/UA 7.18.1 and 7.18.5) — adopted from sre-troubleshooting, carrying its half-description fix forward: selection is by BOX OVERLAP not word centre, so two adjacent citations that extract as one word are both described [@rnd-link-alt]. And the deliverable declares the PDF/UA identification metadata the office export omits — a post-export stamp writes the document title (READ from the paper's own paper.toml, never hardcoded), the pdfuaid identification schema, and the ViewerPreferences DisplayDocTitle flag, closing the three identification clauses (ISO 14289-1 section 5 test 1, 7.1 tests 9 and 10) that a headless LibreOffice conversion leaves unset — none is content, all three are a stamp [@rnd-pdfua-meta]. So paperkit's OWN paper is PDF/UA-1 conformant BY CONSTRUCTION — the deliverable is built as the pdf check builds it and then repaired (link descriptions restored, identification metadata stamped), and veraPDF validates it at UA-1 with zero failed checks over a Tagged PDF, gating on the flavour the producer targets (LibreOffice emits UA-1 and declares pdfuaid part 1) — what was an opt-in measurement a downstream deliverable pointed at is now a live warrant of the render project's own output, earned by the adopted repair rather than asserted [@rnd-a11y].
