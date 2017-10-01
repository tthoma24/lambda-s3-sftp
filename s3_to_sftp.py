"""
AWS Lambda function for transferring files from S3 to SFTP on a
PUT event (i.e. new files).

Required env vars:

    SSH_HOSTNAME
    SSH_PORT
    SSH_USERNAME
    SSH_PASSWORD

Optional env vars

    SSH_DIR - if specified the SFTP client will chdir into this directory
              prior to transferring the file across.

"""
import logging
import os

import boto3
import paramiko

logger = logging.getLogger()
logger.setLevel(os.getenv('LOGGING_LEVEL', 'DEBUG'))


# This is the Lambda entrypoint
def on_trigger(event, context):
    """Open SFTP connection and transfer S3 file across on PUT trigger."""
    transport = get_transport()
    sftp_client = get_sftp_client(transport)
    # context manager handles connection close / cleanup
    with transport:
        for record in event['Records']:
            bucket, key = get_bucket_key(record)
            transfer_file(sftp_client, bucket, key)


def get_bucket_key(record):
    """Parse bucket, key from S3 PUT trigger record."""
    bucket = record['s3']['bucket']['name']
    key = record['s3']['object']['key']
    return bucket, key


def get_transport():
    """Return a connected Transport object."""
    hostname = os.environ['SSH_HOST']
    port = int(os.environ['SSH_PORT'])
    username = os.environ['SSH_USERNAME']
    password = os.environ['SSH_PASSWORD']
    transport = paramiko.Transport((hostname, port))
    transport.connect(username=username, password=password)
    return transport


def get_sftp_client(transport):
    """Return an SFTP client, chdir to SSH_DIR if specified."""
    client = paramiko.SFTPClient.from_transport(transport)
    if os.getenv('SSH_DIR'):
        client.chdir(os.getenv('SSH_DIR'))
    return client


def transfer_file(sftp_client, bucket, key):
    """
    Download file from S3 and upload to SFTP
    """
    filename = key.split('/')[-1]
    s3_client = boto3.client('s3')
    with sftp_client.file(filename, 'w') as sftp_file:
        try:
            s3_client.download_fileobj(
                Bucket=bucket,
                Key=key,
                Fileobj=sftp_file
            )
        except Exception:
            logger.exception("Error uploading '%s' to SFTP", filename)
        else:
            logger.info("Successfully uploaded '%s' to SFTP", filename)
