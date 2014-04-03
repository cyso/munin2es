KEY=CD9C0E84
DIST=saucy

clean:
	rm -vfR build
	rm -vfR debian/control
	rm -vfR debian/munin2es*
	rm -vf doc/munin2es

changelog:
	git dch --ignore-branch --snapshot --auto --git-author

release:
	git dch --ignore-branch --release --auto -N $(VERSION) --git-author

generate_all: generate_control generate_default_config generate_initd generate_man

generate_control:
	cat debian/control.source debian/control.precise > debian/control

generate_default_config:
	python -m munin2es.helpers.create-config > doc/munin2es.config

generate_initd:
	cp -v doc/munin2es-initd doc/munin2es

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

pbuild:
	pbuilder-dist "$(DIST)" "$(CHANGES)"
