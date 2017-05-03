#!/usr/bin/env python

from copy import deepcopy
from collections import OrderedDict
import json
import os
from os import environ as env, path
from subprocess import PIPE, Popen

from git import GitRepo
from update_dependencies import get_package_updates, update_packages


PACKAGE_FILES = ["package.json"]


def update_package_json(req_file_path, package, old_version, new_version):
    # In order to maintain formatting of the JSON file we want to keep ordering
    # of objects.
    with open(req_file_path, 'r') as f:
        package_json = json.load(f, object_pairs_hook=OrderedDict)

    # Keep a copy.
    original_json = deepcopy(package_json)

    # Update the package we want to change.
    package_json['devDependencies'][package] = new_version

    # Don't rewrite the file if no changes were made.
    if original_json != package_json:
        with open(req_file_path, 'w') as f:
            # Try to keep the same indentation.
            json.dump(package_json, f, indent=2, separators=(',', ': '))
            # End with a trailing blank line.
            f.write('\n')


def npm_outdated(req_file_path):
    # Get every outdated package using npm.
    req_dir = path.dirname(req_file_path)
    proc = Popen(['npm', 'outdated'], stdout=PIPE, stderr=PIPE, cwd=req_dir)
    proc.wait()
    if proc.returncode is 0:
        # npm outdated returns 1 if requirements are out of date.
        return {}
    result = proc.stdout.read()

    # The first line is the column titles, the last is blank.
    package_updates = {}
    for line in result.split('\n')[1:-1]:
        # "Current" version is what's installed, "wanted" is what's in the file.
        # Nowhere does this machine install these dependencies though, so
        # current_version should always be the string "MISSING".
        package, current_version, wanted_version, latest_version = line.split()
        package_updates[package] = (wanted_version, latest_version)

    return package_updates


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
        repo = GitRepo(root_path, repo_path)

        # Make sure everything is nice and up to date
        repo.update()

        package_updates = get_package_updates(repo, PACKAGE_FILES, npm_outdated)
        update_packages(repo, env["OAUTHTOKEN"], PACKAGE_FILES, package_updates, update_package_json)


if __name__ == '__main__':
    main()
