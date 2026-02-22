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
=== KULTÚRA ÉS MŰVÉSZET ===

• művészeti szervezetek
  Használd, ha a szervezet FÓKUSZA művészet, kultúra.
  Ide tartozik: zenei együttesek, színházak, festészet, tánccsoportok,
  kulturális rendezvények, művészeti oktatás, galériák, kiállítások.

• etnikai szervezetek
  Használd, ha a szervezet FÓKUSZA etnikai, nemzeti kisebbségek, népcsoportok.
  Ide tartozik: roma, német, horvát, szerb nemzetiségi szervezetek,
  hagyományőrzés, néptánc, népzenei csoportok, kisebbségi jogok.

• vallási szervezetek
  Használd, ha a szervezet FÓKUSZA vallási értékek terjesztése.
  Ide tartozik: egyházi alapítványok, bibliai programok, keresztény/zsidó/iszlám
  közösségek, hitéleti programok, lelkiségi fejlesztés.
  NEM ide tartozik: egyházi szociális tevékenység (azt szociális szervezeteknél jelöld).

• egyéb kulturális szervezetek
  Használd, ha kulturális tevékenység, de egyik specifikus alkategóriába sem illik.
  Ide tartozik: könyvtári támogatás, közösségi házak, kulturális örökség megőrzése,
  helytörténet, múzeumok támogatása.

=== EMBERI JOGOK ÉS CIVIL TÁRSADALOM ===

• sajtó, média
  Használd ezt a címkét, ha a szervezet FÓKUSZA sajtó vagy média tevékenység.
  Ide tartozik: újságok, online hírportálok, magazinok, rádió, televízió,
  hírszolgáltatás, újságírás támogatása, média szabadság.
  NEM ide tartozik: ha csak mellesleg írnak hírleveleket vagy van weboldaluk.
  Ide tartozik a Partizán.

• demokrácia és átláthatóság
  Használd, ha a szervezet FÓKUSZA demokrácia erősítése, civil társadalom fejlesztése.
  Ide tartozik: átláthatóság, anti-korrupció, választási megfigyelés,
  állampolgári részvétel, nyílt kormányzás, társadalmi párbeszéd.

• nőjogi szervezetek
  Használd, ha FÓKUSZA nők jogai, nők egyenlősége.
  Ide tartozik: női esélyegyenlőség, nők ellen irányuló erőszak megelőzése,
  anyák támogatása, női karrierfejlesztés, nők társadalmi szerepe.

• LMBTQ+ szervezetek
  Használd, ha FÓKUSZA LMBTQ+ közösség jogai.
  Ide tartozik: leszbikus, meleg, biszexuális, transznemű, queer közösségek,
  nemi identitás, szexuális orientáció alapú diszkrimináció elleni küzdelem.

• egyéb jogvédő szervezetek
  Használd, ha jogvédő tevékenység, de nem nő- vagy LMBTQ-specifikus.
  Ide tartozik: általános emberi jogi szervezetek, fogyasztóvédelem,
  munkavállalói jogok, bérlők jogai, menekültek jogai, emberi jogi monitoring.

=== OKTATÁS ===

• gimnáziumok
  Használd, ha GIMNÁZIUM támogató alapítvány/egyesület.
  Ide tartozik: budapesti és vidéki gimnáziumok baráti körei,
  támogató alapítványai, 4, 6 és 8 évfolyamos gimnáziumok.

• általános iskolák
  Használd, ha ÁLTALÁNOS ISKOLA (8 osztályos) támogató alapítvány/egyesület.
  Ide tartozik: alsó és felső tagozatos iskolák baráti körei, támogató alapítványai,
  1-8. osztályos oktatási intézmények.

• óvodák
  Használd, ha ÓVODA támogató alapítvány/egyesület.
  Ide tartozik: óvodák baráti körei, támogató alapítványai,
  óvodai fejlesztések, óvodai eszközök beszerzése, óvodai programok.

• egyéb iskolák
  Használd, ha EGYÉB OKTATÁSI INTÉZMÉNY (szakiskola, kollégium, stb.).
  Ide tartozik: szakgimnáziumok, szakiskolák, kollégiumok,
  nemzetiségi iskolák, művészeti iskolák támogató szervezetei.
  NEM ide tartozik: gimnáziumok, általános iskolák, óvodák.

