import sys, os, json, time, re, asyncio, tkinter, mimetypes, threading
from copy import deepcopy
from tkinter import filedialog
from tkinter.messagebox import showerror, showinfo, showwarning

from src.utils.mime_process import parseMultipartMIME, createMIME
from src.utils.send_email import sendEmail, receiveEmails, checkRemoteSync, deleteRemoteEmail
from src.utils.filter_config import Filter, FilterConfig, readFilterConfig
from src.utils.config_socket_init import GeneralConfig, initSocket, readConfig
from src.utils.email_metadata import EmailMetadata, EmailStatus
from src.utils.string_utils import parseStringByDelim


class EmailClient:
    def __init__(self, defaultCategory='Inbox'):
        self.generalConfigPath = 'config/config.json'
        self.filterPath = 'config/filter.json'
        self.emailStatusMetadataPath = 'config/metadata.json'
        self.inboxDir = 'email'
        self.defaultCategory = defaultCategory
        self.defaultAutoloadTime = 60

        self.mutex = threading.Lock()

        #Maximum file size (in megabytes)
        self.maxImageSize = 3
        self.maxTextFileSize = 2
        self.maxVideoAudioFileSize = 5.5
        self.maxOtherFileSize = 3

        self.generalConfig = readConfig(self.generalConfigPath)
        self.filterConfig = readFilterConfig(self.filterPath)
        if self.generalConfig == None:
            self.generalConfig = GeneralConfig()
            self.generalConfig.configs['autoload'] = self.defaultAutoloadTime
        if self.filterConfig == None:
            self.filterConfig = FilterConfig()
            self.filterConfig.category_parent_dir_path = self.inboxDir
            self.filterConfig.default_category = defaultCategory
        self.emailStatusMetadata = EmailMetadata()
        self.emailStatusMetadata.readJSON(self.emailStatusMetadataPath)

    def sendEmailAPI(self, sendto: str, data: str, maxAttempt=10):
        for i in range(maxAttempt):
            sendResult = sendEmail(self.generalConfig, sendto, data)
            if sendResult == True:
                return True
        return False

    def receiveEmailAPI(self, index, receiveEmailDirectory: str=None, maxAttempt=10):
        if receiveEmailDirectory == None:
            emailDirectory = self.inboxDir
        else:
            emailDirectory = receiveEmailDirectory
        if self.emailStatusMetadata is None:
            newEmailMetadata = EmailMetadata()
        else:
            newEmailMetadata = deepcopy(self.emailStatusMetadata)
        for i in range(maxAttempt):
            receiveResult, newEmailMetadata = receiveEmails(self.generalConfig, index=index, receiveEmailDirectory=receiveEmailDirectory, emailMetadata=newEmailMetadata, maxAttempt=20)
            if receiveResult == True:
                with self.mutex:
                    self.emailStatusMetadata = newEmailMetadata
                return True
        return False

    def fetchFromServerAndMoveToFilter(self, redownloadEvenIfInSync=False, maxAttempt=20):
        metadata = EmailMetadata()
        
        serverStatus = (-1, -1)
        i = 0
        while serverStatus[0] == -1 and i < maxAttempt:
            serverStatus = checkRemoteSync(config=self.generalConfig, emailMetadata=self.emailStatusMetadata)
            i += 1
        if serverStatus[0] == 0 and redownloadEvenIfInSync == True:
            #Download from start if force download email
            result = self.receiveEmailAPI(-1, receiveEmailDirectory=self.inboxDir, maxAttempt=maxAttempt)
        elif serverStatus[0] > 0:
            result = self.receiveEmailAPI(serverStatus[0], receiveEmailDirectory=self.inboxDir, maxAttempt=maxAttempt)
        else: #serverStatus[0] == -1, failure checking
            return False
        
        if result == False:
            return result
        else:
            #If resync successfully, move emails to filters
            with self.mutex:
                for i in range(len(self.emailStatusMetadata.email_metadata_list)):
                    oldPath = self.emailStatusMetadata.email_metadata_list[i].emailPath
                    newEmailPathAfterFilter, newCategory = self.filterConfig.moveToCategory(oldPath)
                    if newEmailPathAfterFilter is not None:
                        self.emailStatusMetadata.email_metadata_list[i].emailPath = newEmailPathAfterFilter
                    if newCategory is not None:
                        self.emailStatusMetadata.email_metadata_list[i].category = newCategory
            return True

    def sendEmailFromUserInput(self, MIMEEmailStringDict: dict, maxAttempt=10):
        send_to_addr_str = MIMEEmailStringDict.get('To')
        cc_addr_str = MIMEEmailStringDict.get('CC')

        send_to_list = parseStringByDelim(send_to_addr_str, ',')
        from_address = self.generalConfig.configs['email_address']

        if from_address is None:
            from_address += ' <{}>'.format(MIMEEmailStringDict.get('From') if MIMEEmailStringDict.get('From') != None else '')
        
        statuses = list()
        finalResult = True

        subject = MIMEEmailStringDict.get('Subject') if MIMEEmailStringDict.get('Subject') != None else ''
        cc_list = parseStringByDelim(cc_addr_str, ',')
        bcc_list = parseStringByDelim(MIMEEmailStringDict.get('BCC'), ',')
        content = MIMEEmailStringDict.get('Content')
        attachment_list = MIMEEmailStringDict.get('Attachments')
        if type(attachment_list) == str:
            attachment_list = parseStringByDelim(attachment_list, ',')
        elif type(attachment_list) == list:
            attachment_list = [attachment for attachment in attachment_list if type(attachment) == str]

        #Mail to send to To and BCC recipents
        mail_without_bcc = createMIME(content, from_address, send_to=send_to_list, send_to_cc=send_to_list, subject=subject, attachments=attachment_list)
        receivers_without_bcc = send_to_list + cc_list
        for receiver in receivers_without_bcc:
            result = self.sendEmailAPI(receiver, mail_without_bcc, maxAttempt)
            if result == False:
                finalResult = False
                statuses.append("Sending email to {} failed".format(receiver))
        
        #Mail to send to CC recipents
        for receiver in bcc_list:
            mail_with_bcc = createMIME(content, from_address, send_to=send_to_list, send_to_cc=send_to_list, send_to_bcc=receiver, subject=subject, attachments=attachment_list)
            result = self.sendEmailAPI(receiver, mail_with_bcc, maxAttempt)
            if result == False:
                finalResult = False
                statuses.append("Sending email to {} failed".format(receiver))

        if finalResult == True: #No email sent failure
            statuses.append("All emails sent successfully")
        return finalResult, statuses

    def getConfig(self):
        username = self.generalConfig.configs.get('username')
        password = self.generalConfig.configs.get('password')
        POP3Port = self.generalConfig.configs.get('pop3_port')
        SMTPPort = self.generalConfig.configs.get('smtp_port')
        server = self.generalConfig.configs.get('server')
        emailAddress = self.generalConfig.configs.get('email_address')
        autoload = self.generalConfig.configs.get('autoload')

        result = dict()
        result['Username'] = username
        result['Password'] = password
        result['Address'] = emailAddress
        result['SMTP Port'] = SMTPPort
        result['POP3 Port'] = POP3Port
        result['Server'] = server
        result['Autoload'] = int(autoload)
        return result

    def saveConfig(self, configStringDict: dict, saveToPath=None, defaultPOP3Port=2225, defaultSMTPPort=3335, maxAttempt=3):
        if saveToPath == None:
            savePath = self.generalConfigPath
        else:
            savePath = saveToPath

        username = configStringDict.get('Username')
        password = configStringDict.get('Password')
        POP3Port = configStringDict.get('POP3 Port') or defaultPOP3Port
        SMTPPort = configStringDict.get('SMTP Port') or defaultSMTPPort
        address = configStringDict.get('Address')
        server = configStringDict.get('Server')
        try:
            autoload = int(configStringDict.get('Autoload'))
        except:
            autoload = self.defaultAutoloadTime
        
        if username is None or username == '':
            showerror("Invalid configuration", "Username mustn't be empty")
            return False
        
        if password is None or username == '':
            showerror("Invalid configuration", "Password mustn't be empty")
            return False
        if address is None or username == '':
            showerror("Invalid configuration", "Email address mustn't be empty")
            return False
        if server is None or username == '':
            showerror("Invalid configuration", "Server address mustn't be empty")
            return False
        
        newConfig = GeneralConfig()
        newConfig.addConfig('username', username)
        newConfig.addConfig('password', password)
        newConfig.addConfig('email_address', address)
        newConfig.addConfig('server', server)
        newConfig.addConfig('smtp_port', SMTPPort)
        newConfig.addConfig('pop3_port', POP3Port)
        newConfig.addConfig('autoload', autoload)

        for i in range(maxAttempt):
            result = newConfig.toJSON(savePath)
            if result == True:
                self.generalConfig = newConfig
                return True
        return False

    def addFilter(self, filterStringDict: dict):
        newFilter = Filter()
        category = filterStringDict.get('Category')
        from_address_keyword_str = filterStringDict.get('From')
        subject_keyword_str = filterStringDict.get('Subject')
        content_keyword_str = filterStringDict.get('Content')
        subject_or_content_keyword_str = filterStringDict.get('Subject or Content')

        #Check for empty category or filter with no keyword
        if category == '' or (from_address_keyword_str == '' and subject_keyword_str == ''
                            and content_keyword_str == '' and subject_or_content_keyword_str == ''):
            return False
        if category == None or (from_address_keyword_str == None and subject_keyword_str == None
                            and content_keyword_str == None and subject_or_content_keyword_str == None):
            return False
        #Check for each
        from_address_keywords = parseStringByDelim(from_address_keyword_str, ',')
        subject_keywords = parseStringByDelim(subject_keyword_str, ',')
        content_keywords = parseStringByDelim(content_keyword_str, ',')
        subject_or_content_keywords = parseStringByDelim(subject_or_content_keyword_str, ',')

        #Add filter
        newFilter.directory = category
        newFilter.address_from = from_address_keywords
        newFilter.subject = subject_keywords
        newFilter.content = content_keywords
        newFilter.subject_or_content = subject_or_content_keywords

        self.filterConfig.addFilter(newFilter)
        return True

    def deleteFilter(self, categoryName=None, index=None):
        if categoryName is None and index is None:
            return True #No category or index to delete

        numberOfFilters = len(self.filterConfig.filters)
        i = 0
        while i < numberOfFilters:
            filter = self.filterConfig.filters[i]
            if index == i:
                self.filterConfig.filters.pop(i)
                return True
            if categoryName == filter.directory:
                self.filterConfig.filters.pop(i)
                return True
            i += 1 
        return False

    def showFilters(self):
        result = dict()
        result['email_directory'] = self.filterConfig.category_parent_dir_path
        result['default_category'] = self.filterConfig.default_category
        result['filter_list'] = list()
        for filter in self.filterConfig.filters:
            filter_json_dict = dict()
            filter_json_dict['Category'] = filter.directory
            filter_json_dict['From'] = filter.address_from
            filter_json_dict['Subject'] = filter.subject
            filter_json_dict['Content'] = filter.content
            filter_json_dict['Subject_or_Content'] = filter.subject_or_content
            result['filter_list'].append(filter_json_dict)
        return result
    
    def getFilter(self, category: str):
        result = dict()
        for filter in self.filterConfig.filters:
            if filter.directory == category:
                filter_json_dict = dict()
                filter_json_dict['Category'] = filter.directory
                filter_json_dict['From'] = filter.address_from
                filter_json_dict['Subject'] = filter.subject
                filter_json_dict['Content'] = filter.content
                filter_json_dict['Subject_or_Content'] = filter.subject_or_content
                result = filter_json_dict
                return result
        return None

    def readEmail(self, position, getAttachments=False, attachmentDirectory=None):
        result = dict()
        with self.mutex:
            for i in range(len(self.emailStatusMetadata.email_metadata_list)):
                email_status = self.emailStatusMetadata.email_metadata_list[i]
                if email_status.position == position:
                    email_headers = parseMultipartMIME(email_status.emailPath, attachment_download_dir=attachmentDirectory, download_text=False, 
                                getEmailHeaderValues=True, doNotGetAttachments=(not getAttachments))
                    if email_headers is not None:
                        self.currentEmail = position
                        email_status.isRead = True
                        from_addresses = email_headers.get('From')
                        to_addresses = email_headers.get('To')
                        cc_addresses = email_headers.get('CC')
                        bcc_address = email_headers.get('BCC')
                        subject = email_headers.get('Subject')
                        content_list = email_headers.get('Content')
                        attachments = email_headers.get('Attachments')
                        from_addresses = from_addresses if from_addresses is not None else ''
                        to_addresses = to_addresses if to_addresses is not None else ''
                        cc_addresses = cc_addresses if cc_addresses is not None else ''
                        bcc_address = bcc_address if bcc_address is not None else ''
                        subject = subject if to_addresses is not None else ''
                        attachments = attachments if attachments is not None or len(attachments)>0 else ''

                        result['Result'] = True
                        result['From'] = from_addresses
                        result['To'] = to_addresses
                        result['CC'] = cc_addresses
                        result['BCC'] =  bcc_address
                        result['Subject'] = subject
                        result['Content'] = content_list
                        result['Attachments'] = attachments
                        return result
        #Email at index not found
        result['Result'] = False
        return result

    def showAllEmails(self):
        result = list()
        with self.mutex:
            for i in range(len(self.emailStatusMetadata.email_metadata_list)):
                email_status = self.emailStatusMetadata.email_metadata_list[i]
                email_headers = parseMultipartMIME(email_status.emailPath, attachment_download_dir=None, download_text=False, getEmailHeaderValues=True, 
                                doNotGetAttachments=True)
                isRead = email_status.isRead
                category = email_status.category if email_status.category != '' else 'Undefined'
                if email_headers is not None:
                    email_data = dict()
                    
                    self.currentEmail = email_status.position
                    from_addresses = email_headers.get('From')
                    subject = email_headers.get('Subject')
                    from_addresses = from_addresses if from_addresses is not None else ''
                    subject = subject if subject is not None else ''
                    subject = subject[:37] +'...' if len(subject) > 40 else subject #Cut subject preview to not exceed 40 chars
                    email_preview = '<{}> {}'.format(from_addresses, subject)

                    email_data['isRead'] = isRead
                    email_data['position'] = int(email_status.position)
                    email_data['category'] = category
                    email_data['preview'] = email_preview
                    result.append(email_data)
            
        return result

    def showAllCategories(self):
        categories_count = dict()
        with self.mutex:
            for i in range(len(self.emailStatusMetadata.email_metadata_list)):
                email_status = self.emailStatusMetadata.email_metadata_list[i]
                category = email_status.category
                if category not in categories_count.keys():
                    categories_count[category] = 0
                else:
                    categories_count[category] += 1
        
        return categories_count
        
      
    def showEmailInCategory(self, category: str):
        result = list()
        with self.mutex:
            for i in range(len(self.emailStatusMetadata.email_metadata_list)):
                email_status = self.emailStatusMetadata.email_metadata_list[i]
                email_category = email_status.category
                if category == email_category:
                    email_headers = parseMultipartMIME(email_status.emailPath, attachment_download_dir=None, download_text=False, getEmailHeaderValues=True, 
                                doNotGetAttachments=True)
                    isRead = email_status.isRead is True #check if email is read
                    email_data = dict()
                    if email_headers is not None:
                        currentEmailPosition = email_status.position
                        from_addresses = email_headers.get('From')
                        subject = email_headers.get('Subject')
                        from_addresses = from_addresses if from_addresses is not None else ''
                        subject = subject if subject is not None else ''
                        subject = subject[:37] +'...' if len(subject) > 40 else subject #Cut subject preview to not exceed 40 chars
                        email_preview = '<{}> {}'.format(from_addresses, subject)

                        email_data['isRead'] = isRead
                        email_data['position'] = currentEmailPosition
                        email_data['category'] = category
                        email_data['preview'] = email_preview
                        result.append(email_data)
        return result



    def markAllEmailAsRead(self):
        with self.mutex:
            for i in range(len(self.emailStatusMetadata.email_metadata_list)):
                email_status = self.emailStatusMetadata.email_metadata_list[i]
                email_status.isRead = True

    #Don't mutex this as the method call this already has a mutex
    def updateMetadataAfterDelete(self, deleteIndex):
        for i in range(len(self.emailStatusMetadata.email_metadata_list)):
            email_status = self.emailStatusMetadata.email_metadata_list[i]
            if email_status.position > deleteIndex:
                email_status.position = email_status.position - 1
    
    def deleteEmail(self, index, deleteLocalCopy=True):
        result = False
        with self.mutex:
            for i in range(len(self.emailStatusMetadata.email_metadata_list)):
                email_status = self.emailStatusMetadata.email_metadata_list[i]
                if index == email_status.position:
                    email_status.isPendingRemoval = True
                    result, status_text = deleteRemoteEmail(self.generalConfig, self.emailStatusMetadata, index, deleteLocalCopy)
                    print(status_text)
                    if result == True:
                        self.emailStatusMetadata.email_metadata_list.pop(i)
                        self.updateMetadataAfterDelete(index)
                        continue
                #Delete all pending removal email as well
                if email_status.isPendingRemoval == True:
                    pending_result, status_text = deleteRemoteEmail(self.generalConfig, self.emailStatusMetadata, email_status.position, deleteLocalCopy)
                    print(status_text)
                    if pending_result == True:
                        self.emailStatusMetadata.email_metadata_list.pop(i)
                        self.updateMetadataAfterDelete(index)
                        continue
        return result

    def saveCurrentConfigAndFilters(self):
        with self.mutex:
            self.emailStatusMetadata.toJSON(self.emailStatusMetadataPath)
            self.generalConfig.toJSON(self.generalConfigPath)
            self.filterConfig.toJSON(self.filterPath)
            return

    def getAttachments(self, useGUI=False):
        attachmentList = list()
        attachment_limit_text = 'Limit for each attachment:\nText: {} MB\nImage: {} MB\nVideo and Audio: {} MB\nOthers: {} MB'.format(
                self.maxTextFileSize, self.maxImageSize, self.maxVideoAudioFileSize, self.maxOtherFileSize)
        if useGUI == True:
            showinfo('Choose attachment limit', attachment_limit_text)
            attachmentList = filedialog.askopenfilenames()
            if len(attachmentList) == 0: #User press Cancel button
                showwarning('Choosing attachment cancelled', 'Choosing attachment cancelled')
                return None
        else:
            print('Input attachment file names, enter \'end\' to stop adding: ')
            print(attachment_limit_text)
            attachmentName = ''
            while True:
                attachmentName = input()
                if attachmentName == 'end':
                    break
                attachmentList.append(attachmentName)
            if len(attachmentList) == 0: #User press Cancel button
                print('Choosing attachment cancelled')
                return None
        for attachment in attachmentList:
            if os.path.isfile(attachment) == False or os.path.islink(attachment) == True:
                #Show warning message if the attachment doesn't exist or is a directory/symlink 
                if useGUI == True:
                    showwarning('Attachment {} does not exist or not a file'.format(attachment))
                else:
                    print('Attachment file {} does not exist or not a file'.format(attachment))
                return None
            mimetypes.init()
            attachment_mimetype = mimetypes.guess_type(attachment)[0]
            if attachment_mimetype == None:
                file_limit = int(self.maxOtherFileSize*1024*1024)
            else:
                attachment_filetype = attachment_mimetype.split('/')[0]
                if attachment_filetype == 'audio' or attachment_filetype == 'video':
                    file_limit = int(self.maxVideoAudioFileSize*1024*1024)
                elif attachment_filetype == 'image':
                    file_limit = int(self.maxImageSize*1024*1024)
                elif attachment_filetype == 'text':
                    file_limit = int(self.maxTextFileSize*1024*1024)
                else:
                    file_limit = int(self.maxOtherFileSize*1024*1024)
            
            try:
                file_size = os.path.getsize(attachment)
                if file_size > file_limit:
                    if useGUI == True:
                        showwarning('Attachment size is over limit', attachment_limit_text)
                    else:
                        print('Attachment size is over limit. ', attachment_limit_text)
                    return None
            except OSError:
                if useGUI == True:
                    showwarning('OS Error. Cannot get file attributes (size)')
                else:
                    print('OS Error. Cannot get file attributes (size)')
                return None
        return attachmentList

    #Destructor, this will call the method which save the config and email statuses when the object is garbage collected
    def __del__(self):
        self.saveCurrentConfigAndFilters()

    def autoload(self, actionAfterLoad=None):
        autoload = self.generalConfig.configs['autoload']
        if autoload == 0: #Disable autoload if autoload == 10
            return 
        #TODO:
        while True:
            with self.mutex:
                self.fetchFromServerAndMoveToFilter(redownloadEvenIfInSync=False)
            if actionAfterLoad != None:
                actionAfterLoad()
            time.sleep(float(autoload))

