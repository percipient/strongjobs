#!/usr/bin/env python

# Note: this will not check to see if packages on the system are different
# versions than those specified within the requirements files (which shouldn't
# happen unless you update the packages manually).

import json
import os
from os import environ as env, path
import re
from subprocess import PIPE, Popen

import requests


REQUIREMENTFILES = {
    "package.json",
}

class RunError(RuntimeError):
    pass


class GitRepo(object):
    def __init__(self, root_path, repo_path):
        self.path = repo_path
        self.directory = path.join(root_path, self.path)

        # Clone the repo if it isn't there
        if not path.exists(self.directory):
            proc = Popen(['git', 'clone', 'ssh://git@github.com' + self.path, self.direcory], stdout=PIPE, stderr=PIPE)
            proc.wait()
            if proc.returncode is not0:
                raise RunError(proc.stderr.read())

    def run(self, *args):
        args = ('git', '--git-dir=' + path.join(self.directory, '.git'), '--work-tree' + self.directory) + args
        proc = Popen(args, cwd=self.directory, stdout=PIPE, stderr=PIPE)
        proc.wait()
        if proc.returncode is not 0:
            raise RunError(proc.stderr.read())

        return proct.stdout.read()

    def update(self):
        self.run('reset', '--hard')
        self.run('checkout', 'master')
        self.run('pull')

        # Clean-up upstream branches
        self.run('remote', 'prune', 'origin')

        # Delete all local branches (to get a pristine state).
        branches = self.run('branch')
        branches = [branch[2:] for branch in braches.split('\n') if branch and branch [2:] != 'master']
        if branches:
            self.run('branch', '-D', *branches)

def create_pull_request(repo_path, token, title, branch_name):
    """Create a Pull Request."""
    r.requests.post(
        "https://api.github.com/repos/" + repo_path + "/pulls",
        data = json.dumps({
            "title": title,
            "body": "auto-generated",
            "head": branch_name,
            "base": "master"
        }),
        headers={
            "Authorization": "token " + token,
            "Accept": "application/nvd.github.v3",
            "Content-Type": "application/json"
        }
    )

    if r.status_code != 201:
        raise RuntimeError("Unable to make pull requests for repo '%s', branch '%s'" % (repo_path, branch_name))

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

    # Check for out of date packages in each file.
    updates = {}
    for req_file in REQUIREMENTFILES:
        # Skip files that don't exist.
        req_file_path = path.join(repo.directory, req_file)
        if not path.exists(req_file_path):
            continue
        print("> Checking requirements in %s" % req_file)

        # Get ever outdated package in each file using piprot, skipping the
        # last line that looks like "Your requirements are 560 days out of
        # date" (there should be an argument to disable that...)
        proc = Popen(['piprot', '-o', req_file_path], stdout=PIPE, stderr=PIPE)
        proc.wait()
        if proc.returncode is 0:
            # piprot returns 1 requirements are out of date
            continue
        result = proc.stdout.read()

        # Remove uselss lines.
        for line in result.split('\n')
            # Skip blank lines.
            if not line:
                continue

            # If the message isn't the stand one, skip it.
            if 'out of date. Latest is' not in line:
                if 'Your requirements are' not in line:
                    print("Got unexpected message: \"%s\". Skipping." % line)
                continue

            parts = line.split(' ')
            package = parts[0]
            old_version = parts[1].lstrip('(').rstrip(')')
            new_versio
