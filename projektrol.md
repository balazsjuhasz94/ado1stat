## Cél

Ez az oldal egy hobbiprojekt, mely két hétvége alatt készült, nagyrészt AI által íródott kódok segítségével ("vibe-coding"). 
A projekt célja, hogy 
- bemutassa a civil szervezeteknek felajánlott adó 1% összegek trendjeit, 
- lehetőséget adjon az embereknek böngészni a lehetséges szervezetek között
- mutasson egy példát arra, hogy milyen jó dolgokra lehet használni az AI-t


## Adatforrások
A felhasznált adatok bárki által elérhető adatok az interneten, 
- NAV nyilvános adatok - az SZJA 1%-os felajánlásban részesült civil kezdeményezettek listája ([2025-ös közzététel](https://nav.gov.hu/ado/szja1_1/kimutatasok_elszamolasok/civil-szervezetek/egyszaz_kiut_2025/kozlemeny-a-2025.-evben-szja-1-os-felajanlasban-reszesult-civil-kedvezmenyezettekrol))
- [civil.info.hu](https://civil.info.hu) - A szervezetek alapadatai (székhely, célkitűzés) és a felajánlásokból való részesedésük a korábbi évekből

## A projekt lépései
2025-ben összesen 20,3 mrd Ft-ot ajánlottak fel, összesen több, mint 37 ezer szervezetnek. 

A felajánlások összegei persze nagyon nem egyenletesen oszlanak el a több mint 30 ezer szervezet között:
- az első 100 legtöbb felajánlást kapó szervezet a teljes összeg 34%-át kapta (7,0 mrd Ft)
- az első 1 000 szervezet az összeg 59%-át (11,9 mrd Ft)
- az első 5 000 szervezet az összeg 79%-át (15,9 mrd Ft)
- az első 10 000 szervezet az összeg 88%-át (17,9 mrd Ft)

A 10 000 legtöbb felajánlást kapó szervezetet választottam végül ki. Ez lefedi a teljes felajánlott összeg zömét, másrészt ennél több adatot nem nagyon lehetne vizualizálni.

A projekt ezt követő lépései:

1. Automatikus adatgyűjtés (scrape-elés) a [civil.info.hu](https://civil.info.hu) oldalról a kiválasztott 10 000 szervezetről
2. A szervezetek kategorizálása megfelelően meghívott (promptolt) LLM (nagy nyelvi modell) segítségével. 
3. Az összegyűjtött adatok vizualizációja
4. Weboldal létrehozása a projektről 

További nem elhanyagolható része volt a folyamatnak az olykor félrekategorizált szervezetek kézzel való fixálása, mely így sem tökéletes. 
Nem feltétlen egyértelmű bekategorizálni a szervezeteket konkrét csoportokba, hiszen a profiljuk nem feltétlenül szűkíthető le egy kategóriára, illetve néhol a kategóriák is összefedhetnek. 

A [civil.info.hu](https://civil.info.hu) oldalon elérhető volt egyébként egyfajta kategorizálás, először azt szerettem volna használni, de a kategóriák sem voltak túl jól szétbontva, és maga a kategorizálás sem volt pontos egyáltalán.

## Technikai részletek és költségek
Igyekszem minél közérthetőbben leírni.

Lényegében sosem néztem bele a generált kódba és minden változtatást automatikusan elfogadtam. A legtöbb esetben elsőre sikerült megvalósítania az aktuális kérésemet, de ha elsőre nem is, sosem kellett háromnál többet iterálni bármilyen komplex kérés esetén sem. 

Az Anthropic cég Claude termékeit használtam a projekt során. 

Előfizettem a Claude Pro-ra (25.4 EUR / hónap) mely segítségével a Claude Code AI asszisztenst használtam. 

Ha ezt intenzíven használja az ember és nem akar várni, akkor rá kell fizetni egy keveset, így én még elhasználtam további 20 EUR-nyi tokent.

Emellett a szervezetek kategorizálásához szükségem volt arra, hogy API-n keresztül, egy programkódon belül hívjam meg a Claude modeljét. Ennek a költségét az elhasznált tokenek száma alapján számolják.
~12 millió bemeneti tokent, és 200 ezer kimeneti tokent használtam, ami 12,29 $-ba került. 
Ez a gyakorlatban úgy néz ki, hogy egy megfelelő szöveget előkészítettem (vagyis inkább előkészíttettem :)) hogy mi lesz a feladata a modellnek. A szöveget lentebb megtalálod. 

Az AI asszisztensnél a Sonnet 4.5-ot használtam, amely ajánlott erre a célra, és nem a legdrágább. 
A kategorizáláshoz a legolcsóbb, Haiku modelt használtam, hiszen ez is elég megbízhatóan képes volt a szervezetek céljainak leírása és a megfelelő bevezető szöveg alapján besorolni az előre elkészített kategóriák közé a szervezeteket.  

A vizualizációhoz Pythonos plotly csomagot használtam, amit már sokszor vettem segítségül interaktív vizualizálásra. Az interaktivitást az ehhez ajánlott dash csomag adja. 

A weboldal létrehozásához egyrészt a webcím domain-jét kellett regisztrálni, mely 1 évre 2527 Ft (.hu-s webcím esetén) a Tárhely.eu oldalon intézve. 
Másrészt a weboldal hostolását egy felhőszolgáltatón keresztül intéztem, amely szerver bérlése havonta 3.49 EUR-ba kerül. Ha egyszerre több, mint 100-an akarnák böngészni az oldalt, akkor szükséges lenne egy nagyobb szerverre váltani.

Az ilyen webhelyes dolgokhoz legkevésbé sem értek, de pofon egyszerűen ment Claude Code segítségével.

Összesítve a projekt költségei:
- Claude Pro előfizetés (25.4 EUR ~ 9680 Ft) (melyet más dolgokra is használhatok persze a hónapban)
- Claude Pro intenzív használata (21.7 EUR ~ 8270 Ft)
- Claude API hívás (12.29 $ ~ 3970 Ft)
- szerver bérlése (3.49 EUR / hónap ~ 1330 Ft)
- web domain megvétele (2527 Ft  (1. évre) )

Összesen 25 777 Ft. 


## Szerzői gondolatok

Rendkívüli módon élveztem a munkát ezen a projekten. Dolgoztam itt-ott az elmúlt években mind scrape-elős, mind vizualizációs kódokkal, ezek tipikusan olyan pepecselős dolgok, hogy ha meg is van az ötlet, hogy mit szeretnék, az implementálás része nagyon hosszadalmas tudott lenni.

Az AI-val ez gyökeresen megváltozott: a fókusz végre az ötleteken lehet, nem az implementáció részletein. Ha megvan a fejemben, hogy pontosan mit szeretnék, onnantól már nem nehéz elérni.

Meglepően sokat tanultam közben. Ha volt valami, amit nem értettem, egyszerűen megkérdezhettem — könnyűvé vált az új tudáshoz való hozzájutás.

Korábban sokszor előfordult, hogy egy-egy technikai nehézség megakasztotta a projektet, különösen olyan területeken, amelyekhez nem értek (például weboldalak készítése). Most ezek nem jelentettek akadályt.

Külön öröm volt a vizualizációkon dolgozni, bogarászni a szervezetek között, olykor meglepődni az adatokon. És jó érzés, hogy valami értelmes dolgon dolgoztam — az oldal sok információt ad át, és mindenki számára elérhető lesz.

Jó volt látni, milyen sok jó ügy van az országban. Félek, az adónk maradék 99%-a nem hasznosul ilyen jól.

Összességében nagyon lelkesít, hogy ilyen gyorsan tudtam haladni, és remélem, hasonló hobbiprojekteknek is nekiülhetek a közeljövőben.

A filozofálásba való belemerülést nélkülözve: persze tudom, hogy nem csak jó dolgokat hoz a technikai fejlődés, és sok mindent felforgat. Rengeteg munkakör fog feleslegessé válni, ami komoly kérdéseket vet fel nekem is — mi lesz a hozzáadott értékem néhány éven belül? Hogy ez az oldal elkészülhessen, kellett az ötlet, kellett hogy a fejemben összeálljon a folyamat lépésenként, kellett hogy kitaláljam, milyen módon lenne érdekes vizualizálni ezeket az adatokat. Eltöltöttem vele néhány napot, és néha észre kellett vennem, hogy valami nem működik elsőre. Viszont nehéz nem arra gondolni, hogy a terület ilyen sebességű fejlődése mellett néhány éven belül akár az egész folyamat oda egyszerűsödhet, hogy ennyi utasítás elég lesz valamilyen jövőbeli modellnek:

*"Vizualizáld egy weboldalon minél részletesebben az SZJA 1%-os felajánlásokat."*

## A kategorizáláshoz használt prompt

Az alábbi szöveget kapta meg a Claude Haiku modell minden egyes szervezet-kötegnél. A `{categories_text}` helyére a kategóriák és leírásaik kerültek, az `{orgs_text}` helyére pedig a szervezetek adatai (név, székhely, célkitűzés).

```
Kategorizáld a magyar civil szervezeteket a céljuk ÉS székhelyük alapján.
Válassz PONTOSAN EGY kategóriát minden szervezethez a lenti lehetőségek közül.

FONTOS SZABÁLYOK:
- Olvasd el FIGYELMESEN minden kategória leírását
- A kategória leírásában a "FÓKUSZA" azt jelenti, hogy ez a FŐDOLOG,
  nem csak mellékesen foglalkoznak vele
- A "Használd, ha..." rész pontosan megmondja, mikor válaszd azt a kategóriát
- A "NEM ide tartozik" rész segít elkerülni a tévesztést
- Ha bizonytalan vagy, válaszd az "egyéb..." kategóriát
  a megfelelő főkategórián belül

{categories_text}

SZERVEZETEK:
{orgs_text}

VÁLASZ FORMÁTUM - csak számozott lista, minden sorban: szám. kategória
FONTOS: Csak a kategória NEVÉT írd, ne a szülő kategóriát!

Példa:
1. kutyák
2. budapesti gimnáziumok
3. hospice

A te válaszod:
```

A `{categories_text}` az alábbi kategóriákat és leírásaikat tartalmazta:

```
=== KULTURÁLIS SZERVEZETEK ===

• sajtó, média
  Használd ezt a címkét, ha a szervezet FÓKUSZA sajtó vagy média tevékenység.
  Ide tartozik: újságok, online hírportálok, magazinok, rádió, televízió,
  hírszolgáltatás, újságírás támogatása, média szabadság.

• vallás népszerűsítés
  Használd, ha a szervezet FÓKUSZA vallási értékek terjesztése.
  Ide tartozik: egyházi alapítványok, bibliai programok, hitéleti programok.

• etnikai szervezetek
  Használd, ha a szervezet FÓKUSZA etnikai, nemzeti kisebbségek, népcsoportok.
  Ide tartozik: roma, német, horvát, szerb nemzetiségi szervezetek, hagyományőrzés.

• művészeti szervezetek
  Használd, ha a szervezet FÓKUSZA művészet, kultúra.
  Ide tartozik: zenei együttesek, színházak, festészet, tánccsoportok, galériák.

• demokráciáért tevő szervezetek
  Használd, ha a szervezet FÓKUSZA demokrácia erősítése, civil társadalom fejlesztése.

• nőjogi szervezetek
  Használd, ha FÓKUSZA nők jogai, nők egyenlősége.

• nemi kisebbségek
  Használd, ha FÓKUSZA LMBTQ+ közösség jogai.

• egyéb jogvédő szervezetek
  Használd, ha jogvédő tevékenység, de nem nő- vagy LMBTQ-specifikus.

• egyéb kulturális szervezetek
  Használd, ha kulturális tevékenység, de egyik specifikus alkategóriába sem illik.

=== OKTATÁSI SZERVEZETEK ===

• budapesti gimnáziumok
• Budapesten kívüli gimnáziumok
• általános iskolák
• óvodák
• egyéb iskolák
  Ide tartozik: szakgimnáziumok, szakiskolák, kollégiumok, nemzetiségi iskolák.
• egyéb oktatási szervezetek
  Ide tartozik: tehetséggondozás, diákversenyek, ösztöndíjak, felnőttképzés.

=== ÁLLAT ÉS TERMÉSZETVÉDELEM ===

• környezet és természetvédelem
• kutyák
• macskák
• madarak
• egyéb konkrét állatok
• állatkertek
• egyéb állatvédelem

=== SZOCIÁLIS SZERVEZETEK ===

• rászorulók segítése
  Ide tartozik: étkeztetés, ruhaosztás, hajléktalan ellátás, szegénység elleni küzdelem.
• hátrányos helyzetű gyerekek támogatása
• gyermekvédelem
• családalapítást segítő szervezetek
• fogyatékkal élők segítése
• beteg emberek lelki és szociális támogatása
  Ide tartozik: hospice, palliatív ellátás, haldoklók kísérése.
• egyházhoz kötődő szociális szervezetek

=== KATASZTRÓFAVÉDELEM ===

• országos szervezetek
• helyi szervezetek
• önkéntes tűzoltó egyesületek

=== FELNŐTT EGÉSZSÉGÜGY ===

• kórházak
• női egészségügy
• daganatos betegek gyógyítása
• egyéb felnőtt egészségügy

=== GYERMEK EGÉSZSÉGÜGY ===

• gyermekkórházak
• beteg gyerekek lelki segítése
• koraszülöttek
• cukorbeteg gyerekek
• leukémiás és daganatos gyerekek
• konkrét beteg gyerekek
• egyéb gyermek egészségügy

=== SZABADIDŐS ÉS SPORTTEVÉKENYSÉGEK ===

• sportklubok
• vadásztársaságok
• horgászegyesületek
• kerékpáros szervezetek
• egyéb szabadidős szervezetek
```
