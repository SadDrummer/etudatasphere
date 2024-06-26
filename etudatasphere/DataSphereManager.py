import requests
import json
from etudatasphere.exceptions import BadProjectRequest, BadStatusCode
from etudatasphere.utils import parse_projects, ProjectSettings


def request_iam_token(oauth_token):
    url = "https://iam.api.cloud.yandex.net/iam/v1/tokens"
    headers = {"Authorization": f"OAuth {oauth_token}"}
    payload = {"yandexPassportOauthToken": oauth_token}

    res = requests.post(url, headers=headers, json=payload)

    if res.status_code != 200:
        raise BadStatusCode(res.status_code, res.text)
    else:
        response_json = res.json()
        return response_json.get("iamToken")


class DataSphereManager:

    def __init__(self, oauth_token: str) -> None:
        iam_token = request_iam_token(oauth_token)
        self.HEADERS = {"Authorization": "Bearer {}".format(iam_token)}

    def __make_get_request(self, url, params=None):
        res = requests.get(url, headers=self.HEADERS, params=params)
        if res.status_code != 200:
            raise BadStatusCode(res.status_code, res.text)
        else:
            return res

    def __make_post_request(self, url, data):
        res = requests.post(url, headers=self.HEADERS, data=json.dumps(data))
        if res.status_code != 200:
            raise BadStatusCode(res.status_code, res.text)
        else:
            return res

    def __make_patch_request(self, url, data):
        res = requests.patch(url, headers=self.HEADERS, data=json.dumps(data))
        if res.status_code != 200:
            raise BadStatusCode(res.status_code, res.text)
        else:
            return res

    def get_organizations(self):
        '''
        Print a list of organizations avialable for the account
        '''
        
        url = "https://organization-manager.api.cloud.yandex.net/organization-manager/v1/organizations"
        res = self.__make_get_request(url)
        orgs = res.json()['organizations']

        for org in orgs:
            print('TITLE', org['title'])
            print('ID', org['id'])
            print('*' * 25)
    
    def get_clouds(self, organization_id: str = ''):
        '''
        organization_id: str - ID of organization
        
        Print a list of clouds in organization\n 
        If organization_id not specified print a list of all clouds in all organizations avialable for the account
        '''
        
        if organization_id:
            params = {
                "organizationId": organization_id
            }
        else:
            params = None
                
        url = "https://resource-manager.api.cloud.yandex.net/resource-manager/v1/clouds"
        res = self.__make_get_request(url, params)
        clouds = res.json()['clouds']
        
        for cloud in clouds:
            print('NAME', cloud['name'])
            print('CLOUD_ID', cloud['id'])
            print('ORGANIZATION_ID', cloud['organizationId'])
            print('*' * 25)

    def get_unit_balance(self, project_id):
        url = "https://datasphere.api.cloud.yandex.net/datasphere/v2/projects/{}:unitBalance".format(project_id)
        res = self.__make_get_request(url)
        return res.json()

    def get_billing_accounts(self):
        url = "https://billing.api.cloud.yandex.net/billing/v1/billingAccounts"
        res = self.__make_get_request(url)
        return res.json()

    def get_possible_ds_roles(self):
        url = "https://iam.api.cloud.yandex.net/iam/v1/roles"
        res = self.__make_get_request(url)
        roles = res.json()['roles']
        return [role for role in roles if 'datasphere' in role['id']]

    def get_organization_members(self, org_id: str):

        url = "https://organization-manager.api.cloud.yandex.net/organization-manager/v1/organizations/{}/users".format(
            org_id)
        res = self.__make_get_request(url)
        users = res.json()['users']
        for user in users:
            print('NAME', user['subjectClaims']['name'])
            print('ID', user['subjectClaims']['sub'])
            print('*' * 25)

    def get_organization_communities(self, organization_id: str):
        url = "https://datasphere.api.cloud.yandex.net/datasphere/v2/communities"
        params = {
            "organizationId": organization_id
        }
        res = self.__make_get_request(url, params)
        return res.json()

    def create_project(self,
                       community_id: str,
                       name: str,
                       description: str = None,
                       vmInactivityTimeout: str = "1800s"):
        data = ProjectSettings(
            community_id=community_id,
            name=name,
            description=description,
            vmInactivityTimeout=vmInactivityTimeout
        ).to_dict()
        url = "https://datasphere.api.cloud.yandex.net/datasphere/v2/projects"
        res = self.__make_post_request(url, data)
        return res.json()

    def check_operation_status(self, id_operation: str):
        url = "https://operation.api.cloud.yandex.net/operations/{}".format(id_operation)
        res = self.__make_get_request(url)
        return res.json()

    def get_projects(self, project_id: str = None, community_id: str = None, parse_projects_flag=False):
        if (community_id and project_id) or (
                (not project_id) and (not community_id)
        ):
            raise BadProjectRequest(community_id, project_id)

        if community_id:
            params = {
                "communityId": community_id
            }
        else:
            params = None
        url = "https://datasphere.api.cloud.yandex.net/datasphere/v2/projects/{}".format(
            project_id if project_id else "")
        res = self.__make_get_request(url, params)
        if parse_projects_flag:
            return parse_projects(res.json())
        else:
            return res.json()

    def add_contributors(self, project_id, contributors: list[dict]):
        """
        project_id: str - ID of project
        contributors: list[dict] - The list of contributors to add
            format:
                [
                    {
                    "id": "aje3e6pnq1io5fe801d3",
                    "role":"datasphere.communities.admin"
                    },
                    {
                    "id": "ajebni1dr6lgce3jkl3d",
                    "role": "datasphere.communities.admin"
                    }
                ]
        """

        if not contributors:
            return 'No participants selected'
        else:
            data = {'accessBindings': []}

            for user in contributors:
                data['accessBindings'].append({
                    "roleId": user['role'],
                    "subject": {
                        "id": user['id'],
                        "type": "userAccount"
                    }
                })
        url = "https://datasphere.api.cloud.yandex.net/datasphere/v2/projects/{}:setAccessBindings". \
            format(project_id)

        res = self.__make_post_request(url, data)
        return res.json()

    def update_unit_balance(self, project_id, new_unit_balance):
        url = "https://datasphere.api.cloud.yandex.net/datasphere/v2/projects/{}:unitBalance".format(project_id)
        data = {"unitBalance": new_unit_balance}
        res = self.__make_post_request(url, data)
        return res.json()

    def update_all_community_projects(self,
                                      community_id: str,
                                      vmInactivityTimeout: str = "1000s",
                                      unit_balance: int = None):
        data = ProjectSettings(
            vmInactivityTimeout=vmInactivityTimeout
        ).to_dict()

        projects = self.get_projects(community_id=community_id)

        updateMask_list = []
        for k, v in data.items():
            for n in v.keys():
                updateMask_list.append(f"{k}.{n}")
        data['updateMask'] = ', '.join(updateMask_list)

        try:
            for idx, project in enumerate(projects['projects']):
                print(f"{idx + 1}/{len(projects['projects'])}")
                url = "https://datasphere.api.cloud.yandex.net/datasphere/v2/projects/{}".format(project.get('id'))
                res = self.__make_patch_request(url, data)
                print('Operation id:', res.json()['id'])

                if unit_balance is not None:
                    self.update_unit_balance(project.get('id'), unit_balance)

            return 'ok'
        except Exception as e:
            raise e
