prefix ?= /usr
data_dir ?= $(prefix)/share
WEBROOT ?= $(DESTDIR)$(data_dir)/allmon3
CSS_DIR = css
IMG_DIR = img
JS_DIR = js

ROOT_FILES = index.html

CSS_FILES = $(wildcard $(CSS_DIR)/*.css)
IMG_FILES = $(wildcard $(IMG_DIR)/*.png)
FAV_FILES = $(wildcard $(IMG_DIR)/favicons/*)
JS_FILES = $(wildcard $(JS_DIR)/*.js)

CSS_INSTALLABLES = $(patsubst $(CSS_DIR)/%, $(WEBROOT)/$(CSS_DIR)/%, $(CSS_FILES))
IMG_INSTALLABLES = $(patsubst $(IMG_DIR)/%, $(WEBROOT)/$(IMG_DIR)/%, $(IMG_FILES))
FAV_INSTALLABLES = $(patsubst $(IMG_DIR)/favicons/%, $(WEBROOT)/$(IMG_DIR)/favicons/%, $(FAV_FILES))
JS_INSTALLABLES = $(patsubst $(JS_DIR)/%, $(WEBROOT)/$(JS_DIR)/%, $(JS_FILES))

ROOT_INSTALLABLES = $(patsubst %, $(WEBROOT)/%, $(ROOT_FILES))

INSTALLABLES = $(CSS_INSTALLABLES) $(IMG_INSTALLABLES) \
	$(FAV_INSTALLABLES) $(JS_INSTALLABLES) $(ROOT_INSTALLABLES)

.PHONY:	install
install:	$(INSTALLABLES)

$(WEBROOT)/css/%: $(CSS_DIR)/%
	install -D -m 0644  $< $@

$(WEBROOT)/img/%: $(IMG_DIR)/%
	install -D -m 0644  $< $@

$(WEBROOT)/img/favicons/%: $(IMG_DIR)/favicons/%
	install -D -m 0644  $< $@

$(WEBROOT)/JS/%: $(JS_DIR)/%
	install -D -m 0644  $< $@

$(WEBROOT)/%:	%
	install -D -m 0644  $< $@
