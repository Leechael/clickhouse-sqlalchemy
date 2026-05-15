import configparser
import os
from pathlib import Path

from sqlalchemy.engine import URL, make_url
from sqlalchemy.dialects import registry

from tests import log


registry.register(
    "clickhouse", "clickhouse_sqlalchemy.drivers.http.base", "dialect"
)
registry.register(
    "clickhouse.native", "clickhouse_sqlalchemy.drivers.native.base", "dialect"
)
registry.register(
    "clickhouse.asynch", "clickhouse_sqlalchemy.drivers.asynch.base", "dialect"
)


def _load_dotenv_test():
    candidates = []
    explicit = os.environ.get("TEST_ENV_FILE")
    if explicit:
        candidates.append(Path(explicit))

    candidates.extend(
        parent / ".env.test" for parent in (Path.cwd(), *Path.cwd().parents)
    )

    for path in candidates:
        if not path.exists():
            continue

        for line in path.read_text().splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue

            key, value = line.split("=", 1)
            os.environ.setdefault(key.strip(), value.strip().strip("'\""))


def _env_int(name, default):
    value = os.environ.get(name)
    return int(value) if value else default


def _flatten_query(query):
    rv = {}
    for key, value in dict(query).items():
        if isinstance(value, (list, tuple)):
            value = value[-1]
        rv[key] = value
    return rv


def _make_uri(schema, database, port, query=None):
    return URL.create(
        schema,
        username=user,
        password=password,
        host=host,
        port=port,
        database=database,
        query=query or {},
    ).render_as_string(hide_password=False)


_load_dotenv_test()

file_config = configparser.ConfigParser()
file_config.read(['setup.cfg'])

log.configure(file_config.get('log', 'level'))

test_url = os.environ.get('TEST_CLICKHOUSE_URL')
parsed_url = make_url(test_url) if test_url else None

host = os.environ.get(
    'TEST_CLICKHOUSE_HOST',
    parsed_url.host if parsed_url else file_config.get('db', 'host')
)
port = _env_int(
    'TEST_CLICKHOUSE_PORT',
    parsed_url.port if parsed_url and parsed_url.port else
    file_config.getint('db', 'port')
)
http_port = _env_int(
    'TEST_CLICKHOUSE_HTTP_PORT',
    file_config.getint('db', 'http_port')
)
database = os.environ.get(
    'TEST_CLICKHOUSE_DATABASE',
    parsed_url.database if parsed_url and parsed_url.database else
    file_config.get('db', 'database')
)
user = os.environ.get(
    'TEST_CLICKHOUSE_USER',
    parsed_url.username if parsed_url and parsed_url.username is not None else
    file_config.get('db', 'user')
)
password = os.environ.get(
    'TEST_CLICKHOUSE_PASSWORD',
    parsed_url.password if parsed_url and parsed_url.password is not None else
    file_config.get('db', 'password')
)

url_query = _flatten_query(parsed_url.query) if parsed_url else {}
clickhouse_settings = {
    'wait_for_async_insert': url_query.get('wait_for_async_insert', '1'),
}

http_uri = _make_uri('clickhouse+http', database, http_port)
native_uri = _make_uri('clickhouse+native', database, port)
asynch_uri = _make_uri('clickhouse+asynch', database, port)

system_http_uri = _make_uri('clickhouse+http', 'system', http_port)
system_native_uri = _make_uri('clickhouse+native', 'system', port)
system_asynch_uri = _make_uri('clickhouse+asynch', 'system', port)
