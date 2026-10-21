# Rodinný dom – architektonická štúdia

Prízemie + obývané podkrovie, murovaný (tehla), sedlová strecha 35°, 4 izby, bez garáže, pozemok 20 × 30 m (ulica na severe).

| Súbor | Čo to je |
|---|---|
| `Rodinný dom.dxf` | výkres (mm, M 1:1): situácia, základy, pôdorysy 1.NP a 2.NP, schéma krovu, rez A–A, 4 pohľady, poznámky |
| `Rodinný dom - náhľad.pdf` | náhľad všetkých častí na prezeranie v mobile |
| `generuj_dom.py` | zdroj – všetky rozmery a geometria; po zmene `python rodinny_dom/generuj_dom.py` (potrebuje `ezdxf`, `shapely`, `matplotlib`) |
| `nahlad_*.png` | náhľady jednotlivých častí |

V AutoCADe: `OPEN` → `Rodinný dom.dxf` → `Uložiť ako` DWG. Alebo do už otvoreného výkresu cez `INSERT` (Prehľadávať → DXF).
Časti výkresu sú v modeli vedľa seba, každá v mierke uvedenej v názve (pozri `ZOOM` → `Extents`).
Vrstvy sú pomenované (`STENY_NOSNE`, `IZOLACIA`, `OKNA`, `DVERE`, `KROV`, `KOTY`…).

Je to predbežná štúdia, nie projekt pre stavebné konanie – statiku, energetické hodnotenie, požiarnu bezpečnosť
a profesie musí vypracovať autorizovaný projektant (pozri poznámky vo výkrese).
