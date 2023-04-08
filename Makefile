BUILDABLES = \
	asl-statmon \
	asl-cmdlink \
	conf \
	doc \
	web

install:
	$(foreach dir, $(BUILDABLES), $(MAKE) -C $(dir);)
