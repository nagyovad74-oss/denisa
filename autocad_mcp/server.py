"""MCP server, cez ktorý Claude Code ovláda bežiaci AutoCAD (2027 a starší) cez COM/ActiveX.

Funguje len na Windows s plnou verziou AutoCADu (AutoCAD LT nemá ActiveX API).
Spustenie: python autocad_mcp/server.py  (Claude Code ho spúšťa sám podľa .mcp.json)
"""

from __future__ import annotations

import functools
import math
import sys
import time
from typing import Any, Callable

from mcp.server.mcpserver import MCPServer

try:
    import pythoncom
    import win32com.client
except ImportError:  # mimo Windows / bez pywin32 – server sa spustí, nástroje vrátia chybu
    pythoncom = None
    win32com = None

PROG_ID = "AutoCAD.Application"
RPC_E_CALL_REJECTED = -2147418111  # AutoCAD je zaneprázdnený (napr. otvorený dialóg)
MAX_LIST = 500

mcp = MCPServer(
    "autocad",
    instructions=(
        "Nástroje na kreslenie a úpravu výkresov v bežiacom AutoCADe. "
        "Súradnice sú v jednotkách výkresu, uhly v stupňoch. "
        "Na čokoľvek, čo nepokrývajú špecializované nástroje, použi run_lisp alebo send_command."
    ),
)


# ---------------------------------------------------------------- COM helpers


def _require_com() -> None:
    if pythoncom is None:
        raise RuntimeError(
            "pywin32 nie je dostupné. Server musí bežať na Windows: pip install -r requirements.txt"
        )


def _retry(fn: Callable[[], Any], attempts: int = 20, delay: float = 0.25) -> Any:
    """Zopakuje COM volanie, kým AutoCAD odmieta hovory, lebo je zaneprázdnený."""
    for i in range(attempts):
        try:
            return fn()
        except pythoncom.com_error as e:  # type: ignore[union-attr]
            if e.hresult != RPC_E_CALL_REJECTED or i == attempts - 1:
                raise
            time.sleep(delay)


def _app():
    _require_com()
    pythoncom.CoInitialize()  # každé volanie nástroja beží vo vlastnom vlákne
    try:
        return _retry(lambda: win32com.client.GetActiveObject(PROG_ID))
    except pythoncom.com_error as e:
        raise RuntimeError(
            "Nenašiel som bežiaci AutoCAD. Spusti AutoCAD 2027 a otvor výkres."
        ) from e


def _doc():
    app = _app()
    if _retry(lambda: app.Documents.Count) == 0:
        raise RuntimeError("V AutoCADe nie je otvorený žiadny výkres.")
    return _retry(lambda: app.ActiveDocument)


def _space(doc):
    # 1 = acModelSpace; v rozvrhnutí (layout) kreslíme do papierového priestoru
    return doc.ModelSpace if doc.ActiveSpace == 1 else doc.PaperSpace


def _pt(x: float, y: float, z: float = 0.0):
    return win32com.client.VARIANT(pythoncom.VT_ARRAY | pythoncom.VT_R8, (float(x), float(y), float(z)))


def _flat(values: list[float]):
    return win32com.client.VARIANT(pythoncom.VT_ARRAY | pythoncom.VT_R8, [float(v) for v in values])


def _finish(ent, layer: str | None, color: int | None) -> dict:
    if layer:
        _ensure_layer(ent.Document, layer)
        ent.Layer = layer
    if color is not None:
        ent.color = color
    ent.Update()
    return {"handle": ent.Handle, "type": ent.ObjectName, "layer": ent.Layer}


def _ensure_layer(doc, name: str):
    try:
        return doc.Layers.Item(name)
    except pythoncom.com_error:
        return doc.Layers.Add(name)


def _polyline(points: list[list[float]], closed: bool, layer: str | None, color: int | None) -> dict:
    if len(points) < 2:
        raise ValueError("Polyline potrebuje aspoň 2 body.")
    doc = _doc()
    pl = _space(doc).AddLightWeightPolyline(_flat([c for p in points for c in p[:2]]))
    pl.Closed = closed
    return _finish(pl, layer, color)


