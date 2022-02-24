#!/usr/bin/env python

import sys
import boto3
import botocore
import argparse

session = None


class initArgs(object):

    def __init__(self):
        self.parser = argparse.ArgumentParser()
        self.parser.add_argument(
            "--no-verify-ssl", action='store_true', help="Disable SSL verification.")
        self.parser.add_argument(
            "--profile", type=str, help="The credential profile used to execute this job.  This configuration is not required if 'aws configure' has been run and a [default] profile is defined in ~/aws/crednetial", required=False)
        self.args = self.parser.parse_args(sys.argv[1:])

    def get_args(self):
        return self.args


def getRegions():
    try:
        client = session.client('ec2', verify=args.no_verify_ssl)
    except botocore.exceptions.NoRegionError as e:
        print("Error initiating AWS client!")
        print("Have you configured your AWS region?  (e.g. in ~/aws/crednetial)  See 'aws configure' ")
        print("If you are using a specific profile, use --profile")
        exit(1)

    regions = []

    try:
        for region in client.describe_regions()['Regions']:
            regions.append(region['RegionName'])
        return regions
    except botocore.exceptions.ClientError as e:
        print("Error executing AWS commands!")
        print("Have you configured your AWS credentials?  (e.g. in ~/aws/crednetial)  See 'aws configure' ")
        print("Or perhaps the access token has expired?")
        exit(1)


def detach_internet_gateways(vpcId, client):
    igws = client.describe_internet_gateways(
        Filters=[
            {
                'Name': 'attachment.vpc-id',
                'Values': [
                    vpcId,
                ]
            },
        ],
    )

    for igw in igws['InternetGateways']:
        igwId = igw['InternetGatewayId']
        print("Detaching Internet Gateway " + igwId + " from " + vpcId + "...")
        client.detach_internet_gateway(
            InternetGatewayId=igwId,
            VpcId=vpcId
        )


def delete_subnets(vpcId, client):
    subnets = client.describe_subnets(
        Filters=[
            {
                'Name': 'vpc-id',
                'Values': [
                    vpcId,
                ]
            },
        ]
    )

    for subnet in subnets['Subnets']:
        subnetId = subnet['SubnetId']
        print("Deleting Subnet " + subnetId + " from " + vpcId + "...")
        client.delete_subnet(
            SubnetId=subnetId,
        )


def remove_default_vpcs(regions):
    client = None
    count = 0

    for region in regions:
        client = session.client(
            'ec2', verify=args.no_verify_ssl, region_name=region)
        response = client.describe_vpcs(
            Filters=[
                {
                    'Name': 'isDefault',
                    'Values': [
                        'true',
                    ]
                }
            ]
        )

        for vpcs in response['Vpcs']:
            vpcId = vpcs['VpcId']
            print("[" + region + "]")

            detach_internet_gateways(vpcId, client)
            delete_subnets(vpcId, client)

            print("Deleting Default VPC " + vpcId + "...\n")
            count += 1
            client.delete_vpc(VpcId=vpcs['VpcId'])

    return count

if __name__ == "__main__":
    args = initArgs().get_args()
    session = boto3.Session(profile_name=args.profile)
    print("Scanning for default VPCs...\n")
    count = remove_default_vpcs(getRegions())
    print(str(count) + " default VPCs deleted.")
