"""ZTI-02 – Schéma kanalizácie (rozvinutý rez) k pôdorysu ZTI-01.

Štýl podľa vzorového výkresu rodinného domu: potrubie červenou čiarou so sklonom,
tvarovky, označenie stúpačky a tabuľka pod rezom (materiál, DN, dĺžka, spád, výšky osi).
Dĺžky a výšky sa berú z geometrie ZTI-01 (generuj_vykres.py), takže obe listy sedia.

Spustenie:  python zti/schema_kanalizacie.py
Výstup:     ZTI_schema_kanalizacie.lsp (príkaz ZTISCHEMA), .dxf, nahlad_schema.png
"""

from __future__ import annotations

import math

import generuj_vykres as g

g.E.clear()
g.PIPES.clear()

NAME = "ZTI_schema_kanalizacie"
S = g.SCALE  # 1 mm na papieri = 25 mm v modeli
OX, OY = 9500.0, -2600.0  # list ZTI-02 leží v modeli vpravo vedľa listu ZTI-01

L_KS = "ZTI_KANALIZACIA_SCHEMA"
LAYERS = {
    L_KS: (1, 50, "Continuous", "ZTI - schema kanalizacie"),
    g.L_ST: g.LAYERS[g.L_ST],
    g.L_TXT: g.LAYERS[g.L_TXT],
    g.L_RAM: g.LAYERS[g.L_RAM],
}


def P(x, y):
    """papier (mm, od ľavého dolného rohu listu A3) -> model"""
    return (OX + x * S, OY + y * S)


def line(layer, pts, **kw):
    g.pl(layer, [P(*p) for p in pts], **kw)


def box(layer, x1, y1, x2, y2, **kw):
    line(layer, [(x1, y1), (x2, y1), (x2, y2), (x1, y2)], closed=True, **kw)


def txt(pos, h, s, align="L", rot=0.0, layer=g.L_TXT):
    g.text(layer, P(*pos), h * S, s, align=align, rot=rot)


def fill(pts, color, layer=g.L_ST):
    g.hatch(layer, [P(*p) for p in pts], color)


# ------------------------------------------------------------------ údaje z ZTI-01
I = g.I_K
H0 = g.H_V
SP = g.K_SPOL


def dist_to(pt):
    """rozvinutá dĺžka spoločného potrubia od odtoku vane po bod pt (mm)"""
    d = 0.0
    for a, b in zip(SP, SP[1:]):
        if g._on_seg(pt, a, b):
            return d + math.dist(a, pt)
        d += math.dist(a, b)
    raise ValueError(pt)


D_PR = dist_to((2370, 1600))
D_U1 = dist_to((2370, 1000))
D_P1 = dist_to((2450, 1000))  # os priečky 2400..2500
D_P2 = dist_to((2560, 1725))  # os prednej steny šachty 1700..1750
D_K1 = g._dlzka(SP)
L_WC = math.dist((3275, 2010), (2641, 2010))
L_U2 = g._dlzka([(3680, 850), (3680, 2010), (3275, 2010)])
D_SW = math.dist((2641, 2010), (2825, 2010))  # bočná stena šachty 2800..2850

H_WC = 230.0  # os odpadu závesného WC
H_WC_K1 = H_WC - I * L_WC
H_U2_SIF, H_U2_H = 500.0, 280.0  # sifón U2, vodorovná časť v stene
H_U2_J = H_U2_H - I * L_U2
H_PR_ZS, H_U1_SIF = 700.0, 500.0


def h_main(d):
    return H0 - I * d


# ------------------------------------------------------------------ mierky schémy
HX = 45.0 / 1000  # vodorovne: 1 m = 45 mm na papieri (≈ 1:22)
VY = 0.14  # zvisle: 100 mm = 14 mm (výšky prevýšené)
YF = 165.0  # ±0,000 na papieri
XV = 78.0
XK1 = XV + D_K1 * HX
XWC = XK1 + L_WC * HX
XU2 = XWC + L_U2 * HX


