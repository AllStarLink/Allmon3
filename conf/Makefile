sysconfdir ?= $(DESTDIR)/etc/allmon3

CONF_FILES = $(wildcard *)
CONF_INSTALLABLES = $(patsubst %, $(sysconfdir)/%, $(CONF_FILES))

INSTALLABLES = $(CONF_INSTALLABLES)

.PHONY:	install
install:	$(INSTALLABLES)

$(sysconfdir)/%: %
	install -D -m 0644 -o 0 -g 0 $< $@
