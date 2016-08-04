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
3. Configure `conf.env` (see `sample.env`).
4. Link your GitHub account to CodeDeploy
   (http://docs.aws.amazon.com/codedeploy/latest/userguide/github-integ.html).

## Regular deployment
1. Upload `conf.env` to `s3://strongjobs/strongjobs.env`. `[s3.push]` or
   `[s3.edit]`
2. Create deployment through CodeDeploy (make sure you've pushed). `[install]`

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
