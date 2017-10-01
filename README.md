S3 to SFTP
==========

Send an S3 file, whenever it is uploaded, to a remote server using SFTP

This project contains the source code and packaging instructions for an AWS Lambda function written in Python3 that will transfer a file from S3 to and SFTP server. The function itself is very simple, and is contained in `s3_to_sftp.py`. It should be self-explanatory for anyone familiar with Python.

Packaging and Deployment
------------------------

Deploying this function to Lambda involves uploaded a zip file that contains the source code and all of the project dependencies (as specified in `requirements.txt`). The tricky part is that Lambda functions run inside an AmazonLinux environment, and that means that Python dependencies need to be generated / built within the same. The brute force approach to this would be to create an AmazonLinux EC2 instance and package up the project there, but this is hard to do, and impractical during development. A simpler solution is provided by the `Dockerfile` in the project.

These instructions assume that you have Docker installed.

1. Build the packaging image

The default amazonlinux:latest docker image provided by Amazon has Python2.7 installed - which is not what we are using. In order to support Python3 development we have to create a new image of the base image that has Python3, and a couple of extra tools that make packaging possible (principally `pip-tools` and `virtualenv`).

Create the new image and give it a sensible name using the `-t` option:

```shell
$ docker build -t packager .
```

2. Use the image created to run the `Makefile`:

```shell
$ docker run --rm --volume $(pwd):/lambda packager
```

This command will mount the current directory (`$(pwd)`) into a new container as `/lambda`, and run the `make package` command.

The `package` make command does the following, inside the new, clean, container:

1. Create and activate a new virtualenv using python3
2. Install all of the requirements specified in `requirements.txt`
3. Copy all the dependencies installed into a `/dist` directory, along with the `s3_to_sftp.py` source
4. Zip up the directory into a new file called `package.zip`

3. Upload `package.zip` to AWS through the Lambda interface.

Configuration
-------------

The following environment variables MUST be set:

    SSH_HOST - the host address of the destination SFTP server
    SSH_PORT - the port number (NB this must be set, there is no default)
    SSH_USERNAME - the SSH account username
    SSH_PASSWORD - the SSH account password

The following environment variables MAY be set:

    SSH_DIR - if set, the files will be uploaded to the specified SFTP directory
