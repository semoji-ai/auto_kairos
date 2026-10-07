import sys,subprocess,os
from PIL import Image,ImageDraw
src,prefix,out=sys.argv[1],sys.argv[2],sys.argv[3]; times=[float(x) for x in sys.argv[4].split(',')]
cols=4; W=400; ims=[]
for t in times:
    f=f'{prefix}_{t:06.1f}.jpg'
    if not os.path.exists(f):
        subprocess.run(['ffmpeg','-loglevel','error','-y','-ss',str(t),'-i',src,'-frames:v','1','-vf',f'scale={W}:-2',f])
    im=Image.open(f).convert('RGB'); d=ImageDraw.Draw(im); d.rectangle([0,0,70,22],fill='black'); d.text((4,4),f'{int(t//60)}:{t%60:04.1f}',fill='yellow'); ims.append(im)
h=ims[0].height; rows=(len(ims)+cols-1)//cols
S=Image.new('RGB',(W*cols,h*rows))
for i,im in enumerate(ims): S.paste(im,((i%cols)*W,(i//cols)*h))
S.save(out,quality=80); print(out,S.size)
