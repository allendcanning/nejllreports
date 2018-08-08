from __future__ import print_function
from __future__ import division
import os, time
import json
import boto3
from boto3.dynamodb.conditions import Key, Attr
from botocore.vendored import requests
from urllib.parse import unquote_plus

os.environ['TZ'] = 'US/Eastern'
time.tzset()

dynamodb = boto3.resource('dynamodb')
# Connect to dynamo db table
table_name = "invoices"
t = dynamodb.Table(table_name)

def log_error(msg):
  print(msg)

def getPayPalToken(environment):
  client = boto3.client('ssm')

  if environment == "sandbox":
    url = "https://api.sandbox.paypal.com/v1/oauth2/token"
  elif environment == "production":
    url = "https://api.paypal.com/v1/oauth2/token"

  ssmpath="/paypal/"+environment+"/client_id"
  response = client.get_parameter(Name=ssmpath,WithDecryption=False)

  client_id = response['Parameter']['Value']

  ssmpath="/paypal/"+environment+"/client_secret"
  response = client.get_parameter(Name=ssmpath,WithDecryption=True)

  client_secret = response['Parameter']['Value']

  headers = { 'Accept': 'application/json',
              'Accept-Language': 'en_US'}

  data = "grant_type=client_credentials"

  r = requests.post(url,auth=(client_id,client_secret),headers=headers,data=data)

  body = r.json()

  return body['access_token']

def listItems():
  table_name = "invoice_items"
  t = dynamodb.Table(table_name)
  items = t.scan()

  return items['Items']

def addItem(item):
  record = {}
  record['id'] = int(time.time())
  record['name'] = item

  table_name = "invoice_items"
  t = dynamodb.Table(table_name)
  t.put_item(Item=record)

def deleteItem(item):
  table_name = "invoice_items"
  t = dynamodb.Table(table_name)
  t.delete_item(Key={ 'id': int(item) })

def getInvoiceData(environment,paypal,invoice):
  # Set authorization header
  headers = {'Content-Type': 'application/json',
             'Authorization': 'Bearer '+paypal}

  if environment == "sandbox":
    url = "https://api.sandbox.paypal.com/v1/invoicing/invoices/"+invoice
  elif environment == "production":
    url = "https://api.paypal.com/v1/invoicing/invoices/"+invoice

  log_error("looking up invoice "+invoice)

  r = requests.get(url,headers=headers)
  body = r.json()
  if 'id' in body:
    return body
  else:
    log_error("Error finding invoice: "+invoice)
    return {}

def sendInvoice(environment,paypal,invoice):
  # Set headers for content and authorization
  headers = { 'Content-Type': 'application/json',
              'Authorization': 'Bearer '+paypal}

  # Get paypal url based on environment
  if environment == "sandbox":
    url = "https://api.sandbox.paypal.com/v1/invoicing/invoices/"+invoice+"/send"
  elif environment == "production":
    url = "https://api.paypal.com/v1/invoicing/invoices/"+invoice+"/send"

  r = requests.post(url,headers=headers)

  if r.status_code == 202:
    print("Successfully sent invoice "+invoice)

def createInvoice(environment,paypal,record):
  # Set headers for content and authorization
  headers = { 'Content-Type': 'application/json',
              'Authorization': 'Bearer '+paypal}

  # Get paypal url based on environment
  if environment == "sandbox":
    url = "https://api.sandbox.paypal.com/v1/invoicing/invoices/"
  elif environment == "production":
    url = "https://api.paypal.com/v1/invoicing/invoices/"

  data = { "merchant_info": {
             "email": "paypal@nejll.org",
             "first_name": "Allen",
             "last_name": "Canning",
             "business_name": "NEJLL",
             "phone": {
               "country_code": "001",
               "national_number": "9788076564"
             },
             "address": {
               "line1": "65 Marblehead St",
               "city": "North Andover",
               "state": "MA",
               "postal_code": "08145",
               "country_code": "US"
             },
           },
           "billing_info": [
             {
               "email": record['email'],
             }
           ],
           "items": [
             {
               "name": record['item'],
               "quantity": 1,
               "unit_price": {
                 "currency": "USD",
                "value": record['amount']
               }
             }
           ],
           "note": "Thank you for your business.",
         }

  r = requests.post(url,headers=headers,data=json.dumps(data))

  if r.status_code == 201:
    body = r.json()
    sendInvoice(environment,paypal,body['id'])
    addInvoice(body)
    body['status'] = 'Success'
    return body
  else:
    return { "status": "Failure" }

