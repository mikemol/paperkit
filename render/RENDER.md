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

