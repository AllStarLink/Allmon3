BINS = \
	asl-cmdlink \
	asl-cmdlink-cli \

SYSDS = \
	asl-cmdlink@.service 

exec_prefix ?= /usr
sysd_service ?= /lib/systemd/system
	
BINS_EXP = $(patsubst %, $(destdir)$(exec_prefix)/bin/%, $(BINS))
SYSDS_EXP = $(patsubst %, $(destdir)$(sysd_service)/%, $(SYSDS))

install: $(BINS_EXP) $(SYSDS_EXP)

$(destdir)$(exec_prefix)/bin/%:	%
	install -D -m 0755 $< $@

$(destdir)$(sysd_service)/%:	%
	install -D -m 0644 $< $@
