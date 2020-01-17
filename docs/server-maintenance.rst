==================
Server maintenance
==================

This part of the documentation contains info about things that need to be managed on the server
from command line.


-----------------------------
Switching to maintenance mode
-----------------------------

If you wish to do maintenance that disrupts the normal function of the website - such as database
maintenance, etc. - it is good to let the users know and disable the normal frontend.

To do this, there is a special ``maintenance.html`` page ready for you. You just have to swap
the normal ``index.html`` file in the static files deployment directory
(probably ``/var/www/html/celus/static/``) for the ``maintenance.html`` file:

>>> cp index.html index.html.bak
>>> cp maintenance.html index.html

Of course you may modify the ``maintenance.html`` page to provide more information to your users,
such as the expected time of recovery, etc.

Once you are done, just put the ``index.html.bak`` back to ``index.html`` and you are done.


.. _cli-management:

-------------------------------------
Using command line management scripts
-------------------------------------

There are a few thing for which you need to use the server's command line. These mostly involve
running Django management commands. Because `Celus` is installed in its own virtual Python
environment, you need to activate it first in order for the commands to work properly.

For this purpose, the Ansible installation playbook creates the file ``activate_virtualenv.sh``
under ``/root``. In order to activate the virtual environment, you must "source" this file:

>>> source activate_virtualenv.sh

After that, you should see the string ``(celus)`` in front of the command line prompt. This shows
that the ``celus`` virtual environment is active. After that you may issue Django management
commands:

>>> cd /opt/celus/
>>> python manage.py XXX

where ``XXX`` is the name of the command.

**Note**: Running ``python manage.py`` alone is a good way to test that everything works well and
there are no configuration problems.


---------------
Backing up data
---------------

There are two important locations of data that `Celus` uses and that you might want to back up:

* the database
* the media directory, which contains all the downloaded SUSHI reports

By default the database is called ``celus`` and the media directory is located under
``/var/www/celus/``. If you modified the installation playbook, it might be different in your case.

For convenience, the ansible installation playbook creates a Cron script for you that creates
daily backups in the ``/root/backup/``. The backups are compressed using the fast
`Zstandard <https://github.com/facebook/zstd>`_ compression algorithm. The contents of the database
is stored in files named ``celus-dump-YYYYmmdd.sql.zst``, the media files are stored in files named
``media-YYYYmmdd.tar.zst``, where ``YYYYmmdd`` is the date of the backup.

It is thus easy to backup the server just by copying the backup files from ``/root/backup/`` to a
separate location.


------------------------------
Restoring database from backup
------------------------------

If you need to restore the database from the backup file - either because of some mishap or to
clone the database on a different system - here is the way we use.

>>> su postgres
>>> dropdb celus   # this will delete the current celus database!
>>> createdb -O celus celus   # create new database celus owned by user celus
>>> zstd -dc name-of-backup-file.sql.zst | psql celus

The procedure above drops the database and creates a new one in order to make sure not residues
from possible previous database collide with data from the backup. All the commands are run as the
user ``postgres`` which is the standard way to work with database creation in PostgreSQL.
