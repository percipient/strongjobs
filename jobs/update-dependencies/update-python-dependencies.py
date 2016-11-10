#!/usr/bin/env python

# Note: this will not check to see if packages are up to date on the system,
# but not in the requirements files (which shouldn't happen unless you update
# the packages manually)

import json
import os
from os import environ as env, path
import re
from subprocess import PIPE, Popen

import requests


REQUIREMENTFILES = [
    "requirements.txt",
    "debug-requirements.txt",
    "dev-requirements.txt",
    "requirements-dev.txt",
    "requirements-debug.txt",
    "requirements-base.txt",
]

class RunError(RuntimeError):
    pass


class GitRepo(object):
    def __init__(self, root_path, repo_path):
        self.path = repo_path
        self.directory = path.join(root_path, self.path)

        # Clone the repo if it isn't there.
        if not path.exists(self.directory):
            proc = Popen(['git', 'clone', 'ssh://git@github.com/' + self.path, self.directory], stdout=PIPE, stderr=PIPE)
            proc.wait()
            if proc.returncode is not 0:
                raise RunError(proc.stderr.read())

    def run(self, *args):
        args = ('git', '--git-dir=' + path.join(self.directory, '.git'), '--work-tree=' + self.directory) + args
        proc = Popen(args, cwd=self.directory, stdout=PIPE, stderr=PIPE)
        proc.wait()
        if proc.returncode is not 0:
            raise RunError(proc.stderr.read())

        return proc.stdout.read()

    def update(self):
        self.run('reset', '--hard')
        self.run('checkout', 'master')
        self.run('pull')

        # Clean-up upstream branches.
        self.run('remote', 'prune', 'origin')

        # Delete all local branches (to get a pristine state).
        branches = self.run('branch')
        branches = [branch[2:] for branch in branches.split('\n') if branch and branch[2:] != 'master']
        if branches:
            self.run('branch', '-D', *branches)


def create_pull_request(repo_path, token, title, branch_name):
    """Create a Pull Request."""
    # Reference: https://developer.github.com/v3/pulls/
    r = requests.post(
        "https://api.github.com/repos/" + repo_path + "/pulls",
        data=json.dumps({
            "title": title,
            "body": "auto-generated",
            "head": branch_name,
            "base": "master"
        }),
        headers={
            "Authorization": "token " + token,
            "Accept": "application/vnd.github.v3+json",
            "Content-Type":"application/json"
        }
    )

    if r.status_code != 201:
        raise RuntimeError("Unable to make pull requests for repo '%s', branch '%s'" % (repo_path, branch_name))


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
    for req_file in REQUIREMENTFILES:
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
    for req_file in REQUIREMENTFILES:
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
        updates = {}
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
