# SSL checkers
## Certification Expiration
Checks your websites' certs to see if they are nearing expiration. If a cert
is almost expired, then the script will create an issue on a GitHub repository.

### Configuration
See `sample.env` for a template of `conf.env`. Set `CERTEXPIRELIST` to be the
hosts you want to scan. It should be formatted as a space separated list of
domains. Set `ISSUEREPOPATH` to be the repo path of a repo where issues can be
created when grades change. `OAUTHTOKEN` should be a GitHub API token for an
account with permission to create issues.

### Running
Nothing special is needed, but using the crontab is recommended.


## Mozilla Observatory
Checks your websites' scores on
https://mozilla.github.io/http-observatory-website/ to make sure your scores
haven't fallen. If one has changed, this will create an issue on a GitHub
repository.

### Configuration
See `sample.env` for a template of `conf.env`. Set `HTTPOBSLIST` to be the
hosts you want to scan, and their scores. It should be formatted as a space
separated list of semicolon separated domain and grade pairs. Set
`ISSUEREPOPATH` to be the repo path of a repo where issues can be created when
grades change. `OAUTHTOKEN` should be a GitHub API token for an account with
permission to create issues.

### Running
Nothing special is needed, but using the crontab is recommended.


## SSL Labs
Checks your websites' configurations on ssllabs.com to make sure your grades
haven't haven't fallen. If one has changed, this will create an issue on a
GitHub repository.

### Configuration
See `sample.env` for a template of `conf.env`. Set `SSLLABSLIST` to be the
hosts you want to scan, and their grades. It should be formatted as a space
separated list of semicolon separated url and grade pairs. Set `ISSUEREPOPATH`
to be the repo path of a repo where issues can be created when grades change.
`OAUTHTOKEN` should be a GitHub API token for an account with permission to
create issues.

### Running
Nothing special is needed, but using the crontab is recommended.
