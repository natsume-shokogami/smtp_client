import socket, re, email
from src.utils.config_socket_init import GeneralConfig, initSocket
from email import message_from_string, errors


#'?:' before () in regex means that will turn the regex inside () from capturing to non-capturing
pop3_uidl_response = r'\+OK[\w ]*[\r\n]{1,2}(?:[0-9]+[ ]+[\w\.\-_]{8,70}[\r\n]{1,2})+\.{1}'
pop3_uidl_msg_identifier_pair = r'[0-9]+[ ]+[\w\.\-_]{8,70}[\r\n]{1,2}'
pop3_list_response = r'\+OK[\w ]*[\r\n]{1,2}(?:[0-9]+[ ]+[0-9]+[\r\n]{1,2})+\.{1}'
pop3_user_pass_dele_response = r'\+OK[\w ]*'
pop3_stat_response = r'\+OK[ ]+\d+[ ]+\d+[ ]*'
pop3_err_response = r'\-ERR[\w ]+[ ]*'

smtp_reponse = r'[2-5]{1}[0-9]{2}[ \w]*'
smtp_send_email_response = r'([2-5]{1}[0-9]{2}[ \w]*[\r\n]{1,2}){3}'
smtp_send_email_ok_response = r'(2[0-9]{2}[ .@<>\w]*[\r\n]{1,2}){3}'
smtp_send_email_wait_email_data = r'354[ ,\'\".\w]*[\r\n]{1,2}'
smtp_ok_response = r'2[0-9]{2}[ \w]*[\r\n]'
smtp_send_email_temporary_error = r'4[0-9]{2}[ ,.\-\w]*[\r\n]{1,2}' #Temporaray errors, may send again in the future
smtp_send_email_permanent_error = r'5[0-9]{2}[ ,.\-\w]*[\r\n]{1,2}' #Permenant/long-term error that the server is unlikely to resolve
smtp_send_email_end_email_ok = r'2[0-9]{2}[ \w]*[\r\n]{1,2}'

def sendall(socket, data):
    data_len = len(data)
    i = 0
    while i < data_len:
        try:
            bytes_send = socket.send(data[i:]) #Broken pipe, either from client or server
        except:
            return False
        if bytes_send == 0: #Socket disruption
            return False
        i += bytes_send
    
    return True

def recvFromSocket(socket):
    try:
        buffer = socket.recv(1024)
    except:
        return ''
    response = buffer
    while not buffer:
        response += buffer
        try:
            buffer = socket.recv(1024)
        except:
            return ''
    
    response = response.decode()
    return response

def expectUserPassDelePOP3CommandResponse(response):
    if re.match(pop3_user_pass_dele_response, response):
        return True
    return False

def expectStatPOP3CommandResponse(response):
    if re.match(pop3_stat_response, response):
        return True
    return False

def expectListPOP3CommandResponse(response):
    if re.match(pop3_list_response, response):
        return True
    return False

def expectUidlPOP3CommandResponse(response):
    if re.match(pop3_uidl_response, response):
        return True
    return False

def getAllMatchesRegex(regex, response):
    matches = re.findall(regex, response)
    expected_strings = list()
    for element in matches:
        if type(element) == str and element != '':
            expected_strings.append(element)
        elif type(element) == tuple:
            for string in element:
                if type(string) == str and string != '':
                    expected_strings.append(string)

def expectRetrPOP3CommandResponse(response):
    if (expectUserPassDelePOP3CommandResponse(response) or
        expectListPOP3CommandResponse(response) or
        expectStatPOP3CommandResponse(response) or 
        expectUidlPOP3CommandResponse(response)):
        return False
    if re.match(r'[\r\n]{1,2}\.', response[:-2]): #Response should have terminal character
        email_vars = message_from_string(response)
        if len(email_vars.defects) > 0: #Defective MIME message
            return False
        return True
    return False

def sendPOP3Command(command: str, socket: socket.socket, arguments: str=None, maxAttempt=10):
    if arguments == None:
        arguments = ''
    if command == 'USER':
        full_command = 'USER '+arguments+'\r\n'
        checker = expectUserPassDelePOP3CommandResponse
    elif command == 'PASS':
        full_command = 'PASS '+arguments+'\r\n'
        checker = expectUserPassDelePOP3CommandResponse
    elif command == 'LIST':
        full_command = 'LIST\r\n'
        checker = expectListPOP3CommandResponse
    elif command == 'UIDL':
        full_command = 'UIDL\r\n'
        checker = expectUidlPOP3CommandResponse
    elif command == 'STAT':
        full_command = 'STAT\r\n'
        checker = expectStatPOP3CommandResponse
    elif command == 'DELE':
        full_command = 'DELE '+arguments+'\r\n'
        checker = expectUserPassDelePOP3CommandResponse
    elif command == 'RETR':
        full_command = 'RETR '+arguments+'\r\n'
        checker = expectRetrPOP3CommandResponse
    elif command == 'RSET':
        full_command = 'RSET\r\n'
        checker = expectUserPassDelePOP3CommandResponse
    else:
        raise RuntimeError('Command not found')

    response = ''

    for i in range(maxAttempt):
        result = sendall(socket, full_command.encode())
        response = recvFromSocket(socket)
        if checker(response) == True:
            return True, response
    
    if re.match(pop3_err_response, response):
        return False, response
    else:
        return False, None

