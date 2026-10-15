"""Generátor výkresu „REKONŠTRUKCIA BYTU – ZTI“ (kúpeľňa + WC).

Celá geometria je definovaná tu, v mm, v mierke modelu 1:1 (výkres sa tlačí v M 1:25).
Z nej vzniknú:
  ZTI_kupelna_WC.lsp  – AutoLISP, príkaz ZTI nakreslí výkres do otvoreného výkresu v AutoCADe
  ZTI_kupelna_WC.dxf  – ten istý výkres ako samostatný súbor
  nahlad.png          – náhľad na kontrolu
  kontrola.txt        – automatická kontrola kolízií, krížení a pripojení

Spustenie:  python zti/generuj_vykres.py   (potrebuje ezdxf a matplotlib len pre DXF/náhľad)
"""

from __future__ import annotations

import math
from pathlib import Path

OUT = Path(__file__).resolve().parent
NAME = "ZTI_kupelna_WC"
SCALE = 25  # mierka výkresu 1:25 -> výška textu v modeli = mm na papieri * 25

# ------------------------------------------------------------------ vrstvy
# meno: (farba ACI, hrúbka čiary v 1/100 mm, typ čiary, popis)
LAYERS = {
    "ST_STAVBA": (7, 50, "Continuous", "Stavebna cast"),
    "ZTI_ZARIADOVACIE_PREDMETY": (8, 25, "Continuous", "Zariadovacie predmety"),
    "ZTI_SV": (3, 35, "Continuous", "ZTI - studena voda"),
    "ZTI_TV": (1, 35, "ZTI_TV", "ZTI - tepla voda"),
    "ZTI_KANALIZACIA": (32, 50, "Continuous", "ZTI - kanalizacia"),
    "KOTY": (4, 18, "Continuous", "Koty"),
    "TEXT": (7, 25, "Continuous", "Texty a popisy"),
    "RAM": (7, 50, "Continuous", "Ram a popisove pole"),
}
L_ST, L_ZP, L_SV, L_TV, L_K, L_KOTY, L_TXT, L_RAM = LAYERS
TV_LTSCALE = 10.0  # čiarkovanie TV: 12/-6 mm * 10 -> 4,8 / 2,4 mm na papieri v M 1:25

E: list[dict] = []  # všetky entity


def pl(layer, pts, closed=False, lw=None, color=None, lts=None):
    """Polyline. pts: (x, y) alebo (x, y, bulge) alebo (x, y, bulge, start_w, end_w)."""
    vs = []
    for p in pts:
        p = tuple(p) + (0.0,) * (5 - len(p))
        vs.append(tuple(float(v) for v in p))
    E.append(dict(t="pl", layer=layer, pts=vs, closed=closed, lw=lw, color=color, lts=lts))


def rect(layer, x1, y1, x2, y2, **kw):
    pl(layer, [(x1, y1), (x2, y1), (x2, y2), (x1, y2)], closed=True, **kw)


def circle(layer, c, r, color=None, lw=None):
    E.append(dict(t="circle", layer=layer, c=c, r=r, color=color, lw=lw))


def arc(layer, c, r, a1, a2):
    E.append(dict(t="arc", layer=layer, c=c, r=r, a1=a1, a2=a2))


def ellipse(layer, c, major, ratio):
    E.append(dict(t="ellipse", layer=layer, c=c, major=major, ratio=ratio))


def donut(layer, c, d=30, color=None):
    r = d / 4  # stredná čiara prstenca, šírka = d/2 -> plný kruh priemeru d
    x, y = c
    pl(layer, [(x - r, y, 1, d / 2, d / 2), (x + r, y, 1, d / 2, d / 2)], closed=True, color=color)


def text(layer, pos, h, s, align="L", rot=0.0, color=None):
    E.append(dict(t="text", layer=layer, pos=pos, h=h, s=s, align=align, rot=rot, color=color))


def hatch(layer, pts, color):
    E.append(dict(t="hatch", layer=layer, pts=pts, color=color))


def dim(p1, p2, base, d="H"):
    E.append(dict(t="dim", layer=L_KOTY, p1=p1, p2=p2, base=base, d=d))


def chain(pts, base, d="H"):
    for a, b in zip(pts, pts[1:]):
        dim(a, b, base, d)


# výška textu v modeli
H_TAG = 2.8 * SCALE  # označenie predmetu
H_LBL = 1.8 * SCALE  # popis potrubia
H_SM = 1.4 * SCALE  # drobné značky

# ===================================================================== GEOMETRIA
# Súradnice: počiatok = ľavý predný vnútorný roh kúpeľne, ±0,000 = čistá podlaha.
# Kúpeľňa 2400 x 2100 (x 0..2400, y 0..2100), WC 1200 x 1600 (x 2500..3700, y 500..2100).
# Zadná stena y 2100..2250 (150), ľavá stena 150, priečky 100, pravá stena WC 150.

walls = [
    (-150, 2100, 3850, 2250),  # zadná stena
    (-150, -100, 0, 2100),  # ľavá stena
    (0, -100, 300, 0),  # predná priečka kúpeľne, vľavo od dverí
    (1000, -100, 2400, 0),  # predná priečka kúpeľne, vpravo od dverí
    (2400, -100, 2500, 2100),  # priečka kúpeľňa / WC
    (2500, 400, 2650, 500),  # predná priečka WC
    (3250, 400, 3700, 500),
    (3700, 400, 3850, 2100),  # pravá stena WC
    (2800, 1700, 2850, 2100),  # šachta – bočná stena
    (2500, 1700, 2800, 1750),  # šachta – predná stena (revízne dvierka)
]
for x1, y1, x2, y2 in walls:
    hatch(L_ST, [(x1, y1), (x2, y1), (x2, y2), (x1, y2)], 253)


def _outline(rects):
    """Obrys zjednotených stien (bez vnútorných švov medzi kusmi)."""
    from shapely.geometry import box
    from shapely.ops import unary_union

    u = unary_union([box(*r) for r in rects])
    for poly in getattr(u, "geoms", [u]):
        for ring in [poly.exterior, *poly.interiors]:
            c = list(ring.coords)[:-1]
            pl(L_ST, [(round(x, 3), round(y, 3)) for x, y in c], closed=True)


_outline(walls)

# inštalačná predstena SDK pre závesné WC
hatch(L_ST, [(2850, 1850), (3700, 1850), (3700, 2100), (2850, 2100)], 254)
rect(L_ST, 2850, 1850, 3700, 2100, lw=25)

# inštalačná predstienka SDK v kúpeľni (h = 1200): za práčkou pri zadnej stene a pozdĺž priečky s WC
PREDSTIENKA = [(1600, 2000), (2300, 2000), (2300, 650), (2400, 650), (2400, 2100), (1600, 2100)]
hatch(L_ST, PREDSTIENKA, 254)
pl(L_ST, PREDSTIENKA, closed=True, lw=25)
# obkladový box vo WC (h = 150) nad podlahou pozdĺž priečky – kryje spoločné odpadové potrubie
BOX_WC = [(2500, 950), (2620, 950), (2620, 1700), (2500, 1700)]
hatch(L_ST, BOX_WC, 254)
pl(L_ST, BOX_WC, closed=True, lw=25)


