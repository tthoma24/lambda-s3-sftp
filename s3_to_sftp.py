"""
AWS Lambda function for transferring files from S3 to SFTP on a PUT event.

Required env vars:

    SSH_HOSTNAME
    SSH_PORT
    SSH_USERNAME
    SSH_PASSWORD

Optional env vars

    SSH_DIR - if specified the SFTP client will transfer the files to the
        specified directory.

"""
import logging
import os

import boto3
import paramiko

logger = logging.getLogger()
logger.setLevel(os.getenv('LOGGING_LEVEL', 'DEBUG'))


def on_trigger_event(event, context):
    """
    Move uploaded S3 files to SFTP endpoint, then delete.

    This is the Lambda entry point. It receives the event
    payload and processes it. In this case it receives a
    set of 'Record' dicts which should contain details of
    an S3 file PUT. The contents of this dict can be found
    in the tests.py::TEST_RECORD - the example comes from
    the Lambda test event rig.

    The only important information we process in this function
    are the `eventName` which must be ObjectCreated:Put, and
    then the bucket name and object key.

    This function then connects to the SFTP server, copies
    the file across, and then (if successful), deletes the
    original. This is done to prevent sensitive data from
    hanging around - it basically only exists for as long
    as it takes Lambda to pick it up and transfer it.

    See http://docs.aws.amazon.com/lambda/latest/dg/python-programming-model-handler-types.html

    Args:
        event: dict, the event payload delivered by Lambda.
        context: a LambdaContext object - unused.

    """
    sftp_client, transport = connect_to_sftp()
    with transport:
        for s3_file in s3_files(event):
            logger.debug("Transferring '%s' from S3 to SFTP", s3_file.key)
            try:
                transfer_file(sftp_client, s3_file)
                delete_file(s3_file)
            except Exception:
                logger.exception("Error processing '%s'", s3_file.key)


def connect_to_sftp():
    """
    Connect to SFTP endpoint.

    Use env vars to connect to the SFTP endpoint, and return a connected
    client object, as well as the Transport object, which can be used as
    a context manager.

    Returns a 2-tuple containing paramiko (SFTPClient, Transport)
        objects, connected to the configured endpoint.

    """
    hostname = os.environ['SSH_HOST']
    port = int(os.environ['SSH_PORT'])
    username = os.environ['SSH_USERNAME']
    password = os.environ['SSH_PASSWORD']
    ssh_dir = os.getenv('SSH_DIR')
    transport = paramiko.Transport((hostname, port))
    transport.connect(username=username, password=password)
    client = paramiko.SFTPClient.from_transport(transport)
    logger.debug("Connected to remote SFTP server")
    if ssh_dir:
        client.chdir(ssh_dir)
        logger.debug("Switched into remote SFTP upload directory")
    return client, transport


def s3_files(event):
    """
    Iterate through event and yield boto3.Object for each S3 file PUT.

    This function loops through all the records in the payload,
    checks that the event is a file PUT, and if so, yields a
    boto3.Object that represents the file.

    Args:
        event: dict, the payload received from the Lambda trigger.
            See tests.py::TEST_RECORD for a sample.

    """
    for record in event['Records']:
        bucket = record['s3']['bucket']['name']
        key = record['s3']['object']['key']
        if record['eventName'] == "ObjectCreated:Put":
            yield boto3.resource('s3').Object(bucket, key)
        else:
            logger.warning("Ignoring invalid event: %s", record)


def transfer_file(sftp_client, s3_file):
    """
    Transfer S3 file to SFTP server.

    Args:
        sftp_client: paramiko.SFTPClient, connected to SFTP endpoint
        s3_file: boto3.Object representing the S3 file

    """
    filename = s3_file.key.split('/')[-1]
    with sftp_client.file(filename, 'w') as sftp_file:
        s3_file.download_fileobj(Fileobj=sftp_file)
    logger.info("Transferred '%s' from S3 to SFTP", s3_file.key)


def delete_file(s3_file):
    """
    Delete file from S3.

    This is only a one-liner, but it's pulled out into its own function
    to make it easier to mock in tests, and to make the trigger
    function easier to read.

    Args:
        s3_file: boto3.Object representing the S3 file

    """
    s3_file.delete()
    logger.info("Deleted '%s' from S3", s3_file.key)
