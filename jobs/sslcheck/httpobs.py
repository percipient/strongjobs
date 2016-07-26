#!/usr/bin/env python

from os import environ as env
from time import sleep

import requests

from utils import createIssue

API_URL = "https://http-observatory.security.mozilla.org/api/v1"


def getScore(host):
    res = requests.post(API_URL + '/analyze?host={host}'.format(host=host),
                        data={"hidden": "true"}).json()
    while res["state"] != "FINISHED":
        print("Status: " + res["state"])
        sleep(10)
        res = requests.post(API_URL + '/analyze?host={host}'.format(host=host),
                            data={"hidden": "true"}).json()
    print res
    return int(res["score"])


def check(s):
    hostName, desiredScore = s.split(';')
    desiredScore = int(desiredScore)
    print("Starting Mozilla Observatory scan for " + hostName)
    score = getScore(hostName)
    if score < desiredScore:
        print("Mozilla Observatory scan failed for {}. "
              "Score is now {}, not {}.".format(hostName, score, desiredScore))
        createIssue(env["ISSUEREPOPATH"],
                    env["OAUTHTOKEN"],
                    "Mozilla Observatory score fell for " + hostName,
                    "Score is now {}, not {}.".format(score, desiredScore))
    else:
        print("Mozilla Observatory scan passed for " + hostName)


def main():
    # Check for environment variables
    if "ISSUEREPOPATH" not in env:
        print("Export GitHub repo to create issues in as ISSUEREPOPATH")
        return 1
    if "OAUTHTOKEN" not in env:
        print("Export GitHub OAuth token as OAUTHTOKEN")
        return 1
    if "HTTPOBSLIST" not in env:
        print("Export hostnames and scores to check with Mozilla Observatory "
              "as HTTPOBSLIST")
        return 1

    for hostName in env["HTTPOBSLIST"].split():
        check(hostName)


if __name__ == "__main__":
    raise SystemExit(main())