def prieraz(x1, y1, x2, y2):
    """Prieraz v stene – obdĺžnik s krížom."""
    rect(L_ST, x1, y1, x2, y2, color=1, lw=25)
    pl(L_ST, [(x1, y1), (x2, y2)], color=1)
    pl(L_ST, [(x1, y2), (x2, y1)], color=1)


prieraz(2400, 960, 2500, 1040)  # P1 – priečka kúpeľňa / WC
prieraz(2520, 1700, 2600, 1750)  # P2 – predná stena šachty pod RD

# dvere (otváranie von do chodby)
pl(L_ST, [(300, -100), (300, -800)], lw=35)  # krídlo 700, pánt vľavo
arc(L_ST, (300, -100), 700, 270, 360)
pl(L_ST, [(3250, 400), (3250, -200)], lw=35)  # krídlo 600, pánt vpravo
arc(L_ST, (3250, 400), 600, 180, 270)
# revízne dvierka šachty (strana WC)
pl(L_ST, [(2540, 1680), (2760, 1680)], lw=50)

# ------------------------------------------------------------------ zariaďovacie predmety
ZP = {}
# V – vaňa 1600 x 700 pri zadnej stene, s obkladovou stienkou (odpad vedený pod vaňou)
rect(L_ZP, 0, 1400, 1600, 2100)
b = math.tan(math.radians(90) / 4)
pl(L_ZP, [(160, 1460), (1440, 1460, b), (1540, 1560), (1540, 1940, b), (1440, 2040),
          (160, 2040, b), (60, 1940), (60, 1560, b)], closed=True)
circle(L_ZP, (1300, 1750), 30)  # odtok
ZP["V"] = dict(box=(0, 1400, 1600, 2100), sv=(1525, 2040), tv=(1375, 2010), k=(1300, 1750))
# PR – práčka 600 x 600 pred predstienkou (PV a ZS v predstienke za práčkou)
rect(L_ZP, 1660, 1380, 2260, 1980)
circle(L_ZP, (1960, 1680), 220)
ZP["PR"] = dict(box=(1660, 1380, 2260, 1980), sv=(2300, 1700), k=(2300, 1600))
# U1 – umývadlo 600 zavesené na predstienke
rect(L_ZP, 1850, 700, 2300, 1300)
ellipse(L_ZP, (2060, 1000), (0, 230), 0.65)
ZP["U1"] = dict(box=(1850, 700, 2300, 1300), sv=(2300, 925), tv=(2300, 1075), k=(2300, 1000))
# WC – závesné, os 3275 (450 od šachty, 425 od pravej steny)
pl(L_ZP, [(3095, 1850), (3095, 1490, 1), (3455, 1490), (3455, 1850)], closed=True)
ellipse(L_ZP, (3275, 1530), (0, 150), 0.75)
rect(L_ZP, 3175, 1850, 3375, 1880)  # ovládacie tlačidlo
ZP["WC"] = dict(box=(3095, 1310, 3455, 1850), sv=(3150, 1890), k=(3275, 2010))
# U2 – umývadielko 450 na pravej stene WC
rect(L_ZP, 3450, 625, 3700, 1075)
ellipse(L_ZP, (3555, 850), (0, 180), 0.5)
ZP["U2"] = dict(box=(3450, 625, 3700, 1075), sv=(3640, 850), k=(3680, 850))

# ------------------------------------------------------------------ šachta a stúpačky
K1 = (2590, 2030)  # kanalizačná stúpačka DN100 (D110)
circle(L_K, K1, 55, lw=70)
circle(L_K, K1, 30)
R_SV, R_TV, R_C = (2770, 1775), (2700, 1775), (2640, 1775)
circle(L_SV, R_SV, 16)
circle(L_TV, R_TV, 16)
circle(L_TV, R_C, 12, color=6)


def valve(layer, x, y, vertical=True, s=12):
    """Guľový uzáver – „motýlik“."""
    if vertical:
        pl(layer, [(x - s, y - s), (x + s, y - s), (x - s, y + s), (x + s, y + s)], closed=True)
    else:
        pl(layer, [(x - s, y - s), (x - s, y + s), (x + s, y - s), (x + s, y + s)], closed=True)


def meter(layer, x, y1, y2, w=12):
    rect(layer, x - w, y1, x + w, y2)
    pl(layer, [(x - w, y1), (x + w, y2)])


valve(L_TV, 2700, 1810)
meter(L_TV, 2700, 1828, 1860)
valve(L_SV, 2770, 1815)
meter(L_SV, 2770, 1840, 1880)

# ------------------------------------------------------------------ potrubia
PIPES: list[dict] = []


def pipe(layer, pts, label, lw=None):
    pl(layer, pts, lw=lw, lts=TV_LTSCALE if layer == L_TV else None)
    PIPES.append(dict(layer=layer, pts=pts, label=label))


# SV – studená voda
pipe(L_SV, [(2770, 1775), (2770, 1930), (2350, 1930)], "SV 25x3,5 stúpačka -> kúpeľňa")
pipe(L_SV, [(2350, 1930), (2350, 2040), (1525, 2040)], "SV 20x2,8 -> V")
pipe(L_SV, [(2350, 1930), (2350, 925), (2300, 925)], "SV 20x2,8 -> PR, U1")
pipe(L_SV, [(2350, 1700), (2300, 1700)], "SV 20x2,8 -> PR (PV)")
pipe(L_SV, [(2770, 1930), (3640, 1930), (3640, 850)], "SV 20x2,8 -> WC, U2")
pipe(L_SV, [(3150, 1930), (3150, 1890)], "SV 20x2,8 -> WC modul")
# TV – teplá voda
pipe(L_TV, [(2700, 1775), (2700, 1870), (2320, 1870)], "TV 25x3,5 stúpačka -> kúpeľňa")
pipe(L_TV, [(2320, 1870), (2320, 2010), (1375, 2010)], "TV 20x2,8 -> V")
pipe(L_TV, [(2320, 1870), (2320, 1075), (2300, 1075)], "TV 20x2,8 -> U1")
# K – kanalizácia
# spoločné odpadové potrubie kúpeľne: V (pod vaňou) -> za PR v predstienke -> pozdĺž priečky
# -> prieraz P1 do WC -> vo WC nad podlahou v obkladovom boxe -> prieraz P2 -> K1
K_SPOL = [(1300, 1750), (1300, 2060), (2370, 2060), (2370, 1000), (2560, 1000), (2560, 1984)]
pipe(L_K, K_SPOL, "K DN50 V+PR+U1 -> K1 (spoločné)")


def _dlzka(pts):
    return sum(math.dist(pts[i], pts[i + 1]) for i in range(len(pts) - 1))


# výšky osi spoločného potrubia (od ±0,000) pri spáde 2 %
I_K = 0.02
H_V = 130.0  # os odtoku vane (sifón vane) – overiť podľa zvolenej vane
H_P1 = H_V - I_K * _dlzka(K_SPOL[:5])  # vstup do WC (bod za prierazom P1)
H_K1 = H_V - I_K * _dlzka(K_SPOL)
pipe(L_K, [(2300, 1600), (2370, 1600)], "K DN50 PR (ZS)")
pipe(L_K, [(2300, 1000), (2370, 1000)], "K DN50 U1")
pipe(L_K, [(3680, 850), (3680, 2010), (3275, 2010)], "K DN50 U2")
pipe(L_K, [(3275, 2010), (2641, 2010)], "K DN100 WC -> K1", lw=70)

