BUILDABLES = \
	asl-statmon \
	asl-cmdlink \
	web

ETCS = \
	allmon3.ini

ETCS_EXP = $(patsubst %, $(DESTDIR)/etc/allmon3/%, $(ETCS))

install: $(ETCS_EXP)
	$(foreach dir, $(BUILDABLES), $(MAKE) -C $(dir);)

$(DESTDIR)/etc/allmon3/%:	%
	install -D -m 0644 $< $@
