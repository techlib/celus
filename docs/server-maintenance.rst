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
(probably ``/var/www/html/celus/static/``) for the ``maintenance.html`` file::

    cp index.html index.html.bak
    cp maintenance.html index.html

Of course you may modify the ``maintenance.html`` page to provide more information to your users,
such as the expected time of recovery, etc.

Once you are done, just put the ``index.html.bak`` back to ``index.html`` and you are done.


.. _cli-management
-------------------------------------
Using command line management scripts
-------------------------------------

There are a few thing for which you need to use the server's command line. These mostly involve
running Django management commands. Because `Celus` is installed in its own virtual Python
environment, you need to activate it first in order for the commands to work properly.

For this purpose, the Ansible installation playbook creates the file ``activate_virtualenv.sh``
under ``/root``. In order to activate the virtual environment, you must "source" this file::

    source activate_virtualenv.sh

After that, you should see the string ``(celus)`` in front of the command line prompt. This shows
that the ``celus`` virtual environment is active. After that you may issue Django management
commands::

    cd /opt/celus/
    python manage.py XXX

where ``XXX`` is the name of the command.

**Note**: Running ``python manage.py`` alone is a good way to test that everything works well and
there are no configuration problems.
