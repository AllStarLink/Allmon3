BINS = \
	asl-cmdlink \
	asl-cmdlink-cli \

SYSDS = \
	asl-cmdlink@.service 

prefix ?= /usr
exec_prefix ?= $(prefix)
bin_prefix ?= $(exec_prefix)/bin
sysd_service ?= /lib/systemd/system
	
BINS_EXP = $(patsubst %, $(destdir)$(bin_prefix)/%, $(BINS))
SYSDS_EXP = $(patsubst %, $(destdir)$(sysd_service)/%, $(SYSDS))

install: $(BINS_EXP) $(SYSDS_EXP)

$(destdir)$(bin_prefix)/%:	%
	install -D -m 0755 $< $@

$(destdir)$(sysd_service)/%:	%
	install -D -m 0644 $< $@
