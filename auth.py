import requests.auth
from hashlib import sha256
from urllib.parse import urlparse
import time
import base64

class QtradeAuth(requests.auth.AuthBase):
    def __init__(self, key):
        self.key_id, self.key = key.split(":")

    def __call__(self, req):
        # modify and return the request
        timestamp = str(int(time.time()))
        url_obj = urlparse(req.url)

        request_details = req.method + "\n"
        request_details += url_obj.path + url_obj.params + "\n"
        request_details += timestamp + "\n"

        if req.body:
            if isinstance(req.body, str):
                request_details += req.body + "\n"
            else:
                request_details += req.body.decode('utf8') + "\n"
        else:
            request_details += "\n"
        request_details += self.key
        hsh = sha256(request_details.encode("utf8")).digest()
        signature = base64.b64encode(hsh)
        req.headers.update({
            "Authorization": f"HMAC-SHA256 {self.key_id}:{signature.decode()}",
            "HMAC-Timestamp": timestamp
        })
        return req