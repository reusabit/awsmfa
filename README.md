# awsmfa
Utility for streamlining the process of obtaining temporary, MFA authenticated session for AWS CLI. Makes requiring MFA for the CLI practical.

## Background Information

For background information, see our blog entry: 
[https://reusabit.com/blog/aws-cli-mfa](https://reusabit.com/blog/aws-cli-mfa)

## Configuration

### AWS files

The utility requires the following files:

~/.aws/credentials
```
[myaccountPerm]         
aws_access_key_id = REDACTED
aws_secret_access_key = REDACTED
                       
[myaccount]             
```

~/.aws/config
```
[myaccountPerm]                                            
output = json                                             
mfa_serial = arn:aws:iam::REDACTED_ACCOUNT_NUMBER:mfa/REDACTED_USER_NAME       
user_arn = arn:aws:iam::REDACTED_ACCOUNT_NUMBER:user/REDACTED_USER_NAME        
                                                          
[myaccount]                                                
region = us-west-2                                        
source_profile = myaccountPerm                             
```

The pair of files contains two profiles.

The credentials under the "myaccountPerm" profile are the permanent
credentials as configured in the AWS console. These are used when
obtaining the temporary session credentials.

The second profile ("myaccount") is where the temporary session credentials
get placed. (The script edits the credentials file.)

The script looks up the mfa_serial from the config file. (This is a required
parameter to the "aws sts" command.)

Note for Windows: If using the Windows version of the AWS CLI with a bash
shell (cygwin, wsl2, etc.), AWS will use the .aws directory in the windows 
home directory. (e.g., C:\Users\USERNAME\.aws). The awsmfa script will access
the $HOME/.aws directory. Resolve this by creating a symbolic link from 
$HOME/.aws to the windows directory:

```
$ ln -s /cygdrive/c/Users/USERNAME/.aws ~/.aws
```


### Add script to path

The script should be added to the path. We also assume for these examples that
a symbolic link is created as follows for more succinct usage:

```
$ ln -s awsmfa.py awsmfa
```

## Usage

Basic usage:
```
$ export AWS_PROFILE=myaccount
$ awsmfa login --token-code 123456
$ # Do some aws cli stuff
$ awsmfa logout
```

Note: The logout command above removes the temp session from the file,
but as far as I'm aware,
there is not a way to invalidate the session on the AWS side.

Any positional parameters are passed through to the "aws sts" command.
(Can use -- to interpret remaining parameters as positional.)
So, for example, the following sets a non-default duration for the session.

```
$ awsmfa login --token-code 123456 -- --duration-seconds 3600
```