def addInvoice(record):
  table_name = "invoices"
  dynamodb = boto3.resource('dynamodb')
  t = dynamodb.Table(table_name)

  t_record = {}
  t_record['id'] = record['id']
  t_record['invoice_id'] = record['number']
  t_record['invoice_date'] = record['invoice_date']
  t_record['invoice_status'] = record['status']
  t_record['email'] = record['billing_info'][0]['email']
  t_record['amount'] = record['total_amount']['value']
  t_record['item'] = record['items'][0]['name']

  t.put_item(Item=t_record)

def updateInvoice(record):
  table_name = "invoices"
  dynamodb = boto3.resource('dynamodb')
  t = dynamodb.Table(table_name)

  try:
    response = t.get_item(
      Key={ 'id': record['id'],
            'invoice_date': record['invoice_date']
          }
    )
  except ClientError as e:
    log_error("Error is"+e.response['Error']['Message'])
    # Record doesn't exist so we add it
    t_record = {}
    t_record['id'] = record['id']
    t_record['invoice_id'] = record['number']
    t_record['invoice_date'] = record['invoice_date']
    t_record['invoice_status'] = record['status']
    t_record['email'] = record['billing_info'][0]['email']
    t_record['amount'] = record['total_amount']['value']
    t_record['item'] = record['items'][0]['name']

    t.put_item(Item=t_record)
  else:
    log_error("Updating record")
    if record['status'] == 'PAID':
      t.update_item(
        Key={
             'id': record['id'],
             'invoice_date': record['invoice_date']
        },
        UpdateExpression="set payment_type=:pt, payment_date=:pd, payment_amount=:pa",
        ExpressionAttributeValues={
          ':pt': record['payments'][0]['type'],
          ':pd': record['payments'][0]['date'],
          ':pa': record['payments'][0]['amount']['value']
        }
      )

def cancelInvoice(record):
  table_name = "invoices"
  dynamodb = boto3.resource('dynamodb')
  t = dynamodb.Table(table_name)

  try:
    response = t.get_item(
      Key={ 'id': record['id'],
            'invoice_date': record['invoice_date']
          }
    )
  except ClientError as e:
    log_error("Error is"+e.response['Error']['Message'])
    # Record doesn't exist so we add it
    t_record = {}
    t_record['id'] = record['id']
    t_record['invoice_id'] = record['number']
    t_record['invoice_date'] = record['invoice_date']
    t_record['invoice_status'] = record['status']
    t_record['email'] = record['billing_info'][0]['email']
    t_record['amount'] = record['total_amount']['value']
    t_record['item'] = record['items'][0]['name']

    t.put_item(Item=t_record)
  else:
    log_error("Updating record")
    if record['status'] == 'CANCELLED':
      t.update_item(
        Key={
             'id': record['id'],
             'invoice_date': record['invoice_date']
        },
        UpdateExpression="set invoice_status=:st",
        ExpressionAttributeValues={
          ':st': record['status']
        }
      )

def listInvoices():
  table_name = "invoices"
  t = dynamodb.Table(table_name)
  items = t.scan()

  return items['Items']

def addItemHandler(event, context):
  if 'body' in event:
    # Parse the post parameters
    postparams = event['body']
    for token in postparams.split('&'):
      key = token.split('=')[0]
      value = token.split('=')[1]
      if key == 'item':
        item = unquote_plus(value)

  if item != '':
    addItem(item)
    content = "Successfully added item: "+item
  else:
    content = "No item to add"

  content += '<p><a href="/Prod/listInvoice">Back to Invoices</a>'
  return { 'statusCode': 200,
           'headers': {
              "Content-type": "text/html",
            },
            'body': content
          }