def Y(h):
    return YF + h * VY


def X(d):
    return XV + d * HX


# ------------------------------------------------------------------ podlaha, steny
fill([(30, YF - 16), (XU2 + 12, YF - 16), (XU2 + 12, YF), (30, YF)], 253)
box(g.L_ST, 30, YF - 16, XU2 + 12, YF, lw=35)
txt((32, YF + 2), 2.0, "±0,000 = čistá podlaha")
txt((32, YF - 13), 1.6, "stropná doska (exist.)")


def wall(xc, w, label=None):
    x1, x2 = xc - w / 2, xc + w / 2
    fill([(x1, YF), (x2, YF), (x2, YF + 48), (x1, YF + 48)], 253)
    box(g.L_ST, x1, YF, x2, YF + 48, lw=25)
    if label:
        txt((xc, YF + 50), 1.6, label, align="C")


wall(X(D_P1), 100 * HX, "P1 Ø80")
wall(X(D_P2), 50 * HX, "P2 Ø80")
wall(XK1 + D_SW * HX, 50 * HX)
txt(((XV + X(D_P1)) / 2, 268), 2.5, "1.01 KÚPEĽŇA", align="C")
txt(((X(D_P1) + X(D_P2)) / 2, 262), 2.0, "1.02 WC", align="C")
txt(((XWC + XU2) / 2, 268), 2.5, "1.02 WC", align="C")
txt((XK1 + 4, 268), 2.5, "Š1", align="L")

# ------------------------------------------------------------------ stúpačka K1
yk_bot, yk_top = YF - 26, 282.0
line(L_KS, [(XK1, yk_bot), (XK1, yk_top - 6)], lw=70)


def zig(x, y):
    line(L_KS, [(x - 3, y), (x - 1, y + 1.5), (x + 1, y - 1.5), (x + 3, y)], lw=35)


zig(XK1, yk_top - 6)
zig(XK1, yk_bot)
txt((XK1 + 1.5, yk_top - 2), 1.6, "↑ vetranie nad strechu (exist.)")
txt((XK1 + 1.5, yk_bot - 4), 1.6, "↓ zvodové potrubie (exist.)")
txt((XK1 - 2, Y(400)), 2.0, "K1 – DN100 PP-HT (exist.)", rot=90)

# ------------------------------------------------------------------ potrubia
ODB = 3.0  # dĺžka šikmého ramena odbočky 45° na papieri


def mark_h(x, y, h, side="L"):
    """výšková kóta osi: trojuholník na osi + text"""
    line(g.L_TXT, [(x, y), (x - 1.2, y + 2), (x + 1.2, y + 2)], closed=True, lw=18)
    txt((x + (1.6 if side == "R" else -1.6), y + 2.6), 1.5, f"+{h:.0f}", align="L" if side == "R" else "R")


def slope_label(x1, x2, ya, yb, s):
    xm = (x1 + x2) / 2
    ang = math.degrees(math.atan2(yb - ya, x2 - x1))
    ym = (ya + yb) / 2
    txt((xm, ym + 1.8), 1.8, s, align="C", rot=ang)


# spoločné potrubie V + PR + U1 -> K1
y_end = Y(h_main(D_K1))
line(L_KS, [(XV, Y(H0)), (XK1 - ODB, y_end + ODB * 0), (XK1, y_end - ODB)])
# vaňa
box(g.L_ST, XV - 30, Y(170), XV + 2, Y(560), lw=25)
txt((XV - 14, Y(380)), 3.0, "V", align="MC")
line(L_KS, [(XV, Y(170)), (XV, Y(H0))])
txt((XV - 29, Y(170) - 3.5), 1.5, "vaňový sifón DN50")
# práčka – zápachová uzávierka v predstienke
for xd, hs, tag, note in [(D_PR, H_PR_ZS, "PR", "ZS práčky +700"), (D_U1, H_U1_SIF, "U1", "sifón umývadla +500")]:
    x, yj = X(xd), Y(h_main(xd))
    line(L_KS, [(x - ODB, Y(hs)), (x - ODB, yj + ODB), (x, yj)])
    g.circle(L_KS, P(x - ODB, Y(hs) + 1.2), 1.2 * S)
    txt((x - ODB, Y(hs) + 4), 3.0, tag, align="C")
    txt((x - ODB + 1.8, Y(hs) - 2.5), 1.5, note)
    txt((x + 0.8, yj + 2.5), 1.4, "odb. 45°")
