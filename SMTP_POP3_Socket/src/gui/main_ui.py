import sys, os
import tkinter as tk
import tkinter.font as tkFont
from tkinter.scrolledtext import ScrolledText
from tkinter import filedialog
from tkinter.messagebox import askyesno

from ttkthemes import ThemedTk, THEMES
from tkinter import *
from tkinter import ttk
from tkinter.messagebox import showerror, showinfo, showwarning
from src.client.api import EmailClient

notReadStyle = ttk.Style()
notReadStyle.configure('notRead.TButton', font=('sans', '10', 'bold'), width=300)
readStyle = ttk.Style()
readStyle.configure('read.TButton', font=('sans', '10', 'italic'), width=300)

def getTextWidgetInput(tk_text_widget):
    input_text = tk_text_widget.get("1.0", "end-1c")
    return input_text

def setTextWidgetText(tk_text_widget, text: str):
    tk_text_widget.delete('1.0', 'end')
    tk_text_widget.insert('1.0', text)


def getEntryWidgetInput(tk_entry_widget):
    return tk_entry_widget.get()

def setEntryWidgetText(tk_entry_widget, text:str):
    tk_entry_widget.delete(0, 'end')
    tk_entry_widget.insert(0, text)

class EmailReadButton(ttk.Button):
    def __init__(self, parent, position, preview='', isRead=False):
        super().__init__()
        self.configure(width=300, padding=(5,5))
        self.position = position
        if isRead == True:
            super().__init__(master=parent, text=preview, width=325, padding=5, style='read.TButton')
        else:
            super().__init__(master=parent, text=preview, width=325, padding=5, style='notRead.TButton')
    
    def changeButtonToRead(self):
        self.configure(style='read.TButton')
     