• egyéb oktatási szervezetek
  Használd, ha oktatási célú, de NEM konkrét intézmény támogatója.
  Ide tartozik: tehetséggondozás, diákversenyek, ösztöndíjak, tanári továbbképzés,
  oktatási programok, tankönyvek, pedagógiai módszertan, felnőttképzés,
  nyelvoktatás, informatikai oktatás.

• tudományos kutatás
  Használd, ha FÓKUSZA tudományos kutatás, akadémiai tevékenység.
  Ide tartozik: kutatóintézetek támogatása, tudományos ösztöndíjak,
  egyetemi kutatási programok, tudománynépszerűsítés, tudományos konferenciák,
  természettudományos, társadalomtudományos, orvostudományi kutatás.
  NEM ide tartozik: közoktatási intézmények támogatása.

=== KÖRNYEZET- ÉS ÁLLATVÉDELEM ===

• környezet- és természetvédelem
  Használd, ha FÓKUSZA természetvédelem, környezetvédelem, ökológia.
  Ide tartozik: erdőtelepítés, klímavédelem, fenntarthatóság, biodiverzitás,
  vízvédelem, hulladékcsökkentés, zöld energia, természetvédelmi területek.
  NEM ide tartozik: csak állatvédelem (ha nincs természetvédelmi cél).

• kutyák
  Használd, ha FÓKUSZA kutyák védelme, mentése, gondozása.
  Ide tartozik: kutyamenhelyek, kóbor kutyák, terápiás kutyák,
  fajta-specifikus kutyamentés.

• macskák
  Használd, ha FÓKUSZA macskák védelme, mentése, gondozása.
  Ide tartozik: macskamenhelyek, kóbor macskák, cicamentés, ivartalanítási programok.

• madarak
  Használd, ha FÓKUSZA madarak védelme.
  Ide tartozik: madármentés, gólyák, ragadozó madarak, madárvédelem,
  madárgyűrűzés, költőhelyek védelme.

• más konkrét állatfajok
  Használd, ha FÓKUSZA EGYÉB KONKRÉT ÁLLATFAJ (nem kutya/macska/madár).
  Ide tartozik: lovak, nyulak, tengerimalacok, hörcsögök, vadállatok,
  egzotikus állatok, víziállatok, hüllők, sünik.

• állatkertek
  Használd, ha FÓKUSZA állatkert, vadaspark támogatása.
  Ide tartozik: állatkertekben és vadasparkokban élő állatok, állatkert fejlesztése,
  zoo oktatási programok.

• egyéb állatvédelem
  Használd, ha általános állatvédelem, de nem specifikus állatfaj.
  Ide tartozik: állatkínzás elleni küzdelem, állatjogi oktatás,
  állatotthonok (több faj), állatorvosi ellátás támogatása.
  Nem ide tartozik, ha főként kutyák védelmével foglalkoznak, ezesetben a kutyákhoz tartozzon.

=== SZOCIÁLIS SEGÍTSÉGNYÚJTÁS ===

• rászorulók segítése
  Használd, ha FÓKUSZA szegények, hajléktalanok, nélkülözők segítése.
  Ide tartozik: étkeztetés, ruhaosztás, téli segély, hajléktalan ellátás,
  szegénység elleni küzdelem, munkanélküliek segítése.

• hátrányos helyzetű gyerekek támogatása
  Használd, ha FÓKUSZA hátrányos helyzetű, rászoruló GYEREKEK.
  Ide tartozik: halmozottan hátrányos gyerekek, szegény családok gyermekei,
  tehetséggondozás hátrányos helyzetűeknek, iskolai felzárkóztatás,
  táborok rászoruló gyerekeknek.
  NEM ide tartozik: beteg gyerekek (azt egészségügynél jelöld).

• gyermekvédelem
  Használd, ha FÓKUSZA gyermekbántalmazás, gyermekvédelem, árva gyerekek.
  Ide tartozik: gyermekotthonok, nevelőszülők támogatása, veszélyeztetett gyerekek,
  családból kiemelt gyerekek, gyermekjogi védelem.

• családalapítást segítő szervezetek
  Használd, ha FÓKUSZA családalapítás, párkapcsolatok, házasság támogatása.
  Ide tartozik: házasságkötés elősegítése, gyermekvállalás támogatása,
  családtervezés, meddőség kezelése, örökbefogadás segítése, családi tanácsadás.

• fogyatékkal élők segítése
  Használd, ha FÓKUSZA fogyatékkal élők támogatása.
  Ide tartozik: vakok, süket emberek, mozgássérültek, értelmi fogyatékosok,
  autisták, Down-szindrómások, fogyatékos gyerekek és felnőttek,
  akadálymentesítés, speciális oktatás. Vakokkal kapcsolatban a vakvezető kutyák is IDE tartozik.