def com_tool(fn: Callable) -> Callable:
    """Registruje nástroj a COM chyby prevedie na čitateľné hlásenie pre Clauda."""

    @functools.wraps(fn)
    def wrapper(*args, **kwargs):
        try:
            return fn(*args, **kwargs)
        except Exception as e:  # noqa: BLE001 – chceme vrátiť chybu modelu, nie zhodiť server
            if pythoncom is not None and isinstance(e, pythoncom.com_error):
                detail = e.excepinfo[2] if e.excepinfo and e.excepinfo[2] else e.strerror
                raise RuntimeError(f"AutoCAD COM chyba: {detail}") from e
            raise

    return mcp.tool()(wrapper)


# ---------------------------------------------------------------- informácie


@com_tool
def get_drawing_info() -> dict:
    """Vráti info o aktívnom výkrese: názov, cestu, jednotky, vrstvy, počet objektov a rozsah."""
    doc = _doc()
    info = {
        "autocad_version": doc.Application.Version,
        "name": doc.Name,
        "path": doc.FullName,
        "saved": bool(doc.Saved),
        "active_space": "model" if doc.ActiveSpace == 1 else "paper",
        "active_layer": doc.ActiveLayer.Name,
        "insunits": doc.GetVariable("INSUNITS"),
        "modelspace_count": doc.ModelSpace.Count,
        "layers": [doc.Layers.Item(i).Name for i in range(doc.Layers.Count)],
    }
    try:
        info["extmin"] = list(doc.GetVariable("EXTMIN"))
        info["extmax"] = list(doc.GetVariable("EXTMAX"))
    except Exception:  # noqa: BLE001
        pass
    return info


@com_tool
def list_open_drawings() -> list[dict]:
    """Zoznam všetkých otvorených výkresov."""
    app = _app()
    active = app.ActiveDocument.FullName if app.Documents.Count else None
    return [
        {"name": d.Name, "path": d.FullName, "active": d.FullName == active}
        for d in (app.Documents.Item(i) for i in range(app.Documents.Count))
    ]


@com_tool
def list_entities(layer: str | None = None, entity_type: str | None = None, limit: int = 200) -> dict:
    """Vypíše objekty v modelovom priestore (handle, typ, vrstva, ohraničenie).

    layer: filter podľa vrstvy; entity_type: filter podľa ObjectName, napr. "AcDbLine", "AcDbCircle".
    """
    doc = _doc()
    ms = doc.ModelSpace
    limit = min(limit, MAX_LIST)
    out, total = [], 0
    for i in range(ms.Count):
        e = ms.Item(i)
        if layer and e.Layer.lower() != layer.lower():
            continue
        if entity_type and e.ObjectName.lower() != entity_type.lower():
            continue
        total += 1
        if len(out) < limit:
            item = {"handle": e.Handle, "type": e.ObjectName, "layer": e.Layer}
            try:
                mn, mx = e.GetBoundingBox()
                item["bbox"] = [list(mn)[:2], list(mx)[:2]]
            except Exception:  # noqa: BLE001 – niektoré objekty bbox nemajú
                pass
            out.append(item)
    return {"total_matching": total, "returned": len(out), "entities": out}


@com_tool
def get_entity(handle: str) -> dict:
    """Detail jedného objektu podľa handle (geometria, vrstva, farba, text…)."""
    e = _doc().HandleToObject(handle)
    props = {"handle": e.Handle, "type": e.ObjectName, "layer": e.Layer, "color": e.color}
    for name in (
        "StartPoint", "EndPoint", "Center", "Radius", "StartAngle", "EndAngle", "Length",
        "Area", "Coordinates", "Closed", "TextString", "InsertionPoint", "Height", "Name",
        "Measurement", "Rotation",
    ):
        try:
            v = getattr(e, name)
        except Exception:  # noqa: BLE001
            continue
        if isinstance(v, tuple):
            v = list(v)
        if name in ("StartAngle", "EndAngle", "Rotation") and isinstance(v, float):
            v = math.degrees(v)
        props[name] = v
    return props


# ---------------------------------------------------------------- kreslenie


@com_tool
def draw_line(x1: float, y1: float, x2: float, y2: float, layer: str | None = None, color: int | None = None) -> dict:
    """Nakreslí úsečku z (x1,y1) do (x2,y2). color = ACI index (1 červená, 2 žltá, 3 zelená, 5 modrá, 7 biela/čierna)."""
    doc = _doc()
    return _finish(_space(doc).AddLine(_pt(x1, y1), _pt(x2, y2)), layer, color)


