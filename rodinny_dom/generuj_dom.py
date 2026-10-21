"""Generátor výkresu „Rodinný dom“ – architektonická štúdia (základy, pôdorysy, krov, rez, pohľady, situácia).

Všetko je v mm, v mierke modelu 1:1. Jednotlivé pohľady sú v modeli vedľa seba (každý má vlastný počiatok).
Spustenie:  python rodinny_dom/generuj_dom.py        (potrebuje ezdxf, shapely, matplotlib)
Výstup:     Rodinný dom.dxf  +  náhľady nahlad_*.png

Súradnice pôdorysov: počiatok = vonkajší juhozápadný roh domu, x -> východ, y -> sever (ulica je na severe).
Rez a pohľady: z = výška nad čistou podlahou 1.NP (±0,000); terén vonku = -300.
"""
from __future__ import annotations

import math
from pathlib import Path

import ezdxf
from ezdxf.enums import TextEntityAlignment as TA
from shapely.geometry import box, Polygon
from shapely.ops import unary_union

OUT = Path(__file__).resolve().parent
NAME = "Rodinný dom"

# ------------------------------------------------------------------ parametre domu
HW, HD = 11000, 9000          # vonkajšie rozmery domu (V–Z × J–S)
T_EPS, T_MUR = 150, 300       # fasádna izolácia, tehlový múr (spolu 450)
IN = T_EPS + T_MUR            # 450 – vnútorný líc obvodového múru
Z_STROP0, Z_STROP1 = 2750, 3000   # ŽB strop nad 1.NP
Z_P2 = 3100                   # čistá podlaha podkrovia
Z_WALL = 4200                 # horná hrana múru (s vencom)
Z_TER = -300                  # terén
Z_FOUND = -1300               # základová škára (1,0 m pod terénom)
ALPHA = 35.0                  # sklon strechy
TAN = math.tan(math.radians(ALPHA))
COS = math.cos(math.radians(ALPHA))
Z_PLATE = 4340                # spodná hrana krokvy nad vonkajším lícom múru (y = 150)
OVER_EAVE, OVER_GABLE = 500, 400
H_RAFTER, H_TILE, H_UNDER = 200, 320, 100   # krokva, krytina s latovaním, podkrokvová vrstva (kolmo na rovinu strechy)
RISERS = 18
RISE = Z_P2 / RISERS          # 172,2
TREAD = 265
Y_HALL0, Y_HALL1 = 5400, 8550  # hala so schodiskom (pôdorys 1.NP)
Z_LAND = 9 * RISE             # medzipodesta


def zur(y: float) -> float:
    """Spodná hrana krokvy (rovina strechy) v mieste y – symetricky okolo hrebeňa y = 4500."""
    yy = min(y, HD - y)
    return Z_PLATE + (yy - 150) * TAN


def zout(y: float) -> float:
    """Vonkajší povrch krytiny."""
    return zur(y) + H_TILE / COS


def zin(y: float) -> float:
    """Vnútorný povrch šikmého stropu v podkroví."""
    return zur(y) - H_UNDER / COS


Z_RIDGE = zout(HD / 2)

# ------------------------------------------------------------------ vrstvy
LAYERS = {
    # meno: (farba ACI, hrúbka čiary 1/100 mm, typ čiary)
    "ZAKLADY": (8, 50, "Continuous"),
    "STENY_NOSNE": (7, 70, "Continuous"),
    "STENY_PRIECKY": (7, 35, "Continuous"),
    "IZOLACIA": (2, 25, "Continuous"),
    "STROP": (7, 50, "Continuous"),
    "OKNA": (4, 25, "Continuous"),
    "DVERE": (3, 25, "Continuous"),
    "SCHODISKO": (6, 25, "Continuous"),
    "NABYTOK": (8, 18, "Continuous"),
    "TERASA": (30, 35, "Continuous"),
    "KROV": (30, 35, "Continuous"),
    "STRECHA": (1, 35, "Continuous"),
    "POHLAD": (7, 35, "Continuous"),
    "TEREN": (94, 50, "Continuous"),
    "POZEMOK": (3, 50, "DASHDOT"),
    "SITUACIA": (7, 35, "Continuous"),
    "PRIPOJKY": (5, 35, "DASHED"),
    "SKRYTE": (8, 18, "DASHED"),
    "REZ_LINIA": (1, 35, "DASHDOT"),
    "KOTY": (4, 18, "Continuous"),
    "TEXT": (7, 25, "Continuous"),
    "RAM": (7, 50, "Continuous"),
}

AL = {"L": "LEFT", "C": "CENTER", "R": "RIGHT", "ML": "MIDDLE_LEFT", "MC": "MIDDLE_CENTER", "MR": "MIDDLE_RIGHT",
      "BL": "BOTTOM_LEFT", "BC": "BOTTOM_CENTER", "BR": "BOTTOM_RIGHT"}


def polys(g):
    if g.is_empty:
        return []
    if g.geom_type == "Polygon":
        return [g]
    return [p for gg in g.geoms for p in polys(gg)]


