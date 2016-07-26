#!/usr/bin/env python

from os import environ as env
from time import sleep

import requests

from utils import createIssue

API_URL = "https://api.ssllabs.com/api/v2/"


def getGrades(host):
    res = requests.get("{api_url}analyze?host={host}&startNew=on".format(
            api_url=API_URL, host=host)).json()
    while res["status"] != "READY":
        print("Status: " + res["status"])
        sleep(10)
        res = requests.get("{api_url}analyze?host={host}&startNew=off".format(
                api_url=API_URL, host=host)).json()
    return [endpoint["grade"] for endpoint in res["endpoints"]]


def check(s):
    hostName, desiredGrade = s.split(';')
    print("Starting SSL Labs scan for " + hostName)
    grades = getGrades(hostName)
    for newGrade in grades:
        if newGrade != desiredGrade:
            print("SSL Labs scan failed for " + hostName)
            createIssue(env["ISSUEREPOPATH"],
                        env["OAUTHTOKEN"],
                        "SSL Labs Grade fell for " + hostName,
                        "Grade is now {}, not {}.".format(newGrade,
                                                          desiredGrade))
            break
    else:
        print("SSL Labs scan passed for " + hostName)


def main():
    # Check for environment variables
    if "ISSUEREPOPATH" not in env:
        print("Export GitHub repo to create issues in as ISSUEREPOPATH")
        return 1
    if "OAUTHTOKEN" not in env:
        print("Export GitHub OAuth token as OAUTHTOKEN")
        return 1
    if "SSLLABSLIST" not in env:
        print("Export hostnames and grades to check with SSL Labs as "
              "SSLLABSLIST")
        return 1

    for hostName in env["SSLLABSLIST"].split():
        check(hostName)


if __name__ == "__main__":
    raise SystemExit(main())
