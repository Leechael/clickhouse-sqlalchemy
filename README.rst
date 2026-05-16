ClickHouse SQLAlchemy (Community Fork)
======================================

This is a maintained community fork of `clickhouse-sqlalchemy <https://github.com/xzkostyan/clickhouse-sqlalchemy>`_.

The upstream repository has been inactive for an extended period, while the
async driver path and newer SQLAlchemy releases accumulated breaking changes.
This fork exists to keep the dialect working for production users who depend on
ClickHouse with SQLAlchemy 2.0.

Notable differences from upstream
---------------------------------

- **Active maintenance** of the ``clickhouse+asynch`` async native (TCP) driver.
- **SQLAlchemy 2.0.44+ compatibility** via async cursor soft-close support.
- **DateTime64 precision preserved** for bound parameters in the async driver.
- **LEFT JOIN null semantics aligned** with SQLAlchemy expectations
  (``join_use_nulls=1`` default for the asynch dialect).
- **Autocommit transaction semantics** declared explicitly; ClickHouse does not
  provide general SQL transactions, and the dialect reflects that instead of
  pretending otherwise.
- **Maintained ``asynch`` dependency** pinned to the current
  ``Leechael/asynch`` upstream commit used by this fork.

Supported drivers
-----------------

- **native** (TCP) via `clickhouse-driver <https://github.com/mymarilyn/clickhouse-driver>`_
- **async native** (TCP) via the maintained `asynch <https://github.com/Leechael/asynch>`_
- **http** via requests

Installation
============

.. code-block:: bash

    pip install "clickhouse-sqlalchemy @ git+https://github.com/Leechael/clickhouse-sqlalchemy.git@master"

This fork is not published to PyPI yet. Install it directly from GitHub. The
async driver requires the maintained ``Leechael/asynch`` package, which is
declared as a pinned Git dependency in this fork's ``pyproject.toml``.

Usage
=====

SQLAlchemy 2.0 style (recommended)
----------------------------------

.. code-block:: python

    from sqlalchemy import create_engine, Column, MetaData, func
    from sqlalchemy.orm import declarative_base, Session

    from clickhouse_sqlalchemy import (
        Table, types, engines
    )

    uri = 'clickhouse+native://localhost/default'

    engine = create_engine(uri)
    metadata = MetaData()
    Base = declarative_base(metadata=metadata)

    class Rate(Base):
        __tablename__ = 'rate'

        day = Column(types.Date, primary_key=True)
        value = Column(types.Int32)

        __table_args__ = (
            engines.Memory(),
        )

    with engine.begin() as conn:
        Base.metadata.create_all(conn)

    with Session(engine) as session:
        from datetime import date, timedelta

        today = date.today()
        rates = [
            {'day': today - timedelta(i), 'value': 200 - i}
            for i in range(100)
        ]

        session.execute(Rate.__table__.insert(), rates)
        session.commit()

        count = session.query(func.count(Rate.day)) \
            .filter(Rate.day > today - timedelta(20)) \
            .scalar()

Async usage (``clickhouse+asynch``)
-----------------------------------

.. code-block:: python

    from sqlalchemy import select
    from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
    from sqlalchemy.orm import sessionmaker

    async_uri = 'clickhouse+asynch://localhost/default'

    async_engine = create_async_engine(async_uri)
    async_session = sessionmaker(async_engine, class_=AsyncSession)

    async with async_session() as session:
        result = await session.execute(select(Rate).limit(10))
        rows = result.scalars().all()

Dialect aliases
---------------

- ``clickhouse://...``  → HTTP driver
- ``clickhouse+http://...``  → HTTP driver
- ``clickhouse+native://...``  → Native (TCP) driver
- ``clickhouse+asynch://...``  → Async native (TCP) driver

Documentation
=============

Upstream documentation is available at https://clickhouse-sqlalchemy.readthedocs.io.
This fork tracks the same API surface; differences are noted in the sections
above.

Development
===========

This fork is managed with `PDM <https://pdm-project.org/>`_. Install the
development dependency groups before running tests or local checks:

.. code-block:: bash

    python -m pip install pdm
    pdm install -G test -G lint -G coverage -G docs

Git hooks are managed by `prek <https://prek.j178.dev/>`_. Install the
pre-commit hook once per checkout:

.. code-block:: bash

    pdm run prek install

Common development commands:

.. code-block:: bash

    pdm run fmt          # whitespace, EOF and line-ending fixers
    pdm run lint         # flake8 checks for package and maintained tests
    pdm run prek-all     # all configured pre-commit hooks
    pdm run test         # full pytest suite
    pdm run test-alembic # focused Alembic suite
    pdm run docs         # build Sphinx docs
    pdm build            # build sdist and wheel

Tests use the ``test-clickhouse-sqlalchemy`` database by default. The test
setup drops and recreates it automatically, so it does not need to exist before
the suite runs. Local ClickHouse connection overrides can be placed in
``.env.test``:

.. code-block:: bash

    TEST_CLICKHOUSE_URL=clickhouse+asynch://default:@127.0.0.1:9000/test-clickhouse-sqlalchemy
    TEST_CLICKHOUSE_HTTP_PORT=8123

Supported variables include ``TEST_CLICKHOUSE_HOST``, ``TEST_CLICKHOUSE_PORT``,
``TEST_CLICKHOUSE_HTTP_PORT``, ``TEST_CLICKHOUSE_DATABASE``,
``TEST_CLICKHOUSE_USER``, ``TEST_CLICKHOUSE_PASSWORD`` and
``TEST_ENV_FILE``. Tests also set ``wait_for_async_insert=1`` for deterministic
read-after-write assertions when ClickHouse async inserts are enabled.

License
=======

Distributed under the `MIT license <http://www.opensource.org/licenses/mit-license.php>`_.

Original work by Konstantin Lebedev.
Fork maintained by Leechael.
