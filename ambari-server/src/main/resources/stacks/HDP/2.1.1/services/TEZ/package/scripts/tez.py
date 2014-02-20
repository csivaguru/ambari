#!/usr/bin/env python2.6
"""
Licensed to the Apache Software Foundation (ASF) under one
or more contributor license agreements.  See the NOTICE file
distributed with this work for additional information
regarding copyright ownership.  The ASF licenses this file
to you under the Apache License, Version 2.0 (the
"License"); you may not use this file except in compliance
with the License.  You may obtain a copy of the License at

    http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.

Ambari Agent

"""

from resource_management import *
import os

def tez():
  import params

  Directory(params.config_dir,
    owner = params.tez_user,
    group = params.user_group,
    recursive = True
  )

  XmlConfig( "tez-site.xml",
            conf_dir = params.config_dir,
            configurations = params.config['configurations']['tez-site'],
            owner = params.tez_user,
            group = params.user_group,
            mode = 0664
  )

  tez_TemplateConfig( ['tez-env.sh'])

  destination_hdfs_dirs = get_tez_hdfs_dir_paths(params.tez_lib_uris)

  # If tez libraries are to be stored in hdfs
  if destination_hdfs_dirs:
    for hdfs_dir in destination_hdfs_dirs:
      params.HdfsDirectory(hdfs_dir,
                          action="create_delayed",
                          owner=params.tez_user,
                          mode=0755
      )
    pass
    params.HdfsDirectory(None, action="create")

    if params.security_enabled:
      kinit_if_needed = format("{kinit_path_local} -kt {hdfs_user_keytab} {hdfs_user};")
    else:
      kinit_if_needed = ""

    if kinit_if_needed:
      Execute(kinit_if_needed,
              user=params.tez_user,
              path='/bin'
      )

    app_dir_path = None
    lib_dir_path = None

    if len(destination_hdfs_dirs) > 1:
      for path in destination_hdfs_dirs:
        if 'lib' in path:
          lib_dir_path = path
        else:
          app_dir_path = path
        pass
      pass
    pass

    if app_dir_path:
      copyFromLocal(path=params.tez_local_api_jars,
                    mode=0655,
                    owner=params.tez_user,
                    dest_dir=app_dir_path,
                    kinnit_if_needed=kinit_if_needed,
                    stub_path=params.stub_path
      )
    pass

    if lib_dir_path:
      copyFromLocal(path=params.tez_local_lib_jars,
                    mode=0655,
                    owner=params.tez_user,
                    dest_dir=lib_dir_path,
                    kinnit_if_needed=kinit_if_needed,
                    stub_path=params.stub_path
      )
    pass

    ExecuteHadoop(format('dfs -touchz {stub_path}'),
                  user = params.tez_user,
                  conf_dir=params.hadoop_conf_dir
    )


def tez_TemplateConfig(name):
  import params

  if not isinstance(name, list):
    name = [name]

  for x in name:
    TemplateConfig(format("{config_dir}/{x}"),
        owner = params.tez_user
    )

def get_tez_hdfs_dir_paths(tez_lib_uris = None):
  hdfs_path_prefix = 'hdfs://'
  lib_dir_paths = []
  if tez_lib_uris and tez_lib_uris.strip().find(hdfs_path_prefix, 0) != -1:
    dir_paths = tez_lib_uris.split(',')
    for path in dir_paths:
      lib_dir_path = path.replace(hdfs_path_prefix, '')
      lib_dir_path = lib_dir_path if lib_dir_path.endswith(os.sep) else lib_dir_path + os.sep
      lib_dir_paths.append(lib_dir_path)
    pass
  pass

  return lib_dir_paths


def copyFromLocal(path=None, owner=None, group=None, mode=None,
                  dest_dir=None, kinnit_if_needed="", stub_path=None):
  import params

  if not stub_path:
    stub_path = params.stub_path
  pass

  copy_cmd = format("fs -copyFromLocal {path} {dest_dir}")
  unless_cmd = format("{kinnit_if_needed} hadoop fs -ls {stub_path} >/dev/null 2>&1")

  ExecuteHadoop(copy_cmd,
                not_if=unless_cmd,
                user=owner,
                conf_dir=params.hadoop_conf_dir,
                ignore_failures = True)

  if not owner:
    chown = None
  else:
    if not group:
      chown = owner
    else:
      chown = format('{owner}:{group}')

  if not chown:
    chown_cmd = format("fs -chown {chown} {dest_dir}")

    ExecuteHadoop(copy_cmd,
                  user=owner,
                  conf_dir=params.hadoop_conf_dir)

  if not mode:
    chmod_cmd = format('fs -chmod {mode} {dest_dir}')

    ExecuteHadoop(chmod_cmd,
                  user=owner,
                  conf_dir=params.hadoop_conf_dir)