import io, os, sys, mimetypes, platform, ntpath
import base64
import re
import email
from pathlib import Path
# Python's email library does not include any utility for SMTP object/protocol, so it's fine
# This library is only used for create MIME message/header (without boilterplate code)
from email import message_from_string
from email import encoders
from email.message import Message
from email.mime.audio import MIMEAudio
from email.mime.application import MIMEApplication
from email.mime.base import MIMEBase
from email.mime.image import MIMEImage
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.parser import Parser

COMMASPACE = ', '
def removeRedundantSlashInPath(path):
    #POSIX compliant OSes such as Linux or MacOS, backslashes can be valid file names
    if os.name == 'posix': 
        if len(path) >= 2 and path[-1] == '/':
            return path[:-1]
        else:
            return path
    elif os.name == 'nt' or os.name == 'ce': #MS Windows
        if path == "..\\" or path == ".\\" or path == "./" or path == "../":
            return path #Relative paths
        if len(path) == 3 and (path[-2:] == ":\\" or path[-2:] == ":/"):
            return path #Drive path
        if path[-1] == '\\' or path[-1] == '/':
            return path[:-1]
    else:
        if len(path) >= 2 and path[-1] == '/':
            return path[:-1]
        else:
            return path
# emailText: Email text (should be plain text, html or markdown or other kinds of text list them in the attachments)
# emailfrom: Address sending email from
# send_to: A list of strings of address to send to (must have at least one)
# send_to_cc: (optional) A list of string of address to send to as CC
# send_to_bcc: A string of address to send to as BCC (If there are multiple BCCs, just call this function for each)
# subject: (optional) Subject of the email
# attachments: (optional) List of absolute/relative paths (for example: C:\Users\example\example.txt for Windows, /home/example/example.txt for Linux/UNIX)
def createMIME(emailText, emailfrom, send_to, send_to_cc=None, send_to_bcc=None, subject=None, attachments=None):
    #No send_to, email without repicent
    if send_to is None:
        return None
    #String of receivers that will be shown, will on include 'To' and 'CC', not 'BCC'
    receiver_string = COMMASPACE.join(send_to)
    
    email_message = MIMEMultipart()
    email_message['Subject'] = subject if subject is not None else ''
    email_message['From'] = emailfrom
    email_message['To'] = receiver_string
    if send_to_cc is not None:
        cc_string = COMMASPACE.join(send_to_cc)
        email_message['CC'] = cc_string
    
    if send_to_bcc is not None:
        email_message['BCC'] = send_to_bcc
    
    email_main_text = MIMEText(emailText, 'plain')
    email_message.attach(email_main_text)

    if attachments is not None:
        for filename in attachments:
            if not os.path.isfile(filename):
                continue #Don't sure if need to raise an error here
            ctype, encoding = mimetypes.guess_type(filename)
            if ctype is None or encoding is not None:
                #No guess could be made, or if the file is encoded (compressed),
                #use the generic octet-stream type
                ctype = 'application/octet-stream'
            maintype, subtype = ctype.split('/', 1)
            if maintype == 'text':
                with open(filename) as fp:
                    #Note: We should handle calculating the charset
                    attach_msg = MIMEText(fp.read(), _subtype=subtype)
            elif maintype == 'image':
                with open(filename, 'rb') as fp:
                    attach_msg = MIMEImage(fp.read(), _subtype=subtype)
            elif maintype == 'audio':
                with open(filename, 'rb') as fp:
                    attach_msg = MIMEAudio(fp.read(), _subtype=subtype)
            else:
                with open(filename, 'rb') as fp:
                    attach_msg = MIMEBase(maintype, subtype)
                    attach_msg.set_payload(fp.read())
                #Encode the payload using Base64
                encoders.encode_base64(attach_msg)
            #Set the filename parameter

            file_n = removeRedundantSlashInPath(filename)
            #Only get file name, not full path
            head, tail = ntpath.split(file_n)
            file_n = tail or ntpath.basename(head)

            attach_msg.add_header('Content-Disposition', 'attachment', filename=file_n)
            email_message.attach(attach_msg)
    
    return email_message.as_string()

#Parse multipart MIME and store all files (both content and attachments)
def parseMultipartMIME(mail_file, attachment_download_dir=None, download_text=False, getEmailHeaderValues=False, doNotGetAttachments=False):
    with open(mail_file) as fp:
        message = email.message_from_file(fp)
    #No need to create attachment folder if calling this function with getting attachments
    if doNotGetAttachments == False:
        try:
            if attachment_download_dir is None:
                #Folder containing all attachments (and downloaded text files)
                attachment_dir = mail_file + "-mailfile-attachments"
            else:
                attachment_dir = attachment_download_dir
            os.mkdir(attachment_dir)
        except FileExistsError:
            pass
        except:
            return None
    
    non_attachment_text = list() #List of text files that aren't attachments 
    header_values = dict()
    attachment_names = list()
    #(if download_text is True this will download all files regardless if that file is attachment or not)
    counter = 1
    for part in message.walk():
        if part.get_content_maintype() == "multipart":
            continue
        if part.get_content_maintype() == "text" and part.get_content_disposition != "attachment" and download_text == False:
            payload = part.get_payload(decode=True)
            #If the payload is binary string, convert it to Python string
            charset = part.get_charsets() 
            if charset != None: #If there's a charset specified
                #Get the charset of the message part
                charset = charset[0] if charset[0] != None else 'utf-8' 
            else:
                charset = 'utf-8'
            if isinstance(payload, bytes):
                payload = payload.decode(charset)
            non_attachment_text.append(payload)
        else:
            #Should have sanitize the file name here 
            #so that an email message can't be used to overwrite important files
            filename = part.get_filename()
            if not filename:
                extension = mimetypes.guess_extension(part.get_content_type())
                if not extension:
                    extension = '.bin'
                filename = 'part%03d%s' % (counter, extension)
            attachment_names.append(filename)
            counter += 1
            if doNotGetAttachments == False:
                try:
                    with open(os.path.join(attachment_dir, filename), 'wb') as fp:
                        fp.write(part.get_payload(decode=True))
                except:
                    continue
    if getEmailHeaderValues == True:
        header_values['From'] = message.get('From')
        header_values['To'] = message.get('To')
        header_values['CC'] = message.get('CC') 
        header_values['BCC'] = message.get('BCC')
        header_values['Subject'] = message.get('Subject')
        header_values['Content'] = non_attachment_text
        header_values['Attachments'] = attachment_names
    if getEmailHeaderValues == False:
        return non_attachment_text
    else:
        return header_values

    
    
    



