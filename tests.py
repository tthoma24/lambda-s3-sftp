from unittest import mock
from s3_to_sftp import *

import paramiko
import pytest

# taken directly from the Lambda test configuration
TEST_RECORD = {
    "eventVersion": "2.0",
    "eventTime": "1970-01-01T00:00:00.000Z",
    "requestParameters": {
        "sourceIPAddress": "127.0.0.1"
    },
    "s3": {
        "configurationId": "testConfigRule",
        "object": {
            "eTag": "0123456789abcdef0123456789abcdef",
            "sequencer": "0A1B2C3D4E5F678901",
            "key": "HappyFace.jpg",
            "size": 1024
        },
        "bucket": {
            "arn": "arn:aws:s3:::mybucket",
            "name": "sourcebucket",
            "ownerIdentity": {
                "principalId": "EXAMPLE"
            }
        },
        "s3SchemaVersion": "1.0"
    },
    "responseElements": {
        "x-amz-id-2": "EXAMPLE123/5678abcdefghijklambdaisawesome/mnopqrstuvwxyzABCDEFGH",
        "x-amz-request-id": "EXAMPLE123456789"
    },
    "awsRegion": "us-east-1",
    "eventName": "ObjectCreated:Put",
    "userIdentity": {
        "principalId": "EXAMPLE"
    },
    "eventSource": "aws:s3"
}


def test_sftp_filename():
    f = mock.Mock(bucket_name='foo', key='bar')
    assert sftp_filename('', f) == ''
    assert sftp_filename('{bucket}', f) == 'foo'
    assert sftp_filename('{bucket}-{key}', f) == 'foo-bar'
    # might fail if you run the test at midnight
    assert (
        sftp_filename('{bucket}-{key}_{current_date}', f) ==
        'foo-bar_' + datetime.date.today().isoformat()
    )


def test_s3_files():
    event = dict(Records=[TEST_RECORD.copy()])
    objs = list(s3_files(event))
    assert len(objs) == 1
    assert objs[0].bucket_name == 'sourcebucket'
    assert objs[0].key == 'HappyFace.jpg'
    # add another record, check we're getting multiple
    event['Records'].append(TEST_RECORD.copy())
    assert len(event['Records']) == 2
    objs = list(s3_files(event))
    assert len(objs) == 2
    # check that non ObjectCreated events are ignored
    event['Records'][0]['eventName'] = 'ObjectRemoved:Delete'
    objs = list(s3_files(event))
    assert len(objs) == 1


@mock.patch('s3_to_sftp.sftp_filename')
@mock.patch('s3_to_sftp.connect_to_sftp')
@mock.patch('s3_to_sftp.archive_file')
@mock.patch('s3_to_sftp.transfer_file')
@mock.patch('s3_to_sftp.delete_file')
def test_on_trigger_event(mock_delete, mock_transfer, mock_archive,
                          mock_connect, mock_filename):

    # lots of mocks to remove the paramiko SSH connection internals
    mock_client = mock.Mock(spec=paramiko.SFTPClient)
    mock_transport = paramiko.Transport(None)
    mock_connect.return_value = (mock_client, mock_transport)

    event = dict(Records=[TEST_RECORD.copy()])
    context = mock.Mock()

    # 1. transfer works, check for archive and deletion
    on_trigger_event(event, context)
    assert mock_transfer.call_count == 1
    assert mock_archive.call_count == 1
    assert mock_delete.call_count == 1
    mock_archive.assert_called_with(
        bucket='sourcebucket',
        filename=mock_filename.return_value,
        contents=''
    )

    # 2. transfer failure, archive is called with error message
    mock_transfer.reset_mock()
    mock_archive.reset_mock()
    mock_delete.reset_mock()
    ex = botocore.exceptions.BotoCoreError()
    mock_transfer.side_effect = botocore.exceptions.BotoCoreError()
    on_trigger_event(event, context)
    assert mock_transfer.call_count == 1
    mock_archive.assert_called_with(
        bucket='sourcebucket',
        filename=mock_filename.return_value + '.x',
        contents=str(ex)
    )
    assert mock_delete.call_count == 1
