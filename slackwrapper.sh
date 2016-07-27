#!/bin/sh

set -euf

usage() {
	cat <<- EOF
	Usage: $0 {all | fail | succeed} <name> <executable>

	Arguments:
	    Condition of when to notify. Choices are:
	        all: notify on every run
	        fail: notify only on failure
	        succeed: notify only on success

	    Name of job to use in the notification. Needs to be quoted for JSON

	    Executable to run. Exit code is used for determining success or failure
	EOF
	exit 1
}

notify() {
	# This function will fail if $name isn't correctly quoted for JSON (e.g.
	# if it has things like "\\" in it), so make sure you're passing in good
	# names.
	name="$1"
	errno="$2"

	# Make payload based on error value and job name
	if [ "$errno" = 0 ];
	then
		data="{\"attachments\": [{\"fallback\": \"Job \\\"$name\\\" succeeded\", \"color\": \"good\", \"title\": \"Job succeeded\", \"text\": \"$name\"}]}"
	else
		data="{\"attachments\": [{\"fallback\": \"Job \\\"$name\\\" failed\", \"color\": \"danger\", \"title\": \"Job failed\", \"text\": \"$name\", \"fields\": [{\"title\": \"Exit code\", \"value\": $errno, \"short\": true}]}]}"
	fi

	# Send notification
	curl -X POST \
		-s \
		-H 'Content-type: application/json' \
		--data "$data" \
		"$SLACKHOOKURL"
}

main() {
	. /opt/strongjobs/.env
	
	# Verify environment and arguments
	if [ "${SLACKHOOKURL:-"x"}" = x ];
	then
		echo "Export SLACKHOOKURL as your Slack API hook URL"
		exit 1
	fi
	if [ "$#" -ne 3 ];
	then
		echo "Wrong number of arguments"
		usage
	fi
	condition="$1"
	name="$2"
	executable="$3"
	if [ ! -x "$executable" ];
	then
		echo "Invalid Executable"
		usage
	fi
	case $condition in
		all | fail | succeed) ;; # Actually process the condition later
		*)
			echo "Invalid condition"
			usage
			;;
	esac

	# Run the job
	set +e
	$executable # Obviously don't run this with untrusted input
	errno=$?
	set -e

	# Notify based on condition
	case $condition in
		all)
			notify "$name" "$errno"
			;;
		fail)
			test "$errno" = 0 || notify "$name" "$errno"
			;;
		succeed)
			test "$errno" = 0 && notify "$name" "$errno"
			;;
	esac
}

main "$@"
