# AutoCAD + Claude Code

Tento repozitár obsahuje MCP server (`autocad_mcp/server.py`), cez ktorý Claude ovláda bežiaci AutoCAD.

Pri práci vo výkrese:
- Najprv zavolaj `get_drawing_info`, aby si poznal jednotky (INSUNITS: 4 = mm, 6 = m) a existujúce vrstvy.
- Kresli do pomenovaných vrstiev (`create_layer`), nie do vrstvy 0.
- Na veci, ktoré nepokrývajú nástroje (šrafy, polia, tabuľky…), použi `run_lisp` alebo `send_command`
  s anglickými názvami príkazov s podčiarkovníkom (`_-HATCH`), aby fungovali v slovenskej/českej verzii.
- Po väčšej zmene zavolaj `zoom_extents`. Výkres neukladaj bez súhlasu používateľa.
