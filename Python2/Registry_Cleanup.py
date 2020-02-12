"""
Azure Automation documentation : https://aka.ms/azure-automation-python-documentation
Azure Python SDK documentation : https://aka.ms/azure-python-sdk
"""

#This script will remove all images from all repositories from the targeting the docker registry. The possibility of bypass parameters included.


import automationassets
from azure.keyvault import KeyVaultClient
from azure.common.credentials import ServicePrincipalCredentials
import os.path
import requests
import json
import sys
from requests.auth import HTTPBasicAuth
import argparse

# Get credential for Automation Account
cred = automationassets.get_automation_credential("CHANGE_ME")
user = cred["username"]
password = cred["password"]

#Setup settings for Azure Key-Vault
ACR_ADMIN_PWD = 'ADMIN-PASSWORD'
ACR_ADMIN_USR = 'ADMIN-USERNAME'
URL_KEY_VAULT = 'https://CHANGE_ME.vault.azure.net/'
TENANT_ID_VAR = 'CHANGE_ME'
URL_DOCKER_REGISTRY = 'https://CHANGE_ME.azurecr.io/v2/'

# Get keys from Azure key-vault
credentials = ServicePrincipalCredentials(user, password, tenant=TENANT_ID_VAR)
client = KeyVaultClient(credentials)
# Get version of key for PASSWORD
admin_password_version = list(client.get_secret_versions(URL_KEY_VAULT, ACR_ADMIN_PWD))
path = admin_password_version[0].as_dict().get('id')
admin_password_version = os.path.split(path)[1]
admin_password = client.get_secret(URL_KEY_VAULT, ACR_ADMIN_PWD, admin_password_version).value
# Get version of key for USERNAME
admin_user_version = list(client.get_secret_versions(URL_KEY_VAULT, ACR_ADMIN_USR))
path = admin_user_version[0].as_dict().get('id')
admin_user_version = os.path.split(path)[1]
admin_user = client.get_secret(URL_KEY_VAULT, ACR_ADMIN_USR, admin_user_version).value

## Parse arguments. Will be used Azure Settings as default.
parser = argparse.ArgumentParser(description='Prepare to cleanup Docker Container Registry by API requests')
parser.add_argument('-l', '--url',
                    dest='url',
                    default=URL_DOCKER_REGISTRY,
                    required=False,
                    help='URL for access Registry')
parser.add_argument('-u', '--user',
                    dest='username',
                    default=admin_user,
                    required=False,
                    help='Username to access Container Registry')
parser.add_argument('-p', '--password',
                    dest='password',
                    default=admin_password,
                    required=False,
                    help='Password for user')
parser.add_argument('-c', '--count',
                    dest='img_count',
                    default=5,
                    required=False,
                    help='How many images can be stored?')
args = parser.parse_args()
url = args.url
user = args.username
password = args.password
img_count = int(args.img_count)

auth = HTTPBasicAuth(user, password)

def main():
    ## Preparing to iterate by repositories and create an empty dicts.
    requests.get(url, auth=auth)
    headers = {'Accept': 'application/vnd.docker.distribution.manifest.v2+json'}
    repositories = requests.get(url + '_catalog', auth=auth).json()
    unsorted_dict = {}
    sorted_dict = {}

    ## Preparing a new dictionary with image name, tag and a timestamp.
    def get_tags(repo_to_tgs):
        for i in repo_to_tgs.get('repositories'):
            tgz = requests.get(url + i + '/tags/list', auth=auth).json().get('tags')
            if i in unsorted_dict and len(unsorted_dict.get(i)) != 0:
                pass
            else:
                unsorted_dict[i] = []
            for j in range(len(tgz)):
                response = requests.get(url + i + '/manifests/' + tgz[j], auth=auth, headers=headers)
                digest = response.headers.get('Docker-Content-Digest')
                response = requests.get(url + i + '/manifests/' + tgz[j], auth=auth).json()
                timestamp = json.loads(response.get('history')[0].get('v1Compatibility')).get('created')
                unsorted_dict.get(i).append({'tag': tgz[j], 'timestamp': timestamp, 'digest': digest})
        return unsorted_dict

    ## Sorting by timestamp.
    def sort_dict_time(to_be_sorted):
        for i in to_be_sorted.keys():
            newlist = sorted(to_be_sorted.get(i), key=lambda k: k['timestamp'])
            sorted_dict[i] = newlist
        return sorted_dict

    ## Preparing a dictionary with images that have to be deleted. Removing from the list images that have to be saved.
    def dict_to_remove(to_be_deleted):
        for i in to_be_deleted.keys():
            del to_be_deleted.get(i)[-img_count:]

    ## Removing images of the sorted dictionary. The keys with an empty list will be excluded from iteration.
    def remove_img(to_be_removed):
        for i in to_be_removed.keys():
            if len(to_be_removed.get(i)) == 0:
                sys.stdout.write('There are no images under the scope in ' + i + ' repo.\n')
            elif len(to_be_removed.get(i)) > 0:
                for j in range(len(sorted_dict.get(i))):
                    tgz = sorted_dict.get(i)[j].get('tag')
                    digest = sorted_dict.get(i)[j].get('digest')
                    try:
                        response = requests.delete(url + i + '/manifests/' + digest, auth=auth)
                        if response.status_code == 202:
                            sys.stdout.write('Deleting image ' + i + ': ' + tgz + ' succeeded with status code ' + str(response.status_code) + '\n')
                        elif response.status_code != 202:
                            sys.stdout.write('Deleting image ' + i + ': ' + tgz + ' failed with status code ' + str(response.status_code) +  '. Error message: ' + response.text + '\n')
                    except requests.exceptions.RequestException as error:
                        return sys.stderr.write(error)
                        sys.exit(1)

    get_tags(repositories)

    sort_dict_time(unsorted_dict)

    dict_to_remove(sorted_dict)

    remove_img(sorted_dict)


if __name__ == '__main__':
    main()

