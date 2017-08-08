#!/usr/bin/env python

from datetime import datetime
from os.path import getmtime

import awacs.aws as aws
import awacs.sts as sts

from troposphere import (AWS_REGION,
                         AWS_STACK_NAME,
                         Base64,
                         codedeploy,
                         Join,
                         Parameter,
                         Ref,
                         Template)
import troposphere.autoscaling as autoscaling
from troposphere.constants import (IMAGE_ID,
                                   SECURITY_GROUP_ID,
                                   SUBNET_ID,)
import troposphere.iam as iam
import troposphere.policies as policies
import troposphere.s3 as s3

OUTPUTFILE = "CloudFormation.json"


t = Template()
t.add_description("CloudFormation template for Strongarm Cronjob setup")
t.add_metadata({
    "Comments": "Made with troposphere",
    "LastUpdated": datetime.utcfromtimestamp(getmtime(__file__)).strftime('%Y-%m-%d %H:%M:%SZ'),
    "Version": "V0.1",
})

# Parameters
securityGroup = t.add_parameter(Parameter(
    "SecurityGroup",
    Description="The security group for the region this stack is running in",
    Type=SECURITY_GROUP_ID,
    ConstraintDescription="The id of the default security group in this "
                          "region to enable communication between instances",
    Default="sg-51530134"
))
imageId = t.add_parameter(Parameter(
    "ImageId",
    Description="The id of the AMI that should be used by these ASGs",
    Type=IMAGE_ID,
    ConstraintDescription="Ubuntu 64-bit is reasonable",
    # Ubuntu 16 LTS--update when CodeDeploy in s3 catches up to git and fixes
    # Ruby version problems.
    # Default="ami-b9ff39d9",
    Default="ami-65579105",  # Ubuntu 14 LTS
))
subnetId = t.add_parameter(Parameter(
    "SubnetId",
    Description="The subnet in which to run",
    Type=SUBNET_ID,
    ConstraintDescription="Should be a private subnet.",
))

# S3 bucket
s3bucket = t.add_resource(s3.Bucket(
    "StrongjobsS3Bucket",
    BucketName="strongjobs",
    AccessControl=s3.Private,
))

# Access management things
serviceRole = t.add_resource(iam.Role(
    "StrongjobsServiceRole",
    AssumeRolePolicyDocument=aws.Policy(
        Statement=[
            aws.Statement(
                Effect=aws.Allow,
                Action=[sts.AssumeRole],
                Principal=aws.Principal("Service",
                                        ["codedeploy.amazonaws.com"])
            ),
            aws.Statement(
                Effect=aws.Allow,
                Action=[sts.AssumeRole],
                Principal=aws.Principal("Service", ["ec2.amazonaws.com"])
            ),
        ],
    ),
    ManagedPolicyArns=["arn:aws:iam::aws:policy/AmazonS3FullAccess",
                       "arn:aws:iam::aws:policy/service-role/"
                       "AWSCodeDeployRole"]
))
IAMInstanceProfile = t.add_resource(iam.InstanceProfile(
    "StrongjobsInstanceProfile",
    Roles=[Ref(serviceRole)]
))

# Launch configuration
launchConfiguration = t.add_resource(autoscaling.LaunchConfiguration(
    "StrongjobsLaunchConfig",
    ImageId=Ref(imageId),
    SecurityGroups=[Ref(securityGroup)],
    IamInstanceProfile=Ref(IAMInstanceProfile),
    InstanceType="t2.micro",
    AssociatePublicIpAddress=False,
    BlockDeviceMappings=[{
        "DeviceName": "/dev/sda1",
        "Ebs": {
            "VolumeSize": "10",
        },
    }],
    UserData=Base64(Join('', [
        "#cloud-boothook\n",
        "#!/bin/bash\n",
        "echo 'userdata is running'\n",
        "apt-get -y install awscli\n",
        "apt-get -y install ruby2.0\n",
        "aws s3 cp s3://aws-codedeploy-",
        {"Ref": AWS_REGION},
        "/latest/install /tmp/codedeploy_install --region ",
        {"Ref": AWS_REGION}, "\n",
        "/bin/chmod +x /tmp/codedeploy_install\n",
        "/tmp/codedeploy_install auto \n"
    ])),
))

# AutoScaling Group
autoScalingGroupStrongjobs = t.add_resource(autoscaling.AutoScalingGroup(
    "StrongjobsGroup",
    UpdatePolicy=policies.UpdatePolicy(
        AutoScalingRollingUpdate=policies.AutoScalingRollingUpdate(
            MinInstancesInService="0",
            MaxBatchSize='1',
        )
    ),
    LaunchConfigurationName=Ref(launchConfiguration),
    VPCZoneIdentifier=[Ref(subnetId)],
    MinSize="1",
    DesiredCapacity="1",
    MaxSize="1",
    Tags=[
        autoscaling.Tag("environment", Ref(AWS_STACK_NAME), "true"),
        autoscaling.Tag("Name",
                        Join("-", [Ref(AWS_STACK_NAME), "asg-strongjobs"]),
                        "true"),
        autoscaling.Tag("application", "strongjobs", "true"),
    ],
))

# CodeDeploy
strongjobsApplication = t.add_resource(codedeploy.Application(
    "StrongjobsApplication",
    ApplicationName=Join("-", ["strongjobs", Ref(AWS_STACK_NAME)])
))
strongjobsCodeDeploy = t.add_resource(codedeploy.DeploymentGroup(
    "StrongjobsDeploymentGroup",
    DeploymentGroupName='strongjobs',
    ApplicationName=Ref(strongjobsApplication),
    AutoScalingGroups=[Ref(autoScalingGroupStrongjobs)],
    ServiceRoleArn=Join("", ["arn:aws:iam::",
                             Ref("AWS::AccountId"),
                             ":role/", Ref(serviceRole)
                             ]),
))

with open(OUTPUTFILE, "w") as f:
    f.write(t.to_json())
print("Wrote " + OUTPUTFILE)