class V:
    """Pohľad/výkres s vlastným počiatkom a mierkou."""

    def __init__(self, msp, ox, oy, sc):
        self.m, self.ox, self.oy, self.sc = msp, ox, oy, sc
        self.lts = sc / 2

    def P(self, x, y):
        return (self.ox + x, self.oy + y)

    def _at(self, layer, lt=None, **kw):
        at = {"layer": layer, **kw}
        if lt:
            at["linetype"] = lt
            at["ltscale"] = self.lts
        return at

    def line(self, x1, y1, x2, y2, layer, lt=None, **kw):
        return self.m.add_line(self.P(x1, y1), self.P(x2, y2), dxfattribs=self._at(layer, lt, **kw))

    def pl(self, pts, layer, closed=False, lt=None, **kw):
        return self.m.add_lwpolyline([self.P(*p) for p in pts], close=closed, dxfattribs=self._at(layer, lt, **kw))

    def rect(self, x1, y1, x2, y2, layer, **kw):
        return self.pl([(x1, y1), (x2, y1), (x2, y2), (x1, y2)], layer, True, **kw)

    def circle(self, x, y, r, layer, **kw):
        return self.m.add_circle(self.P(x, y), r, dxfattribs=self._at(layer, **kw))

    def arc(self, x, y, r, a1, a2, layer, **kw):
        return self.m.add_arc(self.P(x, y), r, a1, a2, dxfattribs=self._at(layer, **kw))

    def text(self, x, y, s, h, layer="TEXT", al="MC", rot=0.0, **kw):
        e = self.m.add_text(s, height=h * self.sc, rotation=rot, dxfattribs={"layer": layer, "style": "DOM", **kw})
        e.set_placement(self.P(x, y), align=TA[AL[al]])
        return e

    def fill(self, g, layer, color=7, pattern=None, ps=1.0, pa=0):
        for p in polys(g):
            h = self.m.add_hatch(color=color, dxfattribs={"layer": layer})
            if pattern:
                h.set_pattern_fill(pattern, color=color, scale=ps, angle=pa)
            else:
                h.set_solid_fill(color=color)
            h.paths.add_polyline_path([self.P(*c) for c in p.exterior.coords[:-1]], is_closed=True)
            for r in p.interiors:
                h.paths.add_polyline_path([self.P(*c) for c in r.coords[:-1]], is_closed=True)

    def outline(self, g, layer, **kw):
        for p in polys(g):
            for r in [p.exterior, *p.interiors]:
                self.pl([tuple(c) for c in r.coords[:-1]], layer, True, **kw)

    def dh(self, xs, y, ref, style=None):
        """Reťazová kóta vodorovne: body xs, kótovacia čiara vo výške y, začiatok pomocných čiar ref."""
        st = style or f"DOM_{self.sc}"
        for a, b in zip(xs, xs[1:]):
            self.m.add_linear_dim(base=self.P(a, y), p1=self.P(a, ref), p2=self.P(b, ref), angle=0, dimstyle=st,
                                  dxfattribs={"layer": "KOTY"}).render()

    def dv(self, ys, x, ref, style=None):
        st = style or f"DOM_{self.sc}"
        for a, b in zip(ys, ys[1:]):
            self.m.add_linear_dim(base=self.P(x, a), p1=self.P(ref, a), p2=self.P(ref, b), angle=90, dimstyle=st,
                                  dxfattribs={"layer": "KOTY"}).render()

    def title(self, x, y, name, scale_txt):
        self.text(x, y, name, 5.0, "TEXT", "MC", color=7)
        self.text(x, y - 5.5 * self.sc, scale_txt, 3.0, "TEXT", "MC")
        self.line(x - 14 * self.sc, y - 2.8 * self.sc, x + 14 * self.sc, y - 2.8 * self.sc, "TEXT", lineweight=50)


def level(v: V, x, z, txt, side=1, size=1.0):
    """Výšková kóta – trojuholník + text (x, z v mm)."""
    d = 1.6 * v.sc * size
    v.pl([(x, z), (x - d * 0.6, z + d), (x + d * 0.6, z + d)], "KOTY", True)
    v.line(x - d, z, x + side * 14 * v.sc, z, "KOTY")
    v.text(x + side * 1.5 * v.sc, z + 0.5 * v.sc, txt, 2.2, "KOTY", "BL" if side > 0 else "BR")


def door(v: V, hx, hy, dc, do, w, layer="DVERE"):
    """Krídlo dverí: záves (hx,hy), zatvorená poloha dc°, otvorená do°, šírka w."""
    v.line(hx, hy, hx + w * math.cos(math.radians(do)), hy + w * math.sin(math.radians(do)), layer)
    a1 = dc if (dc + 90) % 360 == do % 360 else do
    v.arc(hx, hy, w, a1 % 360, a1 % 360 + 90, layer, lineweight=13)


# ------------------------------------------------------------------ otvory (okná a dvere)
# wall: J S V Z, a-b = rozsah pozdĺž steny, sill-head = výška parapetu a nadpražia (z od ±0,000)
WIN = [
    dict(f=1, wall="S", a=900, b=2900, sill=900, head=2400, k="okno"),
    dict(f=1, wall="S", a=3300, b=4900, sill=900, head=2400, k="okno"),
    dict(f=1, wall="S", a=5400, b=7400, sill=0, head=2200, k="dvere"),
    dict(f=1, wall="S", a=8000, b=9600, sill=900, head=2400, k="okno"),
    dict(f=1, wall="E", a=1200, b=2800, sill=900, head=2400, k="okno"),
    dict(f=1, wall="W", a=1600, b=3400, sill=900, head=2400, k="okno"),
    dict(f=1, wall="W", a=6000, b=7400, sill=900, head=2100, k="okno"),
    dict(f=1, wall="N", a=4050, b=4950, sill=0, head=2100, k="dvere"),
    dict(f=1, wall="N", a=1400, b=2600, sill=900, head=2100, k="okno"),
    dict(f=1, wall="N", a=7700, b=8500, sill=1300, head=2100, k="okno"),
    dict(f=1, wall="N", a=9537, b=10137, sill=1500, head=2100, k="okno"),
    dict(f=2, wall="W", a=2000, b=3300, sill=4100, head=5300, k="okno"),
    dict(f=2, wall="W", a=5800, b=7000, sill=4100, head=5300, k="okno"),
    dict(f=2, wall="E", a=2000, b=3300, sill=4100, head=5300, k="okno"),
]
# strešné okná: strana, x od-do (rovnobežne s hrebeňom), spodná hrana y
ROOF_WIN = [("S", 1800, 2580), ("S", 3600, 4380), ("S", 6400, 7180), ("S", 8400, 9180),
            ("N", 1500, 2280), ("N", 7900, 8680)]
RW_Y0, RW_LEN = 300, 1400   # spodná hrana okna (y), dĺžka v rovine strechy


def ext_openings(f):
    out = []
    for w in WIN:
        if w["f"] != f:
            continue
        a, b = w["a"], w["b"]
        out.append({"S": box(a, -1, b, IN + 1), "N": box(a, HD - IN - 1, b, HD + 1),
                    "W": box(-1, a, IN + 1, b), "E": box(HW - IN - 1, a, HW + 1, b)}[w["wall"]])
    return out


# ------------------------------------------------------------------ steny
BEAR1 = [(450, 5150, 10550, 5400), (3800, 5400, 4050, 8550)]
PART1 = [(7075, 5400, 7200, 8550), (7200, 6300, 10550, 6425), (9000, 6425, 9125, 8550),
         (8975, 3625, 9100, 5150), (8975, 3625, 10550, 3750)]
OPEN1 = [(3799, 5700, 4051, 6500), (4050, 5149, 4950, 5401), (7300, 5149, 8200, 5401),
         (7400, 6299, 8200, 6426), (9500, 6299, 10300, 6426), (8974, 4150, 9101, 4950)]
BEAR2 = [(450, 5150, 4975, 5400), (7075, 5150, 10550, 5400)]
PART2 = [(450, 3950, 10550, 4075), (5200, 450, 5325, 3950), (4850, 5400, 4975, 8550), (7075, 5400, 7200, 8550),
         (9400, 5400, 9525, 8550)]
OPEN2 = [(3800, 3949, 4600, 4076), (6200, 3949, 7000, 4076), (3200, 5149, 4000, 5401), (8000, 5149, 8800, 5401),
         (9650, 5149, 10450, 5401)]


