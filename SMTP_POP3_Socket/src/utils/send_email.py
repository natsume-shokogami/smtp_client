import os, time, re, asyncio, email
from email.parser import Parser
from email.message import Message

from src.utils.config_socket_init import GeneralConfig, initSocket, readConfig
from src.utils.email_metadata import EmailMetadata, EmailStatus
from src.utils.filter_config import FilterConfig
from src.utils.client_utils import sendPOP3Command, sendSMTPEmail, pop3_uidl_msg_identifier_pair, parse_UIDL_RETR_STAT
from src.utils.mime_process import createMIME, parseMultipartMIME

def sendCommandAndFetchResult(command: str, regex, socket, maxAttempt=3, compareStatusCode=None):
    #Send any SMTP or POP3 command (need to initiate socket first) and
    #return a tuple containing the response code and a list of all strings matching the regex regex
    #Resend up to three times or when a response containing a response and having substrings matching regex are found
    # If not found, return ('', list()) (Tuple of an empty string and an empty list) 
    #Passing None to regex will return a tuple of the response code and the full response string instead
    
    #Main loop, attempt up to maxAttempt time to fetch the data
    for i in range(maxAttempt):
        socket.send(command.encode())
        buffer = socket.recv(1024)
        response = buffer
        while not buffer:
            buffer = socket.recv(1024)
            response += buffer
        response = response.decode()
        POP3_SMTP_response_regex = r"([\+\-]{1}[\w\S]+)|d+"
        response_code = re.findall(POP3_SMTP_response_regex, response)
        if regex is not None:
            matches = re.findall(regex, response)
            expected_strings = list()
            for element in matches:
                if type(element) == str and element != '':
                    expected_strings.append(element)
                elif type(element) == tuple:
                    for string in element:
                        if type(string) == str and string != '':
                            expected_strings.append(string)
        else:
            expected_strings = response
        
        if compareStatusCode is not None and compareStatusCode in response_code:
            return response_code[0], expected_strings
        #Check if there's an SMTP/POP3 response code and substring with regex in the response
        if len(response_code) > 0 and len(expected_strings) > 0:
            return response_code[0], expected_strings
        if compareStatusCode == None: #Not comparing status code or response, just return the response
            return response_code[0], expected_strings
    return '', list()

def createConfig(username, password, address, server, pop3Port=3335, smtpPort=2225, saveConfig=False, configFilename=None):
    config = GeneralConfig()
    addUsernameRes =  config.addConfig("username", username)
    addPasswordRes =  config.addConfig("password", password)
    addEmailAddress =  config.addConfig("email_address", address)
    addServerAddress =  config.addConfig("server", server)
    addSMTPPort =  config.addConfig("smtp_port", smtpPort)
    addPOP3Port =  config.addConfig("pop3_port", pop3Port)

    if saveConfig == True and configFilename is not None:
        saveConfig =  config.toJSON(configFilename)

    if (not addUsernameRes or not addPasswordRes or not addEmailAddress
    or not addSMTPPort or not addPOP3Port or not addServerAddress or not addPOP3Port):
        return None
    
    return config

def sendEmail(config, sendto, data):
    return sendSMTPEmail(config, sendto, data)

def deleteRemoteEmail(config, emailMetadata: EmailMetadata, index=1, deleteLocalCopy=True):
    socket = initSocket(config, False)
    email_address = config.configs['email_address']
    password = config.configs['password']

    if (socket is None or email_address == None or password == None):
        return False

    user_command_result, response = sendPOP3Command('USER', socket=socket, arguments=email_address)
    pass_command_result, response = sendPOP3Command('PASS', socket=socket, arguments=password)

    if user_command_result == False or pass_command_result ==False:
        socket.send('QUIT\r\n'.encode())
        socket.close()
        return False
    
    stat_command_result, response = sendPOP3Command('STAT', socket=socket)
    if stat_command_result == False:
        socket.send('QUIT\r\n'.encode())
        socket.close()
        return -1, -1

    response = re.findall(r'\d+[ ]+\d+', response)

    try:
        response = response[0].split(' ')
        before_email_count = int(response[0])
    except:
        socket.close()
        return False
    dele_command_result, response = sendPOP3Command('DELE', socket=socket, arguments=str(index))
    if dele_command_result == False:
        #Failure delete email in server, undoing
        response_code, response = sendPOP3Command('RSET', socket=socket)
        response_code, response = sendPOP3Command('QUIT', socket=socket)
        socket.close()
        return False, "Cannot send delete request to server."
        # Check again that STAT command will show the same result after sending DELE command successfully, 
        # so this is not reliable to check if the client has accidentally sent multiple DELE commands to server
    """ else:
        #Recheck if there's two or more request sent on the server
        response_code, response = sendCommandAndFetchResult("STAT\r\n", r'\d+\s+\d+', socket, maxAttempt=5, compareStatusCode="+OK")

        response = response[0].split(' ')
        try:
            after_email_count = int(response[0])
            if before_email_count - 1 != after_email_count:
                raise RuntimeError("There may be two or more delete request sent to server. Undoing")
        except Exception as e:
            print(e)
            response_code, response = sendCommandAndFetchResult("RSET \r\n", None, socket, maxAttempt=5, compareStatusCode="+OK")
            response_code, response = sendCommandAndFetchResult("QUIT \r\n", None, socket, maxAttempt=5, compareStatusCode="+OK")
            socket.close()
            return False """
    if deleteLocalCopy == True:
        for email_status in emailMetadata.email_metadata_list:
            if email_status.notFound != False and email_status.isFendingRemoval:
                email_path = email_status.emailPath
                try:
                    os.remove(email_path)
                except:
                    return False, "Cannot delete local email copy at index {}. Please delete it manually at {}.".format(index, email_status.emailPath)
    return True, "Delete email at index {} successfully.".format(index)

