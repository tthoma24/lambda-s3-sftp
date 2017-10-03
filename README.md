S3 to SFTP Transfer Function
============================

This is a simple single-purpose Lambda function, written in Python3, that will transfer a file from S3 to an SFTP server, on upload to S3. If the file transfer from S3 to SFTP is successful, the source S3 file is deleted.

This project contains the source code for the function along with packaging instructions for preparing the function and its dependencies for upload to AWS. The function itself is very simple, and is contained in `s3_to_sftp.py`. It should be self-explanatory for anyone familiar with Python.

**SFTP Authentication**

The function supports authentication against the remote SFTP server using a username and either a password or a private key. If authenticating using a private key file then the file should be stored in a secure S3 bucket to which the IAM role under which the function is running has read access.

**Tests**

There are tests in the `tests.py` file, which can be run using `pytest`:

```shell
$ pytest tests.py
```

Packaging and Deployment
------------------------

Deploying this function to Lambda involves uploaded a zip file that contains the source code and all of the project dependencies (as specified in `requirements.txt`). The tricky part is that Lambda functions run inside an AmazonLinux environment, and that means that Python dependencies need to be generated / built within the same. The brute force approach to this would be to create an AmazonLinux EC2 instance and package up the project there, but this is hard to do, and impractical during development. A simpler solution is provided by the `Dockerfile` in this project.

These instructions assume that you have Docker installed.

1. Build the packaging image

The default `amazonlinux:latest` docker image provided by Amazon has Python2.7 installed - which is not what we are using. In order to support Python3 development we have to create a new image off the base image that has Python3.

Create the new image and give it a sensible name using the `-t` option:

```shell
$ docker build -t lambda-packager .
```

2. Use the image created to run the `Makefile`:

```shell
$ docker run --rm --volume $(pwd):/lambda lambda-packager package
```

This command will mount the current directory (`$(pwd)`) into a new container as `/lambda`, so that the container has access to `requirements.txt` and the function file (`s3_to_sftp.py`), and run the `make package` command.

The `package` make command does the following, inside the container:

* `pip install` the requirements into `/lambda/.dist`
* Copy `s3_to_sftp.py` source file into `/lambda/.dist`
* Zip up the directory into a new file called `package.zip`

3. Once you have generated the `package.zip`, you can either upload it to AWS
via the console (see screenshot below), or using the `make upload` command,
using the function ARN:

```
$ make update ARN=arn:aws:lambda:us-east-1:account-id:function:s3-to-sftp
```

<img src="screenshots/lambda-configuration.png" />

Configuration
-------------

The following environment variables MUST be set:

    SSH_HOST - the host address of the destination SFTP server
    SSH_USERNAME - the SSH account username
    SSH_PASSWORD - the SSH account password, OR
    SSH_PRIVATE_KEY - path to a private key file on S3, in 'bucket:key' format

The following environment variables MAY be set:

    SSH_PORT - the port number (defaults to 22)
    SSH_DIR - if set, the files will be uploaded to the specified directory
