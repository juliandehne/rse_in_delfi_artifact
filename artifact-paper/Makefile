# Build the LNI artifact paper. Requires lni.cls on TEXINPUTS + biber.
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
