# Značky pre hydraulickú schému kotolne

Značky sú zjednodušené, kreslia sa ako bloky (`_BLOCK`) do vrstvy `sch_zariadenie`.
Presné prepojenie pre CTC EcoAir 406–420 vziať z montážneho návodu výrobcu.

## Zariadenia
| Značka | Ako nakresliť | Skratka |
|---|---|---|
| Tepelné čerpadlo (vonkajšia jednotka) | obdĺžnik s krížom alebo ventilátorom (kruh so 4 lúčmi) | TČ |
| Akumulačná nádrž | zvislý obdĺžnik so zaoblenými rohmi | AN |
| Zásobník teplej vody | zvislý obdĺžnik s cievkou (cik-cak vnútri) | ZTV |
| Expanzná nádoba | kruh s vodorovnou čiarou (membrána) a pripojením zhora | EN |
| Rozdeľovač kúrenia | vodorovný obdĺžnik s výstupmi dole | RK |
| Rozvádzač (elektro) | malý obdĺžnik s písmenom R | R |

## Armatúry a prvky
| Značka | Ako nakresliť | Skratka |
|---|---|---|
| Obehové čerpadlo | kruh s trojuholníkom vo vnútri (smer toku) | OČ |
| Uzatvárací ventil | dva trojuholníky špičkami k sebe (motýlik) | UV |
| Trojcestný ventil | motýlik s tretím vývodom kolmo | TV3 |
| Poistný ventil | ventil s pružinou (cik-cak) a výpustom | PV |
| Spätná klapka | trojuholník s priečkou | SK |
| Filter (kalový) | motýlik s krátkou šikmou čiarou | F |
| Teplomer / manometer | malý kruh s písmenom T alebo M | T, M |
| Odvzdušňovací ventil | malý kruh na hornom bode s výpustom | OV |

## Čiary (vrstvy)
| Vrstva | Farba | Význam |
|---|---|---|
| `sch_vystup` | červená | kúrenie, výstup |
| `sch_vratka` | modrá | kúrenie, vratka |
| `sch_tv` | oranžová | teplá voda |
| `sch_studena` | azúrová | studená voda |
| `sch_zariadenie` | biela/čierna | zariadenia a značky |
| `sch_text` | žltá | popisy |

## Postup
1. Nakresli každú značku raz, vo vrstve 0 (farba aj typ čiary ByLayer).
2. Označ ju, `_BLOCK`, pomenuj bez diakritiky (napr. `OBEH_CERPADLO`), nastav bázový bod.
3. Vkladaj cez `_INSERT` s vrstvou `sch_zariadenie` nastavenou ako aktuálna.
4. Popíš skratku (`_MTEXT`) a pridaj legendu s vysvetlením značiek.
