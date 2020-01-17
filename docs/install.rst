============
Installation
============

This installation instructions manual is based on RHEL/CentOS 8.0 system. It should be possible
to use it with only minor adjustments on other Linux systems as well.

Prerequisites
=============

Apache & shibboleth
-------------------

Installation instructions presume that `Apache` webserver is already installed and configured
to serve the hostname that you will use for the Celus system. In case `shibboleth` is used
for authentication, it should also be set up.


Python
------

`Celus` uses Python 3 (version 3.6 and above). As most of the installation procedure makes use
of `ansible` which depends on Python, you will also need Python to run the installation.

For `ansible` you can decide between Python 2 and Python 3. Python 2 is (at the time of writing
this) the default version of Python that `ansible` uses. To use Python 3, you have to configure
ansible with the ``ansible_python_interpreter`` variable se to ``/usr/bin/python3``.

So in case you decide to go with Python 3 only (**recommended**), install the ``python3`` package.

>>> yum install python3


SSH server
----------

In order to connect to the server, running SSH server is presumed.

>>> yum install openssh-server

It is also presumed that you can login to the server using SSH as the user ``root``.


Ansible
-------

The installation is mostly done automatically by `Ansible <https://www.ansible.com/>`_ using
a playbook which is part of the source code of `Celus`. In order to run the playbook, you
will need `Ansible` installed in version **at least 2.8**.


Installation with Ansible
=========================

The distribution of Celus contains an Ansible playbook ``celus`` (under the ``docs/ansible``
folder), which will set up most of the system for you. You just need to provide several
configuration options.

The ansible playbook will do the following:

* install a few system-wide prerequisites (git, virtualenv support, etc.)
* install the `celery` and `celerybeat` system-wide services - these are used for running
  background jobs like downloading SUSHI data, etc.
* install the Celus system from the git repository under ``/opt/celus/`` (you can configure the
  git branch you want to use)
* create PostgreSQL database for the Celus app with the configured username and password
* configure the Django installation
* create cron scripts in ``/etc/cron.daily/`` to backup the database and downloaded SUSHI data
  under ``/root/backup/`` directory.
* create script ``activate_virtualenv.sh`` in the ``/root/`` home directory.
  (Use ``. activate_virtualenv.sh`` to activate the virtual Python environment under which Celus is
  used when you want to run management commands from the command line on the server.)


Configuring the installation
----------------------------

There are a few configuration options you need to provide for `Ansible` to be able to set up your
system. The ``docs/ansible/`` directory contains the ``host_vars`` directory where configuration
for individual hosts lives. For each host that you wish to configure, you need to provide a
directory with the corresponding name and a ``vars`` file inside that.

For convenience, a sample configuration is provided with the `Celus` source code in the
``example.com`` dir under ``host_vars/``. You can copy this configuration to your hosts config::

    cd host_vars
    cp -r example.com my.domain.org

The ``vars`` file in the ``example.com`` dir contains an annotated configuration. It explicitly
marks the things that you need to modify and the things that you might want to. There are some
things that are only for special cases where you know what you are doing and you should normally
not tweek these.


Running the playbook
--------------------

From the directory ``docs/ansible`` run the following command::

    ansible-playbook celus.yaml -i example.com,

*Note: mind the comma (,) after the name of the host.*

Of course replace the `example.com` name with the name of the system you are installing on.


TODO + notes
============

Create symlink::

    /var/www/html/stats/static# ln -s ./ static


