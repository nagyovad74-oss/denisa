# Prepojenie AutoCAD 2027 ↔ Claude Code

MCP server, vďaka ktorému Claude Code vie priamo kresliť a upravovať výkresy v **bežiacom AutoCADe**:
čiary, polyline, obdĺžniky, kružnice, oblúky, texty, kóty, bloky, vrstvy, presuny/kópie/rotácie,
mazanie, systémové premenné, ľubovoľné príkazy a AutoLISP, otváranie a ukladanie výkresov.

Prepojenie ide cez ActiveX/COM rozhranie AutoCADu, preto:

- ✅ **Windows** + plná verzia **AutoCAD 2027** (funguje aj so staršími, aj s Civil 3D, Architecture, Mechanical…)
- ❌ AutoCAD **LT** – nemá ActiveX API
- ❌ Claude Code v cloude (claude.ai/code) – nedosiahne na AutoCAD v tvojom počítači.
  Claude Code musí bežať **lokálne na tom istom PC** ako AutoCAD.

## Inštalácia (raz)

1. Nainštaluj [Python 3.10+](https://www.python.org/downloads/windows/) (pri inštalácii zaškrtni *Add python.exe to PATH*).
2. Nainštaluj Claude Code pre Windows: <https://code.claude.com/docs/en/setup>
   (alebo použi Claude desktop aplikáciu, záložku **Code**).
3. Stiahni tento repozitár a nainštaluj závislosti (PowerShell):

   ```powershell
   git clone https://github.com/nagyovad74-oss/denisa.git
   cd denisa
   python -m pip install -r requirements.txt
   ```

## Použitie

1. Spusti **AutoCAD 2027** a otvor (alebo vytvor) výkres.
2. V priečinku `denisa` spusti `claude`. Súbor `.mcp.json` server zaregistruje automaticky –
   pri prvom spustení potvrď, že mu dôveruješ. Príkazom `/mcp` overíš, že `autocad` je **connected**.
3. Píš po slovensky, napr.:
   - „Nakresli pôdorys miestnosti 4,5 × 3,2 m so stenami hrúbky 300 mm vo vrstve STENY.“
   - „Vypíš všetky objekty vo vrstve KOTY a posuň ich o 500 doprava.“
   - „Okótuj všetky vodorovné úsečky.“
   - „Spočítaj plochu všetkých uzavretých polyline vo vrstve MIESTNOSTI.“

### Použitie z iného priečinka

Ak chceš AutoCAD nástroje mať k dispozícii všade (nielen v tomto repozitári):

```powershell
claude mcp add autocad --scope user -- python C:\cesta\k\denisa\autocad_mcp\server.py
```

## Nástroje

| Oblasť | Nástroje |
|---|---|
| Info | `get_drawing_info`, `list_open_drawings`, `list_entities`, `get_entity`, `list_layers`, `get_variable` |
| Kreslenie | `draw_line`, `draw_polyline`, `draw_rectangle`, `draw_circle`, `draw_arc`, `draw_text`, `draw_dimension`, `insert_block` |
| Úpravy | `move_entity`, `copy_entity`, `rotate_entity`, `set_entity_properties`, `delete_entities`, `create_layer`, `set_variable` |
| Čokoľvek iné | `send_command` (príkazový riadok), `run_lisp` (AutoLISP s návratovou hodnotou) |
| Súbory | `new_drawing`, `open_drawing`, `save_drawing`, `zoom_extents` |

Všetky zmeny idú cez bežné API AutoCADu, takže ich vrátiš cez **Ctrl+Z** v AutoCADe.

## Riešenie problémov

- **„Nenašiel som bežiaci AutoCAD“** – AutoCAD musí bežať a Claude Code aj AutoCAD musia bežať pod tým istým
  používateľom s rovnakými právami (nespúšťaj jeden „ako správca“ a druhý normálne).
- **Nástroj čaká / timeout** – v AutoCADe je otvorený dialóg alebo rozpracovaný príkaz; stlač Esc.
- **`/mcp` ukazuje failed** – skontroluj, že `python -c "import win32com, mcp"` prebehne bez chyby.
