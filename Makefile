export VERSION=$(shell cat doq/version)

.PHONY: tag
tag:
	git tag v${VERSION}
