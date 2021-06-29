import os
import json
import csv

from jira2gus.salesforce.gus_client import GusClient
from jira2gus.migration.migrator import Migrator


DIRECTORY = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def load_from_properties():
    properties_file_path = os.path.join(DIRECTORY, "properties.json")
    if not os.path.exists(properties_file_path):
        return

    with open(properties_file_path, "r") as f:
        content = f.read()

    properties = json.loads(content)

    for key, value in properties.items():
        os.environ[key] = str(value)





def setup_gus_client():
    gus_instance = os.environ["gus_server"]
    gus_user = os.environ["gus_user"]
    gus_password = os.environ["gus_password"]
    cloud_id = os.environ["gus_cloud_id"]
    return GusClient(instance=gus_instance, user=gus_user, password=gus_password, cloud_id=cloud_id)


def setup_migrator():
    load_from_properties()

    gus_client = setup_gus_client()

    return Migrator(gus_client)

