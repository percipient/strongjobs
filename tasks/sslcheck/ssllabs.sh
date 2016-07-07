#!/bin/sh

set -euf

wget https://github.com/ssllabs/ssllabs-scan/releases/download/v1.3.0/ssllabs-scan_1.3.0-linux64.tgz
tar xf ssllabs-scan_1.3.0-linux64.tgz
./ssllabs-scan -grade strongarm.io | grep '"strongarm.io": "A"' \
		|| logger "Failed ssllabs test for strongarm.io" # TODO: send this somewhere else
./ssllabs-scan -grade app.strongarm.io | grep '"app.strongarm.io": "A+"' \
		|| logger "Failed ssllabs test for app.strongarm.io" # TODO: send this somewhere else
