#!/usr/bin/env python

from datetime import datetime

from troposphere import (AWS_REGION,
                         AWS_STACK_NAME,
                         Base64,
                         Join,
                         Parameter,
                         Ref,
                         Template,
                         codedeploy,)
from troposphere.autoscaling import AutoScalingGroup, LaunchConfiguration, Tag
from troposphere.constants import (IMAGE_ID,
                                   SECURITY_GROUP_ID,
                                   STRING,
                                   SUBNET_ID,)
from troposphere.policies import AutoScalingRollingUpdate, UpdatePolicy
from troposphere.s3 import Bucket, Private


t = Template()
t.add_description("CloudFormation template for Strongarm Cronjob setup")
t.add_metadata({
    "Comments": "Made with troposphere",
    "LastUpdated": datetime.now().strftime('%Y-%m-%d'),
    "Version": "V0.1",
})

# Parameters
securityGroup = t.add_parameter(Parameter(
    "SecurityGroup",
    Description="The security group for the region this stack is running in",
    Type=SECURITY_GROUP_ID,
    ConstraintDescription="The id of the default security group in this "
                          "region to enable communication between instances",
    Default="default"
))
imageId = t.add_parameter(Parameter(
    "ImageId",
    Description="The id of the AMI that should be used by these ASGs",
    Type=IMAGE_ID,
    ConstraintDescription="Ubuntu 64-bit is reasonable",
    #Default="ami-b9ff39d9",  # Ubuntu 16 LTS--update when CodeDeploy in s3
                              # catches up to git master (Ruby version
                              # problems)
    Default="ami-65579105",  # Ubuntu 14 LTS
))
subnetId = t.add_parameter(Parameter(
    "SubnetId",
    Description="The subnet in which to run",
    Type=SUBNET_ID,
    ConstraintDescription="Should be a private subnet.",
))
IAMInstanceProfile = t.add_parameter(Parameter(
    "IAMInstanceProfile",
    Description="IAM Instance Profile",
    Type=STRING,
))
serviceRole = t.add_parameter(Parameter(
    "serviceRole",
    Description="Service Role",
    Type=STRING,
))

# Launch configuration
launchConfiguration = t.add_resource(LaunchConfiguration(
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
autoScalingGroupStrongjobs = t.add_resource(AutoScalingGroup(
    "StrongjobsGroup",
    UpdatePolicy=UpdatePolicy(
        AutoScalingRollingUpdate=AutoScalingRollingUpdate(
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
        Tag("environment", Ref(AWS_STACK_NAME), "true"),
        Tag("Name",
            Join("-", [Ref(AWS_STACK_NAME), "asg-strongjobs"]),
            "true"),
        Tag("application", "strongjobs", "true"),
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
    ServiceRoleArn=Ref(serviceRole),
))

# S3 bucket
s3bucket = t.add_resource(Bucket(
    "StrongjobsS3Bucket",
    BucketName="strongjobs",
    AccessControl=Private,
))

print(t.to_json())
