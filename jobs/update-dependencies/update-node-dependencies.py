#!/usr/bin/env python

import json
import os
from os import environ as env, path
import re
from subprocess import PIPE, Popen

from git import GitRepo
from github import create_pull_request


PACKAGE_FILE = "package.json"


def update_package(repo, oauth_token):

    # Create or checkout this branch.
    new_branch = False
    try:
        # Attempt to get a remote branch with this name.
        repo.run('checkout', '-b', branch_name,  'origin/' + branch_name)
    except RunError:
        # Otherwise, create a new branch.
        new_branch = True
        repo.run('checkout', '-b', branch_name, 'origin/master')

    # Parses package version information
    results = subprocess.check_output("npm outdated", shell=True)
    packages = results.split('\n')[1:]

    # JSON file
    updated_package_json = json.load(open('package.json', 'r'))
    orig_package_json = json.load(open('package.json', 'r'))


    for package in packages:
        # create list in the following format
        # [pckg name, current version, wanted version, latest version, location]
        # we don't need the location data
        package = package.split()

        if not package:
            continue

        # If wanted version is not the latest version, update package.json
        if package[2] != package[3]:
            print('Updating %s to version %s' % (package[0], package[3]))
            updated_package_json['devDependencies'][package[0]] = package[3]

    # If there were any updates, rewrite 'package.json'
    if not orig_package_json == updated_package_json:
        json.dump(updated_package_json, open('package.json', 'w'))

        repo.run('add', req_file_path)

    result = repo.run('status', '--porcelain')
    if not result:
        # Note that this will leave a branch with no changes on it
        return

    # Commit the changes.
    repo.run('commit', '-m', 'Update %s to version %s' % (package[0], package[3]))

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

    # Get every outdated package using npm.
    # TODO Has to be run
    proc = Popen(['npm', 'outdated'], stdout=PIPE, stderr=PIPE)
    proc.wait()
    if proc.returncode is 0:
        # npm outdated returns 1 if requirements are out of date.
        return
    result = proc.stdout.read()

    # The first line is the column titles.
    for line in result.split('\n')[1:]:
        package, current_version, wanted_version, latest_version = line.split()

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
