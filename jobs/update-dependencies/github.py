import json

import requests


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
            "Content-Type": "application/json"
        }
    )

    if r.status_code != 201:
        raise RuntimeError("Unable to make pull requests for repo '%s', branch '%s'" % (repo_path, branch_name))
