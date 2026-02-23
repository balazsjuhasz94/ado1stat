## Adatforrások

A felhasznált adatok **bárki által elérhető** adatok az interneten:
- **[NAV nyilvános adatai, 2025](https://nav.gov.hu/ado/szja1_1/kimutatasok_elszamolasok/civil-szervezetek/egyszaz_kiut_2025/kozlemeny-a-2025.-evben-szja-1-os-felajanlasban-reszesult-civil-kedvezmenyezettekrol)** — az SZJA 1%-os felajánlásban részesült civil kedvezményezettek listája 
- **[civil.info.hu](https://civil.info.hu)** — A szervezetek alapadatai (székhely, célkitűzés) és a felajánlásokból való részesedésük a korábbi évekből

## A projekt lépései

2025-ben összesen **20,3 mrd Ft-ot** ajánlottak fel, összesen több mint **37 ezer szervezetnek**.

A felajánlások összegei nagyon nem egyenletesen oszlanak el a szervezetek között:
- az első **100** legtöbb felajánlást kapó szervezet a teljes összeg **34%-át** kapta (7,0 mrd Ft)
- az első **1 000** szervezet az összeg **59%-át** (11,9 mrd Ft)
- az első **5 000** szervezet az összeg **79%-át** (15,9 mrd Ft)
- az első **10 000** szervezet az összeg **88%-át** (17,9 mrd Ft)

A **10 000 legtöbb felajánlást kapó szervezetet** választottam végül ki. Ez lefedi a teljes felajánlott összeg zömét, másrészt ennél több adatot nem nagyon lehetne vizualizálni.

A projekt lépései:

1. Automatikus adatgyűjtés (scrape-elés) a [civil.info.hu](https://civil.info.hu) oldalról a kiválasztott 10 000 szervezetről
2. A szervezetek kategorizálása megfelelően meghívott (promptolt) LLM (nagy nyelvi modell) segítségével
3. Az összegyűjtött adatok vizualizációja
4. Weboldal létrehozása a projektről

További nem elhanyagolható része volt a folyamatnak az olykor félrekategorizált szervezetek kézzel való javítása, ami így sem tökéletes. Nem feltétlenül egyértelmű bekategorizálni a szervezeteket konkrét csoportokba, hiszen a profiljuk nem feltétlenül szűkíthető le egy kategóriára, illetve néhol a kategóriák is összefedhetnek.

A [civil.info.hu](https://civil.info.hu) oldalon elérhető volt egyébként egyfajta kategorizálás — először azt szerettem volna használni, de a kategóriák sem voltak túl jól szétbontva, és maga a kategorizálás sem volt pontos egyáltalán.

## Technikai részletek és költségek

Igyekszem minél közérthetőbben leírni.

Lényegében **sosem néztem bele a generált kódba**, és minden változtatást automatikusan elfogadtam. A legtöbb esetben elsőre sikerült megvalósítania az aktuális kérésemet, de ha elsőre nem is, **sosem kellett háromnál többet iterálni** bármilyen komplex kérés esetén sem.

Az Anthropic cég Claude termékeit használtam a projekt során.

Előfizettem a **Claude Pro**-ra (25,4 € / hónap), mellyel a **Claude Code** AI asszisztenst használtam.

Ha ezt intenzíven használja az ember és nem akar várni, akkor rá kell fizetni egy keveset — így én még elhasználtam további 48 €-nyi tokent. 

Emellett a szervezetek kategorizálásához szükségem volt arra, hogy API-n keresztül, egy programkódon belül hívjam meg a Claude modelljét. Ennek a költségét az elhasznált tokenek száma alapján számolják. ~12 millió bemeneti tokent és 200 ezer kimeneti tokent használtam, ami **12,29 $-ba** került. Ez a gyakorlatban úgy néz ki, hogy egy megfelelő szöveget előkészítettem (vagyis inkább előkészíttettem), hogy mi lesz a feladata a modellnek. A szöveget a [A használt promptok](/promptok) oldalon megtalálod.

A kategorizálás elég jól működött. Egyedül az oktatás kategória tűnt javítandónak, ott sok esetben a megfelelő iskola típusa nem igazán derült ki a cél leírásából. 
Lehetőség van arra, is hogy a model használja az internetet, ha bizonytalan. Így erre a ~3000 oktatást segítő alapítványra meghívtam ezt a kicsit költségesebb módot, mely összesen **15,39 $**-ba került.   

Persze ezek után is lehetségesek félrekategorizált szervezetek, ha nagyon nagy szervezet esetén ilyen történt, akkor azt kézzel orvosoltam. Összesen kézzel kevesebb, mint 10 kategorizálást változtattam meg. 


Az AI asszisztensnél a **Sonnet 4.5**-öt használtam, amely ajánlott erre a célra, és nem a legdrágább. A kategorizáláshoz a legolcsóbb, **Haiku** modellt használtam, hiszen ez is elég megbízhatóan képes volt a szervezetek céljainak leírása és a megfelelő bevezető szöveg alapján besorolni az előre elkészített kategóriák közé a szervezeteket.

A vizualizációhoz a Pythonos **plotly** csomagot használtam, amit már sokszor vettem segítségül interaktív vizualizálásra. Az interaktivitást az ehhez ajánlott **dash** csomag adja.

A weboldal létrehozásához egyrészt a webcím domainjét kellett regisztrálni, mely 1 évre 2 527 Ft (.hu-s webcím esetén) a Tárhely.eu oldalon intézve. Másrészt a weboldal hostolását egy felhőszolgáltatón keresztül intéztem, amely szerver bérlése havonta **3,49 €-ba** kerül. Ha egyszerre több mint 100-an akarnák böngészni az oldalt, akkor szükséges lenne egy nagyobb szerverre váltani.

Az ilyen webhelyes dolgokhoz legkevésbé sem értek, de pofon egyszerűen ment Claude Code segítségével.

Összesítve a **projekt költségei**:

| Tétel | Költség |
|-------|-------:|
| Claude Pro előfizetés | 25,4 € (~9 680 Ft) |
| Claude Pro intenzív használat | 48,2 € (~18 293 Ft) |
| Claude API hívás kategorizáláshoz | 12,29 $ (~3 970 Ft) |
| Claude API + web search (oktatás) | 15.39 $ (~4 947 Ft) |
| Szerver bérlése az oldalhoz | 3,49 €/hó (~1 330 Ft) |
| Web domain megvétele | 2 527 Ft (1. évre) |
| **Összesen** | **~40 750 Ft** |


