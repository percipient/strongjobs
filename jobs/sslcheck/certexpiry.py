#!/usr/bin/env python

from __future__ import absolute_import

from os import environ as env
import socket
import datetime

from OpenSSL import SSL

from utils import createIssue

EXPIREDAYS = 90


def checkHost(hostName):
    """Get cert on host and create issue if nearing expiration."""
    print("Checking " + hostName)
    # Initialize openssl context
    ctx = SSL.Context(SSL.TLSv1_2_METHOD)
    # Connect to server
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sslSock = SSL.Connection(ctx, sock)
    sslSock.connect((hostName, 443))
    # Extract the certificate from openssl
    sslSock.do_handshake()
    cert = sslSock.get_peer_certificate()
    # Clean up
    sslSock.shutdown()
    sock.close()

    daysLeft = int((datetime.datetime.strptime(cert.get_notAfter(),
                                               "%Y%m%d%H%M%SZ") -
                    datetime.datetime.utcnow()).days)
    print("Certificate for %s has %d days until expiring" %
          (hostName, daysLeft))

    # The cert is close to expiration, so we create a GitHub issue
    if daysLeft <= EXPIREDAYS:
        print(hostName + " is close to expiring")
        createIssue(env["ISSUEREPOPATH"],
                    env["OAUTHTOKEN"],
                    "Certificate for " + hostName + " is nearing expiration",
                    "It has %d days until it expires." % daysLeft)

    # The cert is even closer to expiration, so we create a duplicate, more
    # emphatic GitHub issue
    if daysLeft <= EXPIREDAYS * 2 / 3:
        print(hostName + " is very close to expiring")
        createIssue(env["ISSUEREPOPATH"],
                    env["OAUTHTOKEN"],
                    "CERTIFICATE FOR " + hostName + " IS NEARING EXPIRATION!",
                    "It has %d days until it expires." % daysLeft)


def main():
    # Check for environment variables
    if "ISSUEREPOPATH" not in env:
        print("Export GitHub repo to create issues in as ISSUEREPOPATH")
        return 1
    if "OAUTHTOKEN" not in env:
        print("Export GitHub OAuth token as OAUTHTOKEN")
        return 1
    if "CERTEXPIRELIST" not in env:
        print("Export hostnames to check for certificate expiry as "
              "CERTEXPIRELIST")
        return 1

    for hostName in env["CERTEXPIRELIST"].split():
        checkHost(hostName)


if __name__ == "__main__":
    raise SystemExit(main())
