#
# Build variables
#
SRCNAME = Allmon3
PKGNAME = allmon3
RELVER = 1.4.0
DEBVER = 1
PKGNAME = allmon3
RELPLAT ?= deb$(shell lsb_release -rs 2> /dev/null)

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

deb:	debclean debprep verset
	debchange --distribution stable --package $(PKGNAME) \
		--newversion $(EPOCHVER)$(RELVER)-$(DEBVER).$(RELPLAT) \
		"Autobuild of $(EPOCHVER)$(RELVER)-$(DEBVER) for $(RELPLAT)"
	dpkg-buildpackage -b --no-sign
	git checkout debian/changelog

docker-deb:	debclean debprep
	debchange --distribution unstable --package $(PKGNAME) \
		--newversion $(RELVER)-$(DEBVER).$(RELPLAT) \
		"Autobuild of $(RELVER)-$(DEBVER) for $(RELPLAT)"
	dpkg-buildpackage $(DPKG_BUILTOPTS)

debchange:
	debchange -v $(RELVER)-$(DEBVER)
	debchange -r


debprep:	debclean
	-find . -type d -name __pycache__ -exec rm -rf {} \;
	(cd .. && \
		rm -f $(PKGNAME)-$(RELVER) && \
		rm -f $(PKGNAME)-$(RELVER).tar.gz && \
		rm -f $(PKGNAME)_$(RELVER).orig.tar.gz && \
		ln -s $(SRCNAME) $(PKGNAME)-$(RELVER) && \
		tar --exclude=".git" -h -zvcf $(PKGNAME)-$(RELVER).tar.gz $(PKGNAME)-$(RELVER) && \
		ln -s $(PKGNAME)-$(RELVER).tar.gz $(PKGNAME)_$(RELVER).orig.tar.gz )


debclean:
	rm -f ../$(PKGNAME)_$(RELVER)*
	rm -f ../$(PKGNAME)-$(RELVER)*
	rm -rf debian/$(PKGNAME)
	rm -f debian/files
	rm -rf debian/.debhelper/
	rm -f debian/debhelper-build-stamp
	rm -f debian/*.substvars
	rm -rf debian/$(SRCNAME)/ debian/.debhelper/
	rm -f debian/debhelper-build-stamp debian/files debian/$(SRCNAME).substvars
	rm -f debian/*.debhelper