def addInvoiceHandler(event,context):
  record = {}

  # Parse the post parameters
  if 'body' in event:
    postparams = event['body']
    if '&' in postparams:
      for token in postparams.split('&'):
        key = token.split('=')[0]
        value = token.split('=')[1]
        if key == 'action':
          action = unquote_plus(value)
        if key == 'environment':
          environment = unquote_plus(value)
        else:
          environment = "production"
        if key == 'email':
          email = unquote_plus(value)
        if key == 'item':
          item = unquote_plus(value)
        if key == 'amount':
          amount = unquote_plus(value)
    else:
      key = postparams.split('=')[0]
      value = postparams.split('=')[1]
      if key == 'action':
        action = unquote_plus(value)
      if key == 'environment':
        environment = unquote_plus(value)
      else:
        environment = "production"

  paypal = getPayPalToken(environment)

  if action == 'Form':
    items = listItems()
    content = "<html><head><title>MXB Create Invoice</title></head><body>"
    content += "<h3>MXB Create Invoice</h3>"

    content += '<form method="post" action="">'
    content += '<input type="hidden" name="action" value="Process">'
    content += '<p>Enter billing email address: <input type="email" name="email">'
    content += '<p>Select billing item: <select name="item">'
    for item in items:
      content += '<option value="'+item['name']+'">'+item['name']+'</option>'
    content += '</select>'
    content += '<p>Enter amount: $<input type="text" name="amount">'
    content += '<input type="submit" value="Create Invoice">'
    content += '</form></body></html>'
  elif action == 'Process':
    result = createInvoice(environment,paypal,record)
    if 'status' in result:
      if result['status'] == 'Success':
        content = '<p>Successfully added invoice '+result['number']+'<p><a href="/Prod/listInvoice">Back to Invoices</a>'
      else:
        content = '<p>Failed to add invoice'

  return { 'statusCode': 200,
           'headers': {
              "Content-type": "text/html",
            },
            'body': content
          }


def listInvoiceHandler(event, context):
  if 'action' in event:
    action=event['action']
  else:
    action="Form"
  
  invoice = ""
  
  if 'invoice' in event:
    invoice = event['invoice']
    
  content = "<html><head><title>MXB Invoices</title></head><body>"
  content += "<h3>MXB Invoices</h3>"

  if action == 'Cancel':
    cancelInvoice(invoice)

  # Print out HTML content
  invoices = listInvoices()
  content += '<form method="POST">'
  content += '<table width="85%">'
  content += '<tr align="left"><th>Invoice ID</th><th>Email</th><th>Status</th><th>Item Name</th><th>Amount</th><th>Invoice Date</th><th>Payment Amount</th><th>Payment Date</th><th>Payment Type</th></tr>'
  for invoice in invoices:
    content += '<tr align="left"><td><input type="radio" name="id" value="'+str(invoice['id'])+'">'+str(invoice['invoice_id'])+'</td><td>'+invoice['email']+'</td><td>'+invoice['invoice_status']+'</td><td>'+invoice['item']+'</td><td>'+invoice['amount']+'</td><td>'+invoice['invoice_date']+'</td>'
    if 'payment_amount' in invoice:
      content += '<td>'+invoice['payment_amount']+'</td>'
    else:
      content += '<td>&nbsp;</td>'
    if 'payment_date' in invoice:
      content += '<td>'+invoice['payment_date']+'</td>'
    else:
      content += '<td>&nbsp;</td>'
    if 'payment_type' in invoice:
      content += '<td>'+invoice['payment_type']+'</td>'
    else:
      content += '<td>&nbsp;</td>'
    content += '</tr>'
  content += "</table>"
  content += '<input type=hidden name="action" value="Cancel">'
  content += 'Select Invoice Above to Cancel: <input type="submit" name="Cancel" value="Cancel">'
  content += '<input type="reset">'
  content += "</form>"
  content += '<hr><form method="POST" action="/Prod/addInvoice">'
  content += '<input type="hidden" name="action" value="Form">'
  content += '<input type="submit" value="Add Invoice">'
  content += '</form>'
  content += '<hr><form method="POST" action="/Prod/addItem">'
  content += '<input type=hidden name="action" value="Add">'
  content += 'Enter Item Name: <input type="text" name="item" value="">'
  content += '<input type="submit" name="Add" value="Add">'
  content += '<input type="reset">'
  content += "</form>"

  content += "</body></html>"
  return { 'statusCode': 200,
           'headers': {
              "Content-type": "text/html",
            },
            'body': content
          }
