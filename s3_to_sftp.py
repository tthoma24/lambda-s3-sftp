"""
AWS Lambda function for transferring files from S3 to SFTP on a PUT event.

Required env vars:

    SSH_HOSTNAME
    SSH_USERNAME
    SSH_PASSWORD or SSH_PRIVATE_KEY (S3 file path in 'bucket:key' format)

Optional env vars

    SSH_PORT - defaults to 22
    SSH_DIR - if specified the SFTP client will transfer the files to the
        specified directory.

"""
import logging
import io
import os

import boto3
import paramiko

logger = logging.getLogger()
logger.setLevel(os.getenv('LOGGING_LEVEL', 'DEBUG'))

# read in shared properties on module load - will fail hard if any are missing
SSH_HOST = os.environ['SSH_HOST']
SSH_PORT = int(os.getenv('SSH_PORT', 22))
SSH_USERNAME = os.environ['SSH_USERNAME']
SSH_PASSWORD = os.getenv('SSH_PASSWORD')
SSH_PRIVATE_KEY = os.getenv('SSH_PRIVATE_KEY')
SSH_DIR = os.getenv('SSH_DIR')

# fail hard on startup if no authentication mechanism exists
assert SSH_PASSWORD or SSH_PRIVATE_KEY, "Missing SSH_PASSWORD or SSH_PRIVATE_KEY"


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
    if SSH_PRIVATE_KEY:
        key_obj = get_private_key(*SSH_PRIVATE_KEY.split(':'))
    else:
        key_obj = None

    sftp_client, transport = connect_to_sftp(
        hostname=SSH_HOST,
        port=SSH_PORT,
        username=SSH_USERNAME,
        password=SSH_PASSWORD,
        pkey=key_obj
    )
    if SSH_DIR:
        sftp_client.chdir(SSH_DIR)
        logger.debug("Switched into remote SFTP upload directory")

    with transport:
        for s3_file in s3_files(event):
            logger.debug("Transferring '%s' from S3 to SFTP", s3_file.key)
            try:
                transfer_file(sftp_client, s3_file)
                delete_file(s3_file)
            except Exception:
                logger.exception("Error processing '%s'", s3_file.key)


def connect_to_sftp(hostname, port, username, password, pkey):
    """Connect to SFTP server and return client object."""
    transport = paramiko.Transport((hostname, port))
    transport.connect(username=username, password=password, pkey=pkey)
    client = paramiko.SFTPClient.from_transport(transport)
    logger.debug("Connected to remote SFTP server")
    return client, transport


def get_private_key(bucket, key):
    """
    Return an RSAKey object from a private key stored on S3.

    It will fail hard if the key cannot be read, or is invalid.

    """
    key_obj = boto3.resource('s3').Object(bucket, key)
    key_str = key_obj.get()['Body'].read().decode('utf-8')
    key = paramiko.RSAKey.from_private_key(io.StringIO(key_str))
    logger.debug("Retrieved private key from S3")
    return key


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
