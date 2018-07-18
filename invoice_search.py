#!/Library/Frameworks/Python.framework/Versions/3.6/bin/python3

from __future__ import print_function
from apiclient.discovery import build
from google.oauth2 import service_account
from httplib2 import Http
from oauth2client import file, client, tools
import json
import yaml
import requests
import time
import collections
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

  data = { "status": ["SENT", "PAID"],
           "invoice_date": "2018-06-01 PDT",
           "page_size": 100 }

  #print ("Data = "+str(data))
  #print ("Calling URL = "+url)
  r = requests.post(url,headers=headers,data=json.dumps(data))

  body = r.json()
  #print("Body = "+r.text)

  count = 0
  for invoice in body['invoices']:
    #print(invoice)
    print(str(count)+" ID = "+invoice['id']+" status = "+invoice['status']+" Invoice date = "+invoice['invoice_date'])
    count = count + 1

  #print()
  return body['invoices']

def updateSheet(invoices):
  # Update Google sheet with invoice data

  # Setup the Sheets API
  SCOPES = ['https://www.googleapis.com/auth/spreadsheets']
  SERVICE_ACCOUNT_FILE="service_secret.json"

  creds = service_account.Credentials.from_service_account_file(SERVICE_ACCOUNT_FILE, scopes=SCOPES)
  service = build('sheets', 'v4', credentials=creds)

  # Call the Sheets API
  SPREADSHEET_ID = '1NY1Ue1OA_Yzm0lg7aG-ITH0hZSRdISe_ZhMlAtlXgXU'
  # always set to column 1
  range = collections.defaultdict(dict)
  range['SENT']['ROW'] = 1
  range['PAID']['ROW'] = 1
  COL = 'A'
  value_input_option='USER_ENTERED'

  # Clear the SENT sheet
  result = service.spreadsheets().values().clear(spreadsheetId=SPREADSHEET_ID,range='SENT').execute()
  # Clear the PAID sheet
  result = service.spreadsheets().values().clear(spreadsheetId=SPREADSHEET_ID,range='PAID').execute()
  
  for invoice in invoices:
    values = [ [ invoice['id'], invoice['status'], invoice['invoice_date'], invoice['billing_info'][0]['email'], invoice['total_amount']['value'] ] ]
    body = { 'values': values }

    result = service.spreadsheets().values().update(spreadsheetId=SPREADSHEET_ID,
                                                range=invoice['status']+'!'+COL+str(range[invoice['status']]['ROW']), valueInputOption=value_input_option, body=body).execute()
    time.sleep(1)
    range[invoice['status']]['ROW'] = range[invoice['status']]['ROW'] + 1

# Begin main program
parser = OptionParser()
parser.add_option("-e","--environment", dest="environment", help="Paypal Environment -- OPTIONAL defaults to sandbox [ sandbox, production ]")
parser.add_option("-f","--file",dest="credfile", help="Paypal Credential file (YAML) -- OPTIONAL defaults to paypal.yaml")
parser.add_option("-v","--verbose",dest="verbose", help="Verbose")

(options,args) = parser.parse_args()

if options.environment:
  environment = options.environment
else:
  environment = "sandbox"

if options.credfile:
  credfile = options.credfile
else:
  credfile = "paypal.yaml"

if options.verbose:
  verbose=True
else:
  verbose=False

paypal = getPayPalToken(credfile,environment)
invoices = getInvoices(environment,paypal)
updateSheet(invoices)