@com_tool
def draw_polyline(points: list[list[float]], closed: bool = False, layer: str | None = None, color: int | None = None) -> dict:
    """Nakreslí 2D lomenú čiaru (LWPOLYLINE) cez body [[x,y], ...]."""
    return _polyline(points, closed, layer, color)


@com_tool
def draw_rectangle(x: float, y: float, width: float, height: float, layer: str | None = None, color: int | None = None) -> dict:
    """Nakreslí obdĺžnik s ľavým dolným rohom v (x,y)."""
    pts = [[x, y], [x + width, y], [x + width, y + height], [x, y + height]]
    return _polyline(pts, True, layer, color)


@com_tool
def draw_circle(cx: float, cy: float, radius: float, layer: str | None = None, color: int | None = None) -> dict:
    """Nakreslí kružnicu so stredom (cx,cy)."""
    doc = _doc()
    return _finish(_space(doc).AddCircle(_pt(cx, cy), radius), layer, color)


@com_tool
def draw_arc(cx: float, cy: float, radius: float, start_angle: float, end_angle: float, layer: str | None = None, color: int | None = None) -> dict:
    """Nakreslí oblúk; uhly v stupňoch, proti smeru hodinových ručičiek od osi X."""
    doc = _doc()
    arc = _space(doc).AddArc(_pt(cx, cy), radius, math.radians(start_angle), math.radians(end_angle))
    return _finish(arc, layer, color)


@com_tool
def draw_text(text: str, x: float, y: float, height: float = 2.5, rotation: float = 0.0, layer: str | None = None, color: int | None = None) -> dict:
    """Vloží jednoriadkový text; pri viacriadkovom (\\n) použije MTEXT."""
    doc = _doc()
    if "\n" in text:
        ent = _space(doc).AddMText(_pt(x, y), 0.0, text.replace("\n", "\\P"))
        ent.Height = height
    else:
        ent = _space(doc).AddText(text, _pt(x, y), height)
    ent.Rotation = math.radians(rotation)
    return _finish(ent, layer, color)


@com_tool
def draw_dimension(x1: float, y1: float, x2: float, y2: float, text_x: float, text_y: float, layer: str | None = None) -> dict:
    """Pridá zarovnanú kótu medzi dvoma bodmi; (text_x,text_y) určuje polohu kótovacej čiary."""
    doc = _doc()
    dim = _space(doc).AddDimAligned(_pt(x1, y1), _pt(x2, y2), _pt(text_x, text_y))
    return _finish(dim, layer, None) | {"measurement": dim.Measurement}


@com_tool
def insert_block(name: str, x: float, y: float, scale: float = 1.0, rotation: float = 0.0, layer: str | None = None) -> dict:
    """Vloží blok (definovaný vo výkrese alebo cesta k .dwg súboru)."""
    doc = _doc()
    ref = _space(doc).InsertBlock(_pt(x, y), name, scale, scale, scale, math.radians(rotation))
    return _finish(ref, layer, None)


# ---------------------------------------------------------------- úpravy


@com_tool
def move_entity(handle: str, dx: float, dy: float) -> dict:
    """Posunie objekt o (dx,dy)."""
    e = _doc().HandleToObject(handle)
    e.Move(_pt(0, 0), _pt(dx, dy))
    e.Update()
    return {"handle": handle, "moved_by": [dx, dy]}


@com_tool
def copy_entity(handle: str, dx: float, dy: float) -> dict:
    """Skopíruje objekt a kópiu posunie o (dx,dy). Vráti handle kópie."""
    c = _doc().HandleToObject(handle).Copy()
    c.Move(_pt(0, 0), _pt(dx, dy))
    c.Update()
    return {"handle": c.Handle, "type": c.ObjectName}


@com_tool
def rotate_entity(handle: str, base_x: float, base_y: float, angle: float) -> dict:
    """Otočí objekt okolo bodu o uhol v stupňoch."""
    e = _doc().HandleToObject(handle)
    e.Rotate(_pt(base_x, base_y), math.radians(angle))
    e.Update()
    return {"handle": handle, "rotated_by": angle}


@com_tool
def set_entity_properties(handle: str, layer: str | None = None, color: int | None = None) -> dict:
    """Zmení vrstvu a/alebo farbu (ACI) objektu."""
    e = _doc().HandleToObject(handle)
    return _finish(e, layer, color)


