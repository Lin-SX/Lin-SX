#!/usr/bin/env python3
"""Dependency-free Xiangqi rules, shared game state, and README renderer."""
import json, re, os
from copy import deepcopy
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]; FILES="abcdefghi"
NAMES={"K":"将","A":"士","E":"象","H":"马","R":"车","C":"炮","P":"卒"}
def initial():
 b=[[None]*9 for _ in range(10)]; back="R H E A K A E H R".split()
 for x,k in enumerate(back): b[0][x]="b"+k; b[9][x]="r"+k
 for x in (1,7): b[2][x]="bC"; b[7][x]="rC"
 for x in (0,2,4,6,8): b[3][x]="bP"; b[6][x]="rP"
 return {"board":b,"turn":"r","moves":[],"ply":0}
def inside(x,y): return 0<=x<9 and 0<=y<10
def palace(c,x,y): return 3<=x<=5 and (7<=y<=9 if c=="r" else 0<=y<=2)
def king(b,c):
 for y,row in enumerate(b):
  for x,p in enumerate(row):
   if p==c+"K": return x,y
 return None
def attacks(b,x,y):
 p=b[y][x]; c,k=p[0],p[1]; e="b" if c=="r" else "r"; out=[]
 def add(a,d):
  if inside(a,d) and (b[d][a] is None or b[d][a][0]==e): out.append((a,d))
 if k=="K":
  for dx,dy in ((1,0),(-1,0),(0,1),(0,-1)):
   a,d=x+dx,y+dy
   if palace(c,a,d): add(a,d)
  dy=-1 if c=="r" else 1; d=y+dy
  while 0<=d<10:
   if b[d][x]:
    if b[d][x]==e+"K": out.append((x,d))
    break
   d+=dy
 elif k=="A":
  for dx,dy in ((1,1),(1,-1),(-1,1),(-1,-1)):
   a,d=x+dx,y+dy
   if palace(c,a,d): add(a,d)
 elif k=="E":
  for dx,dy in ((2,2),(2,-2),(-2,2),(-2,-2)):
   a,d=x+dx,y+dy
   if inside(a,d) and (d>=5 if c=="r" else d<=4) and b[y+dy//2][x+dx//2] is None: add(a,d)
 elif k=="H":
  for dx,dy,lx,ly in ((2,1,1,0),(2,-1,1,0),(-2,1,-1,0),(-2,-1,-1,0),(1,2,0,1),(-1,2,0,1),(1,-2,0,-1),(-1,-2,0,-1)):
   a,d=x+dx,y+dy
   if inside(a,d) and b[y+ly][x+lx] is None: add(a,d)
 elif k in ("R","C"):
  for dx,dy in ((1,0),(-1,0),(0,1),(0,-1)):
   a,d=x+dx,y+dy; screen=False
   while inside(a,d):
    q=b[d][a]
    if k=="R":
     if q is None: out.append((a,d))
     else:
      if q[0]==e: out.append((a,d))
      break
    elif not screen:
     if q is None: out.append((a,d))
     else: screen=True
    elif q:
     if q[0]==e: out.append((a,d))
     break
    a+=dx; d+=dy
 elif k=="P":
  dy=-1 if c=="r" else 1; add(x,y+dy)
  if (y<=4 if c=="r" else y>=5): add(x-1,y); add(x+1,y)
 return out
def checked(b,c):
 pos=king(b,c)
 if pos is None: return True
 e="b" if c=="r" else "r"
 return any(p and p[0]==e and pos in attacks(b,x,y) for y,row in enumerate(b) for x,p in enumerate(row))
def legal(b,c):
 out=[]; enemy="b" if c=="r" else "r"
 for y,row in enumerate(b):
  for x,p in enumerate(row):
   if not p or p[0]!=c: continue
   for a,d in attacks(b,x,y):
    if b[d][a]==enemy+"K": continue
    t=deepcopy(b); t[d][a],t[y][x]=t[y][x],None
    if not checked(t,c): out.append((x,y,a,d))
 return out
def apply(s,m):
 if m not in legal(s["board"],s["turn"]): raise ValueError("该走法不合法，可能已被其他玩家抢先落子。")
 x,y,a,d=m; b=s["board"]; p=b[y][x]; cap=b[d][a]; c=s["turn"]
 b[d][a],b[y][x]=p,None; s["turn"]="b" if c=="r" else "r"; s["ply"]+=1
 s["moves"].append({"from":FILES[x]+str(y),"to":FILES[a]+str(d),"piece":p,"captured":cap,"by":c})
 return s
def render(s):
 b=s["board"]; SVG=ROOT/"assets/xiangqi.svg"; SVG.parent.mkdir(exist_ok=True)
 svg=['<svg xmlns="http://www.w3.org/2000/svg" width="760" height="850" viewBox="0 0 760 850"><rect width="100%" height="100%" rx="22" fill="#f4dfb4"/><rect x="22" y="22" width="716" height="806" rx="16" fill="none" stroke="#7b4b25" stroke-width="4"/>']
 for y in range(10): svg.append(f'<path d="M70 {70+y*80} H710" stroke="#70451f" stroke-width="3"/>')
 for x in range(9):
  xx=70+x*80; svg.append(f'<path d="M{xx} 70 V{390 if x not in (0,8) else 790} '+(f'M{xx} 470 V790' if x not in (0,8) else '')+'" stroke="#70451f" stroke-width="3"/>')
 svg.append('<path d="M310 70 L470 230 M470 70 L310 230 M310 630 L470 790 M470 630 L310 790" stroke="#70451f" stroke-width="3" fill="none"/><text x="380" y="438" text-anchor="middle" font-size="34" fill="#9b704b">楚 河　　 漢 界</text>')
 for y,row in enumerate(b):
  for x,p in enumerate(row):
   if not p: continue
   c,k=p; ch=NAMES[k]
   if k=="K": ch="帅" if c=="r" else "将"
   if k=="A": ch="仕" if c=="r" else "士"
   if k=="E": ch="相" if c=="r" else "象"
   if k=="P": ch="兵" if c=="r" else "卒"
   ink="#b32025" if c=="r" else "#252525"; cx=70+x*80; cy=70+y*80
   svg += [f'<circle cx="{cx}" cy="{cy}" r="29" fill="#f9edcf" stroke="{ink}" stroke-width="4"/>',f'<text x="{cx}" y="{cy+11}" text-anchor="middle" font-size="31" font-weight="700" fill="{ink}">{ch}</text>']
 svg.append('<text x="380" y="820" text-anchor="middle" font-size="18" fill="#70451f">LIN-SX · CHINESE CHESS</text></svg>')
 SVG.write_text("\n".join(svg),encoding="utf-8")
 groups={}
 for x,y,a,d in legal(b,s["turn"]): groups.setdefault((x,y),[]).append((a,d))
 side="红方" if s["turn"]=="r" else "黑方"
 lines=["<!-- XIANGQI:START -->","![Chinese chess board](assets/xiangqi.svg)",f"**当前回合：{side}** · 已走 {s['ply']} 手 · 合法走法 {sum(map(len,groups.values()))} 种","","### 下一步怎么走？","和 marcizhu 的国际象棋示例一样，下面直接列出当前所有合法走法。**点击「目标位置」就会跳转到预填好棋步的 GitHub Issue 页面**；你只需提交 Issue，不用手动填写内容。","","| 棋子 / 起点 | 可选目标位置（点击即可提交） |","|:---:|:---|"]
 if not groups: lines.append("| — | 当前没有合法走法，棋局结束。 |")
 for (x,y),dest in sorted(groups.items(),key=lambda z:(z[0][1],z[0][0])):
  p=b[y][x]; c,k=p; name=NAMES[k]
  if k=="K": name="帅" if c=="r" else "将"
  if k=="A": name="仕" if c=="r" else "士"
  if k=="E": name="相" if c=="r" else "象"
  if k=="P": name="兵" if c=="r" else "卒"
  links=[]
  for a,d in dest:
   mv=f"{FILES[x]}{y}-{FILES[a]}{d}"
   from urllib.parse import quote
   url=f"https://github.com/Lin-SX/Lin-SX/issues/new?title={quote('Xiangqi move: '+mv)}&body={quote('xiangqi: '+mv)}"
   links.append(f"[{FILES[a]}{d}]({url})")
  lines.append(f"| **{name} {FILES[x]}{y}** | "+"、".join(links)+" |")
 lines += ["","### 最近走棋"]+[f"- {'红' if m['by']=='r' else '黑'}方：{m['from']} → {m['to']}" for m in s["moves"][-8:][::-1]] or ["- 尚未开始"]
 lines += ["","<sub>点击任一目标位置会创建棋步 Issue；GitHub Actions 验证棋规后自动刷新棋盘。多人共享同一棋局。</sub>","<!-- XIANGQI:END -->"]
 rp=ROOT/"README.md"; old=rp.read_text(encoding="utf-8"); start="<!-- XIANGQI:START -->"; end="<!-- XIANGQI:END -->"
 rp.write_text(old[:old.index(start)]+"\n".join(lines)+old[old.index(end)+len(end):],encoding="utf-8")
def main():
 statefile=ROOT/"state/game.json"; statefile.parent.mkdir(exist_ok=True)
 s=json.loads(statefile.read_text(encoding="utf-8")) if statefile.exists() else initial()
 render(s)
if __name__=="__main__": main()