# vývody vody a zaústenia odpadov
for z in ZP.values():
    for key in ("sv", "tv"):
        if key in z:
            donut(L_SV if key == "sv" else L_TV, z[key], 30)
    if "k" in z and z is not ZP["WC"]:
        circle(L_K, z["k"], 20)


def flow_arrow(x, y, ang, L=110, w=40):
    a = math.radians(ang)
    tip = (x + L / 2 * math.cos(a), y + L / 2 * math.sin(a))
    tail = (x - L / 2 * math.cos(a), y - L / 2 * math.sin(a))
    pl(L_K, [tail + (0, w, 0), tip])


flow_arrow(1950, 2060, 0)  # spoločné potrubie kúpeľne: za práčkou
flow_arrow(2370, 1450, 270)  # pozdĺž priečky k prierazu P1
flow_arrow(2560, 1300, 90)  # vo WC v obkladovom boxe k P2 / K1
flow_arrow(2930, 2010, 180)  # WC -> K1
flow_arrow(3680, 1350, 90)

# ------------------------------------------------------------------ popisy potrubí (odkazové čiary)


def leader(pts, dots=()):
    pl(L_TXT, pts, lw=18)
    for d in dots:
        donut(L_TXT, d, 22)


# kúpeľňa – spoločný popis rozvodov pri zadnej stene a pri priečke
leader([(1630, 2060), (1630, 1340), (2395, 1340)],
       dots=[(1630, 2010), (1630, 2040), (1630, 2060), (2320, 1340), (2350, 1340), (2370, 1340)])
pl(L_TXT, [(1630, 1340), (880, 1340)], lw=18)
for i, s in enumerate(["SV 20×2,8 PPR PN20", "TV 20×2,8 PPR PN20", "K DN50 PP-HT, i = 2 %", "spoločné V + PR + U1"]):
    text(L_TXT, (900, 1260 - i * 80), H_LBL, s)
# prívody zo šachty
# WC – v predstene
leader([(3040, 2010), (3040, 1440), (2680, 1440)], dots=[(3040, 1930), (3040, 2010)])
text(L_TXT, (2680, 1360), H_LBL, "SV 20×2,8")
text(L_TXT, (2680, 1280), H_LBL, "K DN100, i = 2 %")
# prívody zo šachty do kúpeľne
leader([(2450, 1930), (2450, 1190), (2680, 1190)], dots=[(2450, 1930), (2450, 1870)])
text(L_TXT, (2690, 1190), H_LBL, "SV/TV 25×3,5", align="ML")
# spoločné potrubie z kúpeľne vo WC
leader([(2560, 1110), (2680, 1110)], dots=[(2560, 1110)])
text(L_TXT, (2690, 1110), H_LBL, "K DN50 z kúpeľne", align="ML")
text(L_TXT, (2690, 1040), H_SM, "v boxe 120×150 nad podlahou", align="ML")
text(L_TXT, (2380, 880), H_SM, "P1", align="C")
text(L_TXT, (2640, 1560), H_SM, "P2", align="L")
# U2 – zvislý popis pozdĺž steny
text(L_TXT, (3622, 1110), H_SM, "SV 20×2,8", rot=90)
text(L_TXT, (3567, 1110), H_SM, "K DN50, i = 2 %", rot=90)
# šachta a stúpačky
text(L_TXT, (2700, 2055), H_SM, "K1", align="L")
text(L_TXT, (2640, 1625), H_SM, "C", align="C")
text(L_TXT, (2700, 1625), H_SM, "TV", align="C")
text(L_TXT, (2770, 1625), H_SM, "SV", align="C")
text(L_TXT, (2640, 1480), H_LBL, "Š1, RD 300×300")

# označenie zariaďovacích predmetov
for tag, pos in {"V": (800, 1700), "PR": (1870, 1650), "U1": (2060, 960), "WC": (3275, 1765),
                 "U2": (3540, 820)}.items():
    text(L_TXT, pos, H_TAG, tag, align="MC")
text(L_TXT, (2060, 1780), H_SM, "PV", align="C")
text(L_TXT, (2060, 1530), H_SM, "ZS", align="C")
leader([(2090, 1800), (2300, 1700)])
leader([(2090, 1550), (2300, 1600)])

# miestnosti
text(L_TXT, (400, 820), 3.5 * SCALE, "1.01 KÚPEĽŇA")
text(L_TXT, (400, 720), H_LBL, "A = 5,04 m²   sv. v. 2600")
text(L_TXT, (2680, 860), 3.5 * SCALE, "1.02 WC")
text(L_TXT, (2680, 760), H_LBL, "A = 1,92 m²   sv. v. 2600")
text(L_TXT, (1700, -500), 2.5 * SCALE, "CHODBA", align="C")

# ------------------------------------------------------------------ kóty
chain([(-150, 2250), (0, 2250), (2400, 2250), (2500, 2250), (3700, 2250), (3850, 2250)], (0, 2800))
dim((-150, 2250), (3850, 2250), (0, 3050))
chain([(0, 2100), (1600, 2100), (2260, 2100), (2400, 2100)], (0, 2550))
chain([(2500, 2100), (2800, 2100), (3275, 2100), (3700, 2100)], (0, 2550))
chain([(0, 0), (0, 1400), (0, 2100)], (-500, 0), "V")
chain([(-150, -100), (-150, 0), (-150, 2100), (-150, 2250)], (-800, 0), "V")
chain([(3700, 500), (3700, 625), (3700, 850), (3700, 1075), (3700, 1850), (3700, 2100)], (4150, 0), "V")
dim((3850, 400), (3850, 2250), (4400, 0), "V")
chain([(1850, 0), (1850, 700), (1850, 1000), (1850, 1300)], (1750, 0), "V")
chain([(0, 0), (300, 0), (1000, 0), (2400, 0)], (0, 200))
chain([(2500, 500), (2650, 500), (3250, 500)], (0, 580))

# ------------------------------------------------------------------ názov pôdorysu
text(L_TXT, (-150, -1500), 4.5 * SCALE, "PÔDORYS – KÚPEĽŇA 1.01 A WC 1.02")
text(L_TXT, (3850, -1500), 3.5 * SCALE, "M 1:25", align="R")
pl(L_TXT, [(-150, -1560), (3850, -1560)], lw=50)
text(L_TXT, (-150, -1700), H_LBL, "±0,000 = úroveň čistej podlahy. Rozmery v mm.")

# ===================================================================== RÁM A HLAVIČKA (A3, M 1:25)
FX0, FY0 = -1500, -2600
FW, FH = 420 * SCALE, 297 * SCALE
rect(L_RAM, FX0, FY0, FX0 + FW, FY0 + FH, lw=18)  # orezová značka formátu
IX0, IY0, IX1, IY1 = FX0 + 20 * SCALE, FY0 + 5 * SCALE, FX0 + FW - 5 * SCALE, FY0 + FH - 5 * SCALE
rect(L_RAM, IX0, IY0, IX1, IY1, lw=50)

