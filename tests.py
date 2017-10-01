from unittest import mock
from s3_to_sftp import *

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


def test_s3_files():
    data = dict(Records=[TEST_RECORD.copy()])
    objs = list(s3_files(data))
    assert len(objs) == 1
    assert objs[0].bucket_name == 'sourcebucket'
    assert objs[0].key == 'HappyFace.jpg'
    # add another record, check we're getting multiple
    data['Records'].append(TEST_RECORD.copy())
    assert len(data['Records']) == 2
    objs = list(s3_files(data))
    assert len(objs) == 2
    # check that non PUT events are ignored
    data['Records'][0]['eventName'] = 'foo'
    objs = list(s3_files(data))
    assert len(objs) == 1


@mock.patch('s3_to_sftp.get_transport')
@mock.patch('s3_to_sftp.get_sftp_client')
@mock.patch('s3_to_sftp.transfer_file')
@mock.patch('s3_to_sftp.delete_file')
def test_on_trigger_event(mock_delete, mock_transfer, mock_sftp, mock_transport):
    data = dict(Records=[TEST_RECORD.copy()])
    on_trigger_event(data, {})
    assert mock_transfer.call_count == 1
    assert mock_delete.call_count == 1
    # check that a failure in transfer means delete is not called
    mock_transfer.side_effect = Exception("Error transferring file")
    mock_transfer.reset_mock()
    mock_delete.reset_mock()
    on_trigger_event(data, {})
    assert mock_transfer.call_count == 1
    assert mock_delete.call_count == 0
