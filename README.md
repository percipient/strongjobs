## About
This repo is Strongarm's solution to a running a modern and easily updatable
task-scheduler on AWS. At its core is a micro ec2 instance running cron.
## One-time setup
1. Run `cfn-strongjobs.py` and save the output as a JSON file.
2. Upload the json file to CloudFormation (console or CLI).
3. Specify parameters. The defaults should work well, and subnet doesn't
   matter.
4. Configure `conf.env` (see `sample.env`).
5. Link your GitHub account to CodeDeploy
   (http://docs.aws.amazon.com/codedeploy/latest/userguide/github-integ.html).

## Regular deployment
Use the included `deploy.sh` script (warning: might not do exactly what you
want), or:

1. Upload `conf.env` to `s3://strongjobs/strongjobs.env`.
2. Create deployment through CodeDeploy (console or CLI).

##Code layout
```
.
├── README.md -- You're reading this
├── appspec.yml -- Specification for CodeDeploy
├── <cfn-strongjobs.json> -- Specification for CloudFormation. Create from
│                         output of cfn-strongjobs.py.
├── cfn-strongjobs.py -- Script to output CloudFormation template using the
│                     Troposphere library
├── <conf.env> -- Create from template in sample.env
├── crontab -- crontab to run tasks
├── deploy.sh -- Janky script to deploy a new commit using CodeDeploy
├── requirements.txt -- Python requirements file
├── sample.env -- Sample environment file designed to be sourced by a shell
├── scripts/ -- Where CodeDeploy scripts live
│   ├── after-install.sh -- Runs after this repo is copied down
│   ├── application-start.sh -- Runs after the rest of the setup
│   ├── application-stop.sh -- Runs when new CodeDeploy is started to stop the
│   │                       old application
│   └── before-install.sh -- Runs before this repo is copied down
└── tasks/ -- Where your tasks will live
    ├── sslcheck/
    │   ├── README.md -- Info
    │   └── ssllabs.sh -- Check your websites' grades on SSL Labs to make sure
    │                  they're still considered secure.
    └── update-dependencies/ -- Tasks to check and update code dependencies
        ├── README.md -- Info
        └── update-python-dependencies.sh -- Create pull requests for outdated 
                                          Python dependencies across all your
                                          repos.
```
