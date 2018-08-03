from __future__ import print_function
from __future__ import division

import os, time
from datetime import datetime
import boto3
from boto3.dynamodb.conditions import Key, Attr

os.environ['TZ'] = 'US/Eastern'
time.tzset()

dynamodb = boto3.resource('dynamodb')
# Connect to dynamo db table
table_name = "invoices"
t = dynamodb.Table(table_name)

def listInvoices():
  table_name = "invoices"
  t = dynamodb.Table(table_name)
  items = t.scan()

  return items['Items']

def cancelInvoice(record):

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
  content += '<table width="50%">'
  content += '<tr align="left"><th>Invoice ID</th><th>Email</th><th>Status</th><th>Item Name</th><th>Amount</th><th>Invoice Date</th><th>Payment Amount</th><th>Payment Date</th><Payment Type</th></tr>'
  for invoice in invoices:
    content += '<tr align="left"><td><input type="radio" name="id" value="'+str(invoices['id'])+'">'+str(item['id'])+'</td><td>'+invoice['email']+'</td><td>'+invoice['invoice_status']+'</td><td>'+invoice['item']+'</td><td>'+invoice['amount']+'<td></td>'+invoice['invoice_date']+'</td>'
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
  content += '<form method="POST">'
  content += '<input type=hidden name="action" value="Add">'
  content += '<input type="text" name="item" value="">'
  content += 'Enter Item Name: <input type="submit" name="Add" value="Add">'
  content += '<input type="reset">'
  content += "</form>"

  content += "</body></html>"
  return content