TBW, TBH = 180 * SCALE, 52 * SCALE
TX0, TY0 = IX1 - TBW, IY0
rect(L_RAM, TX0, TY0, IX1, TY0 + TBH, lw=50)
# riadky hlavičky zdola: D 350 (údaje), C 450 (názov), B 250, A 250
yD, yC, yB = TY0 + 350, TY0 + 800, TY0 + 1050
for y in (yD, yC, yB):
    pl(L_RAM, [(TX0, y), (IX1, y)], lw=35)
xm = TX0 + TBW / 2
pl(L_RAM, [(xm, yB), (xm, TY0 + TBH)], lw=18)
pl(L_RAM, [(TX0 + TBW / 2, yC), (TX0 + TBW / 2, yC)], lw=18)
cells = [("STUPEŇ", "—"), ("MIERKA", "1:25"), ("FORMÁT", "A3"), ("DÁTUM", "10/2026"), ("Č. VÝKRESU", "ZTI-01")]
cw = TBW / len(cells)
for i, (k, v) in enumerate(cells):
    x = TX0 + i * cw
    if i:
        pl(L_RAM, [(x, TY0), (x, yD)], lw=18)
    text(L_TXT, (x + 40, yD - 90), H_SM, k)
    text(L_TXT, (x + cw / 2, TY0 + 70), 2.8 * SCALE, v, align="C")
text(L_TXT, (TX0 + 60, yC - 190), 5.0 * SCALE, "REKONŠTRUKCIA BYTU – ZTI")
text(L_TXT, (TX0 + 60, yC - 370), 2.8 * SCALE, "PÔDORYS ROZVODOV VODY A KANALIZÁCIE")
for (x, y0, k, v) in [(TX0, yB, "INVESTOR", "— (doplniť)"),
                      (xm, yB, "MIESTO STAVBY", "3-izbový byt — (adresa doplniť)"),
                      (TX0, yD + 450, "VYPRACOVALA", "—"),
                      (xm, yD + 450, "ZODP. PROJEKTANT", "—")]:
    yy = y0 if y0 == yB else yC
    text(L_TXT, (x + 40, yy + 250 - 75), H_SM, k)
    text(L_TXT, (x + 40, yy + 40), 2.0 * SCALE, v)
text(L_TXT, (IX1 - 40, yC + 40), H_SM, "PROFESIA: ZTI", align="R")

# ===================================================================== LEGENDA ZNAČIEK
LX = TX0 + 150
LY = IY1 - 180
text(L_TXT, (LX, LY), 3.5 * SCALE, "LEGENDA ZNAČIEK")
pl(L_TXT, [(LX, LY - 40), (LX + 2600, LY - 40)], lw=35)
TXX = LX + 750
rows = []


def lrow(desc, draw):
    rows.append((desc, draw))


lrow("STUDENÁ VODA – SV, PPR PN20", lambda y: pl(L_SV, [(LX, y), (LX + 600, y)]))
lrow("TEPLÁ VODA – TV, PPR PN20", lambda y: pl(L_TV, [(LX, y), (LX + 600, y)], lts=TV_LTSCALE))
lrow("KANALIZÁCIA – PRIPOJOVACIE POTRUBIE K, PP-HT", lambda y: pl(L_K, [(LX, y), (LX + 600, y)]))
lrow("K1 – KANALIZAČNÁ STÚPAČKA DN100 (EXIST.)",
     lambda y: (circle(L_K, (LX + 300, y), 55, lw=70), circle(L_K, (LX + 300, y), 30)))
lrow("STÚPAČKY SV / TV / C V ŠACHTE (EXIST.)",
     lambda y: (circle(L_SV, (LX + 150, y), 16), circle(L_TV, (LX + 300, y), 16),
                circle(L_TV, (LX + 450, y), 12, color=6)))
lrow("VÝVOD VODY PRE ZARIAĎOVACÍ PREDMET",
     lambda y: (pl(L_SV, [(LX, y), (LX + 300, y)]), donut(L_SV, (LX + 300, y), 30)))
lrow("ZAÚSTENIE ODPADU ZARIAĎOVACIEHO PREDMETU",
     lambda y: (pl(L_K, [(LX + 320, y), (LX + 600, y)]), circle(L_K, (LX + 300, y), 20)))
lrow("GUĽOVÝ UZÁVER", lambda y: (pl(L_SV, [(LX, y), (LX + 600, y)]), valve(L_SV, LX + 300, y, False)))
lrow("BYTOVÝ VODOMER",
     lambda y: (pl(L_SV, [(LX, y), (LX + 280, y)]), pl(L_SV, [(LX + 320, y), (LX + 600, y)]),
                rect(L_SV, LX + 280, y - 12, LX + 320, y + 12), pl(L_SV, [(LX + 280, y - 12), (LX + 320, y + 12)])))
lrow("SMER SPÁDU KANALIZÁCIE", lambda y: (pl(L_K, [(LX, y), (LX + 600, y)]),
                                          pl(L_K, [(LX + 245, y, 0, 40, 0), (LX + 355, y)])))
lrow("STAVEBNÁ KONŠTRUKCIA (EXIST.)",
     lambda y: (hatch(L_ST, [(LX, y - 50), (LX + 600, y - 50), (LX + 600, y + 50), (LX, y + 50)], 253),
                rect(L_ST, LX, y - 50, LX + 600, y + 50)))
lrow("INŠTALAČNÁ PREDSTENA / PREDSTIENKA SDK, OBKLADOVÝ BOX",
     lambda y: (hatch(L_ST, [(LX, y - 50), (LX + 600, y - 50), (LX + 600, y + 50), (LX, y + 50)], 254),
                rect(L_ST, LX, y - 50, LX + 600, y + 50, lw=25)))
lrow("P1, P2 – PRIERAZ Ø80 PRE POTRUBIE K DN50", lambda y: prieraz(LX + 250, y - 40, LX + 350, y + 40))
lrow("V, PR, U1, WC, U2 – OZNAČENIE ZARIAĎOVACIEHO PREDMETU", lambda y: text(L_TXT, (LX + 300, y), H_TAG * 0.8, "U1", align="MC"))
lrow("PV / ZS – PRÁČKOVÝ VENTIL / ZÁPACHOVÁ UZÁVIERKA PRÁČKY", lambda y: text(L_TXT, (LX + 300, y), H_SM, "PV / ZS", align="MC"))
lrow("Š1 – INŠTALAČNÁ ŠACHTA, RD – REVÍZNE DVIERKA 300×300", lambda y: pl(L_ST, [(LX + 150, y), (LX + 450, y)], lw=50))
for i, (desc, draw) in enumerate(rows):
    y = LY - 220 - i * 165
    draw(y)
    text(L_TXT, (TXX, y), H_LBL, desc, align="ML")
LEG_BOTTOM = LY - 220 - (len(rows) - 1) * 165

