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
table_name = "invoice_items"
t = dynamodb.Table(table_name)

def listItems():
  items = t.scan()

  return items['Items']

def addItem(item):
  record = {}
  record['id'] = int(time.time())
  record['name'] = item

  t.put_item(Item=record)

def deleteItem(item):
  t.delete_item(Key={ 'id': int(item) })

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
  content += '<table width="50%">'
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

  content += "</body></html>"
  return content
