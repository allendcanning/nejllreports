#!/Library/Frameworks/Python.framework/Versions/3.6/bin/python3

import json
import yaml
import requests
from optparse import OptionParser

def Usage():
  parser.print_help()

def get_credentials():
    """Gets valid user credentials from storage.

    If nothing has been stored, or if the stored credentials are invalid,
    the OAuth2 flow is completed to obtain the new credentials.

    Returns:
        Credentials, the obtained credential.
    """
    home_dir = os.path.expanduser('~')
    credential_dir = os.path.join(home_dir, '.credentials')
    if not os.path.exists(credential_dir):
        os.makedirs(credential_dir)
    credential_path = os.path.join(credential_dir,
                                   'nejll-contacts.json')

    store = Storage(credential_path)
    credentials = store.get()
    if not credentials or credentials.invalid:
        flow = client.flow_from_clientsecrets(CLIENT_SECRET_FILE, SCOPES)
        flow.user_agent = APPLICATION_NAME
        if flags:
            credentials = tools.run_flow(flow, store, flags)
        else: # Needed only for compatibility with Python 2.6
            credentials = tools.run(flow, store)
        print('Storing credentials to ' + credential_path)
    return credentials

# Begin main program
parser = OptionParser()
parser.add_option("-k","--invoice", dest="invoice", help="Invoice ID -- REQUIRED")
parser.add_option("-e","--email",dest="email", help="Email address -- REQUIRED")
parser.add_option("-i","--item",dest="item", help="Invoice Item -- REQUIRED")
parser.add_option("-s","--status",dest="status", help="Status -- REQUIRED")
parser.add_option("-a","--amount",dest="amount", help="Amount -- REQUIRED")

(options,args) = parser.parse_args()

if options.invoice:
  invoice = options.invoice
else:
  Usage()
  exit(1)

if options.email:
  email = options.email
else:
  Usage()
  exit(1)

if options.item:
  item = options.item
else:
  Usage()
  exit(1)

if options.status:
  status = options.status
else:
  Usage()
  exit(1)

if options.amount:
  amount = options.amount
else:
  Usage()
  exit(1)

credentials = get_credentials()