#Check if local email categories and metadata is in sync with server or not
#Return a 2-tuple with first value is the current number of email in the server
#second value is the first position where mismatch occurs, or the number of 0 if everything in sync
#Return None in failure
#Note that POP3 cannot check email content 
# (Identifier from UIDL command may not be accurate if the server cannot make unique identifier for each email)
#, so if any change between each sync on remote may make this function inaccurate
def checkRemoteSync(config, emailMetadata: EmailMetadata, returnRemoteStatusOnly=False):
    socket = initSocket(config, False)

    password = config.configs.get('password')
    email_address = config.configs.get('email_address')

    if (socket is None) or password == None or email_address == None:
        return -1, -1
    user_command_result = False; pass_command_result = False
    for i in range(10):
        user_command_result, response = sendPOP3Command('USER', socket=socket, arguments=email_address, maxAttempt=1)
        pass_command_result, response = sendPOP3Command('PASS', socket=socket, arguments=password, maxAttempt=1)
        if user_command_result == True and pass_command_result == True:
            break

    if user_command_result == False or pass_command_result ==False:
        socket.send('QUIT\r\n'.encode())
        socket.close()
        return -1, -1

    stat_command_result, response = sendPOP3Command('STAT', socket=socket)
    if stat_command_result == False:
        socket.send('QUIT\r\n'.encode())
        socket.close()
        return -1, -1

    response = re.findall(r'\d+[ ]+\d+', response)
    if len(response) == 0:
        return -1, -1 #Failure getting stat
    else:
        response = response[0].split(' ')
    max_email = int(response[0])
    max_bytes = int(response[1])

    if max_email == 0:
        socket.close()
        return 0, 0

    if returnRemoteStatusOnly == True:
        list_command_result, response = sendPOP3Command('LIST', socket)
        if list_command_result:
            socket.close()
            return -1, -1
        
        remote_index = [0]*(max_email)
        remote_index[0] = 0

        for res in response:
            tokens = res.split(' ') # into tokens
            remote_index[int(tokens[0])-1] = int(tokens[1]) #Assign the byte number to each index

    uidl_command_result, response = parse_UIDL_RETR_STAT('UIDL', socket=socket)

    if uidl_command_result == False:
        socket.send('QUIT\r\n'.encode())
        socket.close()
        return -1, -1

    remote_identifier = ['']*(max_email)

    response = re.findall(pop3_uidl_msg_identifier_pair, response)
    for res in response:
        try:
            tokens = res.split(' ') #Remove ending \r\n and split into tokens
            remote_identifier[int(tokens[0])-1] = tokens[1].replace('\r\n', '') #Assign the unique identifier
        except:
            pass
    if returnRemoteStatusOnly == True:
        socket.close()
        return remote_index, remote_identifier
    
    localNumberOfEmails = len(emailMetadata.email_metadata_list)
    if localNumberOfEmails == 0 and max_email != 0:
        return (max_email, max_email)

    for i in range(max_email, 1, -1):
        #Server has new emails which local doesn't have
        #Return value should be the first email local doesn't have
        localNumberOfEmails = len(emailMetadata.email_metadata_list)
        isEmailFoundLocal = False
        for j in range(localNumberOfEmails):
            if i == emailMetadata.email_metadata_list[j].position:
                isEmailFoundLocal = True
                local_email_identifier = emailMetadata.email_metadata_list[j].identifier
                if local_email_identifier != remote_identifier[i-1]:
                    return (i, max_email)

        if isEmailFoundLocal == False:
            return (i, max_email)

    
    socket.close()
    return (0, max_email)


