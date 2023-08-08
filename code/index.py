# -*- coding: utf-8 -*-
import os,stat
import logging
import requests
from requests.exceptions import ConnectTimeout, RequestException

from alibabacloud_oos20190601.client import Client as oos20190601Client
from alibabacloud_tea_openapi import models as open_api_models
from alibabacloud_oos20190601 import models as oos_20190601_models
from alibabacloud_tea_util import models as util_models

from git import Repo
import tqdm
import hashlib

logger = logging.getLogger()
runtime = util_models.RuntimeOptions()

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

def download(url: str, filename: str):
  with open(filename, 'wb') as f:
    with requests.get(url, stream=True) as r:
      r.raise_for_status()
      total = int(r.headers.get('content-length', 0))

      # tqdm has many interesting parameters. Feel free to experiment!
      tqdm_params = {
        'desc': url,
        'total': total,
        'miniters': 1,
        'unit': 'B',
        'unit_scale': True,
        'unit_divisor': 1024,
      }
      with tqdm.tqdm(**tqdm_params) as pb:
        for chunk in r.iter_content(chunk_size=8192):
          pb.update(len(chunk))
          f.write(chunk)

def update_aur_package(version, client):
  # get ssh key from oos parameter
  get_secret_parameter_request = oos_20190601_models.GetSecretParameterRequest(name='leapp-bin/aur-ssh-key', with_decryption=True)
  try:
    resp = client.get_secret_parameter_with_options(get_secret_parameter_request, runtime)
    if resp.status_code == 200:
      with open('aur-ssh-key', 'w') as f:
        f.write(resp.body.parameter.value)
    else:
      raise Exception('couldS_IRUSR not get right oos parameter leapp-bin/aur-ssh-key!')
  except Exception as error:
    raise Exception(error.message)
  os.chmod('aur-ssh-key', stat.S_IRUSR)
  # clone git repo from aur
  ssh_cmd = 'ssh -i aur-ssh-key -o StrictHostKeyChecking=no'
  repo = Repo.clone_from('ssh://aur@aur.archlinux.org/leapp-bin.git', os.path.join(os.getcwd(), 'leapp-bin'),env=dict(GIT_SSH_COMMAND=ssh_cmd))
  # download latest version deb file and get the sha512sums
  file_name = f"Leapp_{version}_amd64.deb"
  download_url = f"https://asset.noovolari.com/{version}/Leapp_{version}_amd64.deb"
  download(download_url, file_name)
  with open(file_name, 'rb') as f:
    digest = hashlib.file_digest(f, "sha512")
  file_sha512sums = digest.hexdigest()
  # update files of git
  # update PKGBUILD
  with open('leapp-bin/PKGBUILD', 'r') as f:
    content = f.readlines()
  for index, line in enumerate(content):
    if "pkgver=" in line:
      content[index] = f"pkgver={version}\n"
    if "pkgrel=" in line:
      content[index] = f"pkgrel=1\n"
    if "source=(" in line:
      content[index] = f"source=({file_name}::https://asset.noovolari.com/{version}/{file_name})\n"
    if "sha512sums=(" in line:
      content[index] = f"sha512sums=({file_sha512sums})\n"
  with open('leapp-bin/PKGBUILD', 'w') as f:
    f.writelines(content)
  # update .SRCINFO
  with open('leapp-bin/.SRCINFO', 'r') as f:
    content = f.readlines()
  for index, line in enumerate(content):
    if "pkgver = " in line:
      content[index] = f"pkgver = {version}\n"
    if "pkgrel = " in line:
      content[index] = f"pkgrel = 1\n"
    if "source = " in line:
      content[index] = f"source = {file_name}::https://asset.noovolari.com/{version}/{file_name}\n"
    if "sha512sums = " in line:
      content[index] = f"sha512sums = {file_sha512sums}\n"
  with open('leapp-bin/.SRCINFO', 'w') as f:
    f.writelines(content)
  # commit and push aur git repo
  repo.config_writer().set_value("user", "name", "He Qing(robot)").release()
  repo.config_writer().set_value("user", "email", "qing@he.email").release()
  repo.index.add('leapp-bin/PKGBUILD')
  repo.index.add('leapp-bin/.SRCINFO')
  repo.index.commit(f"update version to {version}")
  repo.remotes.origin.push().raise_if_error()
  # update oos parameter version
  update_parameter_request = oos_20190601_models.UpdateParameterRequest(name='leapp-bin/version', value=version)
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
