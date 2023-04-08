BUILDABLES = \
	doc \
	src \
	web

instconf ?= yes

ifeq ($(instconf),yes)
BUILDABLES += conf
endif

install:
	$(foreach dir, $(BUILDABLES), $(MAKE) -C $(dir);)
