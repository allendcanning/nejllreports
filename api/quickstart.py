#!/Library/Frameworks/Python.framework/Versions/3.6/bin/python3
"""
Shows basic usage of the Sheets API. Prints values from a Google Spreadsheet.
"""
from __future__ import print_function
from apiclient.discovery import build
from google.oauth2 import service_account
from httplib2 import Http
from oauth2client import file, client, tools

# Setup the Sheets API
SCOPES = ['https://www.googleapis.com/auth/spreadsheets']
SERVICE_ACCOUNT_FILE="service_secret.json"
store = file.Storage('credentials.json')
creds = store.get()
if not creds or creds.invalid:
    creds = service_account.Credentials.from_service_account_file(SERVICE_ACCOUNT_FILE, scopes=SCOPES)
service = build('sheets', 'v4', credentials=creds)

# Call the Sheets API
SPREADSHEET_ID = '1NY1Ue1OA_Yzm0lg7aG-ITH0hZSRdISe_ZhMlAtlXgXU'
RANGE_NAME = 'A2'
value_input_option='USER_ENTERED'

#result = service.spreadsheets().values().get(spreadsheetId=SPREADSHEET_ID,
#                                              range=RANGE_NAME).execute()
#values = result.get('values', [])
#if not values:
#    print('No data found.')
#else:
#    print('Name, Major:')
#    for row in values:
#        # Print columns A and E, which correspond to indices 0 and 4.
#        print('%s, %s' % (row[0], row[4]))

values=[ [ 'More', 'test', 'data', 1 ] ]
body = { 'values': values }

result = service.spreadsheets().values().update(spreadsheetId=SPREADSHEET_ID,
                                                range=RANGE_NAME, valueInputOption=value_input_option, body=body).execute()

print ('{0} cells updated.'.format(result.get('updatedCells')))
