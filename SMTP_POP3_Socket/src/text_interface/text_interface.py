from src.client.api import EmailClient
import os, sys
import threading

class SMTPClientConsoleInterface:
    def __init__(self):
        self.client = EmailClient()
        #Create a new thread for autoload
        self.autoloadThread = threading.Thread(target=self.client.autoload, daemon=True)
        self.autoloadThread.start()
        self.client.fetchFromServerAndMoveToFilter()

        self.selection = dict()
        self.selection['1'] = ('1. Send email', self.sendEmail)
        self.selection['2'] = ('2. Show all emails', self.showAllEmail)
        self.selection['3'] = ('3. Show email by category', self.showEmailByCategory)
        self.selection['4'] = ('4. Read email', self.readEmail)
        self.selection['5'] = ('5. Delete emails', self.deleteEmail)
        self.selection['6'] = ('6. Show all filters', self.showAllFilter)
        self.selection['7'] = ('7. Show filter by category', self.showFilter)
        self.selection['8'] = ('8. Add filter', self.addFilter)
        self.selection['9'] = ('9. Delete filter', self.deleteFilter)
        self.selection['10'] = ('10. Show configuration', self.printConfig)
        self.selection['11'] = ('11. Change configuration', self.changeConfig)
        self.selection['12'] = ('12. Refetch emails from server', self.refetchEmailFromServer)

    def refetchEmailFromServer(self):
        result = self.client.fetchFromServerAndMoveToFilter(redownloadEvenIfInSync=False)
        if result == True:
            print('Refetch from remote server failed.')
        else:
            print('Refetch from remote server successfully.')

    def sendEmail(self):
        email = dict()
        email['To'] = input('Enter addresses to send this email to, seperated by comma, escape by backslash: ')
        if email['To'] == '' or email['To'] == None:
            print('No email address to send to')
            return
            #To do: Maybe also using regex to check if email typed is valid or not
        
        email['CC'] = input('Enter CC addresses of this email, seperated by comma, escape by backslash: ')
        email['BCC'] = input('Enter BCC addresses of this email, seperated by comma, escape by backslash: ')
        email['Subject'] = input('Enter subject of this email:')
        print('Enter content of this email, press Ctrl+D (MacOS, Linux) or Ctrl+Z+Enter (Windows) to complete \r\n')
        email['Content'] = sys.stdin.read()
        print('\r\n')
        
        email['Attachments'] = self.client.getAttachments(useGUI=False)
        if email['Attachments'] == None:
            email['Attachments'] == list() #empty list meaning no attachment
        result, statuses = self.client.sendEmailFromUserInput(email, maxAttempt=15)
        if result == False:
            for status in statuses:
                print( status)
        else:
            for status in statuses:
                print(status)
        return

    def showAllEmail(self):
        email_status_list = self.client.showAllEmails()
        for email_status in email_status_list:
            isEmailRead = True if email_status['isRead'] == True or email_status['isRead'] == 'True' else False
            category = email_status['category'] if email_status['category'] != None else ''
            try:
                positionOnServer = int(email_status['position'])
            except:
                continue
            preview = email_status['preview']
            isEmailRead = 'R' if isEmailRead == True else 'NR'
            print('[{}-{}][{}]:{}'.format(str(positionOnServer), isEmailRead, category, preview))
        return

    def showEmailByCategory(self):
        self.showAllCategories()
        category = input('Enter category, enter \'Show all\' for all emails: ')
        if category == 'Show all':
            email_status_list = self.client.showAllEmails()
        else:
            email_status_list = self.client.showEmailInCategory(category)
        for email_status in email_status_list:
            isEmailRead = True if email_status['isRead'] == True or email_status['isRead'] == 'True' else False
            try:
                positionOnServer = int(email_status['position'])
            except:
                continue
            preview = email_status['preview']
            isEmailRead = 'R' if isEmailRead == True else 'NR'
            print('[{}-{}]:{}'.format(str(positionOnServer), isEmailRead, preview))
        return
        
    def showAllCategories(self):
        list_of_categories = self.client.showAllCategories()
        categories = list(list_of_categories.keys())
        print('List of categories: ')
        for i in range(len(categories)):
            print(str(i), ': ', categories[i])
        print('-'*45, '\r\n')

    def readEmail(self):
        try:
            position = input('Enter the index of the email you want to read:')
            position = int(position)
        except:
            print('Invalid index')
            return
        fetchAttachment = input('Do you want to get attachment for the email? Enter yes or no: ')
        if fetchAttachment == 'yes':
            directory = input('Enter directory for attachments: ')
            if os.path.isdir(directory) == False:
                print('Error: Directory not found')
            if directory == '':
                print('Error: Empty directory')
            
            result = self.client.readEmail(position=position, getAttachments=True, attachmentDirectory=directory)
        else:
            result = self.client.readEmail(position=position, getAttachments=False)
        if result.get('Result') == True:
            print('From:', result['From'])
            print('To:',result['To'])
            print('CC:',result['CC'])
            print('BCC:',result['BCC'])
            print('Subject:',result['Subject'])
            if len(result['Attachments']) == 0:
                attachmentStr = ''
            elif len(result['Attachments']) == 1:
                attachmentStr = result['Attachments'][0]
            else:
                attachmentStr = ','.join(result['Attachments'])
            
            if len(result['Content']) == 0:
                contentStr = ''
            elif len(result['Content']) == 1:
                contentStr = result['Content'][0]
            else:
                contentStr = '\r\n\r\n'.join(result['Content'])

            print('Attachments:', attachmentStr)
            print('Content:', contentStr)

            self.client.saveMetadata()
    
    
    def deleteEmail(self):
        try:
            position = input('Enter the index of the email you want to delete:')
            position = int(position)
        except:
            print('Invalid index')
            return
        result = self.client.deleteEmail(index=position, deleteLocalCopy=True)
        if result == True:
            print('Delete email successfully')
        else:
            print('Delete email failed')
        self.client.saveMetadata()
        
        return

    def showAllFilter(self):
        filters = self.client.showFilters()
        print('List of filters:')
        for filter in filters['filter_list']:
            print('Category: ', filter.get('Category'))
            print('From address keywords:', filter.get('From'))
            print('Subject:' ,filter.get('Subject'))
            print('Content:', filter.get('Content'))
            print('Keywords in subject or content:', filter.get('Subject_or_Content'))

    def showFilter(self):
        filters = self.client.showFilters()
        print('List of filters:')
        for filter in filters['filter_list']:
            print(filter['Category'])
        print('-'*45, '\r\n')
        category = input('Enter category name, enter \'Show all\' to show all filter: ')

        filter = self.client.getFilter(category)
        if filter == None:
            print('Filter {} does not found.'.format(category))
            return
        filter_category = filter.get('Category') 
        from_address_keywords = filter.get('From')
        subject_keywords = filter.get('Subject')
        content_keywords = filter.get('Content')
        subject_or_content_keywords = filter.get('Subject_or_Content')

        return

    def addFilter(self):
        filter_category = input('Enter category name (mustn\'t be empty):')
        from_address_keywords = input('Enter all from address keywords for this category, seperated by comma, escape by backslash.')
        subject_keywords = input('Enter all subject keywords for this category, seperated by comma, escape by backslash.')
        content_keywords = input('Enter all content keywords for this category, seperated by comma, escape by backslash.')
        subject_or_content_keywords = input('Enter all keywords appear in either subject or content for this category, seperated by comma, escape by backslash.')
        
        if filter_category == '' or (from_address_keywords == '' and subject_keywords == '' 
        and content_keywords == '' and subject_or_content_keywords == ''):
            print('Category or keywords mustn\'t be empty')
            return

        filter = dict()
        filter['Category'] = filter_category
        filter['From'] = from_address_keywords
        filter.get['Subject'] = subject_keywords
        filter.get['Content'] = content_keywords
        filter.get['Subject_or_Content'] = subject_or_content_keywords
        self.client.deleteFilter(categoryName=filter_category)
        result = self.client.addFilter(filter)

        return

    def deleteFilter(self):
        self.showFilter()
        category = input('Input filter name to delete: ')
        result = self.client.deleteFilter(categoryName=category)
        if result == True:
            print('Delete filter {} successfully'.format(category))
        else:
            print('Delete filter {} failed'.format(category))
    
    def changeConfig(self):
        config = dict()
        config['Username'] = input('Enter username: ')
        config['Password'] = input('Enter password: ')
        config['Address'] = input('Enter email address: ')
        config['Server'] = input('Enter server: ')
        config['POP3 Port'] = input('Enter POP3 Port:')
        config['SMTP Port'] = input('Enter SMTP port: ')
        try:
            config['Autoload'] = int(input('Input autoload time, default {} seconds: '.format(self.client.defaultAutoloadTime)))
        except:
            config['Autoload'] = self.client.defaultAutoloadTime

        result = self.client.saveConfig(config, maxAttempt=3)
        if result == False:
            print('Save configurations failed.')
        else:
            print('Save configuration successfully.')
        return

    def printConfig(self):
        config = self.client.getConfig()
        print('Username: ', config.get('Username'))
        print('Password: ', config.get('Password'))
        print('Address: ', config.get('Address'))
        print('Server: ', config.get('Server'))
        print('POP3 Port: ', config.get('POP3 Port'))
        print('SMTP Port: ', config.get('SMTP Port'))
        print('Autoload: ', config.get('Autoload'))

    def showMenu(self):
        for selection in self.selection.values():
            print(selection[0])
    
    def mainMenu(self):
        self.showMenu()
        choice = input('Input choice, enter 0 to exit: ')
        while choice != '0':
            selection = self.selection.get(choice)
            if selection == None:
                print('Action not found')
            else:
                selection[1]() #Perform action

            choice = input('Input choice, enter 0 to exit: ')
        
def SMTPClient_CLI():
    interface = SMTPClientConsoleInterface()
    interface.mainMenu()
    
    
