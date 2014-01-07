export-docker
=============

Export a Docker container to a lxc container

How to use
----------

    sudo ./export-container.py <container id> <new container name>

Example:

    $ sudo ./export-container.py f4e7e632964a registry
    Exporting Docker container to a lxc container
    Docker container id:  f4e7e632964a
    New container name:  registry
    Full container id  f4e7e632964a822bbd0e633b8ef8422c341d0b43d3e72a869c1154e461cf2302
    Container exists [/var/lib/docker/containers/f4e7e632964a822bbd0e633b8ef8422c341d0b43d3e72a869c1154e461cf2302]? True
    Rootfs exists [/var/lib/docker/devicemapper/mnt/f4e7e632964a822bbd0e633b8ef8422c341d0b43d3e72a869c1154e461cf2302/rootfs]? True
    Init-rootfs exists [/var/lib/docker/devicemapper/mnt/f4e7e632964a822bbd0e633b8ef8422c341d0b43d3e72a869c1154e461cf2302-init/rootfs]? True
    Copying rootfs...
    Copying config files...
    Creating run script...

    It's all done! Now just type:
    cd registry && sudo ./run.sh

Check the folder just created:

    $ find registry/ -maxdepth 2
    registry/
    registry/rootfs
    registry/rootfs/usr
    registry/rootfs/home
    ...
    registry/rootfs/tmp
    registry/rootfs/root
    registry/config.lxc.template
    registry/run.sh

* config.lxc.template: The lxc config file
* run.sh: Script to run the container
* rootfs/: Folder with all container files

To run:

    $ sudo ./run.sh
    root@f4e7e632964a:/#

Why
---

* To have a lxc container independent from Docker (docker0 network interface is the only dependency)
* To learn about lxc and Docker
* For fun :)
