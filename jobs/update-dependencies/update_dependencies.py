from os import path

from git import GitRepo
from github import create_pull_request


def update_package(repo, files, oauth_token, package, old_version, new_version, updater):
    """
    Update an individual package across all files.
    """
    # We use the old version so we can get multiple updates in the same branch.
    branch_name = '-'.join([package, old_version])

    print(">> Updating %s from %s to %s" % (package, old_version, new_version))

    # Create or checkout this branch.
    new_branch = False
    try:
        # Attempt to get a remote branch with this name.
        repo.run('checkout', '-b', branch_name,  'origin/' + branch_name)
    except GitRepo.RunError:
        # Otherwise, create a new branch.
        new_branch = True
        repo.run('checkout', '-b', branch_name, 'origin/master')

    # Rewrite each requirements file with the upgrade done.
    for req_file in files:
        # Skip files that don't exist.
        req_file_path = path.join(repo.directory, req_file)
        if not path.exists(req_file_path):
            continue

        updater(req_file_path, package, old_version, new_version)

        # Add the file.
        repo.run('add', req_file_path)

    # Check if anything has changed.
    result = repo.run('status', '--porcelain', '--untracked-files=no')
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


def update_packages(repo, oauth_token, files, package_updates, updater):
    # Now update each package.
    for package, (old_version, new_version) in package_updates.items():
        update_package(repo, files, oauth_token, package, old_version, new_version, updater)


def get_package_updates(repo, files, check_for_updates):
    """
    Returns a dict of package name to (old, new).
    """
    print("Updating requirements for %s" % repo.directory)

    # Check for out of date packages in each file.
    package_updates = {}
    for req_file in files:
        # Skip files that don't exist.
        req_file_path = path.join(repo.directory, req_file)
        if not path.exists(req_file_path):
            continue
        print("> Checking requirements in %s" % req_file)

        # A dictionary of updates found for this particular file.
        more_updates = check_for_updates(req_file_path)
        # Update the global list of packages that need to be updated.
        package_updates.update(more_updates)

    return package_updates
