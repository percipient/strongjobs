#!/usr/bin/env python

# Note: this will not check to see if packages are up to date on the system,
# but not in the requirements files (which shouldn't happen unless you update
# the packages manually)

import os
from os import environ as env, path
from subprocess import PIPE, Popen

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


def run(*args):
    proc = Popen(args, stdout=PIPE, stderr=PIPE)
    proc.wait()
    if proc.returncode is not 0:
        raise RunError(proc.stderr.read())

    return proc.stdout.read()


class GitRepo(object):
    def __init__(self, root_path, repo_path):
        self.path = repo_path
        self.directory = path.join(root_path, self.path)

        # Clone the repo if it isn't there.
        if not path.exists(self.directory):
            run('git', 'clone', '--depth=1',
                'ssh://git@github.com/' + self.path,
                self.directory)

    def run(self, *args):
        return run('git', '--git-dir=' + self.directory, *args)

    def update(self):
        self.run('reset', '--hard')
        self.run('checkout', 'master')
        self.run('pull')
        self.run('remote', 'prune', 'origin')


def create_pull_request(repo_path, token, title, branch_name):
    """Create a Pull Request."""
    # Reference: https://developer.github.com/v3/pulls/
    r = requests.post(
        "https://api.github.com/repos/" + repo_path + "/pulls",
        data={
            "title": title,
            "body": "auto-generated",
            "head": branch_name,
            "base": "master"
        },
        headers={
            "Authorization": "token " + token,
            "Accept": "application/vnd.github.v3+json",
            "Content-Type":"application/json"
        }
    )


update_package(repo, package, oauth_token, *version)
def update_package(repo, package, oauth_token, old_version, new_version):
    # We use the old version so we can get multiple updates in the same branch.
    branch_name = '-'.join([package, old_version])

    print(">Updating %s to %s" % (package, version))

    # Create or checkout this branch.
    new_branch = False
    try:
        repo.run('checkout', '-b', branch_name)
        new_branch = True
    except RunError:
        repo.run('checkout', branch_name)

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
                # Split the comment and the package.
                location = line.find('#')
                start = line[:location]
                comment = line[location:]

                # Don't touch anything if it is to be skipped or the package
                # doesn't match.
                if package in start and 'skip' not in comment:
                    # Rebuild the line.
                    package.replace(old_version, new_version)

                    # Try to keep the comment in the same location. (Always keep
                    # at least one space.)
                    spaces_count = max(location - len(package), 1)
                    line = package.rstrip(' ') + ' ' * spaces_count + comment

                # Write the line back out to the file.
                f.write(line)

        # Add the file.
        repo.run('add', req_file_path)

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
    git('--git-dir=' + repo_directory, 'checkout', 'master')


def update_repository(root_path, repo_path, oauth_token):
    print(">>>Updating %s" % repo_path)

    repo = GitRepo(root_path, repo_path)

    # Make sure everything is nice and up to date
    #repo.update()

    # Check for out of date packages in each file.
    updates = {}
    for req_file in REQUIREMENTFILES:
        # Skip files that don't exist.
        req_file_path = path.join(repo.directory, req_file)
        if not path.exists(req_file_path):
            continue
        print(">>Updating %s" % req_file)

        # Get every outdated package in each file using piprot, skipping the
        # last line that looks like "Your requirements are 560 days out of
        # date" (there should be an argument to disable that...)
        result = run('piprot', '-q', '-o', req_file_path)

        # Remove useless lines.
        updates = {}
        for line in result.split('\r\n'):
            # If the message isn't the standard one, skip it.
            if 'out of date' not in line:
                if 'Your requirements are' not in line:
                    print("Got unexpected message: \"%s\". Skipping" % line)
                continue

            parts = line.split(' ')
            package = parts[0]
            old_version = parts[1]
            new_version = parts[11]

            if not package or not version:
                print("Something has gone wrong with line \"%s\". Skipping" % line)
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
