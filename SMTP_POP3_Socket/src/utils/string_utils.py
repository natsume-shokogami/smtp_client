import string

def parseStringByDelim(pstring, delim):
    if pstring == None:
        return list()
    delim_len = len(delim)
    str_len = len(pstring)
    res = list()
    prev = 0
    for i in range(str_len-delim_len+1):
        if pstring[i:i+delim_len] == delim:
            if i == 0:
                prev = i + delim_len
            if (i>=1 and pstring[i-1] != '\\'):
                res.append(pstring[prev:i])
                prev = i + delim_len

    if prev != str_len-delim_len:
        res.append(pstring[prev:])
    res = [i.replace('\\', '') for i in res if i != '']
    return res