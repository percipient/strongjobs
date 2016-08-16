## About
This repo is Strongarm's solution to a running a modern and easily updatable
job-scheduler on AWS. At its core is a micro ec2 instance running cron.
Management on the host can use [invoke](http://www.pyinvoke.org/). Invoke
tasks are specified in `[]`

## One-time setup
1. Run `CloudFormation.py`, which will write to `CloudFormation.json`.
   `[cf.make]`
2. Upload the json file to CloudFormation, specifying parameters. The defaults
   should be ok, and subnet doesn't matter. `[cf.create]`
3. Configure `conf.env` (see [sample.env](sample.env)).
4. Link your GitHub account to CodeDeploy (see
   [AWS docs](
http://docs.aws.amazon.com/codedeploy/latest/userguide/github-integ.html)).

## Regular deployment
1. Upload `conf.env` to `s3://strongjobs/strongjobs.env`. `[s3.push]` or
   `[s3.edit]`
2. Create deployment through CodeDeploy (make sure you've pushed). `[install]`

## Adding a new job
1. Add your jobs to a directory in [jobs/](jobs/).
2. Add job to [crontab](crontab).
  - Specify how often it should run.
  - Specify when it should create slack alerts.

Depending on your requirements, you might need to:
- Add secrets or configuration to `conf.env` (and add examples to
  [sample.env](sample.env)).
- Add Python dependencies to [requirements.txt](requirements.txt).
- Add system-level dependencies (e.g. Ubuntu packages) to
  [scripts/before-install.sh](scripts/before-install.sh).
- Add documentation in your job directory and below in the directory layout.

Of course, you'll need to push this and do a CodeDeploy `[install]` before it
starts running.

## Disabling a job
The easiest way is to comment it out in the [crontab](crontab). To remove all
traces, follow the instructions for adding a new job, doing the opposite.
Again, you'll have to push and CodeDeploy `[install]` before the job will stop.

## Directory layout
```
.
├── <CloudFormation.json> -- Specification for CloudFormation. Create from
│                         output of CloudFormation.py
├── CloudFormation.py -- Script to output CloudFormation template using the
│                     Troposphere library, run locally
├── README.md -- You're reading this
├── appspec.yml -- Specification for CodeDeploy
├── <conf.env> -- Create from template in sample.env
├── crontab -- crontab to run jobs
├── dev-requirements.txt -- Python requirements file for the host machine
├── jobs/ -- Where your remote jobs will live
│   ├── sslcheck/ -- Jobs to perform checks on TLS certificates and configs and
│   │   │         create Github issues when they fail
│   │   ├── README.md -- Info
│   │   ├── certexpiry.py -- Check certs for nearing expiration
│   │   ├── httpobs.py -- Check for score falling on Mozilla Observatory
│   │   ├── ssllabs.py -- Check for grade falling on SSL Labs
│   │   └── utils.py -- Helper Python functions
│   └── update-dependencies/ -- Jobs to check and update code dependencies
│       ├── README.md -- Info
│       └── update-python-dependencies.sh -- Create pull requests for outdated 
│                                         Python dependencies across all your
│                                         repos.
├── requirements.txt -- Python requirements file for the ec2 instance
├── sample.env -- Sample environment file designed to be sourced by a shell
├── scripts/ -- Where CodeDeploy scripts live
│   ├── after-install.sh -- Runs after this repo is copied down
│   ├── application-start.sh -- Runs after the rest of the setup
│   ├── application-stop.sh -- Runs when new CodeDeploy is started to stop the
│   │                       old application
│   └── before-install.sh -- Runs before this repo is copied down
├── slackwrapper.sh -- Creates Slack notifications when running jobs
└── tasks.py -- Management tasks file for invoke, run locally
```
