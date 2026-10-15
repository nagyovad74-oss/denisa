"""Generátor kuchynského ostrovčeka so stoličkami (príkaz OSTROVCEK v AutoCADe).

Geometria je v lokálnych súradniciach ostrovčeka (mm, stred dosky = 0,0, strana sedenia = -Y).
Z nej vzniknú:
  kuchyna_ostrovcek.lsp – AutoLISP: odstráni vybraný stôl, nakreslí ostrovček na zvolené miesto a natočenie
  kuchyna_ostrovcek.png – náhľad

Spustenie:  python zti/kuchyna_ostrovcek.py   (náhľad potrebuje matplotlib)
"""

from __future__ import annotations

from pathlib import Path

OUT = Path(__file__).resolve().parent
NAME = "kuchyna_ostrovcek"

# ------------------------------------------------------------------ parametre
DL = 1800  # dĺžka ostrovčeka
SKRINKY = 600  # hĺbka spodných skriniek
PRESAH = 300  # presah dosky na strane sedenia (miesto na kolená)
HL = SKRINKY + PRESAH  # hĺbka pracovnej dosky
STOLICKY = 3
D_STOL = 400  # priemer sedáku barovej stoličky
OSOVO = 600  # osová vzdialenosť stoličiek
Y_STOL = -HL / 2 - 130  # os stoličiek – čiastočne zasunuté pod presahom
VOLNO = 1000  # min. voľný priestor okolo ostrovčeka (len kontrolná čiara)

LAYERS = {
    "INT_NABYTOK": (8, 25, "Nabytok - kuchynsky ostrovcek"),
    "INT_NABYTOK_SKRYTE": (9, 13, "Nabytok - skryte hrany, volny priestor"),
    "TEXT": (7, 25, "Texty a popisy"),
}

E: list[dict] = []


def rect(layer, x1, y1, x2, y2):
    E.append(dict(t="pl", layer=layer, pts=[(x1, y1), (x2, y1), (x2, y2), (x1, y2)], closed=True))


def line(layer, a, b):
    E.append(dict(t="pl", layer=layer, pts=[a, b], closed=False))


def circle(layer, c, r):
    E.append(dict(t="circle", layer=layer, c=c, r=r))


def text(layer, pos, h, s):
    E.append(dict(t="text", layer=layer, pos=pos, h=h, s=s))


x0, x1 = -DL / 2, DL / 2
y_top, y_bot = HL / 2, -HL / 2  # doska
y_sk = y_top - SKRINKY  # čelo skriniek na strane sedenia

rect("INT_NABYTOK", x0, y_bot, x1, y_top)  # pracovná doska
line("INT_NABYTOK_SKRYTE", (x0, y_sk), (x1, y_sk))  # hrana skriniek pod doskou
for i in range(STOLICKY):
    cx = (i - (STOLICKY - 1) / 2) * OSOVO
    circle("INT_NABYTOK", (cx, Y_STOL), D_STOL / 2)
    circle("INT_NABYTOK", (cx, Y_STOL), D_STOL / 2 - 60)
rect("INT_NABYTOK_SKRYTE", x0 - VOLNO, y_bot - VOLNO, x1 + VOLNO, y_top + VOLNO)
text("TEXT", (x0 + 60, y_sk + 330), 90, f"KUCHYNSKÝ OSTROVČEK {DL}×{HL}")
text("TEXT", (x0 + 60, y_sk + 200), 60, f"skrinky {SKRINKY}, presah dosky {PRESAH}, h = 900")
text("TEXT", (x0 + 60, y_sk + 90), 60, f"{STOLICKY}× barová stolička Ø{D_STOL}")
text("TEXT", (x0 - VOLNO + 40, y_top + VOLNO - 100), 60, f"min. voľný priestor {VOLNO}")


# ===================================================================== AutoLISP


def lsp_str(s: str) -> str:
    return '"' + "".join("\\\\U+%04X" % ord(c) if ord(c) > 126 else c for c in s.replace('"', '\\"')) + '"'


def f(v) -> str:
    s = f"{float(v):.3f}".rstrip("0")  # vždy s desatinnou bodkou – entmake chce reálne čísla
    return s + "0" if s.endswith(".") else s


def lsp_entity(e) -> str:
    lay = f'"{e["layer"]}"'
    if e["t"] == "pl":
        vs = " ".join(f"'({f(x)} {f(y)})" for x, y in e["pts"])
        return f'(ostr:pl {lay} (list {vs}) {1 if e["closed"] else 0})'
    if e["t"] == "circle":
        return f'(ostr:em (list \'(0 . "CIRCLE") (cons 8 {lay}) (cons 10 (ostr:p {f(e["c"][0])} {f(e["c"][1])})) (cons 40 {f(e["r"])})))'
    if e["t"] == "text":
        x, y = e["pos"]
        return (f'(ostr:em (list \'(0 . "TEXT") (cons 8 {lay}) (cons 10 (ostr:p {f(x)} {f(y)})) '
                f'(cons 40 {f(e["h"])}) (cons 1 {lsp_str(e["s"])}) (cons 50 ostr:a)))')
    raise ValueError(e["t"])


