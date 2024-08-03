sysconfdir ?= /etc/allmon3
prefix ?= /usr
docdir ?= $(prefix)/share/doc/allmon3
apacheconf ?= /etc/apache2/conf-available

CONF_FILES = $(filter-out Makefile allmon3.conf , $(wildcard *))
CONF_INSTALLABLES = $(patsubst %, $(DESTDIR)$(sysconfdir)/%, $(CONF_FILES))
CONF_DOCABLES = $(patsubst %, $(DESTDIR)$(docdir)/%, $(CONF_FILES))

CONF_APACHE_FILES = allmon3.conf
CONF_APACHE = $(patsubst %, $(DESTDIR)$(apacheconf)/%, $(CONF_APACHE_FILES))

INSTALLABLES = $(CONF_INSTALLABLES) $(CONF_DOCABLES) $(CONF_APACHE)

ifeq ($(shell id -u), 0)
INST_UID = -o allmon3 -g allmon3
endif

.PHONY: install
install:	$(INSTALLABLES)

test:
	@echo $(INST_UID)

$(DESTDIR)$(sysconfdir)/allmon3.ini:	allmon3.ini
	install -D -m 0640 $(INST_UID) $< $@

$(DESTDIR)$(sysconfdir)/users:	users
	install -D -m 0640 $(INST_UID) $< $@

$(DESTDIR)$(sysconfdir)/user-restrictions:	user-restrictions
	install -D -m 0640 $(INST_UID) $< $@

$(DESTDIR)$(sysconfdir)/%: %
	install -D -m 0644  $< $@

$(DESTDIR)$(apacheconf)/%:	%
	install -D -m 0644 $< $@

$(DESTDIR)$(docdir)/%: %
	install -D -m 0644  $< $@


