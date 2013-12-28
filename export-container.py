#!/usr/bin/python
import sys
import io
import shutil
import configparser
import os
import subprocess
from subprocess import call

docker_path = '/var/lib/docker/'
docker_init_path = docker_path + "init/"
containers_path = docker_path + 'containers/'


class Container:

    def __init__(self, container_id, container_name):
        self.id = container_id
        self.name = container_name
        self.short_name = container_id[:12]
        self.path = containers_path + container_id
        self.config = containers_path + container_id + '/config.lxc'
        self.rootfs_path = None
        self.init_rootfs_path = None

    def is_valid_container(self):
        self.container_name_exists()
        self.container_folder_exists()
        self.lxc_rootfs_exists()

    def container_name_exists(self):
        container_name_exists = os.path.isdir(self.name)
        if container_name_exists:
            raise Exception('Container name already exists')

    def container_folder_exists(self):
        container_exists = os.path.isdir(self.path)
        print('Container exists [{:s}]? {:s}'.format(self.path, str(container_exists)))
        if not container_exists:
            raise Exception('Container folder not found')

    def lxc_rootfs_exists(self):
        lines = tuple(open(self.config, 'r'))
        rootfs = None
        for line in lines:
            if line.startswith('lxc.rootfs ='):
                rootfs = line
                break

        if rootfs == None:
            raise Exception('lxc.rootfs not found')

        equal_index = rootfs.index('=') + 1
        rootfs_value = rootfs[equal_index:]
        self.rootfs_path = rootfs_value.strip()

        rootfs_exists = os.path.isdir(self.rootfs_path)
        print('Rootfs exists [{:s}]? {:s}'.format(self.rootfs_path, str(rootfs_exists)))
        if not rootfs_exists:
            raise Exception('Rootfs folder not found')

        self.init_rootfs_path = self.rootfs_path.replace(self.id, self.id + '-init')
        init_rootfs_exists = os.path.isdir(self.init_rootfs_path)
        print('Init-rootfs exists [{:s}]? {:s}'.format(self.init_rootfs_path, str(rootfs_exists)))
        if not init_rootfs_exists:
            raise Exception('Init rootfs folder not found')


class Exporter:

    def __init__(self, container):
        self.container = container
        self.allowed_mount_config = [
            'proc',
            'sysfs',
            'devpts',
            'shm',
            '/etc/resolv.conf',
            ]

    def copy(self):
        os.mkdir(self.container.name, 0o755)
        self.copy_init_rootfs()
        self.copy_config_files()
        self.copy_dockerinit()
        self.create_run_script()

    def copy_dockerinit(self):
        version = self.get_docker_version()
        if version == None:
            raise Exception("Docker version not found")

        shutil.copyfile(docker_init_path + 'dockerinit-' + version,
                        self.container.name + '/rootfs/.dockerinit')

    def get_docker_version(self):
        cmd = subprocess.Popen('docker version', shell=True, stdout=subprocess.PIPE)
        version = None
        for line in cmd.stdout:
            line_str = str(line, encoding='utf8')
            if "Client version:" in line_str:
                return line_str[16:len(line_str) - 1]
        return None

    def copy_init_rootfs(self):
        print('Copying rootfs...')
        # shutil.copytree(self.container.init_rootfs_path, self.container.name + "/rootfs")
        call(['cp', '-rp', self.container.init_rootfs_path, self.container.name + '/rootfs'])

    def copy_config_files(self):
        print('Copying config files...')
        shutil.copyfile(self.container.path + '/config.lxc',
                        self.container.name + '/config.lxc.template1')
        shutil.copyfile(self.container.path + '/config.env',
                        self.container.name + '/rootfs/.dockerenv')
        shutil.copyfile(self.container.path + '/hostname',
                        self.container.name + '/rootfs/etc/hostname')
        shutil.copyfile(self.container.path + '/hosts',
                        self.container.name + '/rootfs/etc/hosts')

        call(['sed', '-i', 's/' + self.container.short_name + '/'
             + self.container.name + '/g', self.container.name
             + '/rootfs/etc/hostname'])

        call(['sed', '-i', 's/' + self.container.short_name + '/'
             + self.container.name + '/g', self.container.name
             + '/rootfs/etc/hosts'])

        call(['sed', '-i', 's,' + self.container.rootfs_path
             + ',{container_path}/rootfs,g', self.container.name
             + '/config.lxc.template1'])

        with open(self.container.name + '/config.lxc.template', 'w') as template:
            with open(self.container.name + '/config.lxc.template1', 'r') as template1:
                for line in template1:
                    if self.is_allowed_line(line):
                        template.write(line)

        os.remove(self.container.name + '/config.lxc.template1')

    def is_allowed_line(self, line):
        # FIXME remove blank lines and comments
        if not line.startswith('lxc.mount.entry'):
            return True
        for row in self.allowed_mount_config:
            if line.startswith('lxc.mount.entry = ' + row):
                return True
        return False

    def create_run_script(self):
        print('Creating run script...')
        content = self.get_run_script_template().replace('{name}', self.container.name)
        with open(self.container.name + '/run.sh', 'w') as f:
            f.write(content)
        os.chmod(self.container.name + '/run.sh', 0o755)

    def get_run_script_template(self):
        return """#!/bin/bash

var_path=`pwd`
cp config.lxc.template config.lxc
sed -i "s,{container_path},$var_path,g" config.lxc
lxc-start -n {name} -f config.lxc -- /.dockerinit -g 172.17.42.1 -i 172.17.0.18/16 -- bash
"""

def main():
    print('Exporting docker container to a self-contained runnable lxc container')

    if len(sys.argv) != 3:
        raise Exception('Invalid arguments')

    container_id = sys.argv[1]
    container_name = sys.argv[2]
    print('Container id: ', container_id)
    print('Container name: ', container_name)

    container = Container(container_id, container_name)
    container.is_valid_container()

    exporter = Exporter(container)
    exporter.copy()


if __name__ == '__main__':
    main()
