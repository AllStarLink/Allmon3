sysconfdir ?= /etc/allmon3
prefix ?= /usr
docdir ?= $(prefix)/share/doc/allmon3

CONF_FILES = $(filter-out Makefile, $(wildcard *))
CONF_INSTALLABLES = $(patsubst %, $(DESTDIR)$(sysconfdir)/%, $(CONF_FILES))
CONF_DOCABLES = $(patsubst %, $(DESTDIR)$(docdir)/%, $(CONF_FILES))

INSTALLABLES = $(CONF_INSTALLABLES) $(CONF_DOCABLES)

.PHONY:	install
install:	$(INSTALLABLES)

$(DESTDIR)$(sysconfdir)/%: %
	install -D -m 0644  $< $@

$(DESTDIR)$(docdir)/%: %
	install -D -m 0644  $< $@


