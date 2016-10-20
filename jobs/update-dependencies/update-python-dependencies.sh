#!/bin/sh

# Note: this will not check to see if packages are up to date on the system,
# but not in the requirements files (which shouldn't happen unless you update
# the packages manually)

set -euf

readonly REQUIREMENTFILES="requirements.txt requirements-debug.txt requirements-dev.txt requirements-base.txt"

updatePackage() {
	repoPath=$1
	package=$2
	version=$3
	reqFile=$4
	branchname="$package-$version-$reqFile"
	echo ">Updating $package to $version in $reqFile"

	# Get onto clean new branch
	git branch -D "$branchname" 2> /dev/null || true
	git checkout -b "$branchname" 2> /dev/null
	# Make the upgrade in the file, pinning the package to the new version,
	# leaving whitespace (spaces and tabs) and comments alone
	sed -i.bak -e "s/^$package==[^ #	]*/$package==$version/" "$reqFile"
	# Add, commit, and (try to) push the change
	git add "$reqFile"
	git commit -m "Update $package to $version in $reqFile" > /dev/null 2>&1
	# Pushing can succeed or fail depending on whether or not an identically
	# named branch exists. This is all of the duplicate-checking done; it will
	# create a pull request exactly once per package version per requirements
	# file, but it will continue creating pull requests for new versions,
	# regardless of the status of the previous pull requests. To stop creating
	# new pull requests, add "skip" to a comment in the requirements file on
	# the same line as the package.
	if git push origin "$branchname" > /dev/null 2>&1; then
		# If the push succeeds, submit a pull request
		echo "Pushed branch successfully"
		# Reference: https://developer.github.com/v3/pulls/
		curl "https://api.github.com/repos/$repoPath/pulls" \
				-s \
				-H "Authorization: token $OAUTHTOKEN" \
				-H "Accept: application/vnd.github.v3+json" \
				-H 'Content-Type: application/json' \
				-d "{\"title\": \"Update $package to $version in $reqFile\", \"body\": \"auto-generated\", \"head\": \"$branchname\", \"base\": \"master\"}" \
				> /dev/null
	else
		# If the push fails, it's probably because the branch already exists,
		# and we keep going. It is possible for the branch to exist but a pull
		# request to not exist, but this script isn't going to deal with that.
		echo "Branch already pushed"
	fi
	# Clean up
	git checkout master > /dev/null 2>&1
	git branch -D "$branchname" > /dev/null 2>&1
}

updateRepo() {
	repoPath=$1
	echo ">>>Updating $repoPath"

	# Get into the right directory or set it up if it doesn't exist
	if [ ! -d "$HOME/$repoPath" ];
	then
		mkdir -p "$HOME/$repoPath"
		cd "$HOME/$repoPath" 
		git clone --depth=1 "ssh://git@github.com/$repoPath" . 2> /dev/null
	fi
	cd "$HOME/$repoPath"

	# Make sure everything is nice and up to date
	git reset --hard
	git checkout master > /dev/null 2>&1
	git pull > /dev/null 2>&1

	# Update each file in turn
	for reqFile in $REQUIREMENTFILES;
	do
		# Skip files that don't exist
		test -f "$reqFile" || continue
		echo ">>Updating $reqFile"

		# Get every outdated package in each file using piprot, skipping the
		# last line that looks like "Your requirements are 560 days out of
		# date" (there should be an argument to disable that...)
		outdated="$(piprot -o - < "$reqFile" | sed -e '/Your requirements are.*out of date/d')"
		# The file needs to be read in first, since we edit the file inside
		# the loop
		echo "$outdated" | while read -r pipLine;
		do
			# If if the message isn't the standard one, skip it
			if ! echo "$pipLine" | grep 'out of date' > /dev/null;
			then
				echo "Got unexpected message: \"$pipLine\". Skipping"
				continue
			fi
			package=$(echo "$pipLine" | cut -d ' ' -f 1)
			version=$(echo "$pipLine" | cut -d ' ' -f 11)
			if [ -z "$version" ] || [ -z "$package" ];
			then
				echo "Something has gone wrong with line \"$pipLine\". Skipping"
				continue
			fi
			# Skip lines marked with a comment containing "skip"
			# Otherwise, update the package in the current file
			if grep "^$package==.*#.*skip" "$reqFile" > /dev/null;
			then
				echo ">Skipping $package"
			else
				updatePackage "$repoPath" "$package" "$version" "$reqFile"
			fi
		done
		echo
	done
}

main() {
	. /opt/strongjobs/.env
	if [ "${REPOS:-"x"}" = x ]; then
		echo "No repos. Export REPOS"
		exit 1
	fi
	if [ "${OAUTHTOKEN:-"x"}" = x ]; then
		echo "No Oauth token. Export OAUTHTOKEN"
		exit 1
	fi

	for repoPath in $REPOS;
	do
		updateRepo "$repoPath"
	done
}

main