def receiveEmails(config, index=-1, receiveEmailDirectory=None, emailMetadata: EmailMetadata = None, maxAttempt=5):
    socket = initSocket(config, False)
    mailMetadata = emailMetadata if emailMetadata is not None else EmailMetadata()
    local_email_number = len(emailMetadata.email_metadata_list)
    email_address = config.configs.get('email_address')
    password = config.configs.get('password')

    if receiveEmailDirectory is not None:
        downloaded_email_dir = receiveEmailDirectory
        try:
            os.mkdir(downloaded_email_dir)
        except FileExistsError:
            pass
    else:
        downloaded_email_dir = ''

    if socket is None or email_address is None or password is None:
        return False, mailMetadata

    user_command_result = False; pass_command_result = False
    for i in range(maxAttempt):
        user_command_result, response = sendPOP3Command('USER', socket=socket, arguments=email_address, maxAttempt=1)
        pass_command_result, response = sendPOP3Command('PASS', socket=socket, arguments=password, maxAttempt=1)
        if user_command_result == True and pass_command_result == True:
            break
    
    if user_command_result==False or pass_command_result == False:
        socket.close()
        return False, mailMetadata
        
    stat_command_result, response = sendPOP3Command('STAT', socket=socket)
    if stat_command_result == False:
        socket.send('QUIT\r\n'.encode())
        socket.close()
        return False, mailMetadata

    response = re.findall(r'\d+[ ]+\d+', response)

    if len(response) == 0:
        return False, mailMetadata #Failure getting stat
    else:
        response = response[0].split(' ')

    max_email = int(response[0])
    max_bytes = int(response[1])
    if emailMetadata is not None:
        #Get identifier for each email
        #uidl_command_result, response = sendPOP3Command('UIDL', socket)
        uidl_command_result, response = parse_UIDL_RETR_STAT('UIDL', socket=socket)
        response = re.findall(pop3_uidl_msg_identifier_pair, response)

        if uidl_command_result == False:
            socket.send('QUIT\r\n'.encode())
            socket.close()
            return False, mailMetadata
        
        remote_identifier = [' ']*(max_email+1)
        for res in response:
            tokens = res.split(' ') #Remove ending \r\n and split into tokens
            try:
                remote_identifier[int(tokens[0])-1] = tokens[1].replace('\r\n', '') #Assign the unique identifier
            except:
                continue
    #Download each email
    user = config.configs["username"]

    #If index is negative, download email from oldest email to 1, else download from index to 1
    if index < 0:
        start_index = max_email
    else:
        start_index = index

    for i in range(start_index, 0, -1): #Download email from start_index to 1
        success = False
        buffer = ''
        for j in range(maxAttempt): #maxAttempt = 5
            success = True
            try:
                #retr_result, response = sendPOP3Command('RETR', socket=socket, arguments=str(i))
                retr_result, response = parse_UIDL_RETR_STAT('RETR', socket=socket, arguments=str(i))
                if retr_result == False:
                    continue
                responseStartIndex = response.find('+OK')
                if responseStartIndex == -1:
                    #Broken response and no '+OK' in it
                    success = False
                    continue
                responseEndIndex = response.find('\r\n.', responseStartIndex+1)
                if responseEndIndex == -1:
                    #Broken response and no '+OK' in it
                    success = False
                    continue
                emailStartIndex = response.find('\r\n', responseStartIndex, responseEndIndex)
                if emailStartIndex == -1:
                    success = False
                    continue
                
                downloaded_email_path = os.path.join(downloaded_email_dir, "email_for_" + user + "_" + str(i))

                #Data start from second line until before meeting final '\r\n.'
                response = response[emailStartIndex+2:responseEndIndex]

                with open(downloaded_email_path, 'w+') as saveEmail:
                    saveEmail.write(response)
                if mailMetadata != None:
                    #Update email status
                    for j in range(len(mailMetadata.email_metadata_list)):
                        if mailMetadata.email_metadata_list[j].position == i:
                            mailMetadata.email_metadata_list.pop(j)
                    new_email_identifier = remote_identifier[i-1]
                    new_email_status = EmailStatus()
                    new_email_status.identifier = new_email_identifier
                    new_email_status.emailPath = downloaded_email_path
                    new_email_status.isPendingRemoval = False
                    new_email_status.isRead = False
                    new_email_status.position = i
                    new_email_status.notFound = False
                    #Replace old email status by new one
                    replaced = False
                    mailMetadata.email_metadata_list.append(new_email_status)
            except Exception as e:
                print(e)
                success = False
            
            if success == True:
                break

        if success == False: #Failed to download email after maxAttempt times
            print('Failed to download email at ', str(i), 'from server. Email is either corrupted or not parsable. Also check network connection and server')

    socket.send('QUIT\r\n'.encode())
    socket.close()
    return True, mailMetadata

