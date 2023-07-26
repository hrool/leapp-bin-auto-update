# -*- coding: utf-8 -*-
import logging
import requests
from requests.exceptions import ConnectTimeout, RequestException

from alibabacloud_oos20190601.client import Client as oos20190601Client
from alibabacloud_tea_openapi import models as open_api_models
from alibabacloud_oos20190601 import models as oos_20190601_models
from alibabacloud_tea_util import models as util_models


logger = logging.getLogger()

def get_github_latest_version():
  try:
    response = requests.get('https://api.github.com/repos/Noovolari/leapp/releases/latest', timeout=5)
    # Consider any status other than 2xx an error
    if not response.status_code // 100 == 2:
      logger.info(f"Error: Unexpected response {response}")
      return None
    latest_release_info = response.json()
    if latest_release_info['draft'] != True and latest_release_info['prerelease'] != True:
      return latest_release_info['name']
  except ConnectTimeout:
    logger.info('Request has timed out')
  except RequestException as e:
    logger.info(f'RequestException occurred: {e}')

def get_aur_version_list(client):
  list_parameter_versions_request = oos_20190601_models.ListParameterVersionsRequest(
    name='leapp-bin/version',
    max_results=100)
  runtime = util_models.RuntimeOptions()
  try:
    resp = client.list_parameter_versions_with_options(list_parameter_versions_request, runtime)
    if resp.status_code == 200:
      return [ version.value for version in resp.body.parameter_versions ]
  except Exception as error:
    if error.code == 'EntityNotExists.Parameter':
      logger.info('oos leapp-bin/version not exist. create the Parameter now...')
      create_parameter_request = oos_20190601_models.CreateParameterRequest(name='leapp-bin/version', type='String', value='0.0.0')
      try:
        client.create_parameter_with_options(create_parameter_request, runtime)
        logger.info('Parameter created.')
        return ['0.0.0']
      except Exception as error:
        raise Exception(error.message)
    else:
      raise Exception(error.message)
  
def update_aur_package(version, client):
  update_parameter_request = oos_20190601_models.UpdateParameterRequest(name='leapp-bin/version', value=version)
  runtime = util_models.RuntimeOptions()
  try:
    client.update_parameter_with_options(update_parameter_request, runtime)
    logger.info('aur version updated success!')
  except Exception as error:
    raise Exception(error.message)

def handler(event, context):
  github_latest_version = get_github_latest_version()
  if github_latest_version:
    logger.info(f'The latest github release of leapp is: {github_latest_version}')
  else:
    raise Exception('could not get the github latest release!')
  creds = context.credentials
  config = open_api_models.Config(
    access_key_id=creds.access_key_id,
    access_key_secret=creds.access_key_secret,
    security_token=creds.security_token,
    type='sts'
  )
  config.endpoint = f'oos.cn-hongkong.aliyuncs.com'
  client = oos20190601Client(config)
  aur_version_list = get_aur_version_list(client)
  if not aur_version_list:
    raise Exception('could not get the aur version list!')
  if github_latest_version in aur_version_list:
    logger.info('The latest github release has already synced to aur.')
    return True
  else:
    logger.info(f'aur version should be updated to {github_latest_version}')
    update_aur_package(github_latest_version, client)
