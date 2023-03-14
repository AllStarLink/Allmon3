BUILDABLES = \
	asl-statmon \
	asl-cmdlink

ETCS = \
	allmon3.ini

ETCS_EXP = $(patsubst %, $(DESTDIR)/usr/local/etc/%, $(ETCS))

install: $(ETCS_EXP) web
	$(foreach dir, $(BUILDABLES), make -C $(dir) DESTDIR=$(realpath $(DESTDIR));)

$(DESTDIR)/usr/local/etc/%:	%
	install -D -m 0755 $< $@

.PHONY: web
web:
	test ! -d $(DESTDIR)/var/www/html/allmon3 && mkdir -p $(DESTDIR)/var/www/html/allmon3
	rsync -av web/* $(DESTDIR)/var/www/html/allmon3/
