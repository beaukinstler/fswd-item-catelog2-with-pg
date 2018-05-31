
import json
import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

PROJECT_ROOT = os.path.realpath(os.path.dirname(__file__),'..')
SECRETS_URL = os.path.join(PROJECT_ROOT, 'secrets.json')
DB_CONNECTION_STR =  (
        json.loads(
            open(SECRETS_URL, 'r')
            .read())['db_conn_str']
    )
ENGINE = create_engine(DB_CONNECTION_STR)

DBSession = sessionmaker(bind=ENGINE)
