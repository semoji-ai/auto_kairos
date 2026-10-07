import sys,re
L=[l.rstrip('\n') for l in open(sys.argv[1]) if l.startswith('[')]
n=int(sys.argv[2]) if len(sys.argv)>2 else 4
for i in range(0,len(L),n):
    ts=L[i][1:8]; print(ts,' '.join(x.split('] ',1)[1] for x in L[i:i+n]))
