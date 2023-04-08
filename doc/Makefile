prefix ?= /usr
docdir ?= $(destdir)$(prefix)/share/doc/allmon3

DOC_FILES = $(filter-out Makefile, $(wildcard *))
DOC_INSTALLABLES = $(patsubst %, $(docdir)/%, $(DOC_FILES))

INSTALLABLES = $(DOC_INSTALLABLES)

.PHONY:	install
install:	$(INSTALLABLES)

$(docdir)/%: %
	install -D -m 0644 -o 0 -g 0 $< $@
