#!/usr/bin/python

from certbot import util
from datetime import datetime
from OpenSSL import crypto
import base64
import ConfigParser
import json
import ssl
import subprocess
import sys
import urllib2

# Date
t = datetime.now()
datename = t.strftime("%Y%m%d")

# Configuration
parser = ConfigParser.ConfigParser()
parser.read('config.ini')

ipaddress = parser.get('options', 'ipaddress')
username = parser.get('options', 'username')
password = parser.get('options', 'password')
port = parser.get('options', 'port')
secret = parser.get('options', 'secret')
interface = parser.get('options', 'interface')
domain = parser.get('options', 'domain')
certpath = parser.get('options', 'certpath')
webroot = parser.get('options', 'webroot')
testcert = parser.get('options', 'testcert')
pin = parser.get('options', 'pin')
email = parser.get('options', 'email')

# Untrusted connection to asa mgmt
ssl._create_default_https_context = ssl._create_unverified_context

# Mgmt url
server = "https://" + ipaddress + ":" + port
headers = {'Content-Type': 'application/json'}

# Path for install cert
api_path_cert = "/api/certificate/identity"    # param
url_cert = server + api_path_cert

# Path for install cert
api_path_pin = "/api/cli"    # param
url_pin = server + api_path_pin


# Requset cert and export to pkcs12
def RequestPKCS12(certpath, datename, webroot, domain):
    global testcert
    if 'True' in testcert:
        params = ['certbot', '-n', 'certonly', '--test-cert', '--webroot', '-w', webroot, '-d', domain]
    else:
        params = ['certbot', '-n', 'certonly', '--webroot', '-w', webroot, '-d', domain, '--agree-tos', '--email', email]
    get_cert = util.run_script(params)

    key_pem = open(certpath + 'privkey.pem', 'r').read()
    cert_pem = open(certpath + 'cert.pem', 'r').read()
    ca_pem = open(certpath + 'chain.pem', 'r').read()

    privkey = crypto.load_privatekey(crypto.FILETYPE_PEM, key_pem)
    cert = crypto.load_certificate(crypto.FILETYPE_PEM, cert_pem)
    ca = [crypto.load_certificate(crypto.FILETYPE_PEM, ca_pem)]

    p12 = crypto.PKCS12()
    p12.set_privatekey(privkey)
    p12.set_certificate(cert)
    p12.set_ca_certificates(ca)
    cert_p12 = p12.export(secret)

    with open(certpath + datename + '.p12', 'w') as p12file:
        p12file.write(cert_p12)


# Form post data
def FormPostAddCert(certpath, datename, secret):
    list = ['-----BEGIN PKCS12-----']
    with open(certpath + datename + '.p12', 'rb') as cert:
        encoded_string = base64.b64encode(cert.read())
    c = encoded_string
    while len(c) > 64:
        list.append(c[:64])
        c = c[64:]
    else:
        list.append(c)
    list.append('-----END PKCS12-----')
    add_cert = json.dumps({'certPass': secret, 'kind': 'object#IdentityCertificate', 'certText': list, 'name': datename})
    return add_cert


def FormPostPinCert(datename, interface):
    interface1 = 'ssl trust-point ' + datename + ' ' + interface
    pin_cert = json.dumps({'commands': [interface1, 'write']})
    return pin_cert


# Action
def PostRequest(url, post_data, headers, username, password):
    f = None
    base64string = base64.encodestring('%s:%s' % (username, password)).replace('\n', '')
    req = urllib2.Request(url, post_data, headers)
    req.add_header("Authorization", "Basic %s" % base64string)
    try:
        f = urllib2.urlopen(req)
        status_code = f.getcode()
        print "Status code is "+str(status_code)
        if status_code == 201:
            print "Create was successful"
    except urllib2.HTTPError, err:
        print "Error received from server. HTTP Status code :"+str(err.code)
        try:
            json_error = json.loads(err.read())
            if json_error:
                print json.dumps(json_error,sort_keys=True,indent=4, separators=(',', ': '))
        except ValueError:
            pass
    finally:
        if f:  f.close()


def main():
    pass

if __name__ == '__main__':
    main()

# Run requset cert and export to pkcs12
RequestPKCS12(certpath, datename, webroot, domain)

# Run form post data
add_cert = FormPostAddCert(certpath, datename, secret)
pin_cert = FormPostPinCert(datename, interface)

# Post operation - install cert
PostRequest(url_cert, add_cert, headers, username, password)

# Post operation - pin cert to interface
if 'True' in pin:
    PostRequest(url_pin, pin_cert, headers, username, password)
