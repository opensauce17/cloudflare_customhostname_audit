#!/usr/bin/env python

# Import include files
from bin.includes.imports import *

env = Environment(
    loader=FileSystemLoader('%s/templates/' % os.path.dirname(__file__)))
data = config_json_read()
content_type = data['auth']['content_type']
email = data['auth']['email']
token = data['auth']['token']
toemail = data['email_config']['to_email']
fromemail = data['email_config']['from_email']
relayserver = data['email_config']['relay_server']

def send_mail(bodyContent):
    """
    This function delivers the html email with the report attached in a zip file
    """
    today_date = date.today()
    today_date = today_date.strftime("%d %b, %Y")
    to_email = toemail
    from_email = fromemail
    subject = 'Daily Cloudflare Certificate Inventory for ' + str(today_date)
    message = MIMEMultipart()
    message['Subject'] = subject
    message['From'] = from_email
    message['To'] = to_email

    message.attach(MIMEText(bodyContent, "html"))
    try:
        date_today = date.today()
        filename = 'inventory/cloudflare_certificate_report_{}.csv'.format(date_today)
        with open(filename, "rb") as attachment:

            part = MIMEBase("application", "csv")
            part.set_payload(attachment.read())

            # Encode file in ASCII characters to send by email
            encoders.encode_base64(part)

            # Add header as key/value pair to attachment part
            part.add_header(
                "Content-Disposition",
                f"attachment; filename= {filename}",
            )
            message.attach(part)

    except Exception as e:
        print('Attachment Error ' + e)
        exit()
    msgBody = message.as_string()

    server = SMTP(relayserver, 25)
    server.sendmail(from_email, to_email, msgBody)
    server.quit()

def get_expiration_data():
    """
    This function gathers the certificate expiration data for all hosts in all zones.
    It filters out hosts certiti
    """
    expire_data = []
    zones = match_zones_and_ids()
    for k,v in zones.items():
        zone = k
        zone_id = v
        zone_data = get_all_data(v)
        today_date = date.today()
        for i in zone_data:
            for d in i:
                expire_date = d['ssl']['certificates'][0]['expires_on'].replace("T", " ").replace("Z", " ")
                date_time_obj = datetime.strptime(expire_date, '%Y-%m-%d %H:%M:%S ')
                expire_date = date_time_obj.date()
                days_to_expire = expire_date - today_date
                if days_to_expire.days <= 60:
                    expire_day = d['ssl']['certificates'][0]['expires_on'].replace("T", " ").replace("Z", " ")
                    date_time_obj = datetime.strptime(expire_day, '%Y-%m-%d %H:%M:%S ')
                    expire_day = date_time_obj.date()
                    hostname = d['hostname']
                    expire_data.append({ "hostname": hostname, "expire_date": str(expire_day), "cloudflare_zone": zone })
    return expire_data

def match_zones_and_ids():
    """
    This function matches the zones to the ids in the configuration file
    :return:
    """
    data = config_json_read()
    zones = []
    ids = []
    z = data['zones']
    z_i = data['zone_ids']

    for k, v in z.items():
        z_values = v
        zones.append(z_values)

    for k, v in z_i.items():
        zid_values = v
        ids.append(zid_values)

    dict_of_zones = dict(zip(zones, ids))
    return dict_of_zones

def get_total_pages(zone_id):
    """
    This function returns the total amount of pages. It is used by the get_all_data function
    :return:
    """
    url = 'https://api.cloudflare.com/client/v4/zones/{}/custom_hostnames?per_page=50'

    headers = {
        'Content-Type': content_type,
        'X-Auth-Email': email,
        'X-Auth-Key': token
    }

    r = requests.get(url.format(zone_id), headers=headers)

    result = json.loads(r.text)

    total_pages = (result['result_info']['total_pages'])

    return total_pages

def get_data_per_page(page, zone_id):
    """
    This function is used by the get_all_data function to get data for all pages.
    :param page:
    :return:
    """
    url = 'https://api.cloudflare.com/client/v4/zones/{}/custom_hostnames?' \
          'page={}&per_page=50'
    headers = {
        'Content-Type': content_type,
        'X-Auth-Email': email,
        'X-Auth-Key': token
    }

    r = requests.get(url.format(zone_id, page), headers=headers)

    result = json.loads(r.text)
    custom_hostnames = result['result']
    return custom_hostnames