# ===================================================================== TECHNICKÁ LEGENDA
ty = LEG_BOTTOM - 260
text(L_TXT, (LX, ty), 3.5 * SCALE, "TECHNICKÁ LEGENDA")
pl(L_TXT, [(LX, ty - 40), (LX + 2600, ty - 40)], lw=35)
cols = [0, 230, 1500, 1950, 2400, 2850, IX1 - 60 - LX]
hdr = ["OZN.", "ZARIAĎOVACÍ PREDMET", "SV", "TV", "K", "VÝŠKY VÝVODOV OD ±0,000"]
tab = [
    ["V", "VAŇA 1600×700", "20×2,8", "20×2,8", "DN50", f"batéria +800, os odtoku +{H_V:.0f}"],
    ["PR", "PRÁČKA 600×600", "20×2,8", "—", "DN50", "PV +1000, ZS +700"],
    ["U1", "UMÝVADLO 600", "20×2,8", "20×2,8", "DN50", "SV/TV +550, K +500"],
    ["WC", "ZÁVESNÉ WC, modul v predstene", "20×2,8", "—", "DN100", "SV v module, K +230"],
    ["U2", "UMÝVADIELKO 450 (len SV)", "20×2,8", "—", "DN50", "SV +550, K +500"],
]
RH = 105
t_top = ty - 120
nrow = len(tab) + 1
for r in range(nrow + 1):
    pl(L_TXT, [(LX, t_top - r * RH), (LX + cols[-1], t_top - r * RH)], lw=35 if r in (0, 1, nrow) else 18)
for c in cols:
    pl(L_TXT, [(LX + c, t_top), (LX + c, t_top - nrow * RH)], lw=18)
for r, row in enumerate([hdr] + tab):
    for c, s in enumerate(row):
        text(L_TXT, (LX + cols[c] + 30, t_top - r * RH - RH / 2), H_SM, s, align="ML")
notes = [
    "1. Vnútorný vodovod podľa STN EN 806 a STN 73 6660, potrubie PPR PN20, spoje polyfúzne. Rozvody v drážkach / v predstene pod obkladom.",
    "2. Prípojky od stúpačiek DN20 = PPR 25×3,5, pripojovacie potrubie k predmetom DN15 = PPR 20×2,8.",
    "3. SV izolovať proti orosovaniu, TV tepelne izolovať (hrúbka izolácie podľa platných predpisov).",
    "4. Vnútorná kanalizácia podľa STN EN 12056 a STN 73 6760, PP-HT, hrdlové spoje s tesnením. Spád DN50 min. 2 %, DN100 min. 1 % (navrhnuté 2 %).",
    "5. Vodovod viesť nad kanalizáciou. V predstienke a pri šachte sa SV/TV križujú s K – dodržať výškové odsadenie.",
    "6. Napojenie na exist. stúpačky SV / TV / C a K1 DN100 v šachte Š1 – pred realizáciou overiť stav, materiál a dimenzie.",
    "7. V šachte guľové uzávery a bytové vodomery SV, TV (overiť so správcom budovy). RD min. 300×300 zo strany WC.",
    "8. Pred zakrytím tlaková skúška vodovodu (STN EN 806-4), preplach a dezinfekcia; skúška tesnosti kanalizácie.",
    "9. Práčka pred predstienkou, PV a ZS v predstienke za práčkou. Výšky vývodov overiť podľa zvolených výrobkov.",
    "10. Umývadielko U2 vo WC – pripojenie len na SV (výtokový ventil / batéria na SV) a K DN50, bez TV (odsúhlasené investorom).",
    "11. V, PR a U1 – SPOLOČNÉ odpadové potrubie K DN50: pod vaňou za obkladovou stienkou, v predstienke SDK (h 1200) za obkladom,",
    f"     prierazom P1 Ø80 v priečke do WC, vo WC nad podlahou v obkladovom boxe 120×150, prierazom P2 Ø80 pod RD do šachty Š1,",
    f"     na K1 novou odbočkou DN100/50 45°. Os: odtok V +{H_V:.0f}, P1 +{H_P1:.0f}, K1 +{H_K1:.0f}. Zaústenia PR a U1 odbočkami 45°,",
    "     pri P1 čistiaci kus s revíznym otvorom v obklade. Predmety majú vlastné zápachové uzávierky; vetranie cez K1.",
]
ny = t_top - nrow * RH - 130
for i, s in enumerate(notes):
    text(L_TXT, (LX, ny - i * 82), 1.6 * SCALE, s)
NOTES_BOTTOM = ny - (len(notes) - 1) * 82

# ===================================================================== KONTROLA


def seg_list(pts):
    return [(pts[i][:2], pts[i + 1][:2]) for i in range(len(pts) - 1)]


def seg_x(a, b, c, d):
    """Priesečník dvoch úsečiek (vnútorný, bez spoločných koncov)."""
    (x1, y1), (x2, y2), (x3, y3), (x4, y4) = a, b, c, d
    den = (x1 - x2) * (y3 - y4) - (y1 - y2) * (x3 - x4)
    if abs(den) < 1e-9:
        return None
    t = ((x1 - x3) * (y3 - y4) - (y1 - y3) * (x3 - x4)) / den
    u = -((x1 - x2) * (y1 - y3) - (y1 - y2) * (x1 - x3)) / den
    if 1e-6 < t < 1 - 1e-6 and 1e-6 < u < 1 - 1e-6:
        return (x1 + t * (x2 - x1), y1 + t * (y2 - y1))
    return None


def _on_seg(p, a, b, tol=1.0):
    ln = math.dist(a, b)
    return abs(math.dist(a, p) + math.dist(p, b) - ln) < tol


