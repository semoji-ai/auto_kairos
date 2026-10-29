#!/bin/bash
# 요리사 리그 → 전원 추가 포즈 → 빌드
cd "$(dirname "$0")"
python3 build_rig.py gen c5_chef cast/out/c5_chef.png
python3 build_rig.py build c5_chef > /dev/null
python3 build_rig.py extras walker1 arm_raise_fist,arm_guard_fist,arm_palm_stop,arm_hold,arms_folded,arm_up_hang,legs_sit,face_angry,face_grit,face_frown,face_smile &
python3 build_rig.py extras c2_boss arm_guard_fist,arm_hold,arm_reach,arm_up_hang,arm_out_side,arm_hand_chest,legs_sit,legs_dangle,face_grit,face_worried,face_wide,face_squint,face_angry &
wait
python3 build_rig.py extras c3_woman arm_raise_fist,arms_folded,arm_hold,arm_hand_chin,arm_point,arm_up_hang,face_sparkle,face_smile &
python3 build_rig.py extras c4_elder arm_raise_fist,face_smile,face_grit &
python3 build_rig.py extras c5_chef arm_raise_fist,arm_guard_fist,arm_hold,face_squint,face_grit,face_worried,face_smile &
wait
for c in walker1 c2_boss c3_woman c4_elder c5_chef; do python3 build_rig.py build $c | cut -c1-40; done
cp walk/walker1_backup/legs_stand.png ../../video/public/kit/walker1/legs_stand.png
echo ALL_DONE