@com_tool
def delete_entities(handles: list[str]) -> dict:
    """Zmaže objekty podľa handle."""
    doc = _doc()
    for h in handles:
        doc.HandleToObject(h).Delete()
    return {"deleted": handles}


# ---------------------------------------------------------------- vrstvy


@com_tool
def list_layers() -> list[dict]:
    """Zoznam vrstiev s farbou, stavom a typom čiary."""
    doc = _doc()
    out = []
    for i in range(doc.Layers.Count):
        l = doc.Layers.Item(i)
        out.append({
            "name": l.Name, "color": l.color, "on": bool(l.LayerOn), "frozen": bool(l.Freeze),
            "locked": bool(l.Lock), "linetype": l.Linetype,
        })
    return out


@com_tool
def create_layer(name: str, color: int = 7, linetype: str | None = None, make_current: bool = False) -> dict:
    """Vytvorí (alebo upraví) vrstvu; color = ACI index."""
    doc = _doc()
    l = _ensure_layer(doc, name)
    l.color = color
    if linetype:
        try:
            doc.Linetypes.Item(linetype)
        except pythoncom.com_error:
            doc.Linetypes.Load(linetype, "acadiso.lin")
        l.Linetype = linetype
    if make_current:
        doc.ActiveLayer = l
    return {"name": l.Name, "color": l.color, "linetype": l.Linetype}


# ---------------------------------------------------------------- príkazy a LISP


@com_tool
def send_command(command: str) -> str:
    """Pošle príkaz do príkazového riadku AutoCADu, ako keby ho napísal používateľ.

    Príkaz sa ukončí Enterom automaticky. Používaj anglické názvy s podčiarkovníkom
    (napr. "_ZOOM _E", "_-HATCH ..."), aby fungovali v každej jazykovej verzii.
    """
    doc = _doc()
    cmd = command if command.endswith(("\n", " ")) else command + "\n"
    doc.SendCommand(cmd)
    return "OK"


@com_tool
def run_lisp(expression: str, timeout_s: float = 10.0) -> str:
    """Vyhodnotí AutoLISP výraz a vráti jeho výsledok ako text.

    Príklad: (length (vl-remove-if-not '(lambda (x) t) (list 1 2 3)))
    """
    doc = _doc()
    marker = f"__claude_{time.time_ns()}__"
    doc.SetVariable("USERS5", marker)
    doc.SendCommand(
        f'(progn (vl-load-com) (setvar "USERS5" (vl-prin1-to-string {expression})) (princ)) '
    )
    deadline = time.time() + timeout_s
    while time.time() < deadline:
        value = _retry(lambda: doc.GetVariable("USERS5"))
        if value != marker:
            return value
        time.sleep(0.1)
    raise TimeoutError("LISP výraz nevrátil výsledok včas (chyba vo výraze alebo čaká na vstup?).")


@com_tool
def get_variable(name: str) -> Any:
    """Prečíta systémovú premennú (napr. INSUNITS, LTSCALE, CLAYER)."""
    v = _doc().GetVariable(name)
    return list(v) if isinstance(v, tuple) else v


@com_tool
def set_variable(name: str, value: str | int | float) -> str:
    """Nastaví systémovú premennú."""
    _doc().SetVariable(name, value)
    return "OK"


# ---------------------------------------------------------------- súbory a pohľad


@com_tool
def zoom_extents() -> str:
    """Priblíži pohľad na všetky objekty."""
    _app().ZoomExtents()
    return "OK"


@com_tool
def new_drawing(template: str = "acadiso.dwt") -> dict:
    """Vytvorí nový výkres zo šablóny a aktivuje ho."""
    doc = _app().Documents.Add(template)
    doc.Activate()
    return {"name": doc.Name}


@com_tool
def open_drawing(path: str, read_only: bool = False) -> dict:
    """Otvorí DWG/DXF súbor (absolútna cesta vo Windows)."""
    doc = _app().Documents.Open(path, read_only)
    doc.Activate()
    return {"name": doc.Name, "path": doc.FullName}


@com_tool
def save_drawing(path: str | None = None) -> dict:
    """Uloží aktívny výkres; s `path` urobí 'Uložiť ako'."""
    doc = _doc()
    if path:
        doc.SaveAs(path)
    else:
        doc.Save()
    return {"path": doc.FullName}


if __name__ == "__main__":
    if sys.platform != "win32":
        print("Upozornenie: AutoCAD COM funguje len na Windows.", file=sys.stderr)
    mcp.run()