def walls(f):
    eps = box(0, 0, HW, HD).difference(box(T_EPS, T_EPS, HW - T_EPS, HD - T_EPS))
    mas = box(T_EPS, T_EPS, HW - T_EPS, HD - T_EPS).difference(box(IN, IN, HW - IN, HD - IN))
    bear = BEAR1 if f == 1 else BEAR2
    part = PART1 if f == 1 else PART2
    op = unary_union(ext_openings(f))
    iop = unary_union([box(*o) for o in (OPEN1 if f == 1 else OPEN2)])
    eps = eps.difference(op)
    mas = unary_union([mas, *[box(*r) for r in bear]]).difference(op).difference(iop)
    prt = unary_union([box(*r) for r in part]).difference(iop).difference(mas)
    return eps, mas, prt


def draw_walls(v: V, f):
    eps, mas, prt = walls(f)
    v.fill(eps, "IZOLACIA", 2, "ANSI31", 18, 45)
    v.outline(eps, "IZOLACIA")
    v.fill(mas, "STENY_NOSNE", 252)
    v.outline(mas, "STENY_NOSNE")
    v.fill(prt, "STENY_PRIECKY", 254)
    v.outline(prt, "STENY_PRIECKY")


def draw_openings(v: V, f):
    for w in WIN:
        if w["f"] != f:
            continue
        a, b, wl = w["a"], w["b"], w["wall"]
        if w["k"] == "okno":
            if wl == "S":
                cs = (250, 300, 350)
            elif wl == "N":
                cs = (HD - 350, HD - 300, HD - 250)
            elif wl == "W":
                cs = (250, 300, 350)
            else:
                cs = (HW - 350, HW - 300, HW - 250)
            for c in cs:
                if wl in "SN":
                    v.line(a, c, b, c, "OKNA")
                else:
                    v.line(c, a, c, b, "OKNA")


def stairs(v: V, hidden=False):
    lt = "DASHED" if hidden else None
    lay = "SKRYTE" if hidden else "SCHODISKO"
    xl, xm1, xm2, xr = 4975, 5975, 6075, 7075
    yl = Y_HALL0 + 8 * TREAD   # 7520
    for k in range(0, 9):
        y = Y_HALL0 + k * TREAD
        v.line(xl, y, xm1, y, lay, lt)
    for k in range(0, 9):
        y = yl - k * TREAD
        v.line(xm2, y, xr, y, lay, lt)
    v.pl([(xl, Y_HALL0), (xl, Y_HALL1), (xr, Y_HALL1), (xr, Y_HALL0), (xm2, Y_HALL0), (xm2, yl), (xm1, yl),
          (xm1, Y_HALL0)], lay, True, lt)
    v.line(xl, yl, xm1, yl, lay, lt)
    v.line(xm2, yl, xr, yl, lay, lt)
    if not hidden:
        v.pl([(5475, 5500), (5475, 7350)], "SCHODISKO")
        v.pl([(5475, 7350), (5375, 7150), (5575, 7150)], "SCHODISKO", True)
        v.text(5475, 7900, "HORE", 2.0, "SCHODISKO")
        v.text(6575, 7900, "1.NP → 2.NP", 1.6, "SCHODISKO")


def room(v: V, key, name, area_m2, cx, cy, h=2.4):
    v.text(cx, cy + 1.6 * v.sc, f"{key}  {name}", h, "TEXT")
    v.text(cx, cy - 1.4 * v.sc, f"{area_m2:.1f} m²".replace(".", ","), h * 0.85, "TEXT")


def fr(v: V, x1, y1, x2, y2, **kw):
    v.rect(x1, y1, x2, y2, "NABYTOK", **kw)


def bed(v, x, y, w, l, head="N"):
    fr(v, x, y, x + w, y + l)
    pw = w * 0.4
    if head == "N":
        fr(v, x + 60, y + l - 450, x + pw, y + l - 60)
        fr(v, x + w - pw, y + l - 450, x + w - 60, y + l - 60)
    elif head == "S":
        fr(v, x + 60, y + 60, x + pw, y + 450)
        fr(v, x + w - pw, y + 60, x + w - 60, y + 450)


# ------------------------------------------------------------------ pôdorys 1.NP
def plan1(doc, msp, ox, oy):
    v = V(msp, ox, oy, 50)
    draw_walls(v, 1)
    draw_openings(v, 1)
    # dvere
    door(v, 4950, 8550, 180, 270, 900)           # vstupné
    door(v, 3800, 6500, 270, 180, 800)           # izba
    door(v, 8200, 6425, 180, 90, 800)            # technická
    door(v, 10300, 6425, 180, 90, 800)           # WC
    door(v, 9100, 4150, 90, 0, 800)              # špajza
    door(v, 5400, 450, 0, 90, 1000)              # terasa – dvojkrídlové
    door(v, 7400, 450, 180, 90, 1000)
    stairs(v)
    # terasa
    ter = box(3200, -3500, 9200, 0)
    v.outline(ter, "TERASA", lt="DASHED")
    v.fill(ter, "TERASA", 30, "ANSI37", 40, 0)
    v.text(6200, -1750, "TERASA 21,0 m²", 2.4, "TEXT")
    # nábytok
    bed(v, 1300, 6600, 1600, 2000, "N")
    fr(v, 450, 5400, 2450, 6000)                 # skriňa
    fr(v, 1000, 4750, 3000, 5150)                # TV
    fr(v, 1200, 2800, 3400, 3700)                # sedačka
    fr(v, 1700, 2000, 2700, 2500)                # stolík
    fr(v, 5100, 2700, 6900, 3600)                # jedálenský stôl
    for x in (5300, 5900, 6500):
        fr(v, x, 3650, x + 400, 4050)
        fr(v, x, 2250, x + 400, 2650)
    fr(v, 7700, 2200, 9100, 2900)                # ostrovček
    for x in (7950, 8450, 8950):
        v.circle(x - 100 + 100, 3150, 175, "NABYTOK")
    fr(v, 7600, 450, 9950, 1050)                 # kuchynská linka J
    fr(v, 9950, 450, 10550, 3600)                # linka V
    v.circle(10250, 1300, 200, "NABYTOK")       # drez
    for dx, dy in ((10150, 2900), (10150, 3250)):
        v.circle(dx + 100, dy, 110, "NABYTOK")  # varná doska
    fr(v, 9100, 3750, 9400, 5150)                # police špajza
    fr(v, 10250, 3750, 10550, 5150)
    fr(v, 7250, 7800, 7850, 8500)                # zásobník
    v.circle(7550, 8150, 300, "NABYTOK")
    fr(v, 8150, 7900, 8750, 8500)                # tepelné čerpadlo / vnútorná jednotka
    v.text(8450, 8200, "TČ", 2.0, "NABYTOK")
    fr(v, 8150, 6500, 8750, 7100)                # práčka
    v.circle(8450, 6800, 220, "NABYTOK")
    fr(v, 9600, 7900, 10000, 8550)               # WC misa
    v.circle(9800, 7900, 200, "NABYTOK")
    fr(v, 10150, 6600, 10550, 7000)              # umývadielko
    # miestnosti
    room(v, "1.01", "VSTUPNÁ HALA", 9.53, 4500, 6200, 1.8)
    room(v, "1.02", "IZBA", 10.55, 2100, 5750, 2.0)
    room(v, "1.03", "OBÝVAČKA + JEDÁLEŇ + KUCHYŇA", 45.44, 3300, 1400, 2.8)
    room(v, "1.04", "ŠPAJZA", 2.03, 9825, 4450, 1.5)
    room(v, "1.05", "CHODBA", 3.02, 8700, 5850, 1.6)
    room(v, "1.06", "TECHNICKÁ", 3.83, 8100, 7300, 1.6)
    room(v, "1.07", "WC", 3.03, 9800, 7300, 1.6)
    # kóty
    v.dh([0, 1400, 2600, 4050, 4950, 7700, 8500, 9537, 10137, HW], HD + 900, HD)
    v.dh([0, HW], HD + 1700, HD)
    v.dv([0, HD], -1700, 0)
    # značka rezu A–A
    for yy, a in ((-4500, "A"), (HD + 2600, "A")):
        v.text(6500, yy, a, 3.5, "REZ_LINIA")
    v.line(6500, -4000, 6500, HD + 2300, "REZ_LINIA", "DASHDOT", lineweight=50)
    v.pl([(6500, -3500), (6200, -3500)], "REZ_LINIA", lineweight=50)
    v.pl([(6500, HD + 1800), (6200, HD + 1800)], "REZ_LINIA", lineweight=50)
    v.title(HW / 2, -7200, "PÔDORYS 1.NP", "M 1:50")
    return v


