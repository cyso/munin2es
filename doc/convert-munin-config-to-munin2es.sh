#!/bin/sh -

show_usage() {
	echo "usage: $0 [-h|--help] FILE..."
	echo "Converts munin-server node configuration to munin2es style."
	echo ""
	echo "Converted files are placed in a new folder called \"converted\""
	echo "in the working directory."
	echo "Current working directory: $(pwd)"
	echo ""
}

## Check if we have input filenames
if [ "$#" -eq 0 ]; then 
	show_usage
	echo "No files passed, exiting..."
	exit 1
fi

if [ "$1" = "-h" ] || [ "$1" = "--help" ]; then
	show_usage
	exit 0
fi

echo "Making output dir"
mkdir converted || exit 1

for file; do
	filename=$(basename -s.conf $file)
	echo "Processing $filename"
	cp $file converted/${filename}.config || exit 1
	sed -i -r 's/\s+/ /g;s/^\s*//;s/\s*$//' converted/${filename}.config
	sed -i -r 's/ /=/' converted/${filename}.config
	sed -i -e '/^$/d' converted/${filename}.config
	echo "" >> converted/${filename}.config
done

echo "Done."
