# Build the LNI artifact paper. Requires lni.cls on TEXINPUTS + biber.
# The updated biblatex-LNI style (LNI.bbx/.cbx/.lbx, v0.7 from gi-ev/biblatex-lni)
# is bundled in this folder; running pdflatex here makes kpathsea pick up these
# local copies before the TeX distribution's, so the bundled (unified-DOI) style is used.
DOC = artifact

.PHONY: all clean
all: $(DOC).pdf

$(DOC).pdf: $(DOC).tex $(DOC).bib
	pdflatex -interaction=nonstopmode $(DOC).tex
	biber $(DOC)
	pdflatex -interaction=nonstopmode $(DOC).tex
	pdflatex -interaction=nonstopmode $(DOC).tex

clean:
	rm -f $(DOC).aux $(DOC).bbl $(DOC).bcf $(DOC).blg $(DOC).log \
	      $(DOC).out $(DOC).run.xml $(DOC).toc
