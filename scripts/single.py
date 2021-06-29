import os
import sys

DIRECTORY = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(DIRECTORY)

from jira2gus.migration.migrator_setup import setup_migrator

def run():
    
    migrator = setup_migrator()
    product_tag = os.environ["product_tag"]
    
    migrator.run(product_tag)

    print ("test")

if __name__ == '__main__':
    run()
