# TeX Live 2025 install-tl profile for paperkit's executor image (Ζ·render·hermetic).
# Read by `install-tl -profile`.  Frozen repository: the 2025 tlnet-final on the historic archive,
# so every package byte is the one the release froze on — not "whatever CTAN has today".
#
# Collections are the ones render/checks/latex.py resolves (measured: unicode-math, luaotfload,
# luamml*, lualatex-math, nicematrix, the latex-lab tagging project under \DocumentMetadata):
#   collection-basic            kpsewhich, the engines' shared core
#   collection-latex            latex-lab / tagpdf (the testphase tagging project), the kernel
#   collection-latexrecommended
#   collection-latexextra       nicematrix and the .sty set the old host kept under ~/texmf
#   collection-luatex           lualatex, luaotfload, luamml, lualatex-math
#   collection-mathscience      unicode-math
#   collection-fontsrecommended Latin Modern (the document's main font) + the OpenType maths fonts
# No docs, no sources: the checks read none, and they are most of the download.
selected_scheme scheme-custom
collection-basic 1
collection-latex 1
collection-latexrecommended 1
collection-latexextra 1
collection-luatex 1
collection-mathscience 1
collection-fontsrecommended 1
TEXDIR /opt/texlive/2025
TEXMFCONFIG ~/.texlive2025/texmf-config
TEXMFHOME ~/texmf
TEXMFLOCAL /opt/texlive/texmf-local
TEXMFSYSCONFIG /opt/texlive/2025/texmf-config
TEXMFSYSVAR /opt/texlive/2025/texmf-var
TEXMFVAR ~/.texlive2025/texmf-var
instopt_adjustpath 0
instopt_adjustrepo 0
instopt_letter 0
instopt_portable 0
instopt_write18_restricted 1
tlpdbopt_autobackup 0
tlpdbopt_desktop_integration 0
tlpdbopt_file_assocs 0
tlpdbopt_install_docfiles 0
tlpdbopt_install_srcfiles 0
