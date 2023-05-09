BINS = \
	allmon3 \
	allmon3-passwd \
	allmon3-procmgr \
	allmon3-cmd-client \
	allmon3-status-client \
	allmon3-voter-client 

SYSDS = \
	allmon3@.service \

MANS_SRC = $(wildcard *.1.md)

prefix ?= /usr
exec_prefix ?= $(prefix)
bin_prefix ?= $(exec_prefix)/bin
mandir ?= $(prefix)/share/man
sysd_service ?= /lib/systemd/system
	
BINS_EXP = $(patsubst %, $(DESTDIR)$(bin_prefix)/%, $(BINS))
SYSDS_EXP = $(patsubst %, $(DESTDIR)$(sysd_service)/%, $(SYSDS))
MANS_EXP = $(patsubst %.md, $(DESTDIR)$(mandir)/man1/%, $(MANS_SRC))

install: $(BINS_EXP) $(SYSDS_EXP) $(MANS_EXP)

mans:	$(MANS_EXP)

$(DESTDIR)$(bin_prefix)/%:	%
	install -D -m 0755 $< $@

$(DESTDIR)$(sysd_service)/%:	%
	install -D -m 0644 $< $@

$(DESTDIR)$(mandir)/man1/%:	%.md
	mkdir -p $(DESTDIR)$(mandir)/man1
	pandoc $< -s -t man > $@
	
