#!/usr/bin/python3
#
# Copyright 2021 Reusabit Software LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
# Preconditions:
#   You must have aws configuration files in ~/.aws directory.
#   Don't use the "profile" keyword in the config file sections.
#   Create a profile in "credentials" which contains permanent access key and secret.
#   Create a corresponding profile in "config" which contains mfa_serial, and user_arn.
#   Create a temporary profile in "config" which contains source_profile = <name of the permanent profile>
#   Create an empty temporary profile in "credentials"
#
# Postconditions:
#   The temporary profile in "credentials" is updated to include the temporary session credentials.
#   This temporary profile can then be used with aws cli.


from argparse import ArgumentParser, Namespace
import os
import sys
from configparser import ConfigParser
import os.path as path
import json


defaultProfileEnv = os.getenv("AWS_DEFAULT_PROFILE")
currentProfileEnv = os.getenv("AWS_PROFILE", defaultProfileEnv)

parser = ArgumentParser(
    description="Obtains a temporary session key from AWS using the provided MFA token.",
)

parser.add_argument(
    "--profile",
    default=currentProfileEnv,
    dest="profile",
    help="Name of the (temporary) profile to use. (Permanent profile extracted from config file.)"
)

subparsers = parser.add_subparsers(dest="subcommand")

loginParser = subparsers.add_parser("login")

loginParser.add_argument(
    "--token-code",
    help="Token from the mfa device",
    dest="tokenCode",
    required=True
)

loginParser.add_argument(
    "passThroughArgs",
    nargs="*",
    help="Any additional arguments are passed through to the aws sts command. E.g., '-- --duration-seconds'"
)

logoutParser = subparsers.add_parser("logout")

args = parser.parse_args()
subcommand = args.subcommand

profile = args.profile

home = path.expanduser("~")
awsDir = f"{home}/.aws"
configFile = f"{awsDir}/config"
credentialsFile = f"{awsDir}/credentials"

if profile is None:
    print("Profile not specified and not provided in environment variable.")
    parser.print_help()
    sys.exit(1)

if subcommand == "login":
    passThroughArgs = args.passThroughArgs
    tokenCode = args.tokenCode

    home = path.expanduser("~")
    awsDir = f"{home}/.aws"

    config = ConfigParser()
    config.read(f"{awsDir}/config")
    if not config.has_section(profile):
        print(f"The specified temp profile [{profile}] is not present in the config file")
        sys.exit(1)

    tempConfigSection = config[profile]
    permProfile = tempConfigSection.get("source_profile")

    if permProfile is None:
        print(f"The specified temp profile [{profile}] does not contain a source_profile setting.")
        sys.exit(1)

    if not config.has_section(permProfile):
        print(
            f"The perm profile [{permProfile}] specified by the source_profile setting is not present in the config file.")
        sys.exit(1)

    permConfigSection = config[permProfile]
    mfa_serial = permConfigSection.get("mfa_serial")

    if mfa_serial is None:
        print(f"The perm profile [{permProfile}] does not contain the mfa_serial setting.")
        sys.exit(1)

    if permConfigSection.get("user_arn") is None:
        print(f"The perm profile [{permProfile}] does not contain the user_arn setting.")
        sys.exit(1)

    credentials = ConfigParser()
    credentials.read(credentialsFile)

    if not credentials.has_section(permProfile):
        print(f"The credentials file does not contain the perm profile [{permProfile}] section.")
        sys.exit(1)

    if not credentials.has_section(profile):
        print(f"Creating temp profile section [{profile}]")
        credentials.add_section(profile)

    passThroughArgsJoined = " ".join(passThroughArgs)
    stsCommand = f"aws sts get-session-token --profile {permProfile} --serial-number {mfa_serial} --token-code {tokenCode} {passThroughArgsJoined}"
    #print(f"sts command: {stsCommand}")
    stsResult = os.popen(stsCommand).read()
    #print(f"results: {stsResult}")
    try:
        stsResultJson = json.loads(stsResult)
    except json.decoder.JSONDecodeError:
        print(f"Error from aws sts command: {stsResult}")
        sys.exit(1)

    credentials[profile]['aws_access_key_id'] = stsResultJson['Credentials']['AccessKeyId']
    credentials[profile]['aws_secret_access_key'] = stsResultJson['Credentials']['SecretAccessKey']
    credentials[profile]['aws_session_token'] = stsResultJson['Credentials']['SessionToken']

    with open(credentialsFile, "w") as file:
        credentials.write(file)
elif subcommand == "logout":
    credentials = ConfigParser()
    credentials.read(credentialsFile)

    if not credentials.has_section(profile):
        print(f"The credentials file does not have the specified temp profile [{profile}]")
        sys.exit(1)

    credentials.remove_option(profile, "aws_access_key_id")
    credentials.remove_option(profile, "aws_secret_access_key")
    credentials.remove_option(profile, "aws_session_token")

    with open(credentialsFile, "w") as file:
        credentials.write(file)

