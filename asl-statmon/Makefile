BINS = \
	asl-statmon \
	asl-statmon-test-client.py \

SYSDS = \
	asl-statmon@.service 
	
BINS_EXP = $(patsubst %, $(DESTDIR)/usr/local/bin/%, $(BINS))
SYSDS_EXP = $(patsubst %, $(DESTDIR)/etc/systemd/system/%, $(SYSDS))

install: $(BINS_EXP) $(SYSDS_EXP)

$(DESTDIR)/usr/local/bin/%:	%
	install -D -m 0755 $< $@

$(DESTDIR)/etc/systemd/system/%:	%
	install -D -m 0644 $< $@
