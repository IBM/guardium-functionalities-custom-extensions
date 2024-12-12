
import requests
import json
import smtplib
import io
import os.path
import base64
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
import mimetypes
from email.mime.application import MIMEApplication

SCOPES = ['https://www.googleapis.com/auth/gmail.send']
SERVICE_ACCOUNT_FILE = './credentials.json'
SENDER_EMAIL_ADDRESS = 'SENDER_EMAIL_ADDRESS'
API_URL = 'GUARDIUM_API_URL'
API_KEY = 'WATSONX_API_KEY'

def authenticate_gmail():
    """Shows basic usage of the Gmail API.
    Lists the user's Gmail labels.
    """
    creds = None
    # The file token.json stores the user's access and refresh tokens, and is
    # created automatically when the authorization flow completes for the first
    # time.
    if os.path.exists('token.json'):
        creds = Credentials.from_authorized_user_file('token.json', SCOPES)
    # If there are no (valid) credentials available, let the user log in.
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                SERVICE_ACCOUNT_FILE, SCOPES)
            creds = flow.run_local_server(port=0)
        # Save the credentials for the next run
        with open('token.json', 'w') as token:
            token.write(creds.to_json())
    return creds

def create_message_with_attachment(sender, to, subject, body, file_path):
    """Create a message with an attachment."""
    message = MIMEMultipart()
    message['to'] = to
    message['from'] = sender
    message['subject'] = subject

    # Attach the body
    message.attach(MIMEText(body, 'html'))


    # Attach the file
    if file_path:
        content_type, encoding = mimetypes.guess_type(file_path)
        if content_type is None or encoding is not None:
            content_type = 'application/octet-stream'
        main_type, sub_type = content_type.split('/', 1)

        with open(file_path, 'rb') as f:
            attachment = MIMEApplication(f.read(), _subtype=sub_type)
            attachment.add_header(
                'Content-Disposition',
                'attachment',
                filename=os.path.basename(file_path)
            )
            message.attach(attachment)

    raw_message = base64.urlsafe_b64encode(message.as_bytes()).decode()
    return {'raw': raw_message}


def send_email(service, sender, to, subject, body, file_path):
    """Send an email message."""
    message = MIMEMultipart()
    message['to'] = to
    message['from'] = sender
    message['subject'] = subject

    message.attach(MIMEText(body, 'plain'))

    # raw_message = base64.urlsafe_b64encode(message.as_bytes()).decode()

    try:
        # message = service.users().messages().send(userId="me", body={'raw': raw_message}).execute()
        message = create_message_with_attachment(sender, to, subject, body, file_path)
        sent_message = service.users().messages().send(userId="me", body=message).execute()

        print('Message Id: %s' % sent_message['id'])
        return sent_message
    except Exception as error:
        print(f'An error occurred: {error}')