# čistiaci kus pri P1 (vo WC)
xc = X(D_P1) + 4
yc = Y(h_main(D_P1 + 4 / HX))
box(L_KS, xc - 1.5, yc - 1.5, xc + 1.5, yc + 1.5, lw=25)
txt((xc, yc - 5), 1.4, "ČK DN50", align="C")
txt(((X(D_P1) + X(D_P2)) / 2, Y(10) - 6.5), 1.4, "v obkladovom boxe 120×150", align="C")

# WC – DN100 do K1
yw, ywk = Y(H_WC), Y(H_WC_K1)
line(L_KS, [(XWC, yw), (XK1 + ODB, ywk), (XK1, ywk - ODB)], lw=70)
box(g.L_ST, XWC - 1, Y(300), XWC + 13, Y(420), lw=25)
line(g.L_ST, [(XWC - 1, Y(160)), (XWC - 1, Y(650))], lw=25)  # predstena
txt((XWC + 6, Y(360)), 3.0, "WC", align="MC")
line(L_KS, [(XWC + 1, Y(300)), (XWC, yw)], lw=70)
txt((XWC + 6, Y(300) - 3), 1.4, "modul v predstene", align="C")
# U2 – DN50 zaústené do odpadu WC
yu, yuj = Y(H_U2_H), Y(H_U2_J)
line(L_KS, [(XU2, Y(H_U2_SIF)), (XU2, yu), (XWC + ODB, yuj), (XWC, yuj - ODB)])
g.circle(L_KS, P(XU2, Y(H_U2_SIF) + 1.2), 1.2 * S)
txt((XU2, Y(H_U2_SIF) + 4), 3.0, "U2", align="C")
txt((XU2 - 1.8, Y(H_U2_SIF) - 2.5), 1.5, "sifón +500", align="R")
txt((XWC + 0.8, yuj + 2.5), 1.4, "odb. 45°")
txt((XK1 + 1.5, ywk - 6), 1.4, "odb. DN100/100 45°")
txt((XK1 - 1.5, y_end - 6), 1.4, "nová odb. DN100/50 45°", align="R")

# popisy úsekov
slope_label(XV, X(D_PR), Y(H0), Y(h_main(D_PR)), "DN50, i = 2 %")
slope_label(X(D_U1), X(D_P2), Y(h_main(D_U1)), Y(h_main(D_P2)), "DN50, i = 2 %")
slope_label(XK1, XWC, ywk, yw, "DN100, i = 2 %")
slope_label(XWC, XU2, yuj, yu, "DN50, i = 2 %")

# výškové kóty osí
for x, h, side in [(XV, H0, "R"), (X(D_PR), h_main(D_PR), "R"), (X(D_U1), h_main(D_U1), "R"),
                   (X(D_P2), h_main(D_P2), "L"), (XK1 - ODB, h_main(D_K1), "L"), (XWC, H_WC, "R"),
                   (XK1 + ODB, H_WC_K1, "R"), (XU2, H_U2_H, "L")]:
    mark_h(x, Y(h), h, side)

# ------------------------------------------------------------------ tabuľka pod rezom
TX0, TT = 25.0, 132.0
RH = [7, 7, 7, 7, 7, 14]
rows = ["ÚSEK", "MATERIÁL", "DN", "DĹŽKA [m]", "SPÁD [%]", "VÝŠKA OSI [mm]"]
nodes = [XV, X(D_PR), X(D_U1), X(D_P2), XK1, XWC, XU2]
segs = [("V – PR", "PP-HT", "50", D_PR), ("PR – U1", "PP-HT", "50", D_U1 - D_PR),
        ("U1 – P2", "PP-HT", "50", D_P2 - D_U1), ("P2–K1", "PP-HT", "50", D_K1 - D_P2),
        ("K1 – WC", "PP-HT", "100", L_WC), ("WC – U2", "PP-HT", "50", L_U2)]
