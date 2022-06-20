#!/us/bin/env python3

from certbot import util
from datetime import datetime
from OpenSSL import crypto
from typing import Any
import base64
import json
import yaml
import requests
from requests.auth import HTTPBasicAuth
import sys
import urllib3

class CertAsaInstall():
    
    
    def __init__(
        self, 
        ipaddress: str, 
        username: str,
        password: str,
        secret: str,
        interface: str,
        domain: str,
        certpath: str,
        webroot: str,
        email: str,
        port: int = 443,
        test: bool = False,
        pin: bool = True,
        ):
        
        self.ipaddress = ipaddress
        self.username = username
        self.password = password
        self.interface = interface
        self.domain = domain
        self.certpath = certpath
        self.webroot = webroot
        self.email = email
        self.secret = secret
        self.test = test
        self.pin = pin
        
        # Mgmt url
        if port == 443:
            self.server = f"https://{ipaddress}"
        else:        
            self.server = f"https://{ipaddress}:{port}"
        self.headers = f"{{'Content-Type': 'application/json', 'User-Agent':'REST API Agent'}}"
        
        # Path for install cert
        self.api_path_cert = f"/api/certificate/identity"
        self.url_cert = f"{self.server}{self.api_path_cert}"
        
        # Path for pin cert
        self.api_path_pin = f"/api/cli"
        self.url_pin = f"{self.server}{self.api_path_pin}"

    @staticmethod
    def untrusted_mgmt() -> None:
        urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

    @staticmethod
    def _datename() -> str:
        return str(datetime.now().strftime("%Y%m%d"))

    @staticmethod
    def _post(url: str, post_data: dict[str, Any], username: str, password: str) -> None:
        try:
            r = requests.post(
                url, 
                data=json.dumps(post_data), 
                auth=(username, password), 
                headers={
                    'Content-Type': 'application/json', 
                    'User-Agent': 'REST API Agent'}, 
                verify=False
                )
            if r.status_code == 201:
                print("The certificate has been installed succefully.")
            elif r.status_code == 200:
                print("The certificate has been pinned to the interface.")
            else:
                print("Something went wrong.")
                print(r.text)
        except requests.HTTPError as err:
            print(f"Error received from server. HTTP Status code :{str(err.response.status_code)}")
            try:
                print(err.response.text)
            except ValueError:
                pass

    def request_pkcs12(self) -> None:
        certbot_params = [
            'certbot', 
            '-n', 
            'certonly', 
            '--webroot', 
            '-w', 
            self.webroot, 
            '-d', 
            self.domain, 
            '--agree-tos', 
            '--email', 
            self.email
        ]
        
        if self.test == True:
            certbot_params.append('--test-cert')
        
        util.run_script(certbot_params)

        with open(f"{self.certpath}privkey.pem", "rb") as key_pem:
            privkey = crypto.load_privatekey(crypto.FILETYPE_PEM, key_pem.read())
            
        with open(f"{self.certpath}cert.pem", "rb") as cert_pem:
            cert = crypto.load_certificate(crypto.FILETYPE_PEM, cert_pem.read())
            
        with open(f"{self.certpath}chain.pem", "rb") as ca_pem:
            ca = [crypto.load_certificate(crypto.FILETYPE_PEM, ca_pem.read())]

        p12 = crypto.PKCS12()
        p12.set_privatekey(privkey)
        p12.set_certificate(cert)
        p12.set_ca_certificates(ca)
        cert_p12 = p12.export(str.encode(self.secret))

        with open(f"{self.certpath}{self._datename()}.p12", "wb") as p12file:
            p12file.write(cert_p12)

    def install_cert(self) -> None:
        cert_pkcs12 = ['-----BEGIN PKCS12-----']
        with open(f"{self.certpath}{self._datename()}.p12", "rb") as cert:
            encoded_string = base64.b64encode(cert.read())
        c = encoded_string
        while len(c) > 64:
            cert_pkcs12.append(c[:64].decode("utf-8"))
            c = c[64:]
        else:
            cert_pkcs12.append(c.decode("utf-8") )
        cert_pkcs12.append('-----END PKCS12-----')
        install_cert = {
            'certPass': self.secret, 
            'kind': 'object#IdentityCertificate', 
            'certText': cert_pkcs12, 
            'name': self._datename()
            }
        self._post(self.url_cert, install_cert, self.username, self.password)

    def pin_cert(self) -> None:
        cmd = f"ssl trust-point {self._datename()} {self.interface}"
        pin_cert = {'commands': [cmd, 'write']}
        self._post(self.url_pin, pin_cert, self.username, self.password)
    

if __name__ == '__main__':
    if len(sys.argv) > 1:
        config = sys.argv[1]
    else:
        config = "../configs/params.yaml"
    with open(config) as c:
        params = yaml.safe_load(c)
    cai = CertAsaInstall(**params)
    cai.untrusted_mgmt()
    cai.request_pkcs12()
    cai.install_cert()
    if params['pin'] == True:
        cai.pin_cert()