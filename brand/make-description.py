"""Mark — description card. Generated portrait composited onto the brand ground."""
import pathlib
from PIL import Image, ImageDraw, ImageFont, ImageFilter

OUT = pathlib.Path("/home/claude/mark-icon/desc")
W, H, S = 640, 360, 3
NW, NH = W*S, H*S

INK    = (11, 23, 37)
INK_HI = (19, 38, 58)
GRID   = (28, 52, 78)
GOLD   = (217, 164, 65)
TEXT   = (236, 240, 246)
MUTED  = (130, 156, 184)

def font(px, bold=False):
    p = ("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf" if bold
         else "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf")
    try: return ImageFont.truetype(p, int(px))
    except OSError: return ImageFont.load_default()

def grade(im):
    """Cool the portrait toward the ink palette and lift its blacks to match."""
    px = im.load()
    w, h = im.size
    for y in range(h):
        for x in range(w):
            r, g, b = px[x, y][:3]
            r = min(255, int(r*0.94 + INK[0]*0.16))
            g = min(255, int(g*0.97 + INK[1]*0.16))
            b = min(255, int(b*1.04 + INK[2]*0.16))
            px[x, y] = (r, g, b)
    return im

def build():
    img = Image.new("RGB", (NW, NH), INK)
    d = ImageDraw.Draw(img, "RGBA")
    px = lambda v: int(v*S)

    # ground
    for i in range(200, 0, -1):
        t = i/200; k = (1-t)**2.3; r = int(NH*1.15*t)
        col = tuple(int(INK[j] + (INK_HI[j]-INK[j])*k) for j in range(3))
        d.ellipse([px(430)-r, px(150)-r, px(430)+r, px(150)+r], fill=col)
    for i in range(1, 9):
        y = NH*i/9
        d.line([0, y, NW, y], fill=GRID+(60,), width=max(1, int(S*0.8)))

    # portrait: crop away the warm strip at the far left, keep head and shoulders
    p = Image.open("mark-portrait-source.png").convert("RGB").crop((128, 70, 768, 896))
    tw = px(300)
    p = p.resize((tw, int(p.height * tw / p.width)), Image.LANCZOS)
    if p.height > NH:
        p = p.crop((0, 0, p.width, NH))
    p = grade(p)

    # feather the left edge so he emerges from the ground rather than sitting on it
    mask = Image.new("L", p.size, 255)
    md = ImageDraw.Draw(mask)
    fade = px(110)
    for x in range(fade):
        md.line([x, 0, x, p.size[1]], fill=int(255 * (x/fade)**1.5))
    mask = mask.filter(ImageFilter.GaussianBlur(px(2)))
    img.paste(p, (NW - p.width, NH - p.height), mask)

    # a thin gold rule echoing the rim light, anchoring type to figure
    d.line([px(46), px(196), px(46)+px(150), px(196)], fill=GOLD+(190,),
           width=max(2, int(S*1.1)))

    # type
    x0 = px(46)
    d.text((x0, px(88)),  "MARK", font=font(px(56), True), fill=TEXT)
    d.text((x0+px(3), px(160)), "MOEX  ·  ЕЖЕДНЕВНЫЙ ОБЗОР", font=font(px(16)), fill=GOLD)
    d.text((x0+px(3), px(214)),
           "Что изменилось, что это значит\nи что я бы с этим делал.",
           font=font(px(15)), fill=MUTED, spacing=px(8))
    d.text((x0+px(3), px(286)), "08:52 МСК  ·  ПН–ПТ", font=font(px(12)), fill=(88, 112, 138))

    return img.resize((W, H), Image.LANCZOS)

im = build(); im.save(OUT/"mark-description.png"); print("built", im.size)