# ------------------------------------------------------------------ pôdorys 2.NP (podkrovie)
def plan2(doc, msp, ox, oy):
    v = V(msp, ox, oy, 50)
    draw_walls(v, 2)
    draw_openings(v, 2)
    # schodisko zospodu + otvor
    stairs(v, hidden=True)
    for a, b in (((4975, 5400), (7075, 8550)), ((4975, 8550), (7075, 5400))):
        v.line(a[0], a[1], b[0], b[1], "SCHODISKO", lineweight=13)
    v.line(4975, 5400, 6075, 5400, "SCHODISKO", lineweight=70)   # zábradlie
    v.text(6025, 7000, "OTVOR", 2.0, "SCHODISKO")
    v.text(6025, 6600, "SCHODISKA", 2.0, "SCHODISKO")
    # dvere
    door(v, 3800, 3950, 0, 270, 800)
    door(v, 6200, 3950, 0, 270, 800)
    door(v, 3200, 5400, 0, 90, 800)
    door(v, 8000, 5400, 0, 90, 800)
    door(v, 9650, 5400, 0, 90, 800)
    # hranica výšky 2,20 m
    for y in (zin_y(), HD - zin_y()):
        v.line(450, y, 10550, y, "SKRYTE", "DASHED", lineweight=18)
    v.text(10500, zin_y() - 260, "výška 2,20 m", 1.5, "SKRYTE", "MR")
    v.text(10500, HD - zin_y() + 260, "výška 2,20 m", 1.5, "SKRYTE", "MR")
    # nábytok
    bed(v, 800, 1400, 1800, 2000, "S")           # spálňa
    v.rect(2800, 450, 3400, 1100, "NABYTOK")
    fr(v, 3600, 450, 5200, 1000)                 # skriňa spálňa
    bed(v, 6600, 1400, 1400, 2000, "S")          # izba 3
    fr(v, 8700, 450, 10550, 1050)
    fr(v, 5325, 3350, 6325, 3950)
    bed(v, 1300, 6500, 1400, 2000, "N")          # izba 2
    fr(v, 450, 5400, 2450, 6000)
    fr(v, 3300, 7950, 4850, 8550)
    fr(v, 7250, 7800, 8950, 8500)                # vaňa
    fr(v, 7200, 6400, 7750, 7600)                # umývadlá
    fr(v, 8750, 6700, 9400, 7100)                # WC
    v.circle(8750, 6900, 200, "NABYTOK")
    fr(v, 9525, 5400, 9825, 8550)                # šatník
    fr(v, 10250, 5400, 10550, 8550)
    room(v, "2.01", "CHODBA", 10.86, 3000, 4600, 1.8)
    room(v, "2.02", "SPÁLŇA", 16.63, 3300, 2800, 2.2)
    room(v, "2.03", "IZBA 3", 18.29, 8000, 3300, 2.2)
    room(v, "2.04", "IZBA 2", 13.86, 2300, 7600, 2.0)
    room(v, "2.05", "KÚPEĽŇA", 6.93, 8300, 6000, 1.5)
    room(v, "2.06", "ŠATNÍK", 3.23, 9900, 5900, 1.2)
    v.dh([0, HW], HD + 900, HD)
    v.dv([0, 2000, 3300, 5800, 7000, HD], -900, 0)
    v.dv([0, HD], -1700, 0)
    v.line(6500, -4000, 6500, HD + 2300, "REZ_LINIA", "DASHDOT", lineweight=50)
    v.text(6500, -4500, "A", 3.5, "REZ_LINIA")
    v.text(6500, HD + 2600, "A", 3.5, "REZ_LINIA")
    v.title(HW / 2, -7200, "PÔDORYS 2.NP – PODKROVIE", "M 1:50")
    return v


def zin_y():
    """y, v ktorom je vnútorný šikmý strop 2,20 m nad podlahou podkrovia."""
    return 150 + (Z_P2 + 2200 - H_UNDER / COS * 0 - (Z_PLATE - H_UNDER / COS)) / TAN


# ------------------------------------------------------------------ základy
def zaklady(doc, msp, ox, oy):
    v = V(msp, ox, oy, 50)
    ring = box(0, 0, HW, HD).difference(box(600, 600, HW - 600, HD - 600))
    inner = unary_union([box(600, 5025, HW - 600, 5525), box(3675, 5525, 4175, HD - 600)])
    s = unary_union([ring, inner])
    v.fill(s, "ZAKLADY", 8, "AR-CONC", 4, 0)
    v.outline(s, "ZAKLADY")
    eps, mas, prt = walls(1)
    v.outline(mas, "SKRYTE", lt="DASHED")
    v.outline(eps, "SKRYTE", lt="DASHED")
    # kóty
    v.dh([0, HW], -1400, 0)
    v.dv([0, HD], -1400, 0)
    v.dv([0, 5025, 5525, HD], HW + 1400, 0)
    v.dh([0, 3675, 4175, HW], HD + 900, HD)
    # popisy
    txt = ["Základové pásy ŽB: obvodové š. 600, vnútorné nosné š. 500",
           "Základová škára -1,300 (1,0 m pod terénom, nepremŕzavá hĺbka)",
           "Trieda betónu, výstuž a únosnosť zeminy – podľa statika",
           "a inžinierskogeologického prieskumu (radónové riziko!)"]
    for i, t in enumerate(txt):
        v.text(0, -3300 - i * 420, t, 2.0, "TEXT", "ML")
    v.title(HW / 2, -6200, "ZÁKLADY", "M 1:50")
    return v


