prefix ?= /usr
docdir ?= $(prefix)/share/doc/allmon3

DOC_FILES = $(filter-out Makefile, $(wildcard *))
DOC_INSTALLABLES = $(patsubst %, $(DESTDIR)$(docdir)/%, $(DOC_FILES))

INSTALLABLES = $(DOC_INSTALLABLES)

.PHONY:	install
install:	$(INSTALLABLES)

$(DESTDIR)$(docdir)/%: %
	install -D -m 0644  $< $@
