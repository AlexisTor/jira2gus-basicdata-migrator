import math

import numpy

from jira2gus import logger_wrapper


log = logger_wrapper.get_logger(__name__)


class Migrator:

    def __init__(self, gus_client):
        self.gus_client = gus_client

    def run(self, product_tag):
        log.info("Starting to migrate product_tag {product_tag} with issues from jira query {jira_query}")

        try:
            product_tag_record = self.gus_client.get_product_tag_record(product_tag)
            log.info("Successfully get teams from gus")
            log.info(product_tag_record)

        except Exception:
            log.exception("Error while getting teams from gus")
