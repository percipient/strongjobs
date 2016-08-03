#!/bin/sh

# Fix up file owners
chown -R strongjobs:strongjobs /home/strongjobs/
chown -R strongjobs:strongjobs /opt/strongjobs/

# Install python dependencies
pip install -r /opt/strongjobs/requirements.txt