# ------------------------------------------------------------------ pôdorys strechy / krov
def krov(doc, msp, ox, oy):
    v = V(msp, ox, oy, 50)
    x0, x1, y0, y1 = -OVER_GABLE, HW + OVER_GABLE, -OVER_EAVE, HD + OVER_EAVE
    v.rect(x0, y0, x1, y1, "STRECHA", lineweight=70)
    v.line(x0, HD / 2, x1, HD / 2, "STRECHA", lineweight=70)
    # obrys domu pod strechou
    v.rect(0, 0, HW, HD, "SKRYTE", lt="DASHED")
    n = 13
    for k in range(n + 1):
        x = k * HW / n
        v.line(x, y0, x, HD / 2, "KROV")
        v.line(x, HD / 2, x, y1, "KROV")
    for y, lab in ((300, "pomúrnica 140×140"), (HD - 300, "pomúrnica 140×140")):
        v.line(x0 + 400, y, x1 - 400, y, "KROV", lineweight=70)
        v.text(HW / 2, y + (350 if y < 1000 else -350), lab, 1.8, "KROV")
    for y in (2250, HD - 2250):
        v.line(x0 + 400, y, x1 - 400, y, "KROV", "DASHED", lineweight=50)
        v.text(HW / 2, y + 300, "stredná väznica (dimenzie a podopretie určí statik)", 1.6, "KROV")
    v.text(HW / 2, HD / 2 + 330, "hrebeňová väznica / hrebeň", 1.8, "KROV")
    # strešné okná
    for side, a, b in ROOF_WIN:
        if side == "S":
            ya, yb = RW_Y0 - 0, RW_Y0 + RW_LEN * COS
        else:
            ya, yb = HD - RW_Y0 - RW_LEN * COS, HD - RW_Y0
        v.rect(a, ya, b, yb, "OKNA", lineweight=35)
        v.line(a, ya, b, yb, "OKNA", lineweight=13)
        v.line(a, yb, b, ya, "OKNA", lineweight=13)
    v.text(HW / 2, HD / 4, "SEDLOVÁ STRECHA 35°", 3.0, "STRECHA")
    v.text(HW / 2, HD * 3 / 4, "SEDLOVÁ STRECHA 35°", 3.0, "STRECHA")
    # šípky spádu
    for x in (1500, HW - 1500):
        v.pl([(x, 3800), (x, 1800)], "STRECHA")
        v.pl([(x, 1800), (x - 100, 2050), (x + 100, 2050)], "STRECHA", True)
        v.pl([(x, HD - 3800), (x, HD - 1800)], "STRECHA")
        v.pl([(x, HD - 1800), (x - 100, HD - 2050), (x + 100, HD - 2050)], "STRECHA", True)
    v.dh([x0, 0, HW, x1], y0 - 700, y0)
    v.dh([x0, x1], y0 - 1400, y0)
    v.dv([y0, 0, HD / 2, HD, y1], x1 + 900, x1)
    v.text(0, HD + 1500, "Rozteč krokiev ≈ 850 mm, krokvy 100×200 – schéma, dimenzie krovu navrhne statik", 2.0, "TEXT", "ML")
    v.title(HW / 2, y0 - 3200, "PÔDORYS STRECHY – SCHÉMA KROVU", "M 1:50")
    return v


