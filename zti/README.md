# ZTI-01 – Rekonštrukcia bytu – ZTI (kúpeľňa + WC)

| Súbor | Čo to je |
|---|---|
| `ZTI_kupelna_WC.lsp` | AutoLISP – nakreslí celý výkres do otvoreného výkresu |
| `ZTI_kupelna_WC.dxf` | ten istý výkres ako samostatný súbor (otvoriť v AutoCADe) |
| `nahlad.png`, `nahlad_detail.png` | náhľad celého listu A3 a detailu pôdorysu |
| `kontrola.txt` | automatická kontrola krížení, pripojení a spádov |
| `kuchyna_ostrovcek.lsp` | AutoLISP – príkaz `OSTROVCEK`: odstráni vybraný stôl a nakreslí kuchynský ostrovček 1800×900 s 3 barovými stoličkami |
| `kuchyna_ostrovcek.png` | náhľad ostrovčeka |
| `kuchyna_ostrovcek.py` | zdroj ostrovčeka (rozmery, počet stoličiek) – po zmene spusti `python zti/kuchyna_ostrovcek.py` |
| `generuj_vykres.py` | zdroj – všetka geometria; po zmene spusti `python zti/generuj_vykres.py` (potrebuje `ezdxf`, `matplotlib`, `shapely`) |

## Použitie LSP v AutoCADe

1. Výkres v mm (`INSUNITS` = 4).
2. `APPLOAD` → načítať `ZTI_kupelna_WC.lsp`.
3. Príkaz `ZTI` → bod vloženia (Enter = 0,0 = ľavý predný vnútorný roh kúpeľne).
4. Všetko sa vráti jedným `Ctrl+Z`. Výkres sa neukladá.

Cez MCP server (lokálne): `run_lisp` s `(load "…/zti/ZTI_kupelna_WC.lsp")` a potom `(zti:kresli 0.0 0.0)`.

Vrstvy: `ST_STAVBA`, `ZTI_SV`, `ZTI_TV`, `ZTI_KANALIZACIA`, `ZTI_ZARIADOVACIE_PREDMETY`, `KOTY`, `TEXT`, `RAM`.
Tlač: model M 1:25, list A3 (rám je v modeli).

## Kanalizácia kúpeľne – spoločné potrubie

Vaňa, práčka a umývadlo U1 majú **jedno spoločné odpadové potrubie K DN50**:
pod vaňou za obkladovou stienkou → v inštalačnej predstienke SDK (h 1200) za obkladom →
prierazom **P1** Ø80 v priečke do WC → vo WC **nad podlahou v obkladovom boxe 120×150** →
prierazom **P2** Ø80 pod revíznymi dvierkami do šachty → nová odbočka DN100/50 na stúpačke K1.
Spád 2 %, výšky osi sú v poznámke 11 a v `kontrola.txt`.

## Kuchynský ostrovček

1. `APPLOAD` → `kuchyna_ostrovcek.lsp`.
2. Príkaz `OSTROVCEK` → vyber stôl (a staré stoličky) → Enter → klikni stred ostrovčeka → natočenie.
3. Vrstvy `INT_NABYTOK`, `INT_NABYTOK_SKRYTE` (hrana skriniek, čiara voľného priestoru 1000 mm).

Cez MCP server: stôl zmaž cez `list_entities` + `delete_entities`, potom `run_lisp`
s `(load "…/zti/kuchyna_ostrovcek.lsp")` a `(ostr:kresli x y uhol)`.
