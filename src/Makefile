BINS = \
	asl-statmon \
	asl-statmon-client \
	asl-cmdlink \
	asl-cmdlink-cli \

SYSDS = \
	asl-statmon@.service \
	asl-cmdlink@.service 

prefix ?= /usr
exec_prefix ?= $(prefix)
bin_prefix ?= $(exec_prefix)/bin
sysd_service ?= /lib/systemd/system
	
BINS_EXP = $(patsubst %, $(DESTDIR)$(bin_prefix)/%, $(BINS))
SYSDS_EXP = $(patsubst %, $(DESTDIR)$(sysd_service)/%, $(SYSDS))

install: $(BINS_EXP) $(SYSDS_EXP)

$(DESTDIR)$(bin_prefix)/%:	%
	install -D -m 0755 $< $@

$(DESTDIR)$(sysd_service)/%:	%
	install -D -m 0644 $< $@