def test():
    email = {'From': "tony2@smtp.test.com",
    'Content': "This is a test mail. \r\n Something shouldn't go wrong here.\n Hello world!",
    'To': 'tony2@smtp.test.com',
    'CC': 'natsume@test.com,tony@test.com',
    'BCC': 'test1@test.com',
    'Subject': 'IMPORTANT: Test email',
    'Attachments': 'test.json'}
    important_filter = {
        'Category': 'Important',
        'From': 'natsume@test.com,tony_s@test.com',
        'Subject': 'IMPORTANT,ASAP',
        'Content': 'pls',
        'Subject or Content': '[IMPORTANT],IMPORTANT,Read this ASAP,'
    }
    spam_filter = {
        'Category': 'Spam',
        'Content': '100% free,99% discount',
        'Subject': 'Advertisement',
        'Subject or Content': '[Advertisement],Free account'
    }

    general_configs = {'Username': 'natsume', 'Address': 'natsume2@smtp.test.com', 'Password': '12345678', 'SMTP Port': '2225'
    , 'POP3 Port': '3335', 'Server': '127.0.0.1'}
    

    client = EmailClient()
    attachments = client.getAttachments(useGUI=True)
    print(attachments)
    client.saveConfig(configStringDict=general_configs, maxAttempt=20)

    client.deleteFilter(categoryName='Spam')
    client.deleteFilter(categoryName='Important')

    client.addFilter(important_filter)
    client.addFilter(spam_filter)
    failures, statuses = client.sendEmailFromUserInput(email, maxAttempt=20)
    for status in statuses:
        print(status)

    result = client.fetchFromServerAndMoveToFilter(redownloadEvenIfInSync=False)
    print(result)
    client.saveCurrentConfigAndFilters()
    client.showAllEmails()
    client.showFilters()
    result = client.readEmail(1)
    print(result)
    
    result = client.deleteEmail(1, deleteLocalCopy=True)
    print(result)
    
if __name__ == "__main__":
    test()