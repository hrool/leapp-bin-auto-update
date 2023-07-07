# -*- coding: utf-8 -*-
import logging
import requests
from requests.exceptions import ConnectTimeout, RequestException

logger = logging.getLogger()

def get_github_latest_version():
  try:
    response = requests.get('https://api.github.com/repos/Noovolari/leapp/releases/latest', timeout=5)
    # Consider any status other than 2xx an error
    if not response.status_code // 100 == 2:
      return "Error: Unexpected response {}".format(response)
    latest_release_info = response.json()
    if latest_release_info['draft'] != True and latest_release_info['prerelease'] != True:
      return latest_release_info['name']
    else:
      return None
  except ConnectTimeout:
    logger.info('Request has timed out')
  except RequestException as e:
    logger.info(f'RequestException occurred: {e}')

def get_aur_version_list():
  pass

def update_aur_package(version):
  pass

def handler(event, context):
  github_latest_version = get_github_latest_version()
  if github_latest_version:
    logger.info(f'The latest github release of leapp is: {github_latest_version}')
  else:
    raise Exception('could not get the github latest release!')
  aur_version_list = get_aur_version_list()
  if not aur_version_list:
    raise Exception('could not get the aur version list!')
  if github_latest_version in aur_version_list:
    logger.info('The latest github release has already synced to aur.')
  else:
    update_aur_package(github_latest_version)
  return True
