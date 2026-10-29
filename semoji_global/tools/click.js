// 화면 좌표 클릭(논리 좌표).  usage: osascript -l JavaScript tools/click.js X Y
ObjC.import('CoreGraphics');
function run(a){var x=+a[0],y=+a[1];[5,1,2].forEach(function(t){$.CGEventPost(0,$.CGEventCreateMouseEvent(null,t,$.CGPointMake(x,y),0));delay(0.15);});}
