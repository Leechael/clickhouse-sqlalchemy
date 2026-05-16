.. _development:

Development
===========

Test configuration
------------------

In ``setup.cfg`` you can find ClickHouse server ports, credentials and logging
level that can be tuned during local testing. Packaging and Python
dependencies are managed by PDM through ``pyproject.toml``.

The default test database is ``test-clickhouse-sqlalchemy``. Test setup drops
and recreates this database automatically, so it does not need to exist before
running the suite.

Local overrides can be placed in ``.env.test``. This file is intentionally
ignored by git. The following variables are recognized:

* ``TEST_CLICKHOUSE_URL``: base SQLAlchemy URL used to derive host, native
  port, user, password and database.
* ``TEST_CLICKHOUSE_HOST``
* ``TEST_CLICKHOUSE_PORT``
* ``TEST_CLICKHOUSE_HTTP_PORT``
* ``TEST_CLICKHOUSE_DATABASE``
* ``TEST_CLICKHOUSE_USER``
* ``TEST_CLICKHOUSE_PASSWORD``
* ``TEST_ENV_FILE``: path to an alternate dotenv file.

For example:

    .. code-block:: bash

        TEST_CLICKHOUSE_URL=clickhouse+asynch://default:@127.0.0.1:9000/test-clickhouse-sqlalchemy
        TEST_CLICKHOUSE_HTTP_PORT=8123

Tests set ``wait_for_async_insert=1`` on their ClickHouse sessions. This keeps
read-after-write assertions deterministic on servers where ``async_insert`` is
enabled globally.

Running tests locally
---------------------

Install desired Python version with system package manager/pyenv/another manager.

Install PDM, then install the project with development dependency groups:

    .. code-block:: bash

        python -m pip install pdm
        pdm install -G test -G lint -G coverage -G docs

Install the git hook runner:

    .. code-block:: bash

        pdm run prek install

Run all configured hooks manually:

    .. code-block:: bash

        pdm run prek-all

Run only format-fixing hooks:

    .. code-block:: bash

        pdm run fmt

ClickHouse on host machine
^^^^^^^^^^^^^^^^^^^^^^^^^^

Install desired versions of ``clickhouse-server`` and ``clickhouse-client`` on
your machine.

Run tests:

    .. code-block:: bash

        pdm run pytest -v

ClickHouse in docker
^^^^^^^^^^^^^^^^^^^^

Create container desired version of ``clickhouse-server``:

    .. code-block:: bash

        docker run --rm -p 127.0.0.1:9000:9000 -p 127.0.0.1:8123:8123 --name test-clickhouse-server clickhouse/clickhouse-server:$VERSION

Create container with the same version of ``clickhouse-client``:

    .. code-block:: bash

        docker run --rm --entrypoint "/bin/sh" --name test-clickhouse-client --link test-clickhouse-server:clickhouse-server clickhouse/clickhouse-client:$VERSION -c 'while :; do sleep 1; done'

Create ``clickhouse-client`` script on your host machine:

    .. code-block:: bash

        echo -e '#!/bin/bash\n\ndocker exec test-clickhouse-client clickhouse-client "$@"' | sudo tee /usr/local/bin/clickhouse-client > /dev/null
        sudo chmod +x /usr/local/bin/clickhouse-client

After it container ``test-clickhouse-client`` will communicate with
``test-clickhouse-server`` transparently from host machine.

Set ``host=clickhouse-server`` in ``setup.cfg`` or set
``TEST_CLICKHOUSE_HOST=clickhouse-server`` in ``.env.test``.

Add entry in hosts file:

    .. code-block:: bash

        echo '127.0.0.1 clickhouse-server' | sudo tee -a /etc/hosts > /dev/null

And run tests:

    .. code-block:: bash

        pdm run pytest -v

PDM installs the required test modules through the dependency groups above.

GitHub Actions in forked repository
-----------------------------------

Workflows in forked repositories can be used for running tests.

Workflows don't run in forked repositories by default.
You must enable GitHub Actions in the **Actions** tab of the forked repository.
