This script requests certificate from letsencrypt.org and installs it on cisco asa. Tested with python 3.7

# Requirements
Suppose you have vpn.domain.com. URL https://vpn.domain.com reserved for Cisco 'Anyconnect' portal and for connection to vpn with 'Anyconnect' client.
http://vpn.domain.com are server, where script will be used.
![OUTLINE](doc/outline.png)

Software:
1. Cisco ASA 9.6.3(1) and higher
2. Rest API 1.3.0 and higher
3. Python 3.7

The script uses webroot method for check you are owner of domain name. 

# Installation Centos 7
-------------------------------------------------------------------------
## Preparing.
Cisco asa:
```bash
ciscoasa(config)# boot system disk0:/asa963-17-smp-k8.bin
ciscoasa(config)# rest-api image disk0:/asa-restapi-132100-lfbff-k8.SPA
ciscoasa(config)# rest-api agent
```

Script-machine:
```bash
[netadmin@server]# yum install epel-release -y
[netadmin@server]# yum install nginx certbot -y
[netadmin@server]# mkdir -p /var/www/html/letsencrypt
[netadmin@server]# cat <<EOF >> /etc/nginx/conf.d/vpn.domain.com.conf
server {
    listen       80;
    server_name  vpn.domain.com;
    location ~ /\.well-known {
        root /var/www/html/letsencrypt/;
    }
}
EOF
[netadmin@server]# systemctl enable nginx
[netadmin@server]# systemctl start nginx
```
## Getting script

```bash
git clone https://github.com/nomyownnet/ca-asa-install.git
or
curl -O https://github.com/nomyownnet/ca-asa-install/archive/master.zip
```

## Filling params file

```bash
# Management ip address of cisco asa 
ipaddress: "10.0.0.1"
# Credentionals. Be sure, that your account has admin rights.
username: "admin"
password: "P@ssw0rd"
# Port of admin portal cisco asa, not vpn.
port: 443
# Interface cisco asa, on which anyconnect works. 
interface: "inside"
domain: "vpn.domain.com"
# Path to private key, cert and chain. Default value for Centos 7.
certpath: "/etc/letsencrypt/live/vpn.domain.com/"
# Path for check domain name
webroot: "/var/www/html/letsencrypt/"
# Email address for important account notifications from Let's Encrypt
email: "someone@example.com"
# Password for pkcs12. Be sure, that it's not 'root' or 'qwerty'
secret: "cisco"
# Getting test certificate.
testcert = False
# Import certificate to cisco asa with or without pinning to interface 
pin = True
```

## Run script. 
It can take the path to the config as argumnt. The default path is "../configs/config.yaml"
```bash
[netadmin@server]# ./certasainstall.py ../configs/config.yaml
The certificate has been installed succefully.
The certificate has been pinned to the interface.
```
## Verifying
The script creates trustpoint with current date as a name.

```bash
ciscoasa# sh crypto ca certificate trustpoint_name
CA Certificate
  Status: Available
  Certificate Serial Number: 4df42b95d1ee9b3a4c2eb33b8d105dd6
  Certificate Usage: Signature
  Public Key Type: RSA (2048 bits)
  Signature Algorithm: SHA256 with RSA Encryption
  Issuer Name: 
    cn=(STAGING) Pretend Pear X1
    o=(STAGING) Internet Security Research Group
    c=US
  Subject Name: 
    cn=(STAGING) Artificial Apricot R3
    o=(STAGING) Let's Encrypt
    c=US
  CRL Distribution Points: 
    [1]  http://stg-x1.c.lencr.org/
  Validity Date: 
    start date: 00:00:00 UTC Sep 4 2020
    end   date: 16:00:00 UTC Sep 15 2025
  Storage: config
  Associated Trustpoints: 20220621 

Certificate
  Status: Available
  Certificate Serial Number: 00fa91301208ae678236ea17cf95b885129f7b
  Certificate Usage: General Purpose
  Public Key Type: RSA (2048 bits)
  Signature Algorithm: SHA256 with RSA Encryption
  Issuer Name: 
    cn=(STAGING) Artificial Apricot R3
    o=(STAGING) Let's Encrypt
    c=US
  Subject Name:
    cn=vpn.domain.com
  OCSP AIA: 
    URL: http://stg-r3.o.lencr.org
  Validity Date: 
    start date: 22:18:15 UTC Jun 20 2022
    end   date: 22:18:14 UTC Sep 18 2022
  Storage: config
  Associated Trustpoints: 20220621 

ciscoasa# show run | i trust
... <truncated output>...
crypto ca trustpoint trustpoint_name
... <truncated output>...
ssl trust-point trustpoint_name vpn_interface
... <truncated output>...
```

## Possible errors
1. TrustPoint 'trustpoint_name' name is already assigned with CA certificate
```bash
Something went wrong.
{
    "messages": [
        {
            "code": "INVALID-INPUT",
            "context": "name",
            "details": "TrustPoint 'trustpoint_name' name is already assigned with CA certificate.",
            "level": "Error"
        }
    ]
}
```
Delete trustpoint from cisco asa.
```bash
ciscoasa(config)#no crypto ca trustpoint 20220621 noconfirm
```
2. Keypair name VPN_TP_Sep2013 already exist. 
Delete keypair from cisco asa.
```bash
ciscoasa(config)# crypto key zeroize rsa label trustpoint_name noconfirm
```