# ------------------------------------------------------------------ rez A–A
def rez(doc, msp, ox, oy):
    v = V(msp, ox, oy, 50)
    door_open = box(0, 0, IN, 2200)
    # betón
    conc = unary_union([box(150, Z_STROP0, 5400, Z_STROP1), box(HD - IN, Z_STROP0, HD - T_EPS, Z_STROP1),
                        box(150, Z_WALL - 250, IN, Z_WALL), box(HD - IN, Z_WALL - 250, HD - T_EPS, Z_WALL),
                        box(0, Z_FOUND, 600, -500), box(5025, Z_FOUND, 5525, -500), box(HD - 600, Z_FOUND, HD, -500),
                        Polygon([(7520, 1350), (8550, 1350), (8550, 1550), (7520, 1550)]),
                        Polygon([(7520, 1350), (7520, 1550)] + sum([[(7520 - TREAD * (k - 1), Z_LAND + RISE * k),
                                                                     (7520 - TREAD * k, Z_LAND + RISE * k)] for k in range(1, 9)], [])
                                 + [(Y_HALL0, 2900)])])
    mas = unary_union([box(150, -500, IN, Z_WALL).difference(door_open), box(HD - IN, -500, HD - T_EPS, Z_WALL),
                       box(5150, -500, 5400, Z_STROP0)]).difference(conc)
    eps = unary_union([Polygon([(0, -500), (150, -500), (150, Z_PLATE), (0, zur(0))]).difference(door_open),
                       Polygon([(HD - 150, -500), (HD, -500), (HD, zur(HD)), (HD - 150, Z_PLATE)])])
    v.fill(eps, "IZOLACIA", 2, "ANSI31", 18, 45)
    v.outline(eps, "IZOLACIA")
    v.fill(mas, "STENY_NOSNE", 252)
    v.outline(mas, "STENY_NOSNE")
    v.fill(conc, "STROP", 8, "AR-CONC", 4, 0)
    v.outline(conc, "STROP")
    # podlaha na teréne
    cut = box(5150, -600, 5400, 3000)
    layers = [(-500, -350, "štrk", 8, "GRAVEL", 6), (-350, -200, "betón", 8, "AR-CONC", 4),
              (-200, -80, "EPS", 2, "ANSI31", 14), (-80, 0, "poter", 7, "ANSI37", 20)]
    for z1, z2, _, col, pat, ps in layers:
        g = box(IN, z1, HD - IN, z2).difference(cut)
        v.fill(g, "STROP", col, pat, ps, 0 if pat != "ANSI31" else 45)
        v.outline(g, "STROP", lineweight=13)
    g = box(IN, Z_STROP1, 5400, Z_P2)
    v.fill(g, "STROP", 7, "ANSI37", 20, 0)
    v.outline(g, "STROP", lineweight=13)
    # terasa a terén
    g = box(-3500, -300, 0, -30)
    v.fill(g, "TERASA", 8, "AR-CONC", 4, 0)
    v.outline(g, "TERASA")
    v.line(-8000, Z_TER, -3500, Z_TER, "TEREN")
    v.line(HD, Z_TER, HD + 3500, Z_TER, "TEREN")
    for y in range(-8000, -3500, 500):
        v.line(y, Z_TER, y - 250, Z_TER - 250, "TEREN", lineweight=13)
    for y in range(HD, HD + 3500, 500):
        v.line(y, Z_TER, y - 250, Z_TER - 250, "TEREN", lineweight=13)
    # dvere (terasa) v reze
    v.line(IN / 2, 0, IN / 2, 2200, "DVERE", lineweight=35)
    # schodisko – vzdialený rameno (pohľad)
    v.pl([(Y_HALL0, 0)] + [p for k in range(1, 9) for p in ((Y_HALL0 + TREAD * (k - 1), RISE * k), (Y_HALL0 + TREAD * k, RISE * k))] + [(7520, Z_LAND)], "SCHODISKO", lineweight=18)
    # zábradlie
    v.line(Y_HALL0, Z_P2, Y_HALL0, Z_P2 + 1000, "SCHODISKO", lineweight=35)
    # strecha
    for sgn in (0, 1):
        def Y(y):
            return y if sgn == 0 else HD - y
        # krokva + izolácia
        band = Polygon([(Y(-OVER_EAVE), zur(-OVER_EAVE)), (Y(4500), zur(4500)), (Y(4500), zur(4500) + H_RAFTER / COS),
                        (Y(-OVER_EAVE), zur(-OVER_EAVE) + H_RAFTER / COS)])
        v.fill(band, "KROV", 30, "ANSI31", 18, 45)
        v.outline(band, "KROV")
        tile = Polygon([(Y(-OVER_EAVE), zur(-OVER_EAVE) + H_RAFTER / COS), (Y(4500), zur(4500) + H_RAFTER / COS),
                        (Y(4500), zout(4500)), (Y(-OVER_EAVE), zout(-OVER_EAVE))])
        v.fill(tile, "STRECHA", 1)
        v.outline(tile, "STRECHA")
        und = Polygon([(Y(IN), zur(IN)), (Y(4500), zur(4500)), (Y(4500), zin(4500)), (Y(IN), zin(IN))])
        v.fill(und, "KROV", 8, "ANSI31", 10, 135)
        v.outline(und, "KROV", lineweight=13)
        # pomúrnica
        v.pl([(Y(160), Z_WALL), (Y(160), zur(160)), (Y(300), zur(300)), (Y(300), Z_WALL)], "KROV", True)
    # vnútorný povrch podkrovia
    v.pl([(IN, Z_P2), (IN, zin(IN)), (4500, zin(4500)), (HD - IN, zin(HD - IN)), (HD - IN, Z_P2)], "STROP", lineweight=35)
    v.text(4500, zin(4500) - 450, "PODKROVIE", 2.4, "TEXT")
    v.text(2800, 1100, "OBÝVAČKA + KUCHYŇA", 2.4, "TEXT")
    v.text(6550, 4400, "SCHODISKO", 2.0, "TEXT", rot=0)
    # kóty
    v.dh([0, IN, 5150, 5400, HD - IN, HD], -2200, -1300)
    v.dh([0, HD], -3000, -1300)
    v.dv([Z_FOUND, Z_TER, 0, Z_STROP0, Z_P2, Z_WALL, Z_RIDGE], HD + 2200, HD + 300)
    level(v, -3500, Z_TER, "±0,000 = čistá podlaha 1.NP; terén -0,300", -1)
    for z, t in ((0, "±0,000"), (Z_STROP0, f"+{Z_STROP0 / 1000:.3f}".replace(".", ",") + " podhľad stropu"),
                 (Z_P2, f"+{Z_P2 / 1000:.3f}".replace(".", ",") + " podlaha podkrovia"),
                 (Z_WALL, f"+{Z_WALL / 1000:.3f}".replace(".", ",") + " hrana múru"),
                 (Z_RIDGE, f"+{Z_RIDGE / 1000:.3f}".replace(".", ",") + " hrebeň (od terénu "
                  + f"{(Z_RIDGE - Z_TER) / 1000:.2f}".replace(".", ",") + " m)")):
        level(v, HD + 3300, z, t, 1)
    v.text(-7800, Z_TER + 400, "TERÉN", 2.0, "TEREN", "ML")
    v.title(HD / 2, -5200, "REZ A–A", "M 1:50")
    return v


# ------------------------------------------------------------------ pohľady
def _glaz(v: V, a, b, z1, z2, door_=False):
    v.rect(a, z1, b, z2, "OKNA", lineweight=35)
    v.rect(a + 60, z1 + 60, b - 60, z2 - 60, "OKNA", lineweight=13)
    if not door_ and b - a > 1100:
        m = (a + b) / 2
        v.line(m, z1 + 60, m, z2 - 60, "OKNA", lineweight=13)


def _roof_band(v: V, x0, x1):
    z_e0, z_e1 = zur(-OVER_EAVE), zout(-OVER_EAVE)
    v.rect(x0, z_e0, x1, Z_RIDGE, "POHLAD", lineweight=50)
    z = z_e1 + 400
    v.line(x0, z_e1, x1, z_e1, "POHLAD", lineweight=35)
    while z < Z_RIDGE - 100:
        v.line(x0, z, x1, z, "STRECHA", lineweight=9)
        z += 400


def _terrain(v: V, x0, x1):
    v.line(x0, Z_TER, x1, Z_TER, "TEREN", lineweight=70)
    for x in range(int(x0), int(x1), 600):
        v.line(x, Z_TER, x - 300, Z_TER - 300, "TEREN", lineweight=13)


def elev_long(doc, msp, ox, oy, side):
    """Južný (side='S') alebo severný (side='N') pohľad – dlhá strana, hrebeň v pozadí."""
    v = V(msp, ox, oy, 50)
    xf = (lambda x: x) if side == "S" else (lambda x: HW - x)
    z_wall_top = zur(-OVER_EAVE)
    v.rect(0, Z_TER, HW, z_wall_top, "POHLAD", lineweight=35)
    v.fill(box(0, Z_TER, HW, 0), "POHLAD", 252)     # sokel
    v.line(0, 0, HW, 0, "POHLAD", lineweight=18)
    _roof_band(v, -OVER_GABLE, HW + OVER_GABLE)
    for w in WIN:
        if w["f"] != 1 or w["wall"] != side:
            continue
        a, b = sorted((xf(w["a"]), xf(w["b"])))
        _glaz(v, a, b, w["sill"], w["head"], w["k"] == "dvere")
    for s, a, b in ROOF_WIN:
        if s != side:
            continue
        aa, bb = sorted((xf(a), xf(b)))
        z1 = zout(RW_Y0 if side == "S" else HD - RW_Y0)
        z2 = z1 + RW_LEN * math.sin(math.radians(ALPHA))
        _glaz(v, aa, bb, z1, z2)
    if side == "S":
        v.rect(3200, Z_TER, 9200, -30, "TERASA")
        v.text(6200, -170, "terasa", 1.6, "TERASA")
    else:
        v.rect(xf(4950) - 400, 2300, xf(4050) + 400, 2400, "POHLAD", lineweight=35)  # prístrešok
    _terrain(v, -2500, HW + 2500)
    for z, t in ((0, "±0,000"), (Z_WALL, f"+{Z_WALL / 1000:.3f}".replace(".", ",")),
                 (Z_RIDGE, f"+{Z_RIDGE / 1000:.3f}".replace(".", ","))):
        level(v, HW + 1500, z, t, 1)
    level(v, HW + 1500, Z_TER, "-0,300", 1)
    name = "POHĽAD JUŽNÝ" if side == "S" else "POHĽAD SEVERNÝ (od ulice)"
    v.title(HW / 2, -2400, name, "M 1:50")
    return v


