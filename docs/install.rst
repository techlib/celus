============
Installation
============

This installation instructions manual is based on RHEL/CentOS 8.0 system. It should be possible
to use it with only minor adjustments on other Linux systems as well.

We recommend using a separate (virtual) machine for installation of Celus. The system is relatively
self-contained, but there may be some system wide changes made during the installation that might
conflict with other apps installed in parallel. For example, the system wide services ``celery``
and ``celerybeat`` will be created for `Celus`.


Please note that the install procedure is tailor made for deployment of Celus for the CzechELib
consortium. It might require extra effort to make it work in different environment. In case you
find something missing in the instructions, we welcome fixes - ideally in form of pull requests
on `Github <https://github.com/techlib/celus/>_`.


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
``example.com`` dir under ``host_vars/``. You can copy this configuration to your hosts config:

>>> cd host_vars
>>> cp -r example.com my.domain.org

The ``vars`` file in the ``example.com`` dir contains an annotated configuration. It explicitly
marks the things that you need to modify and the things that you might want to. There are some
things that are only for special cases where you know what you are doing and you should normally
not tweek these.


Running the playbook
--------------------

From the directory ``docs/ansible`` run the following command:

>>> ansible-playbook celus.yaml -i example.com,

*Note: mind the comma (,) after the name of the host.*

Of course replace the `example.com` name with the name of the system you are installing on.

Ansible will provide a nice output showing you what it is doing. If everything goes well,
all steps will go correctly and you will have most of the system set up.

If anything breaks during
the installation, Ansible will stop and provide you with relevant information. You can safely
re-run the playbook at any time after debugging the issue - the playbook is designed to skip steps
that were already successfully completed. However, be warned that changes that you make manually
on the deployment server may be overwritten by Ansible. This is especially true for modification
to files that Ansible created on the server.


Finalizing steps
================

While the provided Ansible playbook will perform most of the installation steps, there are a few
things that you need to do to finalize the install.


Configuring Apache
------------------

The playbook does not attempt to configure Apache (or other webserver) in any way as there are
many things that need to be set up there besides `Celus`. Below are examples of how we integrate
`Celus` with Apache.

Celus (as a Django application) uses WSGI to integrate with the server. We use the ``mod_wsgi``
Apache module to accomplish this. At first you need to install the module:

>>> yum install python3-mod_wsgi

Then you need to integrate `Celus` into your Apache configuration. We use the following config
in the ``VirtualHost`` part of config for our deployment::

    # Django stuff - mod_wsgi
    TimeOut 300
    WSGIScriptAlias /api /opt/celus/config/wsgi.py/api
    WSGIScriptAlias /wsEc67YNV2sq /opt/celus/config/wsgi.py/wsEc67YNV2sq
    WSGIDaemonProcess celus python-home=/opt/virtualenvs/celus/ python-path=/opt/celus/ processes=8 threads=10
    WSGIProcessGroup celus

    <Directory /opt/celus/config>
    <Files production.wsgi>
    Require all granted
    </Files>
    </Directory>

    # Javascript routing needs the following
    FallbackResource /index.html

    Alias /media/ /var/www/celus/media/

If you use `shibboleth` for user authentication, you probably also need the following parts in
your config::

    <Location />
      AuthType shibboleth
      ShibRequestSetting requireSession true
      require valid-user

      RequestHeader set "X-User-Id" "%{accountID}e"
      RequestHeader set "X-Full-Name" "%{givenName}e %{sn}e"
      RequestHeader set "X-First-Name" "%{givenName}e"
      RequestHeader set "X-Last-Name" "%{sn}e"
      RequestHeader set "X-User-Name" "%{uid}e"
      RequestHeader set "X-Mail" "%{mail}e"
      RequestHeader set "X-cn" "%{cn}e"
      RequestHeader set "X-Roles" "%{ntkRole}e"
      RequestHeader set "X-Identity" "%{eppn}e"
    </Location>

    <Location /api>
      AuthType shibboleth
      # when requireSession is false, 401 is returned instead of 302 which is good for the API
      ShibRequestSetting requireSession false
      require valid-user
    </Location>


We also recommend to turn on response compression. For example like this::

    <IfModule mod_deflate.c>
      # Compress HTML, CSS, JavaScript, Text, XML and fonts
      AddOutputFilterByType DEFLATE application/javascript
      AddOutputFilterByType DEFLATE application/json
      AddOutputFilterByType DEFLATE application/xhtml+xml
      AddOutputFilterByType DEFLATE application/xml
      AddOutputFilterByType DEFLATE image/svg+xml
      AddOutputFilterByType DEFLATE image/x-icon
      AddOutputFilterByType DEFLATE text/css
      AddOutputFilterByType DEFLATE text/html
      AddOutputFilterByType DEFLATE text/javascript
      AddOutputFilterByType DEFLATE text/plain
      AddOutputFilterByType DEFLATE text/xml

      # Remove browser bugs (only needed for really old browsers)
      BrowserMatch ^Mozilla/4 gzip-only-text/html
      BrowserMatch ^Mozilla/4\.0[678] no-gzip
      BrowserMatch \bMSIE !no-gzip !gzip-only-text/html
      Header append Vary User-Agent
    </IfModule>


Creating initial superuser account
----------------------------------

In order to log in into the `Celus` administration system, where you can configure most of the
system, like add users, define report types, etc., you need a superuser account. To create one,
you need to use the command line on the server and a Django management command ``createsuperuser``:

>>> cd /root/
>>> source activate_virtualenv.sh
>>> cd /opt/celus
>>> python manage.py createsuperuser

You will be prompted for the username, email and password of the superuser.

**Note**: You can read more about the Django management commands and the activation of python
virtual environment in :ref:`cli-management`.


Loading initial data into the database
--------------------------------------

In `Celus` many parts of the system are not hard-coded but driven by the configuration stored in
the application database. Just after installation this database is empty and thus many essential
pieces are missing, such as the definitions of report types, data dimensions, etc.

Because bootstrapping the whole system manually would be a lot of work which would be the same
between installs, we provide basic set of reports, dimensions, etc. with `Celus`. This data
are meant to be used only once for bootstrapping the system. If you have already made your own
changes in the system database, you could lose data by repeating the procedure described below,
so be careful.

Similarly to superuser account creation, this procedure involves :ref:`cli-management`.

Assuming you are in the ``/opt/celus`` installation directory, just run:

>>> python manage.py loaddata data/initial-data.json

You will be presented with a report that objects have been installed from the fixture.