class IncomingEmailTab(ttk.Frame):
    def __init__(self, parent, client: EmailClient):
        super().__init__(master=parent)

        self.currentEmail = 0
        self.category = 'Show all'
        self.emailButtons = list()
        self.client = client
        self.columnconfigure(0, weight=3)
        self.columnconfigure(1, weight=1)
        self.columnconfigure(2, weight=3)
        self.rowconfigure(0, weight=1)
        self.rowconfigure(1, weight=1)
        self.rowconfigure(2, weight=1)
        self.rowconfigure(3, weight=1)
        self.rowconfigure(4, weight=1)
        self.rowconfigure(5, weight=1)
        self.rowconfigure(6, weight=10)

        self.incomingEmails = ttk.Frame(self)
        self.categoryComboBox = ttk.Combobox(self)
        self.categoryComboBox.grid(column=0, row=0, sticky='wnes')

        self.incomingEmails.grid(column=0, row=1, rowspan=6, sticky='wnes', padx=5, pady=5)

        #Scrollbar for incoming email list
        self.incomingEmailListVerticalScrollbar = Scrollbar(self.incomingEmails)
        self.incomingEmailListVerticalScrollbar.pack(side = RIGHT, fill = Y)

        self.incomingEmailList = tk.Canvas(self.incomingEmails, bg='white', height=600, width=350)
        self.incomingEmailList.config(yscrollcommand=self.incomingEmailListVerticalScrollbar.set)
        self.incomingEmailList.pack()
        self.incomingEmailListVerticalScrollbar.config(command=self.incomingEmailList.yview)

        self.emailActionButtons = ttk.Frame(self)
        self.emailActionButtons.grid(column=0, row=8, columnspan=2, sticky='wnes', padx=5, pady=5)
        self.deleteEmailButton = ttk.Button(self.emailActionButtons, text="Delete this email")
        self.deleteEmailButton.bind('<Button-1>', lambda event: self.onDeleteEmailButtonClick())
        self.deleteEmailButton.pack(side=LEFT)
        self.getAttachmentButton = ttk.Button(self.emailActionButtons, text="Get attachments")
        self.getAttachmentButton.bind('<Button-1>', lambda event: self.onGetAttachmentButtonClick())

        self.getAttachmentButton.pack(side=LEFT)
        self.redownloadEmailButton = ttk.Button(self.emailActionButtons, text="Redownload emails")
        self.redownloadEmailButton.pack(side=LEFT)
        self.redownloadEmailButton.bind('<Button-1>', lambda event: self.onGetRedownloadAllEmailsButtonClick())

        self.fromAddressLabel = ttk.Label(self, text="From: ")
        self.fromAddressLabel.grid(column=1, row=0, sticky='we', padx=5, pady=5)
        self.fromAddressText = ttk.Entry(self)
        self.fromAddressText.grid(column=2, row=0, sticky='we', padx=5, pady=5)
        self.fromAddressText.configure(state='readonly')

        self.toAddressLabel = ttk.Label(self, text="To: ")
        self.toAddressLabel.grid(column=1, row=1, sticky='we', padx=5, pady=5)
        self.toAddressText = ttk.Entry(self )
        self.toAddressText.grid(column=2, row=1, sticky='we', padx=5, pady=5)
        self.toAddressText.configure(state='readonly')

        self.ccAddressLabel = ttk.Label(self, text="Cc: ")
        self.ccAddressLabel.grid(column=1, row=2, sticky='we', padx=5, pady=5)
        self.ccAddressText = ttk.Entry(self)
        self.ccAddressText.grid(column=2, row=2, sticky='we', padx=5, pady=5)
        self.ccAddressText.configure(state='readonly')

        self.bccAddressLabel = ttk.Label(self, text="Bcc: ")
        self.bccAddressLabel.grid(column=1, row=3, sticky='w', padx=5, pady=5)
        self.bccAddressText = ttk.Entry(self)
        self.bccAddressText.grid(column=2, row=3, sticky='we', padx=5, pady=5)
        self.bccAddressText.configure(state='readonly')

        self.subjectLabel = ttk.Label(self, text="Subject: ")
        self.subjectLabel.grid(column=1, row=4, sticky='we', padx=5, pady=5)
        self.subjectText = ttk.Entry(self)
        self.subjectText.grid(column=2, row=4, sticky='we', padx=5, pady=5)
        self.subjectText.configure(state='readonly')

        self.attachmentLabel = ttk.Label(self, text="Attachment: ")
        self.attachmentLabel.grid(column=1, row=5, sticky='we', padx=5, pady=5)
        self.attachmentText = ttk.Entry(self)
        self.attachmentText.grid(column=2, row=5, sticky='we', padx=5, pady=5)
        self.attachmentText.configure(state='readonly')

        self.contentLabel = ttk.Label(self, text="Content: ")
        self.contentLabel.grid(column=1, row=6, sticky='we', padx=5, pady=5)
        self.contentText = ScrolledText(self)
        self.contentText.grid(column=2, row=6, sticky='wnes', padx=5, pady=5)
        self.contentText.configure(state='disabled')
    
    def updateButtonStatusOnClick(self, button: EmailReadButton):
        button.changeButtonToRead()
        self.onEmailButtonClick(button.position)

    def updateUpcomingEmailList(self, category: str):
        self.emailButtons.clear()   
        for email_button in self.incomingEmailList.winfo_children():
            email_button.destroy() #Destroy all old email buttons
        if category == 'Show all':
            email_status_list = self.client.showAllEmails()
        else:
            email_status_list = self.client.showEmailInCategory(category)
        
        i = 0
        for email_status in email_status_list:
            isEmailRead = True if email_status['isRead'] == True or email_status['isRead'] == 'True' else False
            try:
                positionOnServer = int(email_status['position'])
            except:
                continue
            preview = email_status['preview']
            email_button = EmailReadButton(self.incomingEmailList, position=positionOnServer, preview=preview, isRead=isEmailRead)
            email_button.pack(side=tk.TOP)
            self.emailButtons.append(email_button)
        
        for i in range(len(self.emailButtons)):
            self.emailButtons[i].bind('<Button-1>', lambda event, button=self.emailButtons[i]: self.updateButtonStatusOnClick(button))
    
    def updateCategoryCombobox(self):
        list_of_categories = self.client.showAllCategories()
        categories = list(list_of_categories.keys())
        categories.append('Show all')
        self.categoryComboBox['values'] = categories
        self.categoryComboBox.bind('<<ComboboxSelected>>', lambda event, category=self.categoryComboBox.get(): self.onCategoryComboboxChanged(category))

    def onCategoryComboboxChanged(self, value):
        self.category = self.categoryComboBox.get()
        self.updateUpcomingEmailList(self.category)

    def onEmailButtonClick(self, position):
        self.currentEmail = position
        email_headers = self.client.readEmail(position, getAttachments=False, attachmentDirectory=None)
        if email_headers.get('Result') == False:
            showerror('Cannot read email', 'Cannot read email')
            return
        from_addresses = email_headers.get('From')
        to_addresses = email_headers.get('To')
        cc_addresses = email_headers.get('CC')
        bcc_address = email_headers.get('BCC')
        subject = email_headers.get('Subject')
        content_list = email_headers.get('Content')
        attachment_list = email_headers.get('Attachments')

        from_addresses = from_addresses if from_addresses is not None else ''
        to_addresses = to_addresses if to_addresses is not None else ''
        cc_addresses = cc_addresses if cc_addresses is not None else ''
        bcc_address = bcc_address if bcc_address is not None else ''
        subject = subject if to_addresses is not None else ''

        content = '\r\n----------------------------------------------\r\n'.join(content_list)
        attachment = ','.join(attachment_list)
        setEntryWidgetText(self.fromAddressText, from_addresses)
        setEntryWidgetText(self.toAddressText, to_addresses)
        setEntryWidgetText(self.ccAddressText, cc_addresses)
        setEntryWidgetText(self.bccAddressText, bcc_address)
        setEntryWidgetText(self.subjectText, subject)
        setEntryWidgetText(self.attachmentText, attachment)
        setTextWidgetText(self.contentText, content)
        
    def onGetAttachmentButtonClick(self):
        attachmentDirectory = filedialog.askdirectory(mustexist=False)
        if attachmentDirectory == None:
            showerror('Error opening directory', 'Cannot open directory to get attachments')
        else:
            result = self.client.readEmail(self.currentEmail, getAttachments=True, attachmentDirectory=attachmentDirectory)
            if result.get('Result') == False:
                showerror('Error getting attachments', 'Cannot get attachment from email. The email is either corrupted, deleted, or you don\'t have enough permission.')
            else:
                showinfo('Getting attachments at {} successfully'.format(attachmentDirectory))
        
    def onGetRedownloadAllEmailsButtonClick(self):
        result = self.client.fetchFromServerAndMoveToFilter(redownloadEvenIfInSync=True)
        if result == True:
            showinfo('Success',  'Redownload all emails successfully')
            self.updateCategoryCombobox()
        else:
            showerror('Failure', 'Failed refetching email from servers. It can be because of client/server errors or connection.')
            self.updateCategoryCombobox()

    def onDeleteEmailButtonClick(self):
        result = askyesno('Confirming deleting email?', 'Do you want to delete the email on screen?')
        if result == True:
            result = self.client.deleteEmail(self.currentEmail, deleteLocalCopy=True)
            if result == True:
                showinfo('Success', 'Delete email from server successfully.')
            else:
                showerror('Failure', 'Delete email from server failed. Program has marked this email for deletion.')
            self.updateCategoryCombobox()
        else:
            showinfo('Delete cancelled', 'Delete cancelled')
            return

