"""MarkWatch avatar — bold M, lighter W whose final stroke breaks upward."""
import math, pathlib
from PIL import Image, ImageDraw

OUT = pathlib.Path("/home/claude/mark-icon")
S, SS = 512, 8
N = S * SS

INK    = (11, 23, 37)
INK_HI = (17, 34, 54)
GRID   = (30, 55, 82)
BASE   = (44, 76, 108)
GOLD   = (217, 164, 65)
GOLD_D = (168, 122, 42)

def disc(d, cx, cy, r, fill):
    d.ellipse([cx-r, cy-r, cx+r, cy+r], fill=fill)

def geometry(R, oc):
    """Derive M and W, then centre the pair on the disc."""
    foot = oc + R * 0.300
    mtop = foot - R * 0.600
    mval = foot - R * 0.215
    mw   = R * 0.295
    st_m = R * 0.140

    wh    = (foot - mtop) * 0.56
    wtop  = foot - wh
    wrise = wtop - wh * 0.54              # terminal breaks well above the start
    ww    = R * 0.290
    st_w  = st_m * 0.50

    mx = 0.0
    M = [(mx - mw, foot), (mx - mw*0.515, mtop), (mx, mval),
         (mx + mw*0.515, mtop - R*0.045), (mx + mw, foot)]
    wx0 = mx + mw + R * 0.098
    W = [(wx0, wtop), (wx0 + ww*0.26, foot), (wx0 + ww*0.50, wtop + wh*0.28),
         (wx0 + ww*0.74, foot), (wx0 + ww, wrise)]

    # centre the inked pair, not the coordinates
    xs = [x for x, _ in M + W]
    ys = [y for _, y in M + W]
    dx = -((min(xs) - st_m/2 + max(xs) + st_w/2) / 2)
    dy = oc - ((min(ys) - st_m/2 + max(ys) + st_m/2) / 2)
    M = [(x + dx, y + dy) for x, y in M]
    W = [(x + dx, y + dy) for x, y in W]
    return M, W, foot + dy, mtop + dy, st_m, st_w

def build() -> Image.Image:
    img = Image.new("RGB", (N, N), INK)
    d = ImageDraw.Draw(img, "RGBA")
    c, R = N/2, N*0.5
    oc = c - N * 0.010

    for i in range(150, 0, -1):
        t = i/150; k = (1-t)**2.6
        disc(d, c, oc, R*(0.30+0.72*t),
             tuple(int(INK[j] + (INK_HI[j]-INK[j])*k) for j in range(3)))

    M, W, foot, mtop, st_m, st_w = geometry(R, 0.0)
    M = [(c+x, oc+y) for x, y in M]
    W = [(c+x, oc+y) for x, y in W]
    foot += oc; mtop += oc
    st_m, st_w = int(st_m), max(2, int(st_w))

    span = R * 0.78
    for i in range(-3, 4):
        y = foot - (foot - mtop) * (i+3)/6.0
        dy = y - oc
        if abs(dy) < span:
            h = math.sqrt(span**2 - dy**2)
            d.line([c-h, y, c+h, y], fill=GRID+(100,), width=int(N*0.0022))
    dy = foot - oc
    h = math.sqrt(span**2 - dy**2)
    d.line([c-h, foot, c+h, foot], fill=BASE+(160,), width=int(N*0.0032))

    d.line(M, fill=GOLD, width=st_m, joint="curve")
    for x, y in M: disc(d, x, y, st_m/2, GOLD)
    for x, y in (M[0], M[-1]):
        d.rectangle([x-st_m/2, y-st_m/2, x+st_m/2, y], fill=GOLD)

    d.line(W, fill=GOLD, width=st_w, joint="curve")
    for x, y in W: disc(d, x, y, st_w/2, GOLD)

    d.ellipse([c-R+1, oc-R+1, c+R-1, oc+R-1],
              outline=GOLD_D+(95,), width=int(N*0.0035))
    return img.resize((S, S), Image.LANCZOS)

def sheet(icon):
    sizes = [512, 160, 96, 48]; pad, gap = 56, 48
    sh = Image.new("RGB", (pad*2+sum(sizes)+gap*3, pad*2+512+40), (248,246,242))
    x = pad
    for s in sizes:
        m = Image.new("L", (s*4, s*4), 0)
        ImageDraw.Draw(m).ellipse([0,0,s*4-1,s*4-1], fill=255)
        m = m.resize((s, s), Image.LANCZOS)
        cc = Image.new("RGB", (s, s), (248,246,242))
        cc.paste(icon.resize((s, s), Image.LANCZOS), (0,0), m)
        sh.paste(cc, (x, pad+(512-s)//2))
        ImageDraw.Draw(sh).text((x, pad+528), f"{s}px", fill=(120,116,110))
        x += s + gap
    return sh

icon = build()
icon.save(OUT/"mark-avatar-512.png")
icon.resize((1024,1024), Image.LANCZOS).save(OUT/"mark-avatar-1024.png")
sheet(icon).save(OUT/"mark-avatar-scales.png")
print("rebuilt")
