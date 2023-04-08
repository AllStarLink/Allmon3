BINS = \
	asl-statmon \
	asl-statmon-client \

SYSDS = \
	asl-statmon@.service 

exec_prefix ?= /usr
sysd_service ?= /lib/systemd/system
	
BINS_EXP = $(patsubst %, $(DESTDIR)$(exec_prefix)/bin/%, $(BINS))
SYSDS_EXP = $(patsubst %, $(DESTDIR)$(sysd_service)/%, $(SYSDS))

install: $(BINS_EXP) $(SYSDS_EXP)

$(DESTDIR)$(exec_prefix)/bin/%:	%
	install -D -m 0755 $< $@

$(DESTDIR)$(sysd_service)/%:	%
	install -D -m 0644 $< $@
