#!/usr/bin/env python

import requests


def createIssue(repoPath, token, title, body):
    """Create GitHub issue if one with the same title doesn't exist."""
    # Check for already existing issue
    # Reference: https://developer.github.com/v3/search/#search-issues
    r = requests.get("https://api.github.com/search/issues",
                     params={'q': "repo:" + repoPath + " "
                                  "in:title "
                                  "is:open "
                                  "type:issue " +
                                  title},
                     headers={"Authorization": "token " + token,
                              "Accept": "application/vnd.github.v3+json",
                              })
    # Create new issue if not duplicate
    if r.json()["total_count"] == 0:
        # Reference: https://developer.github.com/v3/issues/#create-an-issue
        requests.post("https://api.github.com/repos/" + repoPath + "/issues",
                      headers={"Authorization": "token " + token,
                               "Accept": "application/vnd.github.v3+json",
                               "Content-Type": "application/json"},
                      json={"title": title, "body": body})
