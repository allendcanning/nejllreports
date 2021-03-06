from __future__ import print_function
import boto3
from boto3.dynamodb.conditions import Key, Attr
import json
from botocore.vendored import requests

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
    
  return content