class FilterConfigTab(ttk.Frame):
    def __init__(self, parent, client: EmailClient):
        super().__init__(master=parent)

        self.currentFilter = ''
        self.filterButtons = list()
        self.addMode = False
        self.client = client
        self.columnconfigure(0, weight=3)
        self.columnconfigure(1, weight=1)
        self.columnconfigure(2, weight=3)


        self.filterListFrame = ttk.Frame(self)
        self.filterListFrame.grid(column=0, row=0, rowspan=5, sticky='wnes', padx=5, pady=5)

        #Scrollbar for incoming email list
        self.filterListVerticalScrollbar = Scrollbar(self.filterListFrame)
        self.filterListVerticalScrollbar.pack(side = RIGHT, fill = Y)

        self.filterList = tk.Canvas(self.filterListFrame, bg='white', height=600, width=350)
        self.filterList.config(yscrollcommand=self.filterListVerticalScrollbar.set)
        self.filterList.pack()
        self.filterListVerticalScrollbar.config(command=self.filterList.yview)

        self.filterActionButtons = ttk.Frame(self)
        self.filterActionButtons.grid(column=1, row=5, sticky='wnes', padx=5, pady=5)
        self.deleteFilterButton = ttk.Button(self.filterActionButtons, text="Delete this filter")
        self.deleteFilterButton.pack(side=LEFT)

        self.saveFilterButton = ttk.Button(self.filterActionButtons, text="Save filter")
        self.saveFilterButton.pack(side=LEFT)
        self.resetAddFilterInputButton = ttk.Button(self.filterActionButtons, text="Clear filter configuration inputs")
        self.resetAddFilterInputButton.pack(side=LEFT)

        self.categoryLabel = ttk.Label(self, text="Category: ")
        self.categoryLabel.grid(column=1, row=0, sticky='we', padx=5, pady=5)
        self.categoryText = ttk.Entry(self)
        self.categoryText.grid(column=2, row=0, sticky='we', padx=5, pady=5)

        self.subjectLabel = ttk.Label(self, text="Subject: ")
        self.subjectLabel.grid(column=1, row=1, sticky='we', padx=5, pady=5)
        self.subjectText = ttk.Entry(self )
        self.subjectText.grid(column=2, row=1, sticky='we', padx=5, pady=5)

        self.fromLabel = ttk.Label(self, text="From address: ")
        self.fromLabel.grid(column=1, row=2, sticky='we', padx=5, pady=5)
        self.fromText = ttk.Entry(self)
        self.fromText.grid(column=2, row=2, sticky='we', padx=5, pady=5)

        self.contentLabel = ttk.Label(self, text="Content: ")
        self.contentLabel.grid(column=1, row=3, sticky='w', padx=5, pady=5)
        self.contentText = ttk.Entry(self)
        self.contentText.grid(column=2, row=3, sticky='we', padx=5, pady=5)

        self.subjectOrContentLabel = ttk.Label(self, text="Subject or content: ")
        self.subjectOrContentLabel.grid(column=1, row=4, sticky='we', padx=5, pady=5)
        self.subjectOrContentText = ttk.Entry(self)
        self.subjectOrContentText.grid(column=2, row=4, sticky='we', padx=5, pady=5)

        self.saveFilterButton.bind('<Button-1>', lambda event: self.onSaveFilterButtonClick())
        self.deleteFilterButton.bind('<Button-1>', lambda event: self.onDeleteFilterButtonClick())
        self.resetAddFilterInputButton.bind('<Button-1>', lambda event: self.onResetFilterInputButtonClick())

    
    def updateButtonStatusOnClick(self, button: EmailReadButton):
        button.changeButtonToRead()
        self.onFilterButtonClick(button.position)

    def updateFilterList(self): 
        self.filterButtons.clear()   
        for filter_button in self.filterListFrame.winfo_children():
            filter_button.destroy() #Destroy all old email buttons

            filter_status = self.client.showFilters()
            filter_list = filter_status.get('filter_list') if filter_status.get('filter_list') else list()
        
        isFilterListContainInvalidFilter = False
        for filter in filter_list:
            category = filter.get('Category')
            if category == None:
                isFilterListContainInvalidFilter = True
                continue
            
            filter_button = EmailReadButton(self.filterListFrame, position=category, preview=preview, isRead=True)
            filter_button.pack(side=tk.TOP)
            filter_button.position = category
            filter_button.configure(width=280)
            self.filterButtons.append(filter_button)

        for i in range(self.filterButtons):
            self.filterButtons[i].bind('<Button-1>', lambda event, category=self.filterButtons[i].category: self.onFilterButtonClick(category))
    
    def onFilterButtonClick(self, category):
        self.currentFilter = category
        filter = self.client.getFilter(category)
        if filter == None:
            showerror('Filter not found', 'Filter {} does not found.'.format(category))
            return
        filter_category = filter.get('Category') or category
        from_address_keywords = filter.get('From')
        subject_keywords = filter.get('Subject')
        content_keywords = filter.get('Content')
        subject_or_content_keywords = filter.get('Subject_or_Content')

        from_address_text = ','.join(from_address_keywords) if from_address_keywords != None else ''
        subject_text = ','.join(subject_keywords) if subject_keywords != None else ''
        content_text = ','.join(content_keywords) if content_keywords != None else ''
        subject_or_content_text = ','.join(subject_or_content_keywords) if subject_or_content_keywords != None else ''
        setEntryWidgetText(self.fromText, from_address_text)
        setEntryWidgetText(self.subjectText, subject_text)
        setEntryWidgetText(self.contentText, content_text)
        setEntryWidgetText(self.subjectOrContentText, subject_or_content_text)
        setEntryWidgetText(self.categoryText, filter_category)

    def onResetFilterInputButtonClick(self):
        setEntryWidgetText(self.fromText, '')
        setEntryWidgetText(self.subjectText, '')
        setEntryWidgetText(self.contentText, '')
        setEntryWidgetText(self.subjectOrContentText, '')
        setEntryWidgetText(self.categoryText, '')

    def onSaveFilterButtonClick(self):
        category = getEntryWidgetInput(self.categoryText)
        fromAddressKeywords = getEntryWidgetInput(self.fromText)
        contentKeywords = getEntryWidgetInput(self.contentText)
        subjectKeywords = getEntryWidgetInput(self.subjectText)
        subjectOrContentKeywords = getEntryWidgetInput(self.subjectOrContentText)
        filter = dict()
        filter['Category'] = category
        filter['From'] = fromAddressKeywords
        filter['Content'] = contentKeywords
        filter['Subject'] = subjectKeywords
        filter['Subject or Content'] = subjectOrContentKeywords

        #Try delete old filter
        self.client.deleteFilter(categoryName=category)
        self.client.addFilter(filter)
        self.updateFilterList()

    def onDeleteFilterButtonClick(self):
        result = self.client.deleteFilter(self.currentFilter)
        self.currentFilter = ''
        self.updateFilterList()
        if result == False:
            showerror('Failure deleting filter', 'Error deleting filter or filter not found')
        else:
            showinfo('Delete filter successfully', 'Delete filter successfully')
        return
    

