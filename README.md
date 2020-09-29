# Cloudflare Custom Hostname Audit #

### Requirements ###

* python 3.6 or later
* create a virtual environment in the project root, in a folder called .env and install required libraries from requirements.txt

### The Report Script ###

The report.py script produces a single csv file with custom hostname domain certificate details for all cloudflare zones. The csv file will have the following columns:

* Expiry Date
* Hostname
* SANS
* Issuer
* Origin Server
* Zone
* Hostname Status
* Issued Date
* Minimum TLS Version
* Cipher
* http2
* TLS 1.3

It will then email the report to the required recipients as well as report on the domain certificates that are to expire in 60 days or less. 