def get_all_data(zone_id):
    """
    This function returns a list of all hostname data
    :return:
    """
    total_pages = get_total_pages(zone_id)
    cs = []
    for i in range(1, total_pages + 1):
        d = get_data_per_page(i, zone_id)
        cs.append(d)
    return cs

def get_all_hostnames():
    """
    This function returns a list of all hostnames
    :return:
    """
    hostnames = []
    d = get_all_data()
    for i in d:
        for a in i:
            hostnames.append(a['hostname'])
    return hostnames

def send_email_report():
    """
    This function prepares the html template data for the email report
    It then calls the send_mail function to deliver the email report
    """
    get_data = get_expiration_data()
    today_date = date.today()
    today_date = today_date.strftime("%d %b, %Y")
    template = env.get_template('child.html')
    output = template.render(data=get_data, date=today_date)
    send_mail(output)

def cleanup():
    """
    This function cleans up the created csv files and the zip file
    """
    today_date = date.today()
    filename_csv = 'inventory/cloudflare_certificate_report_{}.csv'.format(today_date)
    os.remove(filename_csv)

def combine_csv():
    """
    This function combines all the zone csv file into a single csv
    It also removes all the individual csv files
    """
    today_date = date.today()
    os.chdir('inventory')
    extension = 'csv'
    all_filenames = [i for i in glob.glob('*.{}'.format(extension))]
    combined_csv = pd.concat([pd.read_csv(f) for f in all_filenames])
    combined_csv.to_csv("cloudflare_certificate_report_{}.csv".format(today_date), index=False, encoding='utf-8-sig')
    files = glob.glob('zones-*')
    for f in files:
        os.remove(f)
    os.chdir('../')

def produce_inventory_files():
    """
    This function uses the Cloudflare API to create the per zone csv file
    """
    zones = match_zones_and_ids()

    for k,v in zones.items():
        f = open("inventory/zones-{}.csv".format(k), "a")
        f.write('Expiry Date' + ',' + 'Hostname' + ',' + 'SANS' + ',' + 'Issuer' + ',' 
        + 'Origin' + ',' + 'Zone' + ',' + 'Hostname Status' + ',' +
         'Issued Date' + ',' + 'Minimum TLS Version' + ',' + 'Cipher' + ','
        + 'http2' + ',' + 'TLS 1.3' + '\n')
        f.close

    for k,v in zones.items():
        zone = k
        zone_id = v
        zone_data = get_all_data(v)
        for i in zone_data:
            for d in i:
                hostname = d['hostname']
                try:
                    origin = d['custom_origin_server']
                except KeyError:
                    origin = "Not Available"
                status = d['ssl']['status']
                sans = d['ssl']['hosts']
                try:
                    issuer = d['ssl']['issuer']
                except KeyError:
                    issuer = d['ssl']['certificates'][0]['issuer']
                issued_date = d['ssl']['certificates'][0]['issued_on']
                expire_date = d['ssl']['certificates'][0]['expires_on'].replace("T", " ").replace("Z", " ")
                date_time_obj = datetime.strptime(expire_date, '%Y-%m-%d %H:%M:%S ')
                expire_date = date_time_obj.date()
                expire_date = expire_date.strftime("%d-%b-%y")
                try:
                    min_tls_version = d['ssl']['settings']['min_tls_version']
                except KeyError:
                    min_tls_version = "Not Available"
                try: 
                    ciphers = d['ssl']['settings']['ciphers']
                except KeyError:
                    ciphers = ["Not Available"]
                try:
                    http2 = d['ssl']['settings']['http2']
                except KeyError:
                    http2 = "Not Available"
                try:
                    tls_1_3 = d['ssl']['settings']['tls_1_3']
                except KeyError:
                    tls_1_3 = "Not Available"

                f = open("inventory/zones-{}.csv".format(zone), "a")

                f.write(expire_date + ',' + hostname + ',' + " ".join(sans) + ',' + issuer + ','
                + origin + ',' + zone + ',' + status + ','
                + issued_date + ',' + min_tls_version + ',' + " ".join(ciphers) + ','
                + http2 + ',' + tls_1_3 + '\n')

                f.close


if __name__ == "__main__":
    produce_inventory_files()
    combine_csv()
    send_email_report()
    cleanup()
