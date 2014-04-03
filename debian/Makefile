KEY=CD9C0E84
DIST=saucy

clean:
	rm -vfR build
	rm -vfR debian/control
	rm -vfR debian/munin2es*

changelog:
	git dch --ignore-branch --snapshot --auto --git-author

release:
	git dch --ignore-branch --release --auto -N $(VERSION) --git-author

package: clean generate_control generate_man
	dpkg-buildpackage -A -us -uc

generate_control:
	cat debian/control.source debian/control.precise > debian/control

generate_default_config:
	python -m munin2es.helpers.create-config > debian/munin2es.config

generate_man:
	help2man --version-option="--version" --no-discard-stderr -N ./main.py > debian/munin2es.1 && echo "debian/munin2es.1" >> debian/munin2es.manpages
	help2man --version-option="--version" --no-discard-stderr -N ./river.py > debian/munin2es-river.1 && echo "debian/munin2es-river.1" >> debian/munin2es.manpages

source: clean generate_control generate_man
	dpkg-buildpackage -S -k$(KEY)

source_no_sign: clean generate_control
	dpkg-buildpackage -S -us

upload_to_ppa:
	dput ppa:lordgaav/munin2es "$(CHANGES)"

pbuild:
	pbuilder-dist "$(DIST)" "$(CHANGES)"
