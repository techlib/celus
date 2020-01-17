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


-------------------------------------
Using command line management scripts
-------------------------------------

TODO
