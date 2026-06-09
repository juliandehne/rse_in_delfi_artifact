# artifact-paper

`artifact.tex` — the artifact description in the **LNI** (Lecture Notes in
Informatics, Gesellschaft für Informatik) format, modelled on the LNI setup used in
`publications/pub_rse_methodology` (`_quarto-lni.yml`: `documentclass: lni`,
`biblatex`, `pdflatex` + `biber`).

## Building

The LNI document class `lni.cls` is **not** bundled here (it is the official GI
class). Obtain it once, then build:

1. Get the LNI class — either:
   - the official GI LNI template (`lni.cls`, `lni.bst`/biblatex `lni` style) from
     the Gesellschaft für Informatik, or
   - the **Overleaf** "LNI – Lecture Notes in Informatics" template (upload
     `artifact.tex` + `artifact.bib` there to build with zero local setup).
2. Build locally (class on your `TEXINPUTS`):

   ```bash
   make            # pdflatex → biber → pdflatex × 2
   # or manually:
   pdflatex artifact && biber artifact && pdflatex artifact && pdflatex artifact
   ```

   On **Windows**, use the PowerShell equivalent of the Makefile instead:

   ```powershell
   pwsh ./build.ps1            # pdflatex → biber → pdflatex × 2
   pwsh ./build.ps1 -Clean     # remove intermediates
   ```

   `build.ps1` deliberately compiles with the TinyTeX distribution that Quarto
   manages (`%APPDATA%\TinyTeX`), not the system MiKTeX on `PATH` — the latter has a
   version-mismatched kernel that fails on recent packages. Override the engine
   location with `-TexBinDir` if needed.

Output: `artifact.pdf`.

## Notes
- Uses `biblatex` with `biber` (matches the companion paper's LNI config).
- `\orcidID` is guarded with `\providecommand` so the file builds across `lni.cls`
  variants; if your class defines it, the guard is a no-op.
- The reproduced numbers in the paper (ICR averages, disagreement counts) are the
  exact outputs of `python run_pipeline.py` on the shipped data.
