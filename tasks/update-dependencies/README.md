# Dependency checkers
## Python dependency checker
Submits pull requests for outdated python packages pinned in requirements
files.
### Configuration
See `sample.env` for a template of `conf.env`. Specify the repositories (or
just one) as a space separated array of `owner/repo` pairs. You will also need
a personal OAUTH token from Github, and a private SSH key (without a
passphrase) for pushing branches.
### Running
It's recommended to run from the included crontab. Alternatively, run the
script from a POSIX shell. It will clone repositories to the `strongjobs` user
home directory.
