#!/usr/bin/env python
"""
Check a set of requirements files to see if the packages are outdated. If an
outdated package is found, update it in all requirements files and create a Pull
Request to the GitHub repository.

Internally this uses piprot to decide if a requirement is out of date. It
(oddly) iterates all requirements files multiple times:

1. The first finds all outdated dependencies (across all files).
2. Each outdated dependency is then iterated over and updated in all files at once.
3. A separate Pull Request is made for each depency and the branch is named on
  the current version, thus if the package is updated multiple times before the
  branch is merged, additional commits will be added to the same branch.

Some notes:

* Delete your branches after merging pull requests.
* Care is taken to perserve spacing and comments on the same line as dependencies.
* "skip" can be added to a line to ignore dependency checking.

"""

import json
import os
from os import environ as env, path
import re
from subprocess import PIPE, Popen

from git import GitRepo
from github import create_pull_request


REQUIREMENTS_FILES = [
    "requirements.txt",
    "debug-requirements.txt",
    "dev-requirements.txt",
    "requirements-dev.txt",
    "requirements-debug.txt",
    "requirements-base.txt",
]


def update_package(repo, package, oauth_token, old_version, new_version):
    # We use the old version so we can get multiple updates in the same branch.
    branch_name = '-'.join([package, old_version])

    print(">> Updating %s from %s to %s" % (package, old_version, new_version))

    # Create or checkout this branch.
    new_branch = False
    try:
        # Attempt to get a remote branch with this name.
        repo.run('checkout', '-b', branch_name,  'origin/' + branch_name)
    except RunError:
        # Otherwise, create a new branch.
        new_branch = True
        repo.run('checkout', '-b', branch_name, 'origin/master')

    # Rewrite each requirements file with the upgrade done.
    for req_file in REQUIREMENTS_FILES:
        # Skip files that don't exist.
        req_file_path = path.join(repo.directory, req_file)
        if not path.exists(req_file_path):
            continue

        # First read it all into memory.
        with open(req_file_path, 'r') as f:
            requirements = f.readlines()

        # Now re-open the file and change any lines that have this on it.
        with open(req_file_path, 'w') as f:
            for line in requirements:
                # Split the line into a few parts.
                start, end = re.match(r'^(.*)([\r\n]+)$', line).groups()
                parts = start.split('#', 1)
                start = parts[0]
                if len(parts) == 2:
                    comment = parts[1]
                else:
                    comment = None

                # Split the line into package and version. See PEP 508 for the list of version comparisons.
                try:
                    temp_package, cmp, version = re.split(r'([<>]=?|[!=~]=|===)', start)
                except ValueError:
                    # A bare package without a version.
                    temp_package = ''

                # Don't touch anything if it is to be skipped or the package
                # doesn't match.
                if temp_package.lower() == package.lower() and (comment is None or 'skip' not in comment):
                    # Rebuild the line.
                    line = start.replace(version, new_version)

                    if comment is not None:
                        # Try to keep the comment in the same location. (Always keep
                        # at least one space.)
                        line = line.rstrip(' ')
                        spaces_count = max(len(start) - len(line), 1)
                        line += ' ' * spaces_count + '#' + comment

                    # Add back the line ending.
                    line += end

                # Write the line back out to the file.
                f.write(line)

        # Add the file.
        repo.run('add', req_file_path)

    # Check if anything has changed.
    result = repo.run('status', '--porcelain')
    if not result:
        # Note that this will leave a branch with no changes on it.
        return

    # Commit the changes.
    repo.run('commit', '-m', 'Update %s to %s.' % (package, new_version))

    # Pushing can succeed or fail depending on whether or not an identically
    # named branch exists. This is all of the duplicate-checking done; it will
    # create a pull request exactly once per package version per requirements
    # file, but it will continue creating pull requests for new versions,
    # regardless of the status of the previous pull requests. To stop creating
    # new pull requests, add "skip" to a comment in the requirements file on
    # the same line as the package.
    repo.run('push', 'origin', branch_name)

    if new_branch:
        # Reference: https://developer.github.com/v3/pulls/
        create_pull_request(repo.path, oauth_token,
                            "Update " + package + " to " + new_version,
                            branch_name)

    # Clean up.
    repo.run('checkout', 'master')


def update_repository(root_path, repo_path, oauth_token):
    print("Updating requirements for %s" % repo_path)

    repo = GitRepo(root_path, repo_path)

    # Make sure everything is nice and up to date
    repo.update()

    # Check for out of date packages in each file.
    updates = {}
    for req_file in REQUIREMENTS_FILES:
        # Skip files that don't exist.
        req_file_path = path.join(repo.directory, req_file)
        if not path.exists(req_file_path):
            continue
        print("> Checking requirements in %s" % req_file)

        # Get every outdated package in each file using piprot, skipping the
        # last line that looks like "Your requirements are 560 days out of
        # date" (there should be an argument to disable that...)
        proc = Popen(['piprot', '-o', req_file_path], stdout=PIPE, stderr=PIPE)
        proc.wait()
        if proc.returncode is 0:
            # piprot returns 1 if requirements are out of date.
            continue
        result = proc.stdout.read()

        # Remove useless lines.
        for line in result.split('\n'):
            # Skip blank lines.
            if not line:
                continue

            # If the message isn't the standard one, skip it.
            if 'out of date. Latest is' not in line:
                if 'Your requirements are' not in line:
                    print("Got unexpected message: \"%s\". Skipping." % line)
                continue

            parts = line.split(' ')
            package = parts[0]
            old_version = parts[1].lstrip('(').rstrip(')')
            new_version = parts[-1]

            if not package or not old_version or not new_version:
                print("Something has gone wrong with line \"%s\". Skipping." % line)
                continue

            updates[package] = (old_version, new_version)

    # Now update each package.
    for package, version in updates.items():
        update_package(repo, package, oauth_token, *version)


def main():
    # Check for environment variables
    if "REPOS" not in env:
        print("No repos. Export REPOS")
        return 1
    if "OAUTHTOKEN" not in env:
        print("No Oauth token. Export OAUTHTOKEN")
        return 1

    # Get into the right directory or set it up if it doesn't exist.
    root_path = path.expanduser(path.join('~', 'strongjobs-data'))
    if not path.exists(root_path):
        os.makedirs(root_path)

    for repo_path in env["REPOS"].split():
        update_repository(root_path, repo_path, env["OAUTHTOKEN"])


if __name__ == '__main__':
    main()
