import sys,zlib
def apply_bps(src,d):
    assert d[:4]==b'BPS1'
    p=[4]
    def num():
        data=0;shift=1
        while True:
            x=d[p[0]];p[0]+=1
            data+=(x&0x7f)*shift
            if x&0x80: break
            shift<<=7;data+=shift
        return data
    ss=num();ts=num();ms=num();p[0]+=ms
    out=bytearray(ts);o=0;srel=0;trel=0;end=len(d)-12
    while p[0]<end:
        x=num();cmd=x&3;ln=(x>>2)+1
        if cmd==0: out[o:o+ln]=src[o:o+ln];o+=ln
        elif cmd==1: out[o:o+ln]=d[p[0]:p[0]+ln];p[0]+=ln;o+=ln
        else:
            off=num();off=(-1 if off&1 else 1)*(off>>1)
            if cmd==2:
                srel+=off
                out[o:o+ln]=src[srel:srel+ln];srel+=ln;o+=ln
            else:
                trel+=off
                for _ in range(ln): out[o]=out[trel];o+=1;trel+=1
    assert zlib.crc32(out)==int.from_bytes(d[-8:-4],'little')
    return bytes(out)
if __name__=='__main__':
    src=open(sys.argv[1],'rb').read();d=open(sys.argv[2],'rb').read()
    open(sys.argv[3],'wb').write(apply_bps(src,d))
