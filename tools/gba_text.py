CH={0x00:' '}
s="0123456789!?.-"
for i,c in enumerate(s): CH[0xA1+i]=c
CH.update({0xB0:'…',0xB1:'“',0xB2:'”',0xB3:'‘',0xB4:'\'',0xB5:'♂',0xB6:'♀',0xB8:',',0xBA:'/'})
for i in range(26): CH[0xBB+i]=chr(65+i); CH[0xD5+i]=chr(97+i)
CH.update({0xF0:':',0xFE:'|',0xFA:'|',0xFB:'||',0x1B:'é',0x34:'Lv',0x53:'PK',0x54:'MN'})
def dec(b,o=0,maxlen=4000):
    out=[];i=o
    while i<len(b) and i-o<maxlen:
        c=b[i]
        if c==0xFF: break
        if c==0xFD: out.append('{B%02x}'%b[i+1]);i+=2;continue
        if c==0xFC:
            out.append('{C%02x}'%b[i+1]);i+=2;continue
        out.append(CH.get(c,'[%02x]'%c));i+=1
    return ''.join(out)
