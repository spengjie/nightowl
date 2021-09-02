import uuid

import requests
from mongoengine.errors import DoesNotExist

from nightowl.auth import authorize
from nightowl.models import admin as admin_model, task as task_model
from nightowl.utils.datetime import utc_now


def sync(context):
    task_result = context.task_result
    result = authorize('password')
    error_code = result['error_code']
    user_reason = result['user_message']
    admin_reason = result.get('admin_message', user_reason)
    if error_code != 20000:
        log_level = task_model.LogLevel.WARNING
        if error_code == 59999:
            log_level = task_model.LogLevel.ERROR
        task_result.add_log(f'Failed to log into SSO (reason={admin_reason})', log_level)
        task_result.result = task_model.TaskResultStatus.FAILURE
        return
    access_token = result['token']
    task_result.add_log('Logged into SSO')

    user_results = []
    group_results = []
    settings = admin_model.AuthSettings.get()  # pylint: disable=no-member
    sso_settings = settings.sso

    users_api_url = sso_settings.users_api_url
    if users_api_url:
        r = requests.get(
            users_api_url, verify=sso_settings.verify_certificate,
            headers={'Authorization': 'Bearer ' + access_token})
        if r.ok:
            user_results = r.json()
            for result in user_results:
                _id = uuid.UUID(result['_id'])
                for group in result['groups']:
                    group['_id'] = uuid.UUID(group['_id'])
                if result['manager']:
                    result['manager']['_id'] = uuid.UUID(result['manager']['_id'])
                for direct_report in result['direct_reports']:
                    direct_report['_id'] = uuid.UUID(direct_report['_id'])
                try:
                    user = admin_model.User.objects.get(pk=_id)  # pylint: disable=no-member
                    user.type = 'SSO'
                    user.updated_at = utc_now()
                except DoesNotExist:
                    user = admin_model.User(
                        _id=_id,
                        created_at=utc_now(),
                    )
                user.disabled = result['disabled']
                user.username = result['username']
                user.email = result['email']
                user.is_employee = result['is_employee']
                user.name = result['name']
                user.english_name = result['english_name']
                user.title = result['title']
                user.dept = result['dept']
                user.manager = result['manager']
                user.is_manager = result['is_manager']
                user.direct_reports = result['direct_reports']
                user.city = result['city']
                user.immutable_groups = result['groups']
                user.save()
        else:
            task_result.add_log(
                f'Failed to get users (sso_response={r.text})',
                task_model.LogLevel.WARNING)
            task_result.result = task_model.TaskResultStatus.FAILURE
    groups_api_url = sso_settings.groups_api_url
    if groups_api_url:
        r = requests.get(
            groups_api_url, verify=sso_settings.verify_certificate,
            headers={'Authorization': 'Bearer ' + access_token})
        if r.ok:
            group_results = r.json()
            for result in group_results:
                _id = uuid.UUID(result['_id'])
                try:
                    group = admin_model.Group.objects.get(pk=_id)  # pylint: disable=no-member
                    group.type = 'SSO'
                    group.updated_at = utc_now()
                except DoesNotExist:
                    group = admin_model.Group(
                        _id=_id,
                        created_at=utc_now(),
                    )
                group.name = result['name']
                group.save()
        else:
            task_result.add_log(
                f'Failed to get groups (sso_response={r.text})',
                task_model.LogLevel.WARNING)
            task_result.result = task_model.TaskResultStatus.FAILURE

    def generate_organization_tree(org_data):
        _id = uuid.UUID(org_data['_id'])
        org_data['_id'] = _id
        if org_data['type'] == 'Group':
            children = []
            org_node = admin_model.Organization(
                _id=_id,
                name=org_data['name'],
                type=admin_model.OrganizationNodeType.GROUP,
                path=org_data['path'],
                children=children,
                updated_at=utc_now(),
            )
            for child_data in org_data['children']:
                generate_organization_tree(child_data)
                children.append(child_data)
        else:
            org_node = admin_model.Organization(
                _id=_id,
                name=org_data['name'],
                type=admin_model.OrganizationNodeType.PERSON,
                path=org_data['path'],
                updated_at=utc_now(),
            )
        org_node.save()
        return org_node

    organization_api_url = sso_settings.organization_api_url
    if organization_api_url:
        r = requests.get(
            organization_api_url, verify=sso_settings.verify_certificate,
            headers={'Authorization': 'Bearer ' + access_token})
        if r.ok:
            org_result = r.json()
            generate_organization_tree(org_result)
        else:
            task_result.add_log(
                f'Failed to get organization (sso_response={r.text})',
                task_model.LogLevel.WARNING)
            task_result.result = task_model.TaskResultStatus.FAILURE

    logout_api_url = sso_settings.get('logout_api_url')
    if logout_api_url:
        r = requests.post(
            logout_api_url, verify=sso_settings.get('verify_certificate'),
            headers={'Authorization': 'Bearer ' + access_token})
        if r.ok:
            response = r.json()
            if response.get('error_code') == 20000:
                task_result.add_log('Logged out SSO')
            else:
                task_result.add_log('Failed to log out SSO', task_model.LogLevel.WARNING)
        else:
            task_result.add_log('Failed to log out SSO', task_model.LogLevel.WARNING)
    task_result.result = task_model.TaskResultStatus.SUCCESS
