import collections
import functools
import math

from datetime import datetime, timedelta, date

import numpy

from simple_salesforce import format_soql

from jira2gus.salesforce.base_client import BaseClient


class GusClient(BaseClient):

    def __init__(self, instance, user, password, cloud_id):
        BaseClient.__init__(self, user=user, password=password, instance=instance)

        self.sf_session = self.client
        self.server = f"https://{instance}"
        self.cloud_id = cloud_id

        self.cache = collections.defaultdict(functools.partial(collections.defaultdict, dict))
        self.populate_gus_cache('ADM_Frequency__c', 'Name', 'Id')
        self.populate_gus_cache('ADM_Impact__c', 'Name', 'Id')
        self.populate_gus_cache('RecordType', 'Name', 'Id')
        self.populate_gus_cache('User', 'Email', 'Id')
        self.populate_gus_cache('ADM_Scrum_Team__c', 'Id', 'Name', 'Cloud_LU__c', [self.cloud_id])

    ###########################################################################
    # Get From Gus
    ###########################################################################

    def get_scrum_team_record(self, Scrum_Team_id):
        return self.sf_session.ADM_Scrum_Team__c.get(Scrum_Team_id)


    def get_product_tag_record(self, product_tag_id):
        return self.sf_session.ADM_Product_Tag__c.get(product_tag_id)

    def get_existing_keys(self, keys):
        keys = set(keys)
        teams = self.get_team_ids()

        result = self.sf_session.query_all(format_soql("Select Id,ftest__c,Test_Failure_Status__c from ADM_Work__c where Scrum_Team__c in {teams}", teams=teams))
        relevant_records = [record for record in result['records'] if record['ftest__c'] in keys]

        valid_work_items = collections.defaultdict(list)
        for record in relevant_records:
            if record['Test_Failure_Status__c'] in ('Blocking', 'Signed Off'):
                valid_work_items[record['ftest__c']].append(record['Id'])

        selected_valid_work_items = {jira_key: work_ids.pop() for jira_key, work_ids in valid_work_items.items()}

        invalid_work_items = [record['Id'] for record in relevant_records if record['Test_Failure_Status__c'] not in ('Blocking', 'Signed Off')]
        for work_ids in valid_work_items.values():
            invalid_work_items.extend(work_ids)

        return selected_valid_work_items, invalid_work_items

    def get_existing_keys_without_attachments(self, keys):
        keys = set(keys)
        teams = self.get_team_ids()

        result = self.sf_session.query_all(format_soql("Select Id,ftest__c from ADM_Work__c where Scrum_Team__c in {teams} and Test_Failure_Status__c='Blocking'", teams=teams))
        relevant_records = [record for record in result['records'] if record['ftest__c'] in keys]

        valid_work_items = collections.defaultdict(list)
        for record in relevant_records:
            valid_work_items[record['ftest__c']].append(record['Id'])

        work_items = {jira_key: work_ids.pop() for jira_key, work_ids in valid_work_items.items()}

        return work_items

    ###########################################################################
    # Status
    ###########################################################################

    def set_issues_with_attachments(self, work_ids):
        work_items_updates = [{'Id': work_id, 'Test_Failure_Status__c': 'Signed Off'} for work_id in work_ids]
        self.assign_work_items(work_items_updates)

    def set_issues_without_attachments(self, work_ids):
        work_items_updates = [{'Id': work_id, 'Test_Failure_Status__c': 'Blocking'} for work_id in work_ids]
        self.assign_work_items(work_items_updates)

    ###########################################################################
    # Actions
    ###########################################################################

    def clear_work_items(self, work_ids):
        if not work_ids:
            return

        self.delete_work_connected_items('ADM_Work__Feed', 'ParentId', work_ids)
        self.delete_work_connected_items('ADM_Task__c', 'Work__c', work_ids)
        self.delete_work_connected_items('ADM_Acceptance_Criterion__c', 'Work__c', work_ids)
        self.delete_work_connected_items('ADM_Change_List__c', 'Work__c', work_ids)
        self.delete_work_connected_items('ADM_Theme_Assignment__c', 'Work__c', work_ids)

    def create_work_items(self, work_items):
        work_items = [work_item for work_item in work_items if work_item]
        if not work_items:
            return

        response = self.sf_session.bulk.ADM_Work__c.upsert(work_items, 'Id')
        self.check_response(response)

        result = {}
        for i in range(len(work_items)):
            result[work_items[i]['Ftest__c']] = response[i]['id']

        return result

    def create_epics(self, epics):
        self.create_items('ADM_Epic__c', 'Name', epics)

    def create_themes(self, themes):
        self.create_items('ADM_Theme__c', 'Name', themes, True)

    def create_sprints(self, sprints):
        unknown_sprints = [sprint for sprint in sprints if (sprint['Scrum_Team__c'], sprint['Name']) not in self.cache['ADM_Sprint__c']['Scrum_Team__c_Name']]
        if not unknown_sprints:
            return

        teams = [sprint['Scrum_Team__c'] for sprint in sprints]
        self.update_sprint_cache(teams)

        new_sprints = [sprint for sprint in unknown_sprints if (sprint['Scrum_Team__c'], sprint['Name']) not in self.cache['ADM_Sprint__c']['Scrum_Team__c_Name']]

        if not new_sprints:
            return

        for i in range(len(new_sprints)):
            new_sprints[i]['Start_Date__c'], new_sprints[i]['End_Date__c'] = self.allocate_sprint_range(new_sprints[i]['Scrum_Team__c'], new_sprints[i]['Start_Date__c'], new_sprints[i]['End_Date__c'])
            team_name = self.get_team_name(new_sprints[i]['Scrum_Team__c'])
            new_sprints[i]['Name'] = self.generate_sprint_name(new_sprints[i]['Start_Date__c'], new_sprints[i]['Name'], team_name)

        response = self.sf_session.bulk.ADM_Sprint__c.insert(new_sprints)
        self.check_response(response)

        for i in range(len(new_sprints)):
            team_name = self.get_team_name(new_sprints[i]['Scrum_Team__c'])
            sprint_name = new_sprints[i]['Name'][10:-len(team_name)-3]
            self.cache['ADM_Sprint__c']['Scrum_Team__c_Name'][(new_sprints[i]['Scrum_Team__c'], sprint_name)] = response[i]['id']

    def create_chatter_attachment(self, messageText, obj=None, mention_ids=(), file_name="", file_data=None):
        return self.client.chatter_on_object_with_attachment(messageText, obj, mention_ids, file_name, file_data)

    def create_items(self, table, identifier, items, lower=False):
        unknown_items = self.filter_values_not_in_cache(table, identifier, items, lower)
        unknown_items_values = [item[identifier] for item in unknown_items]
        self.populate_gus_cache(table, identifier, 'Id', identifier, unknown_items_values, lower)
        new_items = self.filter_values_not_in_cache(table, identifier, unknown_items, lower)

        if not new_items:
            return

        response = getattr(self.sf_session.bulk, table).insert(new_items)
        self.check_response(response)

        for i in range(len(new_items)):
            if lower:
                self.cache[table][identifier][new_items[i][identifier].lower()] = response[i]['id']
            else:
                self.cache[table][identifier][new_items[i][identifier]] = response[i]['id']

    ###########################################################################
    # Assignments
    ###########################################################################

    def assign_themes(self, theme_assignments):
        self.assign_items('ADM_Theme_Assignment__c', theme_assignments)

    def assign_feeds(self, feeds):
        self.assign_items('FeedItem', feeds)

    def assign_changes(self, changes):
        self.assign_items('ADM_Change_List__c', changes, False)

    def assign_tasks(self, tasks):
        self.assign_items('ADM_Task__c', tasks)

    def assign_acceptance_criterias(self, acceptance_criterias):
        self.assign_items('ADM_Acceptance_Criterion__c', acceptance_criterias)

    def assign_work_items(self, work_items_updates):
        self.assign_items('ADM_Work__c', work_items_updates)

    def assign_items(self, table, items, validate=True):
        response = getattr(self.sf_session.bulk, table).upsert(items, 'Id')
        if validate:
            self.check_response(response)

    ###########################################################################
    # Get From Cache
    ###########################################################################

    def get_record_type_id(self, name):
        return self.cache['RecordType']['Name'][name]

    def get_epic_id(self, name):
        return self.cache['ADM_Epic__c']['Name'][name]

    def get_theme_id(self, name):
        return self.cache['ADM_Theme__c']['Name'][name.lower()]

    def get_sprint_id(self, team, name):
        return self.cache['ADM_Sprint__c']['Scrum_Team__c_Name'][(team, name)]

    def get_user_id(self, name):
        return self.cache['User']['Email'].get(name, None)

    def get_impact_id(self, name):
        return self.cache['ADM_Impact__c']['Name'][name]

    def get_frequency_id(self, name):
        return self.cache['ADM_Frequency__c']['Name'][name]

    def get_team_name(self, team_id):
        return self.cache['ADM_Scrum_Team__c']['Id'][team_id]

    def get_team_ids(self):
        return list(self.cache['ADM_Scrum_Team__c']['Id'].keys())

    ###########################################################################
    # Private Methods
    ###########################################################################

    def populate_gus_cache(self, table, key_field, value_field, filter_field=None, filter_values=None, lower=False):
        if filter_values is not None and len(filter_values) == 0:
            return

        for key_field_value, value_field_value in self.query_all(table, key_field, value_field, filter_field, filter_values):
            if lower:
                key_field_value = key_field_value.lower()
            self.cache[table][key_field][key_field_value] = value_field_value

    def filter_values_not_in_cache(self, table, identifier, items, lower):
        if lower:
            return [item for item in items if item[identifier].lower() not in self.cache[table][identifier]]
        else:
            return [item for item in items if item[identifier] not in self.cache[table][identifier]]

    def query_all(self, table, key_field, value_field, filter_field, filter_values):
        if filter_values:
            filter_values = format_soql('{filter_values}', filter_values=filter_values)
            query = f"select {key_field}, {value_field} from {table} where {filter_field} IN {filter_values}"
        else:
            query = f"select {key_field}, {value_field} from {table}"

        result = self.sf_session.query_all(query)
        return [(record[key_field], record[value_field]) for record in result['records']]

    def delete_work_connected_items(self, table, work_id_field, work_ids):
        records = []
        for work_ids_group in numpy.array_split(work_ids, math.ceil(len(work_ids) / 200)):
            work_ids_group = list(work_ids_group)
            query = f"Select Id from {table} where {work_id_field} in {format_soql('{work_ids}', work_ids=work_ids_group)}"
            result = self.sf_session.query_all(query)
            records.extend(result['records'])

        items_to_delete = [{'Id': record['Id']} for record in records]
        response = getattr(self.sf_session.bulk, table).delete(items_to_delete)
        self.check_response(response)

    def update_sprint_cache(self, teams):
        for team_id in teams:
            self.cache['ADM_Sprint__c']['Scrum_Team__c'][team_id] = []

        query = format_soql("select Id, Name, Scrum_Team__c, Start_Date__c, End_Date__c from ADM_Sprint__c where Scrum_Team__c IN {teams}", teams=teams)
        result = self.sf_session.query_all(query)

        for record in result['records']:
            team_name = self.get_team_name(record['Scrum_Team__c'])
            sprint_name = record['Name'][10:-len(team_name)][:-3]
            self.cache['ADM_Sprint__c']['Scrum_Team__c_Name'][(record['Scrum_Team__c'], sprint_name)] = record['Id']

            start_date = datetime.strptime(record['Start_Date__c'], "%Y-%m-%d").date()
            end_date = datetime.strptime(record['End_Date__c'], "%Y-%m-%d").date()
            self.cache['ADM_Sprint__c']['Scrum_Team__c'][record['Scrum_Team__c']].append((start_date, end_date))

    def allocate_sprint_range(self, team_id, start_date, end_date):
        if start_date is None or end_date is None:
            start_date, end_date = self.get_available_sprint_date_range(team_id)
            start_date, end_date = start_date.strftime("%Y-%m-%d"), end_date.strftime("%Y-%m-%d")

        start_date = datetime.strptime(start_date[:10], "%Y-%m-%d").date()
        end_date = datetime.strptime(end_date[:10], "%Y-%m-%d").date()

        if end_date - start_date >= timedelta(days=30):
            end_date = start_date + timedelta(days=30)

        for date_range in self.cache['ADM_Sprint__c']['Scrum_Team__c'][team_id]:
            if start_date == date_range[1]:
                start_date = start_date + timedelta(days=1)
            if end_date == date_range[0]:
                end_date = end_date - timedelta(days=1)

            if date_range[0] <= start_date <= date_range[1] or date_range[0] <= end_date <= date_range[1] or start_date <= date_range[0] <= end_date or start_date <= date_range[1] <= end_date:
                start_date, end_date = self.get_available_sprint_date_range(team_id)
                break

        self.cache['ADM_Sprint__c']['Scrum_Team__c'][team_id].append((start_date, end_date))
        return start_date.strftime("%Y-%m-%d"), end_date.strftime("%Y-%m-%d")

    def get_available_sprint_date_range(self, team_id):
        optional_date_ranges = set((date(year=year, month=month, day=1), date(year=year, month=month, day=28)) for year in range(2020, 2022) for month in range(1, 13))
        available_date_ranges = optional_date_ranges.difference(self.cache['ADM_Sprint__c']['Scrum_Team__c'][team_id])
        return available_date_ranges.pop()

    @staticmethod
    def generate_sprint_name(start_date, sprint_name, team_name):
        return f"{start_date[:4]}.{start_date[5:7]} - {sprint_name} - {team_name}"

    @staticmethod
    def check_response(response):
        for item in response:
            if not item['success']:
                raise RuntimeError(item['errors'])
