#!/usr/bin/python
import sys
import io
import shutil
import configparser
import os
import subprocess
import argparse
from subprocess import call

docker_path = "/var/lib/docker"
docker_init_path = docker_path + "/init"
containers_path = docker_path + "/containers"


def sed(regexp, replacement, file):
    call(["sed", "-i", "s," + regexp + "," + replacement + ",g", file])

def copyfile(source, dest):
    shutil.copyfile(source, dest)


class Container:

    def __init__(self, container_id, container_name):
        self.id = self.get_full_id(container_id)
        self.name = container_name
        self.short_id = self.id[:12]
        self.path = containers_path + "/" + self.id
        self.config = containers_path + "/" + self.id + "/config.lxc"
        self.rootfs_path = None
        self.init_rootfs_path = None

    def get_full_id(self, container_id):
        if len(container_id) == 64:
            return container_id
        if len(container_id) < 12:
            raise Exception("Please enter at least 12 container ID characters")

        for container_dir in os.listdir(containers_path):
            if container_dir.startswith(container_id):
                print("Full container id ", container_dir)
                return container_dir

        raise Exception("Container not found")

    def is_valid_container(self):
        self.container_name_exists()
        self.container_folder_exists()
        self.lxc_rootfs_exists()

    def container_name_exists(self):
        container_name_exists = os.path.isdir(self.name)
        if container_name_exists:
            raise Exception("Container name already exists")

    def container_folder_exists(self):
        container_exists = os.path.isdir(self.path)
        print("Container exists [{:s}]? {:s}".format(self.path, str(container_exists)))
        if not container_exists:
            raise Exception("Container folder not found")

    def lxc_rootfs_exists(self):
        lines = tuple(open(self.config, "r"))
        rootfs = None
        for line in lines:
            if line.startswith("lxc.rootfs ="):
                rootfs = line
                break

        if rootfs == None:
            raise Exception("lxc.rootfs not found")

        equal_index = rootfs.index("=") + 1
        rootfs_value = rootfs[equal_index:]
        self.rootfs_path = rootfs_value.strip()

        rootfs_exists = os.path.isdir(self.rootfs_path)
        print("Rootfs exists [{:s}]? {:s}".format(self.rootfs_path, str(rootfs_exists)))
        if not rootfs_exists:
            raise Exception("Rootfs folder not found")

        self.init_rootfs_path = self.rootfs_path.replace(self.id, self.id + "-init")
        init_rootfs_exists = os.path.isdir(self.init_rootfs_path)
        print("Init-rootfs exists [{:s}]? {:s}".format(self.init_rootfs_path, str(init_rootfs_exists)))
        if not init_rootfs_exists:
            self.init_rootfs_path = None


class Exporter:

    def __init__(self, container):
        self.container = container
        self.allowed_mount_config = [
            "proc",
            "sysfs",
            "devpts",
            "shm",
            "/etc/resolv.conf",
            ]

    def copy(self):
        self.create_container_folder()
        self.copy_init_rootfs()
        self.copy_config_files()
        self.copy_dockerinit()
        self.create_run_script()

    def create_container_folder(self):
        os.mkdir(self.container.name, 0o755)

    def copy_dockerinit(self):
        version = self.get_docker_version()
        if version == None:
            raise Exception("Docker version not found")

        copyfile(docker_init_path + "/dockerinit-" + version, self.container.name + "/rootfs/.dockerinit")

    def get_docker_version(self):
        cmd = subprocess.Popen("docker version", shell=True, stdout=subprocess.PIPE)
        version = None
        for line in cmd.stdout:
            line_str = str(line, encoding="utf8")
            if "Client version:" in line_str:
                return line_str[16:len(line_str) - 1]
        return None

    def copy_init_rootfs(self):
        print("Copying rootfs...")
        # shutil.copytree(self.container.init_rootfs_path, self.container.name + "/rootfs")
        source = self.get_rootfs_path()
        call(["cp", "-rp", source, self.container.name + "/rootfs"])

    def get_rootfs_path(self):
        if self.container.init_rootfs_path != None:
            source = self.container.init_rootfs_path
        return self.container.rootfs_path

    def copy_config_files(self):
        print("Copying config files...")
        container = self.container
        root = container.name + "/rootfs"

        copyfile(container.path + "/hostname", root + "/etc/hostname")
        copyfile(container.path + "/hosts", root + "/etc/hosts")
        copyfile(container.path + "/config.lxc", container.name + "/config.lxc.template1")
        copyfile(container.path + "/config.env", root + "/.dockerenv")

        sed(container.short_id, container.name, root + "/etc/hostname")
        sed(container.short_id, container.name, root + "/etc/hosts")
        sed(container.rootfs_path, "{container_path}/rootfs", container.name + "/config.lxc.template1")

        with open(container.name + "/config.lxc.template", "w") as real_template:
            with open(container.name + "/config.lxc.template1", "r") as template1:
                for line in template1:
                    if not self.is_allowed_line(line):
                        real_template.write("#")
                    real_template.write(line)

        os.remove(container.name + "/config.lxc.template1")

    def is_allowed_line(self, line):
        if not line.startswith("lxc.mount.entry"):
            return True
        for allowed_mount_value in self.allowed_mount_config:
            if line.startswith("lxc.mount.entry = " + allowed_mount_value):
                return True
        return False

    def create_run_script(self):
        print("Creating run script...")
        content = self.get_run_script_template().replace("{name}", self.container.name)
        with open(self.container.name + "/run.sh", "w") as script:
            script.write(content)
        os.chmod(self.container.name + "/run.sh", 0o755)

    def get_run_script_template(self):
        return """#!/bin/bash

var_path=`pwd`
cp config.lxc.template config.lxc
sed -i "s,{container_path},$var_path,g" config.lxc

lxc-start -n {name} -f config.lxc -- /.dockerinit -g 172.17.42.1 -i 172.17.0.18/16 -- bash
"""

def main():
    print("Exporting docker container to a self-contained runnable lxc container")

    parser = argparse.ArgumentParser()
    parser.add_argument("docker_container_id", help="Docker container ID to export")
    parser.add_argument("new_container_name", help="New container name")
    args = parser.parse_args()

    print("Docker container id: ", args.docker_container_id)
    print("New container name: ", args.new_container_name)

    container = Container(args.docker_container_id, args.new_container_name)
    container.is_valid_container()

    exporter = Exporter(container)
    exporter.copy()

    print("\nIt's all done! Now just type:\ncd", args.new_container_name, "&& sudo ./run.sh")


if __name__ == "__main__":
    main()
