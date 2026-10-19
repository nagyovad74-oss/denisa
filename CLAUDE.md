# AutoCAD + Claude Code

Tento repozitár obsahuje MCP server (`autocad_mcp/server.py`), cez ktorý Claude ovláda bežiaci AutoCAD.

Pri práci vo výkrese:
- Najprv zavolaj `get_drawing_info`, aby si poznal jednotky (INSUNITS: 4 = mm, 6 = m) a existujúce vrstvy.
- Kresli do pomenovaných vrstiev (`create_layer`), nie do vrstvy 0.
- Na veci, ktoré nepokrývajú nástroje (šrafy, polia, tabuľky…), použi `run_lisp` alebo `send_command`
  s anglickými názvami príkazov s podčiarkovníkom (`_-HATCH`), aby fungovali v slovenskej/českej verzii.
- Po väčšej zmene zavolaj `zoom_extents`. Výkres neukladaj bez súhlasu používateľa.

## Pravidlá pre výkresy Denisy (platí len v tomto repozitári)

- **Studená voda (SV)** sa vždy kreslí **bodkočiarkovanou** čiarou (modrá), **teplá voda (TV)** vždy
  **dvojbodkočiarkovanou** čiarou (červená) – v pôdoryse, v schémach/axonometrii aj v legende značiek.
  Mierku vzoru čiar nastav podľa mierky výkresu tak, aby bola čiarka na papieri cca 6–8 mm.
  Krúžky stúpačiek, vývody a drobné značky na vrstvách SV/TV zostávajú plné.
- **Vzorové fotky a obrázky**, ktoré pošle používateľka, sú len predloha – **nikdy ich neupravuj**.
  Pracuj vždy v jej skutočnom výkrese (napr. ZTI3), nie v novom ukážkovom.
