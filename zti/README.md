# ZTI-01 – Rekonštrukcia bytu – ZTI (kúpeľňa + WC)

| Súbor | Čo to je |
|---|---|
| `ZTI_kupelna_WC.lsp` | AutoLISP – nakreslí celý výkres do otvoreného výkresu |
| `ZTI_kupelna_WC.dxf` | ten istý výkres ako samostatný súbor (otvoriť v AutoCADe) |
| `nahlad.png`, `nahlad_detail.png` | náhľad celého listu A3 a detailu pôdorysu |
| `kontrola.txt` | automatická kontrola krížení, pripojení a spádov |
| `generuj_vykres.py` | zdroj – všetka geometria; po zmene spusti `python zti/generuj_vykres.py` (potrebuje `ezdxf`, `matplotlib`, `shapely`) |

## Použitie LSP v AutoCADe

1. Výkres v mm (`INSUNITS` = 4).
2. `APPLOAD` → načítať `ZTI_kupelna_WC.lsp`.
3. Príkaz `ZTI` → bod vloženia (Enter = 0,0 = ľavý predný vnútorný roh kúpeľne).
4. Všetko sa vráti jedným `Ctrl+Z`. Výkres sa neukladá.

Cez MCP server (lokálne): `run_lisp` s `(load "…/zti/ZTI_kupelna_WC.lsp")` a potom `(zti:kresli 0.0 0.0)`.

Vrstvy: `ST_STAVBA`, `ZTI_SV`, `ZTI_TV`, `ZTI_KANALIZACIA`, `ZTI_ZARIADOVACIE_PREDMETY`, `KOTY`, `TEXT`, `RAM`.
Tlač: model M 1:25, list A3 (rám je v modeli).
