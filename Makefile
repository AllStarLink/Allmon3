#
# Build variables
#
RELVER = 1.2.0
DEBVER = 1
PKGNAME = allmon3

BUILDABLES = \
	doc \
	src \
	web

instconf ?= yes

ifeq ($(instconf),yes)
BUILDABLES += conf
endif

ifdef ${DESTDIR}
DESTDIR=${DESTDIR}
endif

ROOT_FILES = LICENSE README.md SECURITY.md
ROOT_INSTALLABLES = $(patsubst %, $(DESTDIR)$(docdir)/%, $(CONF_FILES))

default:
	@echo This does nothing because of dpkg-buildpkg - use 'make install'

install: $(ROOT_INSTALLABLES)
	@echo DESTDIR=$(DESTDIR)
	$(foreach dir, $(BUILDABLES), $(MAKE) -C $(dir) install;)

$(DESTDIR)$(docdir)/%: %
	install -D -m 0644  $< $@

verset:
	perl -pi -e 's/\@\@HEAD-DEVELOP\@\@/$(RELVER)/g' `grep -rl @@HEAD-DEVELOP@@ src/ web/`

deb:	debclean debprep
	debuild

docker-deb:	debclean debprep
	debchange --distribution unstable --package $(PKGNAME) \
		--newversion $(RELVER)-$(DEBVER).$(RELPLAT) "Autobuil of $(RELVER)-$(DEBVER) for $(RELPLAT)"
	dpkg-buildpackage $(DPKG_BUILTOPTS)

debchange:
	debchange -v $(RELVER)-$(DEBVER)
	debchange -r


debprep:	debclean
	-find . -type d -name __pycache__ -exec rm -rf {} \;
	(cd .. && \
		rm -f allmon3-$(RELVER) && \
		rm -f allmon3-$(RELVER).tar.gz && \
		rm -f allmon3_$(RELVER).orig.tar.gz && \
		ln -s Allmon3 allmon3-$(RELVER) && \
		tar --exclude=".git" -h -zvcf allmon3-$(RELVER).tar.gz allmon3-$(RELVER) && \
		ln -s allmon3-$(RELVER).tar.gz allmon3_$(RELVER).orig.tar.gz )

debclean:
	rm -f ../$(PKGNAME)_$(RELVER)*
	rm -f ../$(PKGNAME)-$(RELVER)*
	rm -rf debian/$(PKGNAME)
	rm -f debian/files
	rm -rf debian/.debhelper/
	rm -f debian/debhelper-build-stamp
	rm -f debian/*.substvars
	rm -rf debian/mfamily-scripts/ debian/.debhelper/
	rm -f debian/debhelper-build-stamp debian/files debian/mfamily-scripts.substvars
