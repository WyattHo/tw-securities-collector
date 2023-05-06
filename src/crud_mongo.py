import configparser
import datetime
import functools
from typing import Dict, List, Protocol

from pymongo import MongoClient
from pymongo.collection import Collection
from pymongo.database import Database


CONFIG_FILE = '.\\src\\config.ini'


class OriginalFunc(Protocol):
    def __call__(self, db: Database, collection_name: str) -> Collection:
        ...


class DecoratedFunc(Protocol):
    def __call__(self, db_name: str, collection_name: str) -> None:
        ...


def read_config() -> Dict[str, str]:
    config = configparser.ConfigParser()
    config.read(CONFIG_FILE)
    return config['mongodb']['url']


def get_database(client: MongoClient, db_name: str) -> Database:
    db_names = client.list_database_names()
    if db_name not in db_names:
        return Database(client, db_name)
    else:
        return client.get_database(db_name)


def close_client(func):
    def wrapper(collection: Collection, docs: List[Dict]):
        func(collection, docs)
        collection.database.client.close()
    return wrapper


@close_client
def insert_docs(collection: Collection, docs: List[Dict]):
    for doc in docs:
        if not collection.find_one(doc):
            collection.insert_one(doc)


def connect_mongodb(url: str = read_config(), tls: bool = True, tls_allow_invalid_certificates: bool = True):
    def decorator(func: OriginalFunc) -> DecoratedFunc:
        @functools.wraps(func)
        def wrapper(db_name: str, collection_name: str):
            client = MongoClient(
                url,
                tls=tls,
                tlsAllowInvalidCertificates=tls_allow_invalid_certificates
            )
            db = get_database(client, db_name)
            return func(db, collection_name)
        return wrapper
    return decorator


@connect_mongodb()
def get_general_collection(db: Database, collection_name: str) -> Collection:
    collection_names = db.list_collection_names()
    if collection_name not in collection_names:
        return db.create_collection(collection_name)
    else:
        return db.get_collection(collection_name)


@connect_mongodb()
def get_timeseries_collection(db: Database, collection_name: str) -> Collection:
    collection_names = db.list_collection_names()
    if collection_name not in collection_names:
        timeseries = {
            'timeField': 'timestamp',
            'metaField': 'metadata',
            'granularity': 'hours'
        }
        return db.create_collection(collection_name, timeseries=timeseries)
    else:
        return db.get_collection(collection_name)


def connect_and_insert_general(db_name: str, collection_name: str, docs: List[Dict]):
    collection = get_general_collection(
        db_name=db_name,
        collection_name=collection_name,
    )
    insert_docs(collection, docs)


def connect_and_insert_timeseries(db_name: str, collection_name: str, docs: List[Dict]):
    collection = get_timeseries_collection(
        db_name=db_name,
        collection_name=collection_name,
    )
    insert_docs(collection, docs)


if __name__ == '__main__':
    general_docs = [
        {'name': 'blender', 'price': 340, 'category': 'kitchen appliance'},
        {'name': 'egg', 'price': 36, 'category': 'food'}
    ]

    connect_and_insert_general(
        db_name='test_db',
        collection_name='kitchen_collection',
        docs=general_docs
    )

    timeseries_docs = [
        {
            'metadata': {'patient': 'wyatt', 'gender': 'male'},
            'timestamp': datetime.datetime(2021, 5, 18),
            'weight': 70.1,
            'body temperature': 37.4
        },
        {
            'metadata': {'patient': 'wyatt', 'gender': 'male'},
            'timestamp': datetime.datetime(2021, 5, 19),
            'weight': 70.6,
            'body temperature': 37.0
        },
        {
            'metadata': {'patient': 'wyatt', 'gender': 'male'},
            'timestamp': datetime.datetime(2021, 5, 20),
            'weight': 70.2,
            'body temperature': 36.8
        },
    ]

    connect_and_insert_timeseries(
        db_name='test_db',
        collection_name='patient_condition',
        docs=timeseries_docs
    )