• idősek gondozása
  Használd, ha FÓKUSZA idős emberek segítése, gondozása.
  Ide tartozik: idősotthonok, nyugdíjas klubok, idősek nappali ellátása,
  magányos idősek látogatása, idősek étkeztetése, idősek házi gondozása,
  alzheimer-es betegek gondozása, demencia.

• beteg emberek lelki és szociális támogatása
  Használd, ha FÓKUSZA beteg FELNŐTTEK LELKI/SZOCIÁLIS segítése (nem orvosi).
  Ide tartozik: hospice, palliatív ellátás, haldoklók kísérése, gyógyíthatatlan betegek,
  hosszú távú betegek szociális támogatása, beteg felnőttek pszichés segítése,
  betegek családjainak támogatása, magányos betegek látogatása.
  NEM ide tartozik: orvosi/gyógyító tevékenység, beteg gyerekek lelki segítése
  (azt gyermek egészségügynél jelöld).

• egyházhoz kötődő szociális szervezetek
  Használd, ha EGYHÁZI szervezet szociális tevékenysége.
  Ide tartozik: Karitász, Máltai Szeretetszolgálat, egyházi szeretetotthonok,
  keresztény/zsidó/iszlám jótékonysági szervezetek.
  FONTOS: csak akkor, ha SZOCIÁLIS a fő tevékenység (nem vallási oktatás).

• mentális egészség és szenvedélybetegségek
  Használd, ha FÓKUSZA mentális egészség, pszichés betegségek, vagy szenvedélybetegségek.
  Ide tartozik: depresszió, szorongás, öngyilkosság megelőzés, pszichiátriai betegek,
  alkoholizmus, drogfüggőség, rehabilitáció, leszokás támogatás,
  drogprevenció, AA csoportok, terápiás közösségek.
  NEM ide tartozik: orvosi pszichiátria (azt egészségügynél jelöld).

• települési és közösségfejlesztés
  Használd, ha FÓKUSZA helyi település fejlesztése, közösségépítés.
  Ide tartozik: faluszépítés, városvédő egyesületek, helyi infrastruktúra fejlesztés,
  közösségi terek kialakítása, lokálpatrióta szervezetek, helyiérdekű szervezetek,
  lakóközösségek, civil fórumok, településfejlesztési alapítványok.
  NEM ide tartozik: kulturális örökségvédelem (azt kultúránál jelöld).

=== KATASZTRÓFAVÉDELEM ÉS KÖZBIZTONSÁG ===

• országos szervezetek
  Használd, ha ORSZÁGOS SZINTŰ katasztrófavédelmi/mentési szervezet.
  Ide tartozik: Magyar Vöröskereszt, országos mentőszervezetek,
  országos szintű katasztrófavédelmi alapítványok.

• helyi mentő szervezetek
  Használd, ha HELYI (városi/települési) mentési szervezet.
  Ide tartozik: városi/települési helyi mentő intézmények,
  települési katasztrófavédelmi egyesületek.

• tűzoltó egyesületek
  Használd, ha TŰZOLTÓ szervezet.
  Ide tartozik: önkéntes tűzoltó egyesületek, tűzoltó baráti körök,
  tűzvédelmi oktatás.

• speciális mentőszervezetek
  Használd, ha valamilyen szempontból speciális a mentés típusa.
  Ide tartozik: barlangi mentők, vízimentők, légimentők, kutató mentők,
  és minden olyan, amit a többi kategóriába nem besorolható.

=== FELNŐTT EGÉSZSÉGÜGY ===

• kórházak
  Használd, ha FELNŐTT KÓRHÁZ/KLINIKA támogató szervezet.
  Ide tartozik: felnőtt kórházak baráti körei, klinikák támogatói,
  kórházi osztályok fejlesztése (ha nem gyermekosztály).

• női egészségügy
  Használd, ha FÓKUSZA női egészség, nőgyógyászat.
  Ide tartozik: emlőrák szűrés, méhnyakrák megelőzés, szülészet,
  női reproduktív egészség, menopauza, terhesség.

• daganatos betegek gyógyítása
  Használd, ha FÓKUSZA FELNŐTT rákos/daganatos betegek gyógyítása.
  Ide tartozik: onkológia, kemoterápia, sugárterápia, rákos betegek támogatása,
  daganatos betegségek kutatása (felnőtteknél).
  NEM ide tartozik: gyerekek rákos megbetegedései.