LSP = r''';;; ===========================================================================
;;; KUCHYNSKY OSTROVCEK SO STOLICKAMI
;;; Vygenerovane skriptom zti/kuchyna_ostrovcek.py - needitovat rucne.
;;;
;;; Pouzitie v AutoCADe (vykres v mm):
;;;   1. APPLOAD -> nacitat tento subor
;;;   2. prikaz OSTROVCEK
;;;      - vyber stol (a stare stolicky) na odstranenie, Enter
;;;      - klikni stred ostrovceka
;;;      - zadaj natocenie dlhsej strany (stolicky su na strane "vpravo" od smeru natocenia)
;;;   Vsetko sa vrati jednym Ctrl+Z. Vykres sa neuklada.
;;;   Z MCP servera / run_lisp:  (ostr:kresli x y uhol_v_stupnoch)
;;; ===========================================================================

(defun ostr:p (x y)
  (list (+ ostr:ox (- (* x (cos ostr:a)) (* y (sin ostr:a))))
        (+ ostr:oy (+ (* x (sin ostr:a)) (* y (cos ostr:a))))
        0.0))
(defun ostr:em (lst) (if (not (entmake lst)) (setq ostr:err (1+ ostr:err))))
(defun ostr:pl (lay pts cl)
  (ostr:em
    (append
      (list '(0 . "LWPOLYLINE") '(100 . "AcDbEntity") (cons 8 lay)
            '(100 . "AcDbPolyline") (cons 90 (length pts)) (cons 70 cl))
      (mapcar '(lambda (v) (cons 10 (reverse (cdr (reverse (ostr:p (car v) (cadr v))))))) pts))))
(defun ostr:layer (name col lw desc)
  (if (not (tblsearch "LAYER" name)) (command "_.-LAYER" "_N" name ""))
  (command "_.-LAYER" "_C" (itoa col) name "_LW" lw name ""))
'''


def write_lsp():
    lines = [LSP, "(defun ostr:geometria ()"]
    lines += ["  " + lsp_entity(e) for e in E]
    lines.append(")")
    lays = "\n".join(f'  (ostr:layer "{n}" {c} "{lw / 100:.2f}" "{d}")' for n, (c, lw, d) in LAYERS.items())
    lines.append(rf'''
(defun ostr:kresli (x y uhol / old)
  (setq ostr:ox x ostr:oy y ostr:a (* pi (/ uhol 180.0)) ostr:err 0)
  (setq old (mapcar (quote getvar) (quote ("CMDECHO" "CLAYER"))))
  (setvar "CMDECHO" 0)
  (command "_.UNDO" "_BE")
{lays}
  (ostr:geometria)
  (setvar "CLAYER" (nth 1 old))
  (command "_.UNDO" "_E")
  (setvar "CMDECHO" (nth 0 old))
  (princ (strcat "\nOstrovcek nakresleny. Neuspesnych entmake: " (itoa ostr:err)))
  ostr:err)

(defun c:OSTROVCEK (/ ss p a)
  (command "_.UNDO" "_BE")
  (princ "\nVyber stol (a stare stolicky) na odstranenie <Enter = nic>: ")
  (if (setq ss (ssget))
    (progn (command "_.ERASE" ss "")
           (princ (strcat "\nOdstranenych objektov: " (itoa (sslength ss))))))
  (setq p (getpoint "\nStred kuchynskeho ostrovceka: "))
  (if p
    (progn
      (setq a (getangle p "\nNatocenie dlhsej strany <0>: "))
      (ostr:kresli (car p) (cadr p) (if a (* 180.0 (/ a pi)) 0.0))))
  (command "_.UNDO" "_E")
  (princ))

(princ "\nOstrovcek nacitany. Spusti prikazom OSTROVCEK.")
(princ)
''')
    (OUT / f"{NAME}.lsp").write_text("\n".join(lines), encoding="ascii")


def write_png():
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.patches import Circle

    col = {"INT_NABYTOK": "#555", "INT_NABYTOK_SKRYTE": "#999", "TEXT": "#000"}
    fig, ax = plt.subplots(figsize=(8, 6))
    for e in E:
        c = col[e["layer"]]
        ls = "--" if e["layer"] == "INT_NABYTOK_SKRYTE" else "-"
        if e["t"] == "pl":
            pts = e["pts"] + (e["pts"][:1] if e["closed"] else [])
            ax.plot([p[0] for p in pts], [p[1] for p in pts], ls, color=c, lw=1.2)
        elif e["t"] == "circle":
            ax.add_patch(Circle(e["c"], e["r"], fill=False, color=c, lw=1.2))
        else:
            ax.text(*e["pos"], e["s"], fontsize=e["h"] / 9, va="bottom")
    ax.set_aspect("equal")
    ax.axis("off")
    ax.set_title("Kuchynský ostrovček – náhľad (rozmery v mm)")
    fig.savefig(OUT / f"{NAME}.png", dpi=130, bbox_inches="tight")
    plt.close(fig)


if __name__ == "__main__":
    write_lsp()
    try:
        write_png()
    except ImportError as ex:
        print("Náhľad preskočený:", ex)
    print(f"{NAME}.lsp: {len(E)} objektov")
