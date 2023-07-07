# -*- coding: utf-8 -*-
import logging
import requests
from requests.exceptions import ConnectTimeout, RequestException

logger = logging.getLogger()

def get_latest_version():
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
# To enable the initializer feature (https://help.aliyun.com/document_detail/158208.html)
# please implement the initializer function as below：
# def initializer(context):
#   logger = logging.getLogger()
#   logger.info('initializing')

def handler(event, context):
  release = get_latest_version()
  if release:
    logger.info(f'The latest release of leapp is: {release}')
    return release
  else:
    logger.info('could not get the right latest release!')
