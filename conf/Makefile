sysconfdir ?= /etc/allmon3

CONF_FILES = $(filter-out Makefile, $(wildcard *))
CONF_INSTALLABLES = $(patsubst %, $(destdir)$(sysconfdir)/%, $(CONF_FILES))

INSTALLABLES = $(CONF_INSTALLABLES)

.PHONY:	install
install:	$(INSTALLABLES)

$(destdir)$(sysconfdir)/%: %
	install -D -m 0644 -o 0 -g 0 $< $@