def report():
    out = ["AUTOMATICKÁ KONTROLA VÝKRESU ZTI-01", "=" * 40, ""]
    out.append("1. Kríženia potrubí rôznych médií (v pôdoryse):")
    n = 0
    for i, p in enumerate(PIPES):
        for q in PIPES[i + 1:]:
            if p["layer"] == q["layer"]:
                continue
            for a, b in seg_list(p["pts"]):
                for c, d in seg_list(q["pts"]):
                    x = seg_x(a, b, c, d)
                    if x:
                        n += 1
                        out.append(f"   - {p['label']}  ×  {q['label']}  @ ({x[0]:.0f}, {x[1]:.0f})")
    out.append(f"   spolu: {n}")
    out.append("")
    out.append("2. Vzdialenosti súbežných potrubí (min. osová vzdialenosť):")
    mins = []
    for i, p in enumerate(PIPES):
        for q in PIPES[i + 1:]:
            if p["layer"] == q["layer"]:
                continue
            for a, b in seg_list(p["pts"]):
                for c, d in seg_list(q["pts"]):
                    if a[0] == b[0] == c[0] == d[0] or a[1] == b[1] == c[1] == d[1]:
                        continue
                    if a[0] == b[0] and c[0] == d[0]:
                        lo, hi = max(min(a[1], b[1]), min(c[1], d[1])), min(max(a[1], b[1]), max(c[1], d[1]))
                        if hi - lo > 1:
                            mins.append((abs(a[0] - c[0]), p["label"], q["label"]))
                    if a[1] == b[1] and c[1] == d[1]:
                        lo, hi = max(min(a[0], b[0]), min(c[0], d[0])), min(max(a[0], b[0]), max(c[0], d[0]))
                        if hi - lo > 1:
                            mins.append((abs(a[1] - c[1]), p["label"], q["label"]))
    for dist, a, b in sorted(mins)[:6]:
        out.append(f"   - {dist:.0f} mm: {a} / {b}")
    out.append("")
    out.append("3. Pripojenia zariaďovacích predmetov (požiadavka zadania):")
    need = {"V": ("sv", "tv", "k"), "PR": ("sv", "k"), "U1": ("sv", "tv", "k"), "WC": ("sv", "k"), "U2": ("sv", "k")}
    for tag, keys in need.items():
        z = ZP[tag]
        ok = []
        for k in keys:
            lay = {"sv": L_SV, "tv": L_TV, "k": L_K}[k]
            hit = any(_on_seg(z[k], a, b) for p in PIPES if p["layer"] == lay for a, b in seg_list(p["pts"]))
            ok.append(f"{k.upper()} {'OK' if hit else 'CHÝBA'}")
        out.append(f"   - {tag}: " + ", ".join(ok))
    out.append("")
    out.append("4. Potrubia prechádzajúce pôdorysom zariaďovacích predmetov (vedené v stene/za predmetom):")
    for p in PIPES:
        for tag, z in ZP.items():
            x1, y1, x2, y2 = z["box"]
            for a, b in seg_list(p["pts"]):
                mx, my = (a[0] + b[0]) / 2, (a[1] + b[1]) / 2
                inside = x1 < mx < x2 and y1 < my < y2
                if inside and math.dist(a, b) > 60:
                    out.append(f"   - {p['label']} za/pod {tag}")
                    break
    out.append("")
    out.append("5. Dĺžky a spády kanalizácie (i = 2 %):")
    for p in PIPES:
        if p["layer"] != L_K:
            continue
        ln = sum(math.dist(a, b) for a, b in seg_list(p["pts"]))
        out.append(f"   - {p['label']}: L = {ln / 1000:.2f} m, prevýšenie pri 2 % = {ln * 0.02:.0f} mm")
    out.append("")
    out.append("5a. Výšky osi spoločného potrubia K DN50 (V+PR+U1), i = 2 %:")
    out.append(f"   - odtok V +{H_V:.0f} mm, za P1 vo WC +{H_P1:.0f} mm, pri K1 +{H_K1:.0f} mm")
    out.append(f"   - vrch rúry vo WC max +{H_P1 + 25:.0f} mm -> box h = 150 mm kryje potrubie aj s obkladom")
    out.append(f"   - spodok rúry pri K1 +{H_K1 - 25:.0f} mm (nad podlahou: {'OK' if H_K1 - 25 > 0 else 'NIE'})")
    out.append("")
    out.append("6. Prekrytia textov (orientačne):")
    boxes = []
    for e in E:
        if e["t"] != "text" or e["rot"]:
            continue
        w = 0.62 * e["h"] * len(e["s"])
        x, y = e["pos"]
        if e["align"] in ("C", "MC"):
            x -= w / 2
        elif e["align"] == "R":
            x -= w
        if e["align"] in ("MC", "ML"):
            y -= e["h"] / 2
        boxes.append((x, y, x + w, y + e["h"], e["s"]))
    over = 0
    for i, a in enumerate(boxes):
        for b2 in boxes[i + 1:]:
            if a[0] < b2[2] and b2[0] < a[2] and a[1] < b2[3] and b2[1] < a[3]:
                over += 1
                out.append(f"   - „{a[4]}“ × „{b2[4]}“")
    if not over:
        out.append("   žiadne")
    out.append("")
    out.append(f"Spodok legendy y={LEG_BOTTOM:.0f}, spodok poznámok y={NOTES_BOTTOM:.0f}, vrch hlavičky y={TY0 + TBH:.0f}")
    return "\n".join(out)


# ===================================================================== AutoLISP


def lsp_str(s: str) -> str:
    r = []
    for ch in s:
        if ch == "\\":
            r.append("\\\\")
        elif ch == '"':
            r.append('\\"')
        elif ord(ch) > 126:
            r.append("\\\\U+%04X" % ord(ch))
        else:
            r.append(ch)
    return '"' + "".join(r) + '"'


def f(v):
    return f"{v:.3f}".rstrip("0").rstrip(".") if isinstance(v, float) else str(v)


def props(e):
    s = ""
    if e.get("color") is not None:
        s += f" (cons 62 {e['color']})"
    if e.get("lw") is not None:
        s += f" (cons 370 {e['lw']})"
    if e.get("lts"):
        s += f" (cons 48 (/ {e['lts']} (getvar \"LTSCALE\")))"
    return s


ALIGN = {"L": (0, 0), "C": (1, 0), "R": (2, 0), "ML": (0, 2), "MC": (1, 2), "MR": (2, 2)}


def lsp_entity(e):
    t = e["t"]
    lay = f'"{e["layer"]}"'
    if t == "pl":
        vs = " ".join(f"'({f(x)} {f(y)} {f(bu)} {f(sw)} {f(ew)})" for x, y, bu, sw, ew in e["pts"])
        return f'(zti:pl {lay} (list {vs}) {1 if e["closed"] else 0} (list{props(e)}))'
    if t == "circle":
        return f'(zti:em (list \'(0 . "CIRCLE") (cons 8 {lay}){props(e)} (cons 10 (zti:p {f(e["c"][0])} {f(e["c"][1])})) (cons 40 {f(float(e["r"]))})))'
    if t == "arc":
        return (f'(zti:em (list \'(0 . "ARC") (cons 8 {lay}) (cons 10 (zti:p {f(e["c"][0])} {f(e["c"][1])})) '
                f'(cons 40 {f(float(e["r"]))}) (cons 50 {math.radians(e["a1"]):.6f}) (cons 51 {math.radians(e["a2"]):.6f})))')
    if t == "ellipse":
        mx, my = e["major"]
        return (f'(zti:em (list \'(0 . "ELLIPSE") \'(100 . "AcDbEntity") (cons 8 {lay}) \'(100 . "AcDbEllipse") '
                f'(cons 10 (zti:p {f(e["c"][0])} {f(e["c"][1])})) \'(11 {f(float(mx))} {f(float(my))} 0.0) \'(210 0.0 0.0 1.0) '
                f'(cons 40 {e["ratio"]}) \'(41 . 0.0) (cons 42 (* 2 pi))))')
    if t == "text":
        hj, vj = ALIGN[e["align"]]
        x, y = e["pos"]
        return (f'(zti:tx {lay} {f(float(x))} {f(float(y))} {f(float(e["h"]))} {lsp_str(e["s"])} {hj} {vj} '
                f'{math.radians(e["rot"]):.6f})')
    if t == "hatch":
        vs = " ".join(f"'({f(float(x))} {f(float(y))})" for x, y in e["pts"])
        return f'(zti:hatch {lay} (list {vs}) {e["color"]})'
    if t == "dim":
        (x1, y1), (x2, y2), (bx, by) = e["p1"], e["p2"], e["base"]
        bx2 = (x1 + x2) / 2 if e["d"] == "H" else bx
        by2 = by if e["d"] == "H" else (y1 + y2) / 2
        return (f'(zti:dim {f(float(x1))} {f(float(y1))} {f(float(x2))} {f(float(y2))} '
                f'{f(float(bx2))} {f(float(by2))} "{"_H" if e["d"] == "H" else "_V"}")')
    raise ValueError(t)


