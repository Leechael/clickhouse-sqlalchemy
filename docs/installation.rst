.. _installation:

Installation
============

Python Version
--------------

Clickhouse-sqlalchemy supports Python 3.9 and newer.

Dependencies
------------

These distributions will be installed automatically when installing
clickhouse-sqlalchemy:

* `clickhouse-driver`_ ClickHouse Python Driver with native (TCP) interface support.
* `requests`_ a simple and elegant HTTP library.
* `asynch`_ An asyncio ClickHouse Python Driver with native (TCP) interface support.

.. _clickhouse-driver: https://pypi.org/project/clickhouse-driver/
.. _requests: https://pypi.org/project/requests/
.. _asynch: https://github.com/Leechael/asynch

If you are planning to use ``clickhouse-driver`` with compression you should
also install compression extras as well. See clickhouse-driver `documentation <https://clickhouse-driver.readthedocs.io>`_.

Installation from GitHub
------------------------

This fork is not published to PyPI yet. Install it directly from GitHub:

    .. code-block:: bash

       pip install "clickhouse-sqlalchemy @ git+https://github.com/Leechael/clickhouse-sqlalchemy.git@master"
