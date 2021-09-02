import json

import boto3
from botocore.exceptions import ClientError

from nightowl.utils.model import find_item


def get_name(tags, default=None):
    if not tags:
        return default
    name_tag = find_item(tags, lambda tag: tag['Key'] == 'Name')
    return name_tag['Value'] if name_tag else default


def get_secret_data(secret_id, region_name):
    client = boto3.client(
        'secretsmanager',
        region_name=region_name,
    )
    try:
        response = client.get_secret_value(
            SecretId=secret_id,
        )
    except ClientError:
        return None
    else:
        if 'SecretString' in response:
            return json.loads(response['SecretString'])
    return None


def set_secret_data(secret_id, region_name, data):
    client = boto3.client(
        'secretsmanager',
        region_name=region_name,
    )
    try:
        client.put_secret_value(
            SecretId=secret_id,
            SecretString=json.dumps(data),
        )
    except ClientError:
        return None
    else:
        return data
    return None
