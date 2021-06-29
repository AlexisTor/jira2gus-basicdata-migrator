from jira2gus.salesforce.rest_client import RestClient
from jira2gus.salesforce.session import SoapSession


class BaseClient:
    def __init__(self, user, password, instance='login.salesforce.com', session_id=None):
        if session_id is not None:
            session = SoapSession(session_id=session_id, instance=instance)
            if not session.is_valid():
                session_id = None

        if session_id is None:
            session = SoapSession(instance)
            session.login(user, password)
            session_id = session.get_session_id()

        self.client = RestClient(instance_url=f"https://{instance}", session_id=session_id)
        self.session_id = session_id