def elev_gable(doc, msp, ox, oy, side):
    """Východný ('E') alebo západný ('W') pohľad – štít."""
    v = V(msp, ox, oy, 50)
    sf = (lambda y: y) if side == "E" else (lambda y: HD - y)
    wall = Polygon([(0, Z_TER), (HD, Z_TER), (HD, zur(0)), (HD / 2, zur(HD / 2)), (0, zur(0))])
    v.outline(wall, "POHLAD", lineweight=35)
    v.fill(box(0, Z_TER, HD, 0), "POHLAD", 252)
    v.line(0, 0, HD, 0, "POHLAD", lineweight=18)
    band = Polygon([(-OVER_EAVE, zur(-OVER_EAVE)), (HD / 2, zur(HD / 2)), (HD + OVER_EAVE, zur(-OVER_EAVE)),
                    (HD + OVER_EAVE, zout(-OVER_EAVE)), (HD / 2, Z_RIDGE), (-OVER_EAVE, zout(-OVER_EAVE))])
    v.fill(band, "STRECHA", 1, "ANSI31", 30, 0)
    v.outline(band, "POHLAD", lineweight=50)
    for w in WIN:
        if w["wall"] != side:
            continue
        a, b = sorted((sf(w["a"]), sf(w["b"])))
        _glaz(v, a, b, w["sill"], w["head"])
    _terrain(v, -2500, HD + 2500)
    for z, t in ((0, "±0,000"), (Z_WALL, f"+{Z_WALL / 1000:.3f}".replace(".", ",")),
                 (Z_RIDGE, f"+{Z_RIDGE / 1000:.3f}".replace(".", ","))):
        level(v, HD + 1700, z, t, 1)
    level(v, HD + 1700, Z_TER, "-0,300", 1)
    v.title(HD / 2, -2400, "POHĽAD VÝCHODNÝ" if side == "E" else "POHĽAD ZÁPADNÝ", "M 1:50")
    return v


# ------------------------------------------------------------------ situácia + poznámky
def situacia(doc, msp, ox, oy):
    v = V(msp, ox, oy, 200)
    PW, PD = 20000, 30000
    hx, hy = 4500, 14000
    v.pl([(0, 0), (PW, 0), (PW, PD), (0, PD)], "POZEMOK", True, "DASHDOT", lineweight=50)
    # ulica
    road = box(-3000, PD, PW + 3000, PD + 5000)
    v.fill(road, "SITUACIA", 253)
    v.outline(road, "SITUACIA", lineweight=18)
    v.text(PW / 2, PD + 2500, "ULICA (verejná komunikácia)", 3.0, "TEXT")
    # dom
    v.rect(hx - OVER_GABLE, hy - OVER_EAVE, hx + HW + OVER_GABLE, hy + HD + OVER_EAVE, "SKRYTE", lt="DASHED")
    v.fill(box(hx, hy, hx + HW, hy + HD), "STENY_NOSNE", 254)
    v.rect(hx, hy, hx + HW, hy + HD, "STENY_NOSNE", lineweight=70)
    v.line(hx - OVER_GABLE, hy + HD / 2, hx + HW + OVER_GABLE, hy + HD / 2, "SKRYTE", lineweight=35)
    v.text(hx + HW / 2, hy + HD / 2 + 700, "RODINNÝ DOM", 3.0, "TEXT")
    v.text(hx + HW / 2, hy + HD / 2 - 100, "11,0 × 9,0 m", 2.4, "TEXT")
    v.text(hx + HW / 2, hy + HD / 2 - 1100, "zastavaná plocha 99,0 m²", 2.0, "TEXT")
    v.text(hx + HW / 2, hy + HD / 2 - 1900, "sedlová strecha 35°, hrebeň V–Z", 1.8, "TEXT")
    # terasa
    v.rect(hx + 3200, hy - 3500, hx + 9200, hy, "TERASA", lt="DASHED")
    v.text(hx + 6200, hy - 1750, "terasa", 2.0, "TERASA")
    # chodník + brána
    v.rect(hx + 4050, hy + HD, hx + 4950, PD, "SITUACIA", lineweight=25)
    v.text(hx + 4500, PD - 3000, "chodník", 2.0, "TEXT", rot=90)
    v.line(hx + 3800, PD, hx + 5200, PD, "SITUACIA", lineweight=100)
    v.text(hx + 4500, PD + 700, "vchod", 2.0, "TEXT")
    # státie
    v.rect(14000, 25000, 19000, PD, "SITUACIA", lineweight=25)
    v.fill(box(14000, 25000, 19000, PD), "SITUACIA", 253, "ANSI37", 90, 0)
    v.text(16500, 27500, "STÁTIE 2 AUTÁ", 2.2, "TEXT")
    v.text(16500, 26700, "5,0 × 5,0 m", 2.0, "TEXT")
    v.line(14000, PD, 19000, PD, "SITUACIA", lineweight=100)
    v.text(16500, PD + 700, "vjazd 5,0 m", 2.0, "TEXT")
    # prípojky (orientačne)
    for x, t in ((11800, "voda"), (12400, "kanalizácia"), (13000, "elektro NN")):
        v.line(x, PD, x, hy + HD, "PRIPOJKY", "DASHED", lineweight=35)
        v.text(x, PD - 1500, t, 1.8, "PRIPOJKY", "MC", rot=90)
    v.text(12400, hy + HD + 700, "prípojky – orientačne", 1.6, "PRIPOJKY")
    # záhrada
    v.text(PW / 2, 5000, "ZÁHRADA (juh)", 3.5, "TEXT")
    v.text(PW / 2, 3800, "pozemok 20 × 30 m = 600 m²", 2.4, "TEXT")
    v.text(PW / 2, 2800, "zastavanosť domu 16,5 %", 2.0, "TEXT")
    # kóty
    v.dh([0, PW], -1800, 0)
    v.dv([0, PD], -1800, 0)
    v.dh([0, hx], hy + HD / 2 + 600, hy + HD / 2)
    v.dh([hx + HW, PW], hy + HD / 2 + 600, hy + HD / 2)
    v.dv([0, hy], hx - 600, hx)
    v.dv([hy + HD, PD], hx - 600, hx)
    # severka
    nx, ny = 17500, 8000
    v.circle(nx, ny, 1200, "SITUACIA")
    v.pl([(nx, ny - 900), (nx - 450, ny - 1400), (nx, ny + 1300), (nx + 450, ny - 1400)], "SITUACIA", True)
    v.text(nx, ny + 1900, "S", 3.0, "TEXT")
    v.title(PW / 2, -4800, "SITUÁCIA", "M 1:200")
    return v


NOTES = [
    "PREDBEŽNÁ ARCHITEKTONICKÁ ŠTÚDIA – nie je projekt pre stavebné konanie.",
    "",
    "Predpoklady (upraviť podľa skutočnosti):",
    "• pozemok 20 × 30 m, rovinatý, ulica na severe, terasa a obytné miestnosti na juh,",
    "• murovaný dom z tehly, sedlová strecha 35°, prízemie + obývané podkrovie, bez garáže,",
    "• regulatívy územného plánu obce (zastavanosť, odstupy, výška, tvar strechy) treba overiť.",
    "",
    "Nad rámec tejto štúdie – vypracujú autorizovaní projektanti:",
    "• statika (základy, ŽB strop, krov) podľa STN EN 1990 – 1997,",
    "• tepelnotechnické posúdenie a energetické hodnotenie (budova A0, STN 73 0540),",
    "• požiarna bezpečnosť (STN 73 0802), ZTI, kúrenie, vetranie, elektro,",
    "• geologický prieskum, radónové riziko, nepremŕzavá hĺbka.",
    "",
    "Schodisko: 18 stupňov × 172 mm, šírka stupnice 265 mm, ramená 1000 mm (STN 73 4130 overiť).",
    "",
    "Orientačné skladby (hrúbky izolácií určí energetický posudok):",
    "Obvodová stena: omietka | EPS fasádny 150 | tehlový múr 300 | vnútorná omietka.",
    "Podlaha na teréne: krytina + anhydrit 80 | EPS 120 | ŽB doska 150 | hydroizolácia | štrk 150.",
    "Strop nad 1.NP: ŽB monolitická doska 250 + plávajúca podlaha podkrovia 100.",
    "Strecha: škridla | latovanie + kontralatovanie | difúzna fólia | krokvy 100×200 s minerálnou vlnou",
    "medzi krokvami 200 + pod krokvami 60 | parozábrana | SDK 12,5.",
]


def poznamky(doc, msp, ox, oy):
    v = V(msp, ox, oy, 100)
    y = 0
    v.text(0, y, "POZNÁMKY, PREDPOKLADY A SKLADBY", 4.0, "TEXT", "ML")
    y -= 900
    for ln in NOTES:
        v.text(0, y, ln, 2.5, "TEXT", "ML")
        y -= 550
    return v


def frame_info(doc, msp, ox, oy):
    v = V(msp, ox, oy, 100)
    v.text(0, 0, "RODINNÝ DOM", 9.0, "TEXT", "ML")
    v.text(0, -1500, "Architektonická štúdia – základy, pôdorysy, krov, rez, pohľady, situácia", 3.5, "TEXT", "ML")
    v.text(0, -2300, "Dátum: 21. 10. 2026   |   Jednotky: mm   |   Súbor: Rodinný dom", 3.0, "TEXT", "ML")


# ------------------------------------------------------------------ hlavné
def build():
    doc = ezdxf.new("R2018", setup=True)
    doc.units = ezdxf.units.MM
    doc.header["$INSUNITS"] = 4
    doc.header["$MEASUREMENT"] = 1
    doc.header["$LTSCALE"] = 1.0
    doc.styles.add("DOM", font="arial.ttf")
    for name, (col, lw, lt) in LAYERS.items():
        doc.layers.add(name, color=col, lineweight=lw, linetype=lt)
    for sc in (50, 100, 200):
        ds = doc.dimstyles.new(f"DOM_{sc}")
        for k, val in dict(dimscale=sc, dimtxt=2.2, dimasz=1.5, dimtsz=1.2, dimexe=1.5, dimexo=1.0, dimgap=0.6,
                           dimdle=1.2, dimdec=0, dimtad=1, dimtih=0, dimtoh=0, dimzin=8, dimtxsty="DOM",
                           dimclrd=4, dimclre=4, dimclrt=7).items():
            ds.dxf.set(k, val)
    msp = doc.modelspace()
    frame_info(doc, msp, 0, 52000)
    situacia(doc, msp, 0, 6000)
    zaklady(doc, msp, 40000, 6000)
    plan1(doc, msp, 62000, 6000)
    plan2(doc, msp, 84000, 6000)
    krov(doc, msp, 106000, 6000)
    rez(doc, msp, 30000, -22000)
    elev_long(doc, msp, 55000, -22000, "S")
    elev_long(doc, msp, 75000, -22000, "N")
    elev_gable(doc, msp, 95000, -22000, "E")
    elev_gable(doc, msp, 112000, -22000, "W")
    poznamky(doc, msp, 0, -8000)
    doc.saveas(OUT / f"{NAME}.dxf")
    return doc


# oblasti náhľadov (x1, y1, x2, y2)
PREVIEWS = {
    "situacia": (-4000, 500, 25500, 41500),
    "zaklady": (37000, -1500, 55500, 17000),
    "plan1": (59000, -3000, 77500, 18000),
    "plan2": (81000, -3000, 99500, 18000),
    "krov": (103000, -3500, 121500, 17000),
    "rez": (20000, -28500, 45500, -9500),
    "pohlad_J": (51500, -28500, 69500, -9500),
    "pohlad_S": (71500, -28500, 89500, -9500),
    "pohlad_V": (91000, -28500, 108000, -9500),
    "pohlad_Z": (108000, -28500, 125000, -9500),
    "poznamky": (-1000, -20000, 30000, -7000),
}


def previews(doc):
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from ezdxf.addons.drawing import Frontend, RenderContext
    from ezdxf.addons.drawing.config import Configuration, BackgroundPolicy, ColorPolicy, LineweightPolicy
    from ezdxf.addons.drawing.matplotlib import MatplotlibBackend

    for nm, (x1, y1, x2, y2) in PREVIEWS.items():
        w, h = x2 - x1, y2 - y1
        fig = plt.figure(figsize=(12, 12 * h / w))
        ax = fig.add_axes([0, 0, 1, 1])
        cfg = Configuration(background_policy=BackgroundPolicy.WHITE, color_policy=ColorPolicy.COLOR,
                            lineweight_policy=LineweightPolicy.ABSOLUTE, lineweight_scaling=0.6)
        Frontend(RenderContext(doc), MatplotlibBackend(ax), config=cfg).draw_layout(doc.modelspace())
        ax.set_xlim(x1, x2)
        ax.set_ylim(y1, y2)
        fig.savefig(OUT / f"nahlad_{nm}.png", dpi=110)
        plt.close(fig)


if __name__ == "__main__":
    import sys

    d = build()
    print("DXF zapísaný:", OUT / f"{NAME}.dxf")
    if "--bez-nahladov" not in sys.argv:
        previews(d)
        print("náhľady hotové")