#Since commands with large response (UIDL, RETR, LIST) can be corrupted in that part of the old response
def parse_UIDL_RETR_STAT(command: str, socket: socket.socket, arguments: str='', maxAttempt=5):
    if command == 'RETR':
        full_command = 'RETR '+arguments+'\r\n'
        checker = expectRetrPOP3CommandResponse
    elif command == 'UIDL':
        full_command = 'UIDL\r\n'
        checker = expectUidlPOP3CommandResponse
    elif command == 'LIST':
        full_command = 'LIST\r\n'
        checker = expectListPOP3CommandResponse
    else:
        raise RuntimeError('Command not found')

    response = ''
    stat_uidl_retr_regex = r'\+OK[ \w]*[\r\n]{1,2}[^\0]+[\r\n]{1,2}\.'

    for i in range(maxAttempt):
        sendall(socket, full_command.encode())
        response += recvFromSocket(socket)
        #This will match every RETR response, but also match all STAT and UIDL response so 
        #we also need to check
    
        if command == 'RETR':
            match_response_substrs = re.findall(stat_uidl_retr_regex, response)
            match_response_substrs = [substr for substr in match_response_substrs 
                                    if (re.match(pop3_list_response, substr)==None 
                                    and re.match(pop3_uidl_response, substr)==None)]
        elif command == 'LIST':
            match_response_substrs = re.findall(pop3_list_response, response)
        else: #command == 'UIDL':
            match_response_substrs = re.findall(pop3_uidl_response, response)
        
        if len(match_response_substrs) > 0 and command != 'RETR':
            return True, match_response_substrs[0]
        if len(match_response_substrs) > 0 and command == 'RETR':
            min_defects = 999
            index = -1
            #Get the MIME string with least defects
            i = 0
            for substr in match_response_substrs:
                message = message_from_string(substr)
                #If we got complete message, stop resending
                if (errors.StartBoundaryNotFoundDefect not in message.defects 
                and errors.CloseBoundaryNotFoundDefect not in message.defects):
                    return True, substr
            
    
    return False, None
    
    

def sendSMTPEmail(config: GeneralConfig, sendTo: str, data: str, maxAttempt=10):
    bin_data_with_terminal_line = (data + '\r\n.\r\n').encode()
    socket = initSocket(config, True)
    server = config.configs.get('server')
    from_address = config.configs.get('email_address')


    if (socket is None) or server == None or from_address == None:
        return False, -1
    
    ehlo_command = ('EHLO '+server+'\r\n').encode()
    mail_from = ('MAIL FROM: '+from_address+'\r\n').encode()
    rcpt_to = ('RCPT TO: '+sendTo+'\r\n').encode()
    data_command = 'DATA\r\n'.encode()
    quit_command = 'QUIT\r\n'.encode()
    
    response = recvFromSocket(socket)

    if re.match(smtp_send_email_temporary_error, response):
        sendall(socket, quit_command)
        socket.close()
        return False
    
    if re.match(smtp_send_email_permanent_error, response):
        sendall(socket, quit_command)
        socket.close()
        return False
    
    for i in range(maxAttempt):
        sendall(socket, ehlo_command)
        sendall(socket, mail_from)
        sendall(socket, rcpt_to)

        response = recvFromSocket(socket)

        if re.match(smtp_send_email_temporary_error, response):
            continue
    
        if re.match(smtp_send_email_permanent_error, response):
            sendall(socket, quit_command)
            socket.close()
            return False

        if re.match(smtp_send_email_ok_response, response) == None:
            continue #Corrupted/out of order response

        sendall(socket, data_command)
        response = recvFromSocket(socket)

        result = sendall(socket, bin_data_with_terminal_line)
        if result == False:
            socket.close()
            return False

        response = recvFromSocket(socket)

        if re.match(smtp_send_email_end_email_ok, response):
            sendall(socket, quit_command)
            socket.close()
            return True
        else:
            continue
    sendall(socket, quit_command)
    socket.close()
    return False





    

