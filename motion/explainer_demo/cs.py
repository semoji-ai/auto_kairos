import sys
from pathlib import Path
from PIL import Image
D=str(Path(__file__).resolve().parent.parent / "video/out/explainer_demo_stills") + "/"
out=sys.argv[1]; fs=sys.argv[2:]
ims=[Image.open(f'{D}f{int(x):04d}.jpg').resize((960,540)) for x in fs]
rows=(len(ims)+1)//2
s=Image.new('RGB',(1920,540*rows))
for i,im in enumerate(ims): s.paste(im,((i%2)*960,(i//2)*540))
s.save(f'{out}.jpg',quality=85)