class SendingEmailTab(ttk.Frame):
    def __init__(self, parent, client: EmailClient):
        super().__init__(master=parent)
        self.client = client
        self.attachments = list()

        self.columnconfigure(0, weight=1)
        self.columnconfigure(1, weight=3)
        self.rowconfigure(0, weight=1)
        self.rowconfigure(1, weight=1)
        self.rowconfigure(2, weight=1)
        self.rowconfigure(3, weight=1)
        self.rowconfigure(4, weight=1)
        self.rowconfigure(5, weight=1)
        self.rowconfigure(6, weight=10)

        self.emailActionButtons = ttk.Frame(self)
        self.emailActionButtons.grid(column=0, row=7, columnspan=2, sticky='wnes', padx=5, pady=5)
        self.addAttachmentsButton = ttk.Button(self.emailActionButtons, text="Add attachments")
        self.addAttachmentsButton.pack(side=LEFT)
        self.resetAttachmentAddButton = ttk.Button(self.emailActionButtons, text="Cancel adding attachments")
        self.resetAttachmentAddButton.pack(side=LEFT)
        self.sendEmailButton = ttk.Button(self.emailActionButtons, text="Send email")
        self.sendEmailButton.pack(side=LEFT)

        """ self.fromAddressLabel = ttk.Label(self, text="From: ")
        self.fromAddressLabel.grid(column=0, row=0, sticky='we', padx=5, pady=5)
        self.fromAddressText = ttk.Entry(self)
        self.fromAddressText.grid(column=1, row=0, sticky='we', padx=5, pady=5) """

        self.toAddressLabel = ttk.Label(self, text="To: ")
        self.toAddressLabel.grid(column=0, row=1, sticky='we', padx=5, pady=5)
        self.toAddressText = ttk.Entry(self )
        self.toAddressText.grid(column=1, row=1, sticky='we', padx=5, pady=5)

        self.ccAddressLabel = ttk.Label(self, text="Cc: ")
        self.ccAddressLabel.grid(column=0, row=2, sticky='we', padx=5, pady=5)
        self.ccAddressText = ttk.Entry(self)
        self.ccAddressText.grid(column=1, row=2, sticky='we', padx=5, pady=5)

        self.bccAddressLabel = ttk.Label(self, text="Bcc: ")
        self.bccAddressLabel.grid(column=0, row=3, sticky='w', padx=5, pady=5)
        self.bccAddressText = ttk.Entry(self)
        self.bccAddressText.grid(column=1, row=3, sticky='we', padx=5, pady=5)

        self.subjectLabel = ttk.Label(self, text="Subject: ")
        self.subjectLabel.grid(column=0, row=4, sticky='we', padx=5, pady=5)
        self.subjectText = ttk.Entry(self)
        self.subjectText.grid(column=1, row=4, sticky='we', padx=5, pady=5)

        self.attachmentLabel = ttk.Label(self, text="Attachments: ")
        self.attachmentLabel.grid(column=0, row=5, sticky='we', padx=5, pady=5)
        self.attachmentText = ttk.Entry(self)
        self.attachmentText.grid(column=1, row=5, sticky='we', padx=5, pady=5)

        self.contentLabel = ttk.Label(self, text="Content: ")
        self.contentLabel.grid(column=0, row=6, sticky='we', padx=5, pady=5)
        self.contentText = ScrolledText(self)
        self.contentText.grid(column=1, row=6, sticky='wnes', padx=5, pady=5)
        
        #Bind buttons on click
        self.addAttachmentsButton.bind('<Button-1>', lambda event: self.onAddAttachmentsButtonClick())
        self.resetAttachmentAddButton.bind('<Button-1>', lambda event: self.onResetAddAttachmentClick())
        self.sendEmailButton.bind('<Button-1>', lambda event: self.onSendEmailButtonClick())
    
    def onAddAttachmentsButtonClick(self):
        attachments = self.client.getAttachments(useGUI=True)
        if attachments == None or len(attachments) == 0: #User choose no attachment
            return
        else:
            self.attachments += attachments
            attachmentText = ','.join(self.attachments) if len(self.attachments) > 1 else self.attachments[0] #New attachent text
            setEntryWidgetText(self.attachmentText, attachmentText)
    
    def onResetAddAttachmentClick(self):
        self.attachments.clear()
        setEntryWidgetText(self.attachmentText, '')
    
    def onSendEmailButtonClick(self):
        email = dict()
        email['To'] = getEntryWidgetInput(self.toAddressText)
        if getEntryWidgetInput(self.toAddressText) == '' or getEntryWidgetInput(self.toAddressText) == None:
            showerror('No email address to send to', 'No email address to send to')
            #To do: Maybe also using regex to check if email typed is valid or not
        
        email['CC'] = getEntryWidgetInput(self.ccAddressText)
        email['BCC'] = getEntryWidgetInput(self.bccAddressText)
        email['Subject'] = getEntryWidgetInput(self.subjectText)
        email['Content'] = getTextWidgetInput(self.contentText)
        email['Attachments'] = self.attachments
        result, statuses = self.client.sendEmailFromUserInput(email, maxAttempt=15)
        if result == False:
            for status in statuses:
                showerror('Send email failed', status)
        else:
            for status in statuses:
                showinfo('Send all email successfully', status)

