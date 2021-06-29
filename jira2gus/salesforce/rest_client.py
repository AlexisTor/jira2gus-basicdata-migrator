import requests
import json

from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from simple_salesforce import Salesforce


class RestClient(Salesforce):
    def __init__(self, **kwargs):
        session = requests.Session()

        retries = Retry(total=10,
                        backoff_factor=0.1,
                        status_forcelist=[500, 502, 503, 504])

        session.mount('https://', HTTPAdapter(max_retries=retries))

        Salesforce.__init__(self, version="36.0", session=session, **kwargs)

    def get_chatter_profile(self, obj='me'):
        url = self.base_url + 'chatter/users/{}'.format(obj)
        params = {}

        result = requests.get(url, headers=self.headers, params=params)

        if result.status_code != 200:
            _exception_handler(result)

        return result.json()

    def create_chatter_body(self, text, mention_ids=()):
        text = {
            "type": "Text",
            "text": text
        }

        segments = [text]

        if len(mention_ids) > 0:
            segments.append({
                "type": "Text",
                "text": "\n\ncc: "
            })

        for mention_id in mention_ids:
            segments.append({
                "type": "mention",
                "id": mention_id
            })

        message = {
            "body": {
                "messageSegments": segments,
            }
        }

        return message

    def create_chatter_body_for_attachment(self, text, mention_ids=(), file_name=""):
        message = self.create_chatter_body(text, mention_ids)

        message["attachment"] = {
            "attachmentType": "NewFile",
            "description": "attachment migrated from Jira",
            "title": file_name
        }

        return message

    def chatter_post(self, text, mention_ids=()):
        url = self.base_url + 'chatter/feeds/news/me/feed-items'
        body = self.create_chatter_body(text, mention_ids=mention_ids)

        data = json.dumps(body)

        result = requests.post(url, data=data, headers=self.headers)

        if result.status_code != 201:
            _exception_handler(result)

        return result.json()

    def chatter_on_object(self, message, obj, mention_ids=()):
        url = self.base_url + 'chatter/feeds/record/{}/feed-items'.format(obj)

        body = self.create_chatter_body(message, mention_ids=mention_ids)
        data = json.dumps(body)

        result = requests.post(url, data=data, headers=self.headers)

        if result.status_code != 201:
            _exception_handler(result)

        return result.json()

    def chatter_on_object_with_attachment(self, message, obj, mention_ids=(), file_name="", file_data=None):
        boundary = 'F9jBDELnfBLAVmLNbnLIYibT5Icp0h3VJ7mkI'
        attachment_headers = {
            'Content-Type': 'multipart/form-data; boundary=F9jBDELnfBLAVmLNbnLIYibT5Icp0h3VJ7mkI',  # abcdeedcbaabcdeedcba'
            'Accept': 'application/json',
            'Authorization': 'Bearer ' + self.session_id,
            'X-PrettyPrint': '1'
        }

        url = self.base_url.replace(self.sf_version, '30.0') + 'chatter/feeds/record/{}/feed-items'.format(obj)

        body_prefix = '--' + boundary + "\r\n"
        body_prefix += 'Content-Disposition: form-data; name="json"' + "\r\n"
        body_prefix += 'Content-Type: application/json; charset=UTF-8;' + "\r\n\r\n"

        body = self.create_chatter_body_for_attachment(message, mention_ids=mention_ids, file_name=file_name)

        data = json.dumps(body)
        data = body_prefix + data + "\r\n\r\n\r\n"

        body_suffix = '--' + boundary + "\r\n"
        body_suffix += 'Content-Disposition: form-data; name="feedItemFileUpload"; filename=' + '"' + file_name + '"' + "\r\n";
        # https://developer.mozilla.org/en-US/docs/Web/HTTP/Basics_of_HTTP/MIME_types/Common_types
        # https://fileinfo.com/extension/docx # check if file is binary by extension
        # https://file-examples.com/index.php/sample-video-files/sample-mov-files-download/ #download file examples

        supported_types = {
            "png": "image/png",
            "jpg": "image/jpeg",
            "jpeg": "image/jpeg",
            "gif": "image/gif",
            "pdf": "application/pdf",
            "doc": "application/msword",
            "xls": "application/vnd.ms-excel",
            "mov": "video/quicktime",
            "txt": "text/plain",
            "log": "text/plain",
            "csv": "text/csv",
            "docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            "xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            "xml": "application/xml",
            "mp4": "application/mp4",
            "json": "application/json",
            "html": "text/html"
        }
        ending = file_name.split(".")[-1]

        content_type = supported_types[ending] if ending in supported_types else "application/octet-stream"
        body_suffix += 'Content-Type: ' + content_type + "\r\n\r\n"

        binaryBodySuffix = body_suffix.encode()
        binaryBodySuffix += file_data
        boundary = "\r\n" + '--' + boundary + '--' + "\r\n"
        BinaryBoundary = boundary.encode()
        binaryBodySuffix += BinaryBoundary

        binarydata = data.encode()
        binarydata += binaryBodySuffix

        result = requests.post(url, data=binarydata, headers=attachment_headers)

        if result.status_code != 201:
            _exception_handler(result)

        return result.json()

    def get_news_feed(self):
        url = self.base_url + 'chatter/feeds/news/me/feed-items'
        params = {}
        result = requests.get(url, headers=self.headers, params=params)

        if result.status_code != 200:
            _exception_handler(result)

        return result.json()

    def get_object_feed(self, obj):
        url = self.base_url + 'chatter/feeds/record/{}/feed-items'.format(obj)

        result = requests.get(url, headers=self.headers)

        if result.status_code != 200:
            _exception_handler(result)

        return result.json()


def _exception_handler(result, name=""):
    url = result.url
    try:
        response_content = result.json()
    except Exception:
        response_content = result.text

    if result.status_code == 300:
        message = f"More than one record for {url}. Response content: {response_content}"
        raise SalesforceMoreThanOneRecord(message)
    elif result.status_code == 400:
        message = f"Malformed request {url}. Response content: {response_content}"
        raise SalesforceMalformedRequest(message)
    elif result.status_code == 401:
        message = f"Expired session for {url}. Response content: {response_content}"
        raise SalesforceExpiredSession(message)
    elif result.status_code == 403:
        message = f"Request refused for {url}. Resonse content: {response_content}"
        raise SalesforceRefusedRequest(message)
    elif result.status_code == 404:
        message = f"Resource {name} Not Found. Response content: {response_content}"
        raise SalesforceResourceNotFound(message)
    else:
        message = f"Error Code {result.status_code}. Response content: {response_content}"
        raise SalesforceGeneralError(message)


class SalesforceMoreThanOneRecord(Exception):
    '''
    Error Code: 300
    The value returned when an external ID exists in more than one record. The
    response body contains the list of matching records.
    '''
    pass


class SalesforceMalformedRequest(Exception):
    '''
    Error Code: 400
    The request couldn't be understood, usually becaue the JSON or XML body contains an error.
    '''
    pass


class SalesforceExpiredSession(Exception):
    '''
    Error Code: 401
    The session ID or OAuth token used has expired or is invalid. The response
    body contains the message and errorCode.
    '''
    pass


class SalesforceRefusedRequest(Exception):
    '''
    Error Code: 403
    The request has been refused. Verify that the logged-in user has
    appropriate permissions.
    '''
    pass


class SalesforceResourceNotFound(Exception):
    '''
    Error Code: 404
    The requested resource couldn't be found. Check the URI for errors, and
    verify that there are no sharing issues.
    '''
    pass


class SalesforceGeneralError(Exception):
    '''
    A non-specific Salesforce error.
    '''
    pass