def main(params):

    try:
        startDate = params['startDate'] + ' 00:00:00'
        endDate = params['endDate'] + ' 23:59:00'
        reportName = params['reportName']
        userEmail = params['userEmail']
        username = params['username']
        password = params['password']

        tokenUrl = '${API_URL}/oauth/token'
        tokenBody = {
            "client_id": "client_id",
            "client_secret": "client_secret",
            "grant_type": "password",
            "username": username,
            "password": password
        }

        res = requests.post(tokenUrl, data=tokenBody, verify=False)
        response = res.json()

        if("error" in response and response['error'] == 'invalid_grant'):
            return {
                "headers": {
                    "Content-Type": "application/json",
                },
                "statusCode": 400,
                "body": {
                    'response' : response['error_description']
                },
            }
        
        accessToken = res.json()['access_token']

        if(res.status_code):
            reportUrl = "${API_URL}/restAPI/online_report"
            reportHeaders = {
                'Authorization': 'Bearer' + accessToken,
                'Content-Type': 'application/json'
            }

            reportBody = json.dumps({
                "reportName": reportName,
                "indexFrom": "1",
                "reportParameter": {
                    "QUERY_FROM_DATE": startDate,
                    "QUERY_TO_DATE": endDate,
                    "REMOTE_SOURCE": "%",
                    "SHOW_ALIASES": "",
                    "ServerIPLike": "%",
                    "ServerIPLike": "%",
                    "USER_NAME": "%",
                    "SOURCE_IP": "%",
                    "DESCRIPTION": "%",
                    "TARGET_IP": "%"
                }
            })

            reportResponse = requests.post(reportUrl, headers=reportHeaders, data=reportBody, verify=False).json()
            if(type(reportResponse) == dict and reportResponse['ID'] == '0'):
                return {
                    "headers": {
                        "Content-Type": "application/json",
                    },
                    "statusCode": 200,
                    "body": {
                        'response' : reportResponse['Message']
                    },
                }

            if(type(reportResponse) == dict and reportResponse['ErrorCode'] == "1001"):
                return {
                    "headers": {
                        "Content-Type": "application/json",
                    },
                    "statusCode": reportResponse['ErrorCode'],
                    "body": {
                        'response' : reportResponse['ErrorMessage']
                    },
                }
        
            REQ_URL = 'https://bam-api.res.ibm.com/v2/text/generation?version=2024-08-27'
            HEADERS = {
                'accept': 'application/json',
                'content-type': 'application/json',
                'Authorization': 'Bearer {}'.format(API_KEY)
            }
            
            llmPayload = {
                "model_id": "mistralai/mixtral-8x7b-instruct-v01",
                "parameters": {
                    "decoding_method": "greedy",
                    "min_new_tokens": 1,
                    "max_new_tokens": 16384
                },
                "moderations": {
                    "hap": {
                        "input": {
                            "enabled": True,
                            "threshold": 0.75
                        },
                        "output": {
                            "enabled": True,
                            "threshold": 0.75
                        }
                    }
                },
                "prompt_id": "prompt_builder",
                "data": {
                    "input": json.dumps(reportResponse),
                    "instruction": "Write a summary, from the perspective of an Enterprise Auditor, for a given "+reportName+" report starting with this statement 'Please find the summary of the " + reportName+ "'",
                    "input_prefix": "Input:",
                    "output_prefix": "Output:",
                    "examples": []
                }
            }

            response_llm = requests.post(REQ_URL, headers=HEADERS, data=json.dumps(llmPayload))
            response_llm_json = response_llm.json()

            creds = authenticate_gmail()
            service = build('gmail', 'v1', credentials=creds)

            sender = SENDER_EMAIL_ADDRESS
            to = userEmail
            subject = 'Summary of ' + reportName
            body = """\
    <html>
    <body>
        <p> Dear """ + userEmail + """,<br> </p>

        <p>I hope you’re doing well.</p>

        <p>Attached is a summarization of the """ + reportName + """ for your review. This document provides a concise overview of the key findings from the full report, including the most critical vulnerabilities identified and recommended actions.</p>
        <p> Feel free to <strong>let us</strong> know what content would be useful for you!</p>
        <p><b> Points included in the summary: </b></p>
        <ul>
            <li>Key Findings</li>
            <li>Observations</li>
        </ul>
        <p>Please take a moment to review the summary. Should you require the full report or have any questions, don’t hesitate to reach out.</p>
        <p> <b> Thank you for your time and attention. </b> </p>
    </body>
    </html>
    """
            file_path = './summary.txt'

            f = open(file_path, "x")
            f.write(response_llm_json['results'][0]['generated_text'])
            f.close()

            send_email(service, sender, to, subject, body, file_path)

            return {
                "headers": {
                    "Content-Type": "application/json",
                },
                "statusCode": 200,
                "body": {
                    'response': True,
                    # 'response' : reportResponse,
                    # 'instruction': "Write a summary, from the perspective of an Enterprise Auditor, for a given "+reportName+" report starting with this statement 'Please find the summary of the " + reportName+ ".'",
                    # 'summary': response_llm_json['results'][0]['generated_text']
                },
            }
    
    except Exception as e:
        print('e', e)
        print(f"Failed to execute the API {str(e)}")
