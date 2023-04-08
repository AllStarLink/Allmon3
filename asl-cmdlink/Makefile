BINS = \
	asl-cmdlink \
	asl-cmdlink-cli \

SYSDS = \
	asl-cmdlink@.service 

exec_prefix ?= /usr
	
BINS_EXP = $(patsubst %, $(DESTDIR)$(exec_prefix)/bin/%, $(BINS))
SYSDS_EXP = $(patsubst %, $(DESTDIR)/lib/systemd/system/%, $(SYSDS))

install: $(BINS_EXP) $(SYSDS_EXP)

$(DESTDIR)$(exec_prefix)/bin/%:	%
	install -D -m 0755 $< $@

$(DESTDIR)/lib/systemd/system/%:	%
	install -D -m 0644 $< $@
