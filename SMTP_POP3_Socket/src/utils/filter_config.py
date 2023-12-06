import json, string, shutil
import io, os, sys, mimetypes, platform, ntpath
import base64
import re
import email
from pathlib import Path
from src.utils.string_utils import parseStringByDelim
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

def path_leaf(path):
    head, tail = ntpath.split(path)
    return tail or ntpath.basename(head)

#Filter class, which defines a filter
# self.directory: Directory to put the email if it meet the conditions of the filter (relative or absolute directory)
# self.address_from: Filter keywords/email addresses (scope: Address where the email was sent)
# self.subject: Filter keywords in email's subject
# self.content: Filter keywords in email's content
# self.subject_or_content: Filter keywords in email's subject and content
class Filter:
    def __init__(self):
        self.directory = ''
        self.address_from = list()
        self.subject = list()
        self.content = list()
        self.subject_or_content = list()
    def toDict(self):
        res = dict()
        res['directory'] = self.directory
        res['address_from'] = self.address_from
        res['subject'] = self.subject
        res['content'] = self.content
        res['subject_or_content'] = self.subject_or_content
        return res
    #email_mime_or_file: A email content string in MIME format if isFilePath is False
    #Otherwises, if isFilePath is True, treat email_mime_or_file as a relative/absolute path
    # to a MIME email file
    #Return False if file not found or not meet the conditions of the filter or not in MIME format, True if
    #the MIME email file/string meets the conditions of the filter 
    def isInFilter(self, email_mime_or_file, isFilePath=False, filterTextAttachment=False):
        if isFilePath == True:
            try:
                with open(email_mime_or_file, 'r+') as fp:
                    message = email.message_from_file(fp)
            except FileNotFoundError:
                return False
        else:
            message = email_mime_or_file

        #Keywords
        address_from = self.address_from if self.address_from != None else list()
        subject = self.subject if self.subject != None else list()
        subject_or_content = self.subject_or_content if self.subject_or_content != None else list()
        content_keywords = self.content if self.content != None else list()

        for part in message.walk():
            from_addresses = part.get_all("From") 
            if from_addresses is not None:
                for address in from_addresses:
                    for keyword in address_from:
                        if keyword in address:
                            #If any From address contain any keyword in the filter, return True
                            return True
            subjects = part.get_all("Subject")
            if subjects is not None:
                for subject in subjects:
                    for keyword in subject:
                        if keyword in subject:
                            return True
                    for keyword in subject_or_content:
                        if keyword in subject:
                            return True
            if part.get_content_maintype() == "multipart":
                continue #Multipart part does not contain payload

            #If isFilterAttachment is False, this function will not filter attachment
            #Else this function will also filter text attachment as well
            if ((part.get_content_maintype() == "text" and part.get_content_disposition() != "attachment")
            or (part.get_content_maintype() == "text" and part.get_content_disposition() != "attachment" 
            and filterTextAttachment==True)):
                content = part.get_payload(decode=False)
                for keyword in content_keywords:
                    if keyword in content:
                        return True
   

class FilterConfig:
    def __init__(self):
        self.filters = list()
        #Parent directory path containing the email category directories
        self.category_parent_dir_path = None 
        self.default_category = None

    def addFilter(self, filter: Filter):
        self.filters.append(filter)
    
    def toJSON(self, jsonFile):
        filterConfig = dict()
        filter_list = list()
        email_category_dir = self.category_parent_dir_path if self.category_parent_dir_path is not None else ''
        default_category = self.default_category if self.default_category is not None else ''
        filter_list['email_category_dir'] =  email_category_dir
        filter_list.append['default_category'] = default_category
        #Only objects such as list or dict can be converted to JSON string
        for filter in self.filters:
            filter_list.append(filter.toDict())
        filterConfig['filter_list'] = filter_list
        with open(jsonFile, 'w') as writeJSON:
            json.dump(filterConfig, writeJSON)

    #Return None if the email is not moved, or the new path to the email file if it is in any category
    def moveToCategory(self, email_file_path):
        current_run_path = os.getcwd()
        filename = path_leaf(email_file_path)
        
        if os.path.isabs(email_file_path) == False: #email_file_path is relative
            email_full_path = os.path.join(current_run_path, email_file_path)
        else:
            email_full_path = email_file_path
        #Create email categories parent directory full path
        if self.category_parent_dir_path == None:
            category_current_path = current_run_path
        elif os.path.isabs(self.category_parent_dir_path) == False:
            category_current_path = os.path.join(current_run_path, self.category_parent_dir_path)
        else:
            category_current_path = self.category_parent_dir_path

        for filter in self.filters:
            if filter.isInFilter(email_file_path, isFilePath=True) == True:
                if filter.directory is None:
                    return None, None
                else:
                    category = filter.directory
                    full_path = os.path.join(category_current_path, filter.directory)

                    try:
                        os.mkdir(category_current_path)
                    except FileExistsError:
                        pass
                    try:
                        os.mkdir(full_path)
                    except FileExistsError:
                        pass

                    try:
                        shutil.move(email_full_path, os.path.join(full_path, filename))
                    except:
                        return None, None
                
                return os.path.join(full_path, filename), category
        #Move to default category
        try:
            full_path = os.path.join(category_current_path, self.default_category)
            os.mkdir(full_path)
        except FileExistsError:
            pass
        try:
            shutil.move(email_full_path, os.path.join(full_path, filename))
        except:
            return None, None
        return os.path.join(full_path, filename), self.default_category

def readFilterConfig(configFile):
    try:
        configObj = FilterConfig()
        with open(configFile, 'r') as readConfig:
            json_str = readConfig.read()
            configs = json.loads(json_str)

        configObj.category_parent_dir_path = configs.get('email_category_dir')
        filter_list = configs.get('filter_list') if configs.get('filter_list') != None else list()
        configObj.default_category = configs.get('default_category') if configs.get('default_category') != None else ''
        
        for i in range(len(filter_list)):
            filter = Filter()
            filter.directory = filter_list[i].get('directory')
            filter.address_from = filter_list[i].get('address_from')
            filter.content = filter_list[i].get('content')
            filter.subject = filter_list[i].get('subject')
            filter.subject_or_content = filter_list[i].get('subject_or_content')
            configObj.addFilter(filter)
        return configObj
    except:
        return None               
