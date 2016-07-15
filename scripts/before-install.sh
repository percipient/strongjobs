#!/bin/sh

# Install dependencies
apt-get -y install git curl python python-pip

# Create user and home dir (/home/strongjobs/)
useradd -m strongjobs || true

# I don't know a way to get just the region, so take the availability zone up
# until the end of the numbers, leaving off the zone letter at the end.
# Example: us-west-2c --> us-west-2
readonly REGION=$(ec2metadata --availability-zone | grep -o '^.*[0-9]\+')
# Sync the environment variables (creds and configurations) down
aws --region=$REGION s3 cp s3://strongjobs/conf.env /opt/strongjobs/.env

# Set up the ssh key for github
. /opt/strongjobs/.env  # Needs to be done after aws s3 sync
mkdir /home/strongjobs/.ssh
chmod 0700 /home/strongjobs/.ssh
echo "$SSHPRIVKEY" > /home/strongjobs/.ssh/id_rsa
chmod 0400 /home/strongjobs/.ssh/id_rsa

# Skip host authentication for github
echo 'github.com,192.30.252.130 ssh-rsa AAAAB3NzaC1yc2EAAAABIwAAAQEAq2A7hRGmdnm9tUDbO9IDSwBK6TbQa+PXYPCPy6rbTrTtw7PHkccKrpp0yVhp5HdEIcKr6pLlVDBfOLX9QUsyCOV0wzfjIJNlGEYsdlLJizHhbn2mUjvSAHQqZETYP81eFzLQNnPHt4EVVUh7VfDESU84KezmD5QlWpXLmvU31/yMf+Se8xhHTvKSCZIFImWwoG6mbUoWf9nzpIoaSjB+weqqUUmpaaasXVal72J+UX2B+2RPW3RcT0eOzQgqlJL3RKrTJvdsjE3JEAvGq3lGHSZXy28G3skua2SmVi/w4yCE6gbODqnTWlg7+wC604ydGXA8VJiS5ap43JXiUFFAaQ==' >> /etc/ssh/ssh_known_hosts