ys = [TT]
for h in RH:
    ys.append(ys[-1] - h)
XR = XU2 + 6
for i, y in enumerate(ys):
    line(g.L_TXT, [(TX0, y), (XR, y)], lw=35 if i in (0, len(ys) - 1) else 18)
for x in [TX0, XV - 4] + nodes + [XR]:
    line(g.L_TXT, [(x, ys[0]), (x, ys[-1])], lw=35 if x in (TX0, XR) else 18)
for r, name in enumerate(rows):
    txt((TX0 + 1.5, (ys[r] + ys[r + 1]) / 2), 1.6, name, align="ML")
for (a, b), (sname, mat, dn, ln) in zip(zip(nodes, nodes[1:]), segs):
    xm = (a + b) / 2
    narrow = b - a < 12
    for r, v in enumerate([sname, mat, dn, f"{ln / 1000:.2f}".replace(".", ","), "2"]):
        txt((xm, (ys[r] + ys[r + 1]) / 2), 1.3 if narrow else 1.6, v, align="MC",
            rot=90 if (narrow and r == 0) else 0)
heights = [H0, h_main(D_PR), h_main(D_U1), h_main(D_P2), None, H_WC, H_U2_H]
yh = (ys[5] + ys[6]) / 2
for x, h in zip(nodes, heights):
    if h is None:
        txt((x - 0.8, yh), 1.5, f"+{h_main(D_K1):.0f}", align="MC", rot=90)
        txt((x + 2.4, yh), 1.5, f"+{H_WC_K1:.0f}", align="MC", rot=90)
    else:
        txt((x + (2.4 if x != XU2 else -0.8), yh), 1.5, f"+{h:.0f}", align="MC", rot=90)

# ------------------------------------------------------------------ legenda + poznámky
LX, LY = 25.0, 76.0
txt((LX, LY), 3.5, "LEGENDA")
line(g.L_TXT, [(LX, LY - 1.5), (LX + 95, LY - 1.5)], lw=35)
leg = [
    (lambda y: line(L_KS, [(LX, y), (LX + 20, y)]), "kanalizačné potrubie PP-HT DN50"),
    (lambda y: line(L_KS, [(LX, y), (LX + 20, y)], lw=70), "kanalizačné potrubie / stúpačka DN100"),
    (lambda y: line(L_KS, [(LX, y), (LX + 14, y), (LX + 17, y + 3)]), "odbočka 45°"),
    (lambda y: (line(L_KS, [(LX, y), (LX + 20, y)]), box(L_KS, LX + 8.5, y - 1.5, LX + 11.5, y + 1.5, lw=25)),
     "čistiaci kus s revíznym otvorom (ČK)"),
    (lambda y: g.circle(L_KS, P(LX + 10, y), 1.2 * S), "zápachová uzávierka / sifón"),
    (lambda y: line(g.L_TXT, [(LX + 10, y - 1), (LX + 8.8, y + 1), (LX + 11.2, y + 1)], closed=True, lw=18),
     "výška osi potrubia od ±0,000 [mm]"),
    (lambda y: (fill([(LX + 8, y - 2), (LX + 12, y - 2), (LX + 12, y + 2), (LX + 8, y + 2)], 253),
                box(g.L_ST, LX + 8, y - 2, LX + 12, y + 2, lw=25)), "stena / prieraz P1, P2"),
]
for i, (draw, desc) in enumerate(leg):
    y = LY - 8 - i * 6.5
    draw(y)
    txt((LX + 24, y), 1.8, desc, align="ML")
