#! /usr/bin/env python3.3

import sys, io
import configparser, os

containers_path = '/var/lib/docker/containers/'

class Container:
	def __init__(self, container_id):
		self.container_id = container_id
		self.container_path = containers_path + container_id
		self.container_config = containers_path + container_id + '/config.lxc'

	def is_valid_container(self):
		self.container_folder_exists()
		self.lxc_rootfs_exists()

	def container_folder_exists(self):
		container_exists = os.path.isdir(self.container_path)
		print("Container exists [{:s}]? {:s}".format(self.container_path, str(container_exists)))
		if not container_exists:
			raise Exception("Container folder not found")

	def lxc_rootfs_exists(self):
		lines = tuple(open(self.container_config, 'r'))
		rootfs = None
		for line in lines:
			if line.startswith('lxc.rootfs ='):
				rootfs = line
				break;

		if rootfs == None:
			raise Exception("lxc.rootfs not found")

		equal_index = rootfs.index("=") + 1
		rootfs_value = rootfs[equal_index:]
		self.rootfs_path = rootfs_value.strip()

		rootfs_exists = os.path.isdir(self.rootfs_path)
		print("Rootfs exists [{:s}]? {:s}".format(self.rootfs_path, str(rootfs_exists)))
		if not rootfs_exists:
			raise Exception("Rootfs folder not found")

		self.init_rootfs_path = self.rootfs_path.replace(container_id, container_id + "-init")
		init_rootfs_exists = os.path.isdir(self.init_rootfs_path)
		print("Init-rootfs exists [{:s}]? {:s}".format(self.init_rootfs_path, str(rootfs_exists)))
		if not init_rootfs_exists:
			raise Exception("Init rootfs folder not found")


print("Exporting docker container to a self-contained runnable lxc container")

if len(sys.argv) != 2:
	raise Exception("Invalid arguments")

container_id = sys.argv[1]
print("Container id: ", container_id)

container = Container(container_id)

container.is_valid_container()


