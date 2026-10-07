import subprocess,numpy as np,sys,json
v=sys.argv[1]; W,H=160,90
p=subprocess.run(['ffmpeg','-v','error','-i',v,'-vf',f'scale={W}:{H}','-f','rawvideo','-pix_fmt','rgb24','-'],capture_output=True)
a=np.frombuffer(p.stdout,np.uint8).reshape(-1,H,W,3).astype(np.int16)
np.save(v.replace('.mp4','_small.npy'),a.astype(np.uint8))
d=np.abs(np.diff(a,axis=0)).mean(axis=(1,2,3))
np.save(v.replace('.mp4','_diff.npy'),d)
print(v,len(a),'frames')
