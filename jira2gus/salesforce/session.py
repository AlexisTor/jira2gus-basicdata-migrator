import re, requests


class SoapSession:
    def __init__(self, instance='login.salesforce.com', session_id=None):
        self.instance = instance
        self.sessionId = session_id
        self.version = "0.1.6"
        
    def login(self, user, password, security_token=''):

        headers = {
            'User-Agent'      : 'shawns-client',
            'Accept'          : 'text/html,application/xhtml+xml,application/xml',
            'Accept-Encoding' : 'none',
            'Accept-Charset'  : 'utf-8',
            'Connection'      : 'close',
            'Content-Type'    : 'text/xml; charset=utf-8',
            'SOAPAction'      : '"urn:enterprise.soap.sforce.com/login"'}
        body = '''
            <soap:Envelope xmlns:soap="http://schemas.xmlsoap.org/soap/envelope/" xmlns:tns="urn:enterprise.soap.sforce.com" xmlns:fns="urn:fault.enterprise.soap.sforce.com" xmlns:ens="urn:sobject.enterprise.soap.sforce.com"><soap:Header></soap:Header><soap:Body><tns:login><username>%s</username><password>%s%s</password></tns:login></soap:Body></soap:Envelope>
                ''' % (user, password, security_token)
        r = requests.post("https://{}/services/Soap/c/v29.0".format(self.instance), data=body, headers=headers)
        data = r.text
        try:
            regex = re.compile(str("<sessionId>(.*)</sessionId>"), re.MULTILINE)
            match = regex.search(data)
            sessionId = match.group(1)
            self.sessionId = str(sessionId)
        except:
            self.sessionId = None
            raise Exception(f"Login Failed {data}")
        
    def is_valid(self):
        headers = {'Authorization':'Bearer {}'.format(self.sessionId)}
        url = "https://{}/services/data/v29.0/chatter/users/me".format(self.instance)
        r = requests.get(url, headers=headers)
        if r.status_code == 200:
            return True
        else:
            return False
        
    def get_session_id(self):
        return self.sessionId
