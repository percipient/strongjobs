#!/usr/bin/env python
"""Run management tasks locally."""

from time import sleep

import boto3
from botocore.exceptions import NoRegionError
from invoke import run, task, Collection


# Utility functions
def clientWrapper(service, region=None):
    if region:
        cl = boto3.client(service, region_name=region)
    else:
        try:
            cl = boto3.client(service)
        except NoRegionError:
            print("You need to specify a region in some way. See "
                  "http://docs.aws.amazon.com/cli/latest/userguide/cli-chap-"
                  "getting-started.html for ways that you can set it "
                  "globally, or pass 'region' as an argument to this task.")
            raise SystemExit(1)
    return cl


# Default namespace
@task
def clean(ctx):
    """Remove created files and caches."""
    run("rm -rf CloudFormation.json")
    run("find . \( -name '__pycache__' -o -name '*.pyc' \) -print -delete")


@task(aliases=['code', 'install'])
def codeDeploy(ctx,
               region=None,
               repo="percipient/strongjobs",
               commitId="newest",
               wait=True):
    """Deploy new code at specified revision to instance.

    arguments:
    - repo: GitHub repository path from which to get the code
    - commitId: commit ID to be deployed
    - wait: wait until the CodeDeploy finishes
    """
    codedeploy = clientWrapper("codedeploy", region)
    if commitId == "newest":
        commitId = run("git rev-list --max-count=1 HEAD",
                       hide=True).stdout.strip()
        print("Got newest commitId as " + commitId)

    print("Launching CodeDeploy with commit " + commitId)
    res = codedeploy.create_deployment(applicationName="strongjobs-Strongjobs",
                                       deploymentGroupName="strongjobs",
                                       revision={
                                                "revisionType": "GitHub",
                                                "gitHubLocation": {
                                                        "repository": repo,
                                                        "commitId": commitId,
                                                        }})
    depId = res["deploymentId"]
    print("Deployment ID: " + depId)

    # The deployment is launched at this point, so exit unless asked to wait
    # until it finishes
    if not wait:
        return

    # This should use a boto3 waiter instead, but that hasn't been
    # implemented yet: https://github.com/boto/boto3/issues/708
    # So instead we check the status every few seconds manually
    info = {'status': 'Created'}
    while info['status'] not in ('Succeeded', 'Failed', 'Stopped',):
        info = codedeploy.get_deployment(deploymentId=depId)['deploymentInfo']
        print(info)
        print(info['status'])
        sleep(3)
    if info['status'] == 'Succeeded':
        print("\nDeploy Succeeded")
    else:
        print("\nDeploy Failed")
        print(info)

ns = Collection(clean, codeDeploy)


# cf (CloudFormation) namespace
@task(aliases=['make'], pre=[clean])
def makeTemplate(ctx):
    """Make CloudFormation template."""
    import CloudFormation  # pylint: disable=unused-import


@task(pre=[makeTemplate])
def create(ctx,
           region=None,
           subnetId=None,
           securityGroup="sg-51530134",
           wait=True):
    """Create new CloudFormation stack.

    arguments:
    - region: AWS region name. Not required if specified in environment
    - subnetId: AWS subnet. If not specified, pick one for you
    - securityGroup: AWS SecurityGroup. Default is "default", and will
      fail if you have renamed or deleted it
    - wait: wait until the CloudFormation stack creation finishes
    """
    ec2 = clientWrapper('ec2', region)
    if not subnetId:
        subnetId = ec2.describe_subnets()["Subnets"][0]["SubnetId"]
        print("Subnet ID not passed, so selecting first one: " + subnetId)
    with open("CloudFormation.json", "r") as f:
        cfTemplate = f.read()
    cf = clientWrapper('cloudformation', region)
    res = cf.create_stack(
        StackName='Strongjobs',
        TemplateBody=cfTemplate,
        Parameters=[
            {
                'ParameterKey': 'SecurityGroup',
                'ParameterValue': securityGroup,
            },
            {
                'ParameterKey': 'SubnetId',
                'ParameterValue': subnetId,
            },
        ],
        Capabilities=['CAPABILITY_IAM'],
    )
    stackId = res["StackId"]
    print("CloudFormation stack update started with id: " + stackId)
    waiter = cf.get_waiter('stack_create_complete')
    waiter.wait(StackName=stackId)
    print("CloudFormation create completed")


@task(default=True, pre=[makeTemplate])
def update(ctx,
           region=None,
           subnetId=None,
           securityGroup="sg-51530134",
           wait=True):
    """Update CloudFormation stack.

    arguments:
    - region: AWS region name. Not required if specified in environment
    - subnetId: AWS subnet. If not specified, this will pick one for you
    - securityGroup: AWS SecurityGroup. Default is "default", and will
      fail if you have renamed or deleted it
    - wait: wait until the CloudFormation stack creation finishes
    """
    ec2 = clientWrapper('ec2', region)
    if not subnetId:
        subnetId = ec2.describe_subnets()["Subnets"][0]["SubnetId"]
        print("Subnet ID not passed, so selecting first one: " + subnetId)
    with open("CloudFormation.json", "r") as f:
        cfTemplate = f.read()
    cf = clientWrapper('cloudformation', region)
    res = cf.update_stack(
        StackName='Strongjobs',
        TemplateBody=cfTemplate,
        UsePreviousTemplate=False,
        Capabilities=['CAPABILITY_IAM'],
        Parameters=[
            {
                'ParameterKey': 'SecurityGroup',
                'ParameterValue': securityGroup,
            },
            {
                'ParameterKey': 'SubnetId',
                'ParameterValue': subnetId,
                # I'm not sure why this shouldn't work here, but it gives the
                # error: "botocore.exceptions.ClientError: An error occurred
                # (ValidationError) when calling the UpdateStack operation:
                # Invalid input for parameter key subnetId. Cannot specify
                # usePreviousValue as true for a parameter key not in the
                # previous template" FIXME
                #'UsePreviousValue': True
            },
        ],
    )
    stackId = res["StackId"]
    print("CloudFormation stack update started with id: " + stackId)
    waiter = cf.get_waiter('stack_create_complete')
    waiter.wait(StackName=stackId)
    print("CloudFormation update completed")

cfCollection = Collection("cf", makeTemplate, create, update)
ns.add_collection(cfCollection)


# s3 namespace
@task(aliases=["get"])
def pull(ctx):
    """Pull s3 env down."""
    s3 = boto3.client('s3')
    s3.download_file("strongjobs", "conf.env", "conf.env")
    print("conf.env downloaded")


@task(aliases=["set"])
def push(ctx):
    """Push s3 env up."""
    s3 = boto3.client('s3')
    s3.upload_file("conf.env", "strongjobs", "conf.env")
    print("conf.env uploaded")


@task(default=True, pre=[pull], post=[push])
def edit(ctx):
    """Pull s3 env down, edit it, and push it back up."""
    # -i NONE means to not use a viminfo, to minimize artifacts left
    run("vim -i NONE conf.env", pty=True)

s3Collection = Collection("s3", edit, push, pull)
ns.add_collection(s3Collection)