class GeneralConfigTab(ttk.Frame):
    def __init__(self, parent, client: EmailClient):
        super().__init__(master=parent)
        self.client = client
        self.currentEmail = None

        self.columnconfigure(0, weight=1)
        self.columnconfigure(1, weight=3)
        self.usernameLabel = ttk.Label(self, text="Username: ")
        self.usernameLabel.grid(column=0, row=0, sticky='we', padx=5, pady=5)
        self.usernameText = ttk.Entry(self)
        self.usernameText.grid(column=1, row=0, sticky='we', padx=5, pady=5)

        self.passwordLabel = ttk.Label(self, text="Password: ")
        self.passwordLabel.grid(column=0, row=1, sticky='we', padx=5, pady=5)
        self.passwordText = ttk.Entry(self)
        self.passwordText.grid(column=1, row=1, sticky='we', padx=5, pady=5)

        self.emailAddressLabel = ttk.Label(self, text="Email address: ")
        self.emailAddressLabel.grid(column=0, row=2, sticky='we', padx=5, pady=5)
        self.emailAddressText = ttk.Entry(self)
        self.emailAddressText.grid(column=1, row=2, sticky='we', padx=5, pady=5)

        self.serverLabel = ttk.Label(self, text="Server: ")
        self.serverLabel.grid(column=0, row=3, sticky='we', padx=5, pady=5)
        self.serverText = ttk.Entry(self)
        self.serverText.grid(column=1, row=3, sticky='we', padx=5, pady=5)

        self.SMTPPortLabel = ttk.Label(self, text="SMTP Port: ")
        self.SMTPPortLabel.grid(column=0, row=4, sticky='we', padx=5, pady=5)
        self.SMTPPortText = ttk.Entry(self)
        self.SMTPPortText.grid(column=1, row=4, sticky='we', padx=5, pady=5)

        self.POP3PortLabel = ttk.Label(self, text="POP3 Port: ")
        self.POP3PortLabel.grid(column=0, row=5, sticky='we', padx=5, pady=5)
        self.POP3PortText = ttk.Entry(self)
        self.POP3PortText.grid(column=1, row=5, sticky='we', padx=5, pady=5)

        self.autoloadLabel = ttk.Label(self, text="Autoload: ")
        self.autoloadLabel.grid(column=0, row=6, sticky='we', padx=5, pady=5)
        self.autoloadText = ttk.Entry(self)
        self.autoloadText.grid(column=1, row=6, sticky='we', padx=5, pady=5)

        self.generalConfigActionButtons = ttk.Frame(self)
        self.generalConfigActionButtons.grid(column=1, row=7, sticky='wnes', padx=5, pady=5)
        self.saveConfigButton = ttk.Button(self.generalConfigActionButtons, text="Save")
        self.saveConfigButton.pack(side=LEFT)
        self.resetConfigButton = ttk.Button(self.generalConfigActionButtons, text="Clear configuration input")
        self.resetConfigButton.pack(side=LEFT)

        self.saveConfigButton.bind('<Button-1>', lambda event: self.onSaveConfigButtonClick())
        self.resetConfigButton.bind('<Button-1>', lambda event: self.onClearConfigButtonClick())

    def onSaveConfigButtonClick(self):
        config = dict()
        config['Username'] = getEntryWidgetInput(self.usernameText)
        config['Password'] = getEntryWidgetInput(self.passwordText)
        config['Address'] = getEntryWidgetInput(self.emailAddressText)
        config['Server'] = getEntryWidgetInput(self.serverText)
        config['POP3 Port'] = getEntryWidgetInput(self.POP3PortText)
        config['SMTP Port'] = getEntryWidgetInput(self.SMTPPortText)
        try:
            config['Autoload'] = int(getEntryWidgetInput(self.autoloadText))
        except:
            config['Autoload'] = self.client.defaultAutoloadTime

        result = self.client.saveConfig(config, maxAttempt=3)
        if result == False:
            showerror('Save configurations failed', 'Save configurations failed.')
        else:
            showinfo('Save configuration successfully', 'Save configuration successfully.')
        

    def onClearConfigButtonClick(self):
        confirm = askyesno('Clear config', 'Do you want to clear the config?')
        if confirm == True:
            setEntryWidgetText(self.usernameText, '')
            setEntryWidgetText(self.passwordText, '')
            setEntryWidgetText(self.emailAddressText, '')
            setEntryWidgetText(self.POP3PortText, '')
            setEntryWidgetText(self.SMTPPortText, '')
            setEntryWidgetText(self.autoloadText, '')
            setEntryWidgetText(self.serverText, '')
            return

class SMTPClient_GUI(ThemedTk):

    def __init__(self, theme="adapta"):
        """
        :param theme: Theme to show off
        """
        ThemedTk.__init__(self, fonts=False, themebg=True)
        #super().__init__()
        self.title("SMTP_Client")
        self.tabControl = ttk.Notebook(self)
        self.geometry("1000x600")
        self.resizable(0,0)
        self.set_theme(theme)
        self.client = EmailClient(defaultCategory='Inbox')

        self.incomingEmailTab = IncomingEmailTab(self.tabControl, self.client)
        self.sendEmailTab = SendingEmailTab(self.tabControl, self.client)
        self.configTab = GeneralConfigTab(self.tabControl, self.client)
        self.filterConfigTab = FilterConfigTab(self.tabControl, self.client)

        self.tabControl.add(self.incomingEmailTab, text='Incoming Emails')
        self.tabControl.add(self.sendEmailTab, text='Sending Email')
        self.tabControl.add(self.configTab, text='Sending Configurations')
        self.tabControl.add(self.filterConfigTab, text='Filter Configurations')

        self.tabControl.pack(expand=1, fill="both")
    def updateFromServer(self):
        return
    def redownloadEmail(self):
        return   

