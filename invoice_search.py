#!/Library/Frameworks/Python.framework/Versions/3.6/bin/python3

import json
import yaml
import requests
from optparse import OptionParser

def log_error(msg):
  print(msg)

def getPayPalToken(infile,environment):
  with open(infile, 'r') as stream:
    try:
      y = yaml.load(stream)
    except yaml.YAMLError as e:
      log_error(e)
      exit(1)

  if environment == "sandbox":
    url = "https://api.sandbox.paypal.com/v1/oauth2/token"
  elif environment == "production":
    url = "https://api.paypal.com/v1/oauth2/token"

  headers = { 'Accept': 'application/json',
              'Accept-Language': 'en_US'}

  data = "grant_type=client_credentials"

  r = requests.post(url,auth=(y["environment"][environment]['client_id'],y["environment"][environment]['client_secret']),headers=headers,data=data)

  body = r.json()

  return body['access_token']

def getInvoiceData(environment,paypal,invoice):
  # Set authorization header
  headers = {'Content-Type': 'application/json',
             'Authorization': 'Bearer '+paypal}

  if environment == "sandbox":
    url = "https://api.sandbox.paypal.com/v1/invoicing/invoices/"+invoice
  elif environment == "production":
    url = "https://api.paypal.com/v1/invoicing/invoices/"+invoice
  
  r = requests.get(url,headers=headers)
  body = r.json()
  #print("Body = "+r.text)

  return body

def getInvoices(environment,paypal):
  # Set headers for content and authorization
  headers = { 'Content-Type': 'application/json',
              'Authorization': 'Bearer '+paypal}

  # Get paypal url based on environment
  if environment == "sandbox":
    url = "https://api.sandbox.paypal.com/v1/invoicing/search/"
  elif environment == "production":
    url = "https://api.paypal.com/v1/invoicing/search/"

  data = { 'invoice_date': '2018-06-01 PDT',
           'page_size': 100
  }

  #print ("Data = "+str(data))
  #print ("Calling URL = "+url)
  r = requests.post(url,headers=headers,data=json.dumps(data))

  body = r.json()
  #print("Body = "+r.text)

  count = 0
  #for invoice in body['invoices']:
  #  print(str(count)+" ID = "+invoice['id']+" status = "+invoice['status']+" Invoice date = "+invoice['invoice_date'])
  #  count = count + 1

  #print()
  return body['invoices']

def updateSheet(invoices):
  # Update Google sheet with invoice data

  google_auth="nejllreports"
  #for each invoice in invoices:
    # Find in sheets
    # Update status

# Begin main program
parser = OptionParser()
parser.add_option("-e","--environment", dest="environment", help="Paypal Environment -- OPTIONAL defaults to sandbox [ sandbox, production ]")
parser.add_option("-f","--file",dest="credfile", help="Paypal Credential file (YAML) -- OPTIONAL defaults to paypal.yaml")

(options,args) = parser.parse_args()

if options.environment:
  environment = options.environment
else:
  environment = "sandbox"

if options.credfile:
  credfile = options.credfile
else:
  credfile = "paypal.yaml"

paypal = getPayPalToken(credfile,environment)
invoices = getInvoices(environment,paypal)
for invoice in invoices:
  invoice_data = getInvoiceData(environment,paypal,invoice['id'])
  print(" ID = "+invoice_data['id']+" status = "+invoice_data['status']+" Invoice date = "+invoice_data['invoice_date']+" Email = "+invoice_data['billing_info'][0]['email'])
  for item in invoice_data['items']:
    print("    Item = "+item['name']+" Amount = "+item['unit_price']['value'])
  #updateSheet(environment,paypal,invoices)

