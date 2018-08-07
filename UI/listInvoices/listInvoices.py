from __future__ import print_function
from __future__ import division
import os, time
import json
import boto3
from boto3.dynamodb.conditions import Key, Attr
from botocore.vendored import requests

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

def addInvoice(record):
  table_name = "invoices"
  dynamodb = boto3.resource('dynamodb')
  t = dynamodb.Table(table_name)

  t_record = {}
  t_record['id'] = record['id']
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

def listItemHandler(event, context):
  if 'action' in event:
    action=event['action']
  else:
    action="Form"

  item = ""

  if 'item' in event:
    item = event['item']

  content = "<html><head><title>MXB Invoice Items</title></head><body>"
  content += "<h3>MXB Invoice Items</h3>"

  if action == 'Add':
    addItem(item)
  elif action == 'Delete':
    deleteItem(item)

  # Print out HTML content
  items = listItems()
  content += '<form method="POST">'
  content += '<table width="70%">'
  content += '<tr align="left"><th>ID</th><th>Item Name</th></tr>'
  for item in items:
    content += '<tr align="left"><td><input type="radio" name="id" value="'+str(item['id'])+'">'+str(item['id'])+'</td><td>'+item['name']+'</td></tr>'
  content += "</table>"
  content += '<input type=hidden name="action" value="Delete">'
  content += 'Select Item Above to Delete: <input type="submit" name="Delete" value="Delete">'
  content += '<input type="reset">'
  content += "</form>"
  content += '<form method="POST">'
  content += '<input type=hidden name="action" value="Add">'
  content += '<input type="text" name="item" value="">'
  content += 'Enter Item Name: <input type="submit" name="Add" value="Add">'
  content += '<input type="reset">'
  content += "</form>"
  content += '<a href="/PROD/listInvoice">Back to Invoices</a>'

  content += "</body></html>"
  return { 'statusCode': 200,
           'headers': {
              "Content-type": "text/html",
            },
            'body': content
          }

def addInvoiceHandler(event,context):
  if 'environment' in event:
    environment = event['environment']
  else:
    environment = 'production'

  paypal = getPayPalToken(environment)

  content = {}

  content['environment'] = environment

  if 'event_type' in event:
    event_type = event['event_type']
  else:
    event_type = 'INVOICING.INVOICE.UNKNOWN'

  content['event_type'] = event_type
  log_error("Event type = "+event_type)

  if 'invoice' in event:
    invoice = event['invoice']
    log_error('Invoice = '+invoice)
    record = getInvoiceData(environment,paypal,invoice)
    content['invoice'] = invoice
    if 'id' in record:
      if event_type == 'INVOICING.INVOICE.CREATED':
        addInvoice(record)
        content['status'] = "Success"
      elif event_type == 'INVOICING.INVOICE.PAID':
        updateInvoice(record)
        content['status'] = "Success"
      elif event_type == 'INVOICING.INVOICE.CANCELLED':
        cancelInvoice(record)
        content['status'] = "Success"
    else:
      content['status'] = "Failure"
  else:
    content['status'] = "Failure"

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
  content += '<tr align="left"><th>Invoice ID</th><th>Email</th><th>Status</th><th>Item Name</th><th>Amount</th><th>Invoice Date</th><th>Payment Amount</th><th>Payment Date</th><Payment Type</th></tr>'
  for invoice in invoices:
    content += '<tr align="left"><td><input type="radio" name="id" value="'+str(invoice['id'])+'">'+str(invoice['id'])+'</td><td>'+invoice['email']+'</td><td>'+invoice['invoice_status']+'</td><td>'+invoice['item']+'</td><td>'+invoice['amount']+'<td></td>'+invoice['invoice_date']+'</td>'
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
  content += '<form method="POST" action="/PROD/addItem">'
  content += '<input type=hidden name="action" value="Add">'
  content += '<input type="text" name="item" value="">'
  content += 'Enter Item Name: <input type="submit" name="Add" value="Add">'
  content += '<input type="reset">'
  content += "</form>"

  content += "</body></html>"
  return { 'statusCode': 200,
           'headers': {
              "Content-type": "text/html",
            },
            'body': content
          }
