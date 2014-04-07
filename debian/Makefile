KEY=CD9C0E84
DIST=saucy
GIT_REV=$(shell git rev-parse --short --verify HEAD)

clean:
	rm -vfR build
	rm -vfR debian/control
	rm -vfR debian/munin2es*

changelog:
	git dch --ignore-branch --snapshot --auto --git-author

release:
	git dch --ignore-branch --release --auto -N $(VERSION) --git-author

bump_version:
	sed -i 's/VERSION = ".*"/VERSION = "$(VERSION)"/;s/BUILD = ".*"/BUILD = "$(GIT_REV)"/' munin2es/version.py
	tail -n3 munin2es/version.py

generate_all: generate_control generate_default_config generate_initd generate_man

generate_control:
	cat debian/control.source debian/control.saucy > debian/control

generate_default_config:
	python -m munin2es.helpers.create-config > debian/munin2es.config

generate_initd:
	cp -v doc/munin2es-initd debian/munin2es.init

generate_man:
	help2man --version-option="--version" --no-discard-stderr -N ./main.py > debian/munin2es.1 && echo "debian/munin2es.1" >> debian/munin2es.manpages
	help2man --version-option="--version" --no-discard-stderr -N ./river.py > debian/munin2es-river.1 && echo "debian/munin2es-river.1" >> debian/munin2es.manpages

package: clean generate_all
	dpkg-buildpackage -A -us -uc

source: clean generate_all
	dpkg-buildpackage -S -k$(KEY)

source_no_sign: clean generate_all
	dpkg-buildpackage -S -us

upload_to_ppa:
	dput ppa:lordgaav/munin2es "$(CHANGES)"

pbuild_create:
	pbuilder-dist "$(DIST)" create
	gunzip ~/pbuilder/$(DIST)-base.tgz
	tar -Af ~/pbuilder/$(DIST)-base.tar debian/lordgaav-ppa-key.tar
	gzip ~/pbuilder/$(DIST)-base.tar
	mv ~/pbuilder/$(DIST)-base.tar.gz ~/pbuilder/$(DIST)-base.tgz

pbuild_update:
	@OTHERMIRROR="deb http://ppa.launchpad.net/lordgaav/python-elasticsearch/ubuntu/ $(DIST) main|deb http://ppa.launchpad.net/lordgaav/python-chaos/ubuntu/ $(DIST) main" \
	pbuilder-dist "$(DIST)" update

pbuild:
	pbuilder-dist "$(DIST)" "$(CHANGES)"
