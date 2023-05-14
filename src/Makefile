BINS = \
	allmon3 \
	allmon3-passwd \
	allmon3-cmd-client \
	allmon3-status-client \
	allmon3-voter-client 

SYSDS = \
	allmon3.service \

MANS_SRC = $(wildcard *.1.md)

PY_SRC = $(wildcard asl_allmon/*/__init__.py)

prefix ?= /usr
exec_prefix ?= $(prefix)
bin_prefix ?= $(exec_prefix)/bin
pylibdir ?= $(exec_prefix)/lib/python3/dist-packages
mandir ?= $(prefix)/share/man
sysd_service ?= /lib/systemd/system
	
BINS_EXP = $(patsubst %, $(DESTDIR)$(bin_prefix)/%, $(BINS))
SYSDS_EXP = $(patsubst %, $(DESTDIR)$(sysd_service)/%, $(SYSDS))
MANS_EXP = $(patsubst %.md, $(DESTDIR)$(mandir)/man1/%, $(MANS_SRC))
PY_EXP = $(patsubst %, $(DESTDIR)$(pylibdir)/%, $(PY_SRC))

showpy:
	echo $(PY_EXP)

install: $(BINS_EXP) $(SYSDS_EXP) $(MANS_EXP) $(PY_EXP)

mans:	$(MANS_EXP)

$(DESTDIR)$(bin_prefix)/%:	%
	install -D -m 0755 $< $@

$(DESTDIR)$(sysd_service)/%:	%
	install -D -m 0644 $< $@

$(DESTDIR)$(mandir)/man1/%:	%.md
	mkdir -p $(DESTDIR)$(mandir)/man1
	pandoc $< -s -t man > $@

$(DESTDIR)$(pylibdir)/%:	%
	install -D -m 0644 $< $@	
