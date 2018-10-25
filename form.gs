function onFormSubmit(e) {
  var data = {name: e.namedValues['Name'][0], email: e.namedValues['Email'][0], item: e.namedValues['Item'][0]};
  var environment = "production";
  
  if (data.item == "Tuition") {
    amount = "1995.00";
  } else if (data.item == "Camp") {
    amount = "600.00";
  }
    
  var token = getPayPaltoken(environment);
  
  var record = { email: data.email,
                item: data.item,
                amount: amount
               };
  
  createInvoice(environment,token,record);
}

function sendEmail(to,subject,msg) {
  MailApp.sendEmail({
    to: to,
    subject: subject,
    body: msg
  });
}
  
function getPayPaltoken(environment) {
  if (environment == "sandbox") {
    var url = "https://api.sandbox.paypal.com/v1/oauth2/token";
    var client_id = "AW4HmkW_Stq7L2yEDG3y4t1FOE2ZhCy2OhhoEGsiZW1PMdIOrgt91ivmSNzDJQ_6oz0ZO3AlUsD6St0h";
    var client_secret = "EGlGSkuBYzBU-fqfMSW4PaIvkILRP0hocVGqDGSKxvtEH5VWYJqjBgmEzyO843Rjv9ghZFx-yPpqjoyY";
  } else if (environment == "production") {
    var url = "https://api.paypal.com/v1/oauth2/token";
    var client_id = "AUj43NZcGsAerwMoJhlis09wQhPcrGiwy6mPmSWROqPB6v-_6lbDwO9E_RfgjXjZ5uvmQdYXoR0VKQga";
    var client_secret = "EGlGSkuBYzBU-fqfMSW4PaIvkILRP0hocVGqDGSKxvtEH5VWYJqjBgmEzyO843Rjv9ghZFx-yPpqjoyY";
  }
  
  var headers = { 'Accept': 'application/json',
              'Accept-Language': 'en_US',
              'Authorization': 'Basic ' + Utilities.base64Encode(client_id + ":" + client_secret)};
  
  var payload = { 'grant_type': 'client_credentials' };
  
  var options = {
    'method': 'post',
    'headers': headers,
    'payload': payload
  };
  
  //Logger.log("Calling fetch for "+url+' with Options: '+JSON.stringify(options)+' with Payload: '+JSON.stringify(payload));
  response = UrlFetchApp.fetch(url,options);
  //Logger.log("Response == "+response);
  body = JSON.parse(response.getContentText());
  
  return body['access_token'];
}

function sendPayPalInvoice(environment,paypal,id) {
  headers = { 'Content-Type': 'application/json',
              'Authorization': 'Bearer '+paypal};
  
  if (environment == "sandbox") {
    var url = "https://api.sandbox.paypal.com/v1/invoicing/invoices/"+id+"/send";
  } else if (environment == "production") {
    var url = "https://api.paypal.com/v1/invoicing/invoices/"+id+"/send";
  }
  
  var options = {
    'method': 'post',
    'headers': headers
  };
  
  //Logger.log("Calling fetch for "+url+' with Options: '+JSON.stringify(options));
  response = UrlFetchApp.fetch(url,options);
  if (response.getResponseCode() != 202) {
    sendEmail("canning@nejll.org","Unable to send invoice","Unable to send invoice "+id+", please check log files");
  }
}
  
function createInvoice(environment,paypal,record) {
  var headers = { 'Content-Type': 'application/json',
              'Authorization': 'Bearer '+paypal};
  
  if (environment == "sandbox") {
    var url = "https://api.sandbox.paypal.com/v1/invoicing/invoices/";
  } else if (environment == "production") {
    var url = "https://api.paypal.com/v1/invoicing/invoices/";
  }
  
  payload = { "merchant_info": {
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
               "email": record['email']
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
           "note": "Thank you for your business."
         };
  
  var options = {
    'method': 'post',
    'headers': headers,
    'payload': JSON.stringify(payload)
  };
  
  //Logger.log("Calling fetch for "+url+' with Options: '+JSON.stringify(options)+' with Payload: '+JSON.stringify(payload));
  response = UrlFetchApp.fetch(url,options);
  
  if (response.getResponseCode() == 201) {
    Logger.log("Successful invoice submission, getting invoice id");
    body = JSON.parse(response.getContentText());
    sendPayPalInvoice(environment,paypal,body['id'])
  } else {
    Logger.log("Unable to create invoice, sending email to admins");
    sendEmail('canning@nejll.org','Unable to create invoice','Unable to create invoice, please check logs');
  }
}