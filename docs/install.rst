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

>>> yum install httpd

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


Installation with Ansible
=========================

The distribution of Celus contains an Ansible playbook ``celus`` which will set up most of the
system for you. You just need to provide several configuration options.

The ansible playbook will do the following:

* install a few system-wide prerequisites (git, virtualenv support, etc.)
* install the `celery` and `celerybeat` system-wide services - these are used for running
  background jobs like downloading SUSHI data, etc.
* install the Celus system from the git repository under ``/opt/celus/`` (you can configure the
  git branch you want to use)
* create PostgreSQL database for the Celus app
* configure the Django installation
* create cron scripts in ``/etc/cron.daily/`` to backup the database and downloaded SUSHI data
  under ``/root/backup/`` directory.
* create script ``activate_virtualenv.sh`` in the ``/root/`` home directory.
  (Use ``. activate_virtualenv.sh`` to activate the virtual Python environment under which Celus is
  used when you want to run management commands from the command line on the server.)