notes = [
    "POZNÁMKY",
    "1. Schéma – rozvinutý rez, výšky prevýšené (vodorovne ≈ 1:22,",
    "    zvisle ≈ 1:7). Platia kóty a údaje v tabuľke.",
    "2. Potrubie PP-HT, hrdlové spoje s tesnením, odbočky 45°.",
    "3. Spád pripojovacieho potrubia 2 % (DN50 min. 2 %,",
    "    DN100 min. 1 %). Výšky osi od ±0,000 čistej podlahy.",
    "4. V, PR a U1 – spoločné potrubie DN50 (pozri ZTI-01,",
    "    pozn. 11); U2 zaústené do odpadu WC DN100.",
    "5. Napojenie na exist. K1 novou odbočkou – pred realizáciou",
    "    overiť materiál a dimenziu stúpačky.",
    "6. Pred zakrytím skúška tesnosti kanalizácie.",
]
for i, s in enumerate(notes):
    txt((LX + 102, LY - i * 5.4), 3.5 if i == 0 else 1.7, s)

# ------------------------------------------------------------------ rám a pečiatka
box(g.L_RAM, 0, 0, 420, 297, lw=18)
box(g.L_RAM, 20, 5, 415, 292, lw=50)
TBX, TBY, TBW = 235.0, 5.0, 180.0
box(g.L_RAM, TBX, TBY, TBX + TBW, TBY + 52, lw=50)
for yy in (TBY + 14, TBY + 32, TBY + 42):
    line(g.L_RAM, [(TBX, yy), (TBX + TBW, yy)], lw=35)
line(g.L_RAM, [(TBX + 90, TBY + 42), (TBX + 90, TBY + 52)], lw=18)
line(g.L_RAM, [(TBX + 90, TBY + 32), (TBX + 90, TBY + 42)], lw=18)
for i, (k, v) in enumerate([("STUPEŇ", "—"), ("MIERKA", "schéma"), ("FORMÁT", "A3"), ("DÁTUM", "10/2026"),
                            ("Č. VÝKRESU", "ZTI-02")]):
    x = TBX + i * 36
    if i:
        line(g.L_RAM, [(x, TBY), (x, TBY + 14)], lw=18)
    txt((x + 1.6, TBY + 10.5), 1.4, k)
    txt((x + 18, TBY + 2.8), 2.8, v, align="C")
txt((TBX + 2.4, TBY + 24.5), 5.0, "REKONŠTRUKCIA BYTU – ZTI")
txt((TBX + 2.4, TBY + 17.2), 2.8, "SCHÉMA KANALIZÁCIE – ROZVINUTÝ REZ")
for (x, y, k, v) in [(TBX, TBY + 42, "INVESTOR", "— (doplniť)"), (TBX + 90, TBY + 42, "MIESTO STAVBY", "3-izbový byt — (adresa doplniť)"),
                     (TBX, TBY + 32, "VYPRACOVALA", "—"), (TBX + 90, TBY + 32, "ZODP. PROJEKTANT", "—")]:
    txt((x + 1.6, y + 7), 1.4, k)
    txt((x + 1.6, y + 1.6), 2.0, v)
txt((TBX + TBW - 1.6, TBY + 33.6), 1.4, "PROFESIA: ZTI", align="R")
txt((25, 286), 4.5, "SCHÉMA KANALIZÁCIE – KÚPEĽŇA 1.01 A WC 1.02")
line(g.L_TXT, [(25, 284), (200, 284)], lw=50)

if __name__ == "__main__":
    g.write_lsp(name=NAME, cmd="ZTISCHEMA", pfx="zks", label="ZTI-02", layers=LAYERS)
    doc = g.write_dxf(name=NAME, layers=LAYERS)
    g.write_png(doc, views=[("nahlad_schema.png", None)])
    print(f"K1: +{h_main(D_K1):.0f} (DN50), +{H_WC_K1:.0f} (DN100); P1 d={D_P1:.0f}, P2 d={D_P2:.0f}")