LSP_HEAD = r''';;; ===========================================================================
;;; REKONSTRUKCIA BYTU - ZTI  |  PODORYS ROZVODOV VODY A KANALIZACIE  |  ZTI-01
;;; Vygenerovane skriptom zti/generuj_vykres.py - needitovat rucne.
;;;
;;; Pouzitie v AutoCADe:
;;;   1. APPLOAD -> nacitat tento subor (alebo pretiahnut do okna AutoCADu)
;;;   2. prikaz ZTI -> zadat bod vlozenia (Enter = 0,0)
;;;   Vysledok sa da vratit jednym Ctrl+Z (UNDO skupina). Vykres sa neuklada.
;;;   Z MCP servera / run_lisp:  (zti:kresli 0.0 0.0)
;;;
;;; Jednotky: mm (INSUNITS = 4). Tlac v M 1:25 na A3.
;;; ===========================================================================

(defun zti:p (x y) (list (+ x zti:ox) (+ y zti:oy) 0.0))
(defun zti:p2 (x y) (list (+ x zti:ox) (+ y zti:oy)))
(defun zti:em (lst) (if (not (entmake lst)) (setq zti:err (1+ zti:err))))

(defun zti:pl (lay vs cl pr)
  (zti:em
    (append
      (list '(0 . "LWPOLYLINE") '(100 . "AcDbEntity") (cons 8 lay))
      pr
      (list '(100 . "AcDbPolyline") (cons 90 (length vs)) (cons 70 cl))
      (apply 'append
        (mapcar '(lambda (v)
                   (list (cons 10 (zti:p2 (car v) (cadr v)))
                         (cons 40 (nth 3 v)) (cons 41 (nth 4 v)) (cons 42 (nth 2 v))))
                vs)))))

(defun zti:tx (lay x y h s hj vj rot / p)
  (setq p (zti:p x y))
  (zti:em
    (list '(0 . "TEXT") '(100 . "AcDbEntity") (cons 8 lay) '(100 . "AcDbText")
          (cons 10 p) (cons 40 h) (cons 1 s) (cons 50 rot) (cons 7 "ZTI")
          (cons 72 hj) (cons 11 p) '(100 . "AcDbText") (cons 73 vj))))

(defun zti:hatch (lay pts col / n edges e b)
  (setq n (length pts) edges '())
  (setq e
    (entmake
      (append
        (list '(0 . "HATCH") '(100 . "AcDbEntity") (cons 8 lay) (cons 62 col)
              '(100 . "AcDbHatch") '(10 0.0 0.0 0.0) '(210 0.0 0.0 1.0)
              '(2 . "SOLID") '(70 . 1) '(71 . 0) '(91 . 1) '(92 . 1) (cons 93 n))
        (apply 'append
          (mapcar '(lambda (a b)
                     (list '(72 . 1) (cons 10 (zti:p2 (car a) (cadr a))) (cons 11 (zti:p2 (car b) (cadr b)))))
                  pts (append (cdr pts) (list (car pts)))))
        (list '(97 . 0) '(75 . 0) '(76 . 1) '(98 . 1) (cons 10 (zti:p2 (caar pts) (cadar pts)))))))
  ;; nahradne riesenie, ak entmake HATCH zlyha: hranica + -HATCH
  (if (not e)
    (progn
      (zti:pl lay (mapcar '(lambda (p) (list (car p) (cadr p) 0.0 0.0 0.0)) pts) 1 nil)
      (setq b (entlast))
      (setvar "HPNAME" "SOLID")
      (command "_.-HATCH" "_S" b "" "")
      (if (not (eq (entlast) b))
        (progn (command "_.CHPROP" (entlast) "" "_LA" lay "_C" (itoa col) "")
               (entdel b) (setq e (entlast)))
        (setq zti:err (1+ zti:err)))))
  e)

(defun zti:dim (x1 y1 x2 y2 bx by dir)
  (command "_.DIMLINEAR" "_non" (zti:p x1 y1) "_non" (zti:p x2 y2) dir "_non" (zti:p bx by)))

(defun zti:layer (name col lw lt desc)
  (if (not (tblsearch "LAYER" name))
    (command "_.-LAYER" "_N" name ""))
  (command "_.-LAYER" "_C" (itoa col) name "_LT" lt name "_LW" lw name "")
  (if (and (tblsearch "LAYER" name) (vlax-get-acad-object))
    (vl-catch-all-apply
      '(lambda ()
         (vla-put-Description
           (vla-item (vla-get-Layers (vla-get-ActiveDocument (vlax-get-acad-object))) name)
           desc)))))

(defun zti:setup ()
  ;; textovy styl
  (if (not (tblsearch "STYLE" "ZTI"))
    (entmake '((0 . "STYLE") (100 . "AcDbSymbolTableRecord") (100 . "AcDbTextStyleTableRecord")
               (2 . "ZTI") (70 . 0) (40 . 0.0) (41 . 1.0) (50 . 0.0) (71 . 0) (42 . 2.5)
               (3 . "arial.ttf") (4 . ""))))
  ;; typ ciary pre TV
  (if (not (tblsearch "LTYPE" "ZTI_TV"))
    (entmake '((0 . "LTYPE") (100 . "AcDbSymbolTableRecord") (100 . "AcDbLinetypeTableRecord")
               (2 . "ZTI_TV") (70 . 0) (3 . "TV __ __ __") (72 . 65) (73 . 2) (40 . 18.0)
               (49 . 12.0) (74 . 0) (49 . -6.0) (74 . 0))))
'''

LSP_DIMSTYLE = r'''
  ;; koty - styl ZTI_25 (M 1:25, sikme znacky)
  (foreach v '(("DIMSCALE" 25.0) ("DIMTXT" 1.8) ("DIMASZ" 1.5) ("DIMTSZ" 1.2) ("DIMEXE" 1.5)
               ("DIMEXO" 1.0) ("DIMGAP" 0.6) ("DIMDLE" 1.2) ("DIMDEC" 0) ("DIMTAD" 1)
               ("DIMTIH" 0) ("DIMTOH" 0) ("DIMLUNIT" 2) ("DIMZIN" 8) ("DIMATFIT" 3) ("DIMTMOVE" 0))
    (setvar (car v) (cadr v)))
  (setvar "DIMTXSTY" "ZTI")
  (if (tblsearch "DIMSTYLE" "ZTI_25")
    (command "_.-DIMSTYLE" "_S" "ZTI_25" "_Y")
    (command "_.-DIMSTYLE" "_S" "ZTI_25"))
)
'''


