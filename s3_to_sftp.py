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
def on_trigger_event(event, context):
    """Open SFTP connection and transfer S3 file across on PUT trigger."""
    transport = get_transport()
    sftp_client = get_sftp_client(transport)
    # context manager handles connection close / cleanup
    with transport:
        for s3_file in s3_files(event):
            try:
                transfer_file(sftp_client, s3_file)
                delete_file(s3_file)
            except Exception:
                logger.exception("Error processing '%s'", s3_file.key)


def s3_files(event):
    """Generator yielding Boto3.Objects for each PUT file in event dict."""
    for record in event['Records']:
        bucket = record['s3']['bucket']['name']
        key = record['s3']['object']['key']
        if record['eventName'] == "ObjectCreated:Put":
            yield boto3.resource('s3').Object(bucket, key)
        else:
            logger.warning("Ignoring invalid event: %s", record)


def get_transport():
    """Return a connected Transport object configured from env vars."""
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


def transfer_file(sftp_client, s3_file):
    """Download file from S3 and upload directly to SFTP."""
    filename = s3_file.key.split('/')[-1]
    with sftp_client.file(filename, 'w') as sftp_file:
        s3_file.download_fileobj(Fileobj=sftp_file)
    logger.info("Transferred '%s' from S3 to SFTP", s3_file.key)


def delete_file(s3_file):
    """Delete S3 file."""
    s3_file.delete()
    logger.info("Deleted '%s' from S3", s3_file.key)