• egyéb felnőtt egészségügy
  Használd, ha FELNŐTT egészségügy, de egyik specifikus alkategóriába sem illik.
  Ide tartozik: mentőszolgálat, sürgősségi ellátás, diabétesz (felnőtt),
  szív- érrendszer, tüdőbetegségek, idősek egészsége, rehabilitáció,
  oltási kampányok, egészséges életmód, betegségmegelőzés.

=== GYERMEK EGÉSZSÉGÜGY ===

• gyermekkórházak
  Használd, ha GYERMEKKÓRHÁZ/gyermekosztály támogató szervezet.
  Ide tartozik: gyermekkórházak baráti körei, gyermekosztályok fejlesztése,
  gyermekgyógyászati eszközök beszerzése.

• beteg gyerekek lelki segítése
  Használd, ha FÓKUSZA beteg gyerekek LELKI támogatása (nem orvosi kezelés).
  Ide tartozik: kórházi bohócdoktorok gyerekeknél, játszóházak kórházakban,
  beteg gyerekek pszichés támogatása, vigasztalás.

• koraszülöttek
  Használd, ha FÓKUSZA koraszülött/újszülött babák.
  Ide tartozik: koraszülött osztályok, incubatorok, perinatális ellátás,
  koraszülöttek utógondozása.

• cukorbeteg gyerekek
  Használd, ha FÓKUSZA cukorbeteg (diabétesz) GYEREKEK.
  Ide tartozik: 1-es típusú diabétesz gyerekeknél, inzulinellátás,
  diabéteszes gyermektáborok, vércukormérők.

• leukémiás és daganatos gyerekek
  Használd, ha FÓKUSZA rákos/leukémiás GYEREKEK.
  Ide tartozik: gyermekonkológia, leukémia, agydaganat gyerekeknél,
  kemoterápia gyerekeknél, rákos gyerekek családjainak támogatása.

• konkrét beteg gyerekek
  Használd, ha KONKRÉT BETEG GYERMEK nevére alapított alapítvány.
  Ide tartozik: "XY gyermek gyógyításáért", "XY emlékére" alapítványok,
  egyedi gyermek gyógykezelésének támogatása.
  Vannak olyan alapítványok, amik nevében egy konkrét gyermek neve szerepel,
  de a cél leírásában általános célt fogalmaznak meg.
  Ebben az esetben NEM IDE tartozik.

• egyéb gyermek egészségügy
  Használd, ha GYERMEK egészségügy, de egyik specifikus alkategóriába sem illik.
  Ide tartozik: gyermek szívbetegségek, ritka betegségek gyerekeknél,
  veleszületett rendellenességek, gyermek tüdőbetegségek, gyermek allergia,
  gyermek rehabilitáció, gyermek fogászat.

=== SPORT ÉS SZABADIDŐ ===

• sportklubok
  Használd, ha FÓKUSZA sport, sportegyesület, sportklub.
  Ide tartozik: futball, kosárlabda, kézilabda, úszás, atlétika, küzdősport,
  judo, karate, golf, tenisz, sportutánpótlás nevelés, sportversenyek.
  NEM ide tartozik: vadászat, horgászat, kerékpározás (azoknak külön van).

• vadásztársaságok
  Használd, ha FÓKUSZA vadászat.
  Ide tartozik: vadásztársaságok, vadgazdálkodás, lövészetek,
  vadászoktatás, vadvédelem vadászati szempontból.

• horgászegyesületek
  Használd, ha FÓKUSZA horgászat.
  Ide tartozik: horgászegyesületek, horgásztavak, horgászversenyek,
  horgászoktatás, halgazdálkodás.

• kerékpáros szervezetek
  Használd, ha FÓKUSZA kerékpározás illetve azzal való közlekedés.
  Ide tartozik: kerékpáros klubok, kerékpártúrák, kerékpárút-építés,
  biciklis közlekedés támogatása, Mountain bike, közlekedésbiztonság kerékpárosoknak.

• egyéb szabadidős szervezetek
  Használd, ha szabadidős/hobbi tevékenység, de egyik specifikus alkategóriába sem illik.
  Ide tartozik: túrázás, táborozás, cserkészet, közösségi programok,
  hobbiklubok, modellezés, sakkozás, bridzsezés, amatőr fotózás,
  gőzmozdony-helyreállítás, veterán autók.
```
