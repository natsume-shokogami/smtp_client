import os, json

class EmailStatus:
    def __init__(self):
        self.emailPath = None
        self.identifier = ''
        self.byteCount = 0
        self.position = 0 #Position of the email when downloaded from the server (RETR POP3 command)
        self.isRead = False
        self.category = ''
        self.notFound = False
        self.isPendingRemoval = False
    def toDict(self):
        res = dict()
        res['path'] = self.emailPath
        res['byte_count'] = self.byteCount
        res['identifier'] = self.identifier
        res['position'] = self.position
        res['path'] = self.emailPath
        res['category'] = self.category
        res['is_read'] = self.isRead
        res['not_found'] = self.notFound
        res['pending_removal'] = self.isPendingRemoval
        return res
    def fromDict(self, dictionary):
        self.emailPath = dictionary.get('path')
        self.byteCount = dictionary.get('byte_count')
        self.identifier = dictionary.get('identifier')
        self.category = dictionary.get('category')
        self.position = int(dictionary.get('position'))
        self.isRead = dictionary.get('is_read')
        self.notFound = (dictionary.get('not_found') == True)
        self.isPendingRemoval = (dictionary.get('pending_removal') == True)

class EmailMetadata:
    def __init__(self):
        self.email_metadata_list = list()

    def addEmailMetadata(self, emailStatus):
        self.email_metadata_list.append(emailStatus)

    def updateAvailablity(self):
        for email_metadata in self.email_metadata_list:
            #Check if the file is actually an email file, not directory 
            if not os.path.isfile(email_metadata.emailPath):
                email_metadata['not_found'] = False
            else:
                email_metadata['not_found'] = True
    
    def readJSON(self, JSON_file_or_string, isFile=True):
        try:
            if isFile == True:
                with open(JSON_file_or_string, 'r+') as fp:
                    json_string = fp.read()
            else:
                json_string = JSON_file_or_string

            email_metadata_dict_list = json.loads(json_string)
            for email_data in email_metadata_dict_list:
                email_status = EmailStatus()
                email_status.fromDict(email_data)
                self.email_metadata_list.append(email_status)
            return True
        except Exception as e:
            print(e)
            return False

    def toJSON(self, JSON_file):
        try:
            dump = list()
            for email_status in self.email_metadata_list:
                dump.append(email_status.toDict())
            with open(JSON_file, 'w') as fp:
                json.dump(dump, fp)
                return True
        except:
            return False