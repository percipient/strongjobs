#!/bin/sh

set -euf

# Caution: janky shell script

# You will need to customize this with your aws-keychain setup
AWSCOMMAND="aws-keychain exec strongarm-1 aws --region us-west-2"
REPO="percipient/strongjobs"

if ! jq -h > /dev/null 2>&1;
then
	echo "Requires jq for JSON parsing"
	exit 1
fi
if [ "${1:-"x"}" = x ]; then
	echo 'No revision specified. Pass "newest" to use the latest revision on the current branch'
	exit 1
fi
if [ "$1x" = newestx ]; then
	revision=$(git rev-list --max-count=1 HEAD)
else
	revision=$1
fi

$AWSCOMMAND s3 cp conf.env s3://strongjobs/strongjobs.env
deploymentId=$($AWSCOMMAND deploy create-deployment --application-name strongjobs-Strongjobs --deployment-group-name strongjobs --github-location repository=$REPO,commitId=$revision | jq -r .deploymentId)
while :;
do
	res=$($AWSCOMMAND deploy get-deployment --deployment-id $deploymentId)
	echo $res
	status=$(echo "$res" | jq -r .deploymentInfo.status)
	echo status: $status
	if [ "$status" != Created ] && [ "$status" != InProgress ];
	then
		exit 0
	fi
	sleep 3
done