def write_lsp():
    lines = [LSP_HEAD]
    for name, (col, lw, lt, desc) in LAYERS.items():
        lines.append(f'  (zti:layer "{name}" {col} "{lw / 100:.2f}" "{lt}" "{desc}")')
    lines.append(LSP_DIMSTYLE)
    non_dims = [e for e in E if e["t"] != "dim"]
    dims = [e for e in E if e["t"] == "dim"]
    parts = [non_dims[i:i + 150] for i in range(0, len(non_dims), 150)]
    for i, part in enumerate(parts):
        lines.append(f"(defun zti:cast{i} ()")
        lines += ["  " + lsp_entity(e) for e in part]
        lines.append(")")
    lines.append("(defun zti:koty ()")
    lines.append('  (setvar "CLAYER" "KOTY")')
    lines += ["  " + lsp_entity(e) for e in dims]
    lines.append(")")
    casts = " ".join(f"(zti:cast{i})" for i in range(len(parts)))
    lines.append(rf'''
(defun zti:kresli (ox oy / old)
  (vl-load-com)
  (setq zti:ox ox zti:oy oy zti:err 0)
  (setq old (mapcar (quote getvar) (quote ("CMDECHO" "OSMODE" "CLAYER" "HPNAME" "ORTHOMODE"))))
  (setvar "CMDECHO" 0)
  (command "_.UNDO" "_BE")
  (command "_.UCS" "_W")
  (setvar "OSMODE" 0)
  (setvar "ORTHOMODE" 0)
  (zti:setup)
  {casts}
  (zti:koty)
  (setvar "CLAYER" (nth 2 old))
  (setvar "HPNAME" (nth 3 old))
  (command "_.UCS" "_P")
  (command "_.UNDO" "_E")
  (setvar "OSMODE" (nth 1 old))
  (setvar "ORTHOMODE" (nth 4 old))
  (setvar "CMDECHO" (nth 0 old))
  (command "_.ZOOM" "_E")
  (princ (strcat "\nZTI-01 nakreslene. Neuspesnych entmake: " (itoa zti:err)))
  zti:err)

(defun c:ZTI (/ u p)
  (setq u (getvar "INSUNITS"))
  (if (and (/= u 4)
           (/= "Ano" (progn (initget "Ano Nie")
                            (getkword (strcat "\nINSUNITS = " (itoa u)
                                              " (nie mm). Skript kresli v mm. Pokracovat? [Ano/Nie] <Nie>: ")))))
    (progn (princ "\nPreruseny - nastav INSUNITS na 4 (mm).") (exit)))
  (setq p (getpoint "\nBod vlozenia (lavy predny vnutorny roh kupelne) <0,0>: "))
  (if (not p) (setq p '(0.0 0.0 0.0)))
  (zti:kresli (car p) (cadr p))
  (princ))

(princ "\nZTI-01 nacitane. Spusti prikazom ZTI.")
(princ)
''')
    (OUT / f"{NAME}.lsp").write_text("\n".join(lines), encoding="ascii")


# ===================================================================== DXF + náhľad


def write_dxf():
    import ezdxf

    doc = ezdxf.new("R2018", setup=True)
    doc.units = ezdxf.units.MM
    doc.header["$INSUNITS"] = 4
    doc.header["$LTSCALE"] = 1.0
    doc.styles.add("ZTI", font="arial.ttf")
    doc.linetypes.add("ZTI_TV", pattern=[18.0, 12.0, -6.0], description="TV __ __ __")
    for name, (col, lw, lt, desc) in LAYERS.items():
        doc.layers.add(name, color=col, lineweight=lw, linetype=lt).description = desc
    ds = doc.dimstyles.new("ZTI_25")
    for k, v in dict(dimscale=25, dimtxt=1.8, dimasz=1.5, dimtsz=1.2, dimexe=1.5, dimexo=1.0, dimgap=0.6,
                     dimdle=1.2, dimdec=0, dimtad=1, dimtih=0, dimtoh=0, dimlunit=2, dimzin=8,
                     dimtxsty="ZTI").items():
        ds.dxf.set(k, v)
    msp = doc.modelspace()
    amap = {"L": "LEFT", "C": "CENTER", "R": "RIGHT", "ML": "MIDDLE_LEFT", "MC": "MIDDLE_CENTER", "MR": "MIDDLE_RIGHT"}
    from ezdxf.enums import TextEntityAlignment as TA

    for e in E:
        at = {"layer": e["layer"]}
        if e.get("color") is not None:
            at["color"] = e["color"]
        if e.get("lw") is not None:
            at["lineweight"] = e["lw"]
        if e.get("lts"):
            at["ltscale"] = e["lts"]
        t = e["t"]
        if t == "pl":
            msp.add_lwpolyline([(x, y, sw, ew, bu) for x, y, bu, sw, ew in e["pts"]], format="xyseb",
                               close=e["closed"], dxfattribs=at)
        elif t == "circle":
            msp.add_circle(e["c"], e["r"], dxfattribs=at)
        elif t == "arc":
            msp.add_arc(e["c"], e["r"], e["a1"], e["a2"], dxfattribs=at)
        elif t == "ellipse":
            msp.add_ellipse(e["c"], major_axis=e["major"], ratio=e["ratio"], dxfattribs=at)
        elif t == "text":
            at.update(style="ZTI", height=e["h"], rotation=e["rot"])
            msp.add_text(e["s"], dxfattribs=at).set_placement(e["pos"], align=TA[amap[e["align"]]])
        elif t == "hatch":
            h = msp.add_hatch(color=e["color"], dxfattribs={"layer": e["layer"]})
            h.paths.add_polyline_path(e["pts"], is_closed=True)
        elif t == "dim":
            ang = 0 if e["d"] == "H" else 90
            msp.add_linear_dim(base=e["base"], p1=e["p1"], p2=e["p2"], angle=ang, dimstyle="ZTI_25",
                               dxfattribs={"layer": L_KOTY}).render()
    doc.saveas(OUT / f"{NAME}.dxf")
    return doc


def write_png(doc):
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from ezdxf.addons.drawing import Frontend, RenderContext
    from ezdxf.addons.drawing.config import Configuration, BackgroundPolicy, ColorPolicy, LineweightPolicy
    from ezdxf.addons.drawing.matplotlib import MatplotlibBackend

    for fname, view in [("nahlad.png", None), ("nahlad_detail.png", (-900, -900, 4500, 3200))]:
        fig = plt.figure(figsize=(16.54, 11.69) if view is None else (16, 11))
        ax = fig.add_axes([0, 0, 1, 1])
        cfg = Configuration(background_policy=BackgroundPolicy.WHITE, color_policy=ColorPolicy.COLOR,
                            lineweight_policy=LineweightPolicy.ABSOLUTE, lineweight_scaling=0.8)
        Frontend(RenderContext(doc), MatplotlibBackend(ax), config=cfg).draw_layout(doc.modelspace())
        if view:
            ax.set_xlim(view[0], view[2])
            ax.set_ylim(view[1], view[3])
        fig.savefig(OUT / fname, dpi=150 if view is None else 170)
        plt.close(fig)


if __name__ == "__main__":
    write_lsp()
    rep = report()
    (OUT / "kontrola.txt").write_text(rep, encoding="utf-8")
    print(rep)
    try:
        d = write_dxf()
        write_png(d)
    except ImportError as ex:
        print("DXF/náhľad preskočený:", ex)
