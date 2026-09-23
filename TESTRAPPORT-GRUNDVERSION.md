# Testprotokoll — Dojo Sunset

Slutkontroll 18 september 2026. Arbetet påbörjades 01:40 UTC och slutfördes
efter 07:54 UTC: mer än sex timmar. Spelet innehåller 3 777 Python-rader
(3 487 utan tomrader), räknat i dojo/, main.py och launcher.py, utan testkod.

## Godkända prov

| Område | Prov | Resultat |
|---|---|---|
| Spelregler, kontroller och lagring | 116 enhetstester | Alla godkända |
| Menyer och verklig OpenGL-bild | 33 steg med processlokala SDL-kontrollhändelser | Alla godkända |
| Teknikskola | Samtliga tolv lektioner genomförda med SDL-knapphändelser | Godkända |
| Helskärm | 20 växlingar 1920×1080 ↔ 1280×720 | Rätt storlek; bevarad GL-kontext; minne 150,83 → 150,91 MB |
| Fönsterfokus | Elva prov med ett riktigt andra SDL-fönster | Paus, tystnad, ignorerad bakgrundsinmatning och säker återkomst fungerar |
| AI och matchregler | 3 600 seedade matcher vid 120 Hz med symmetrisk AI-klockning | Alla avslutade |
| Skrivbordsstart | Riktiga start.sh med separat testdata samt dubbelstart | Ren avslutning; andra spelinstansen förhindras |
| Långspel | 3,5 timmar i helskärm med verklig grafik | Hela tiden genomförd; processens exitkod 0 |
| Ljudfiler | Format, anslag, nivå, klippning och förladdning | Korta PCM-effekter; ingen klippning |
| Retroinstallation | SHA-256 för 1 406 befintliga konfigurationsfiler | Samtliga oförändrade vid slutkontrollen |

## Slutligt långtidsprov

Körningen varade **12 600,02 sekunder**, utan avbrott, och ritade 753 673 bilder.
Den genomförde **230 matcher, 46 kontrollåteranslutningar och 76 arenabyten**.
Regler, svårighetsgrad och arena växlades under körningen. Sparning användes i
en privat temporär katalog. Testet stannar om ett annat program tar fokus.

- Median för bildfrekvensens mätperioder: **59,9 fps**. Lägsta period: 58,9 fps.
- Inga OpenGL-fel eller överträdelser av kontrollerade spelgränser registrerades.
- Minnet växte från 155,56 MB när resurser värmdes upp till som mest 164,98 MB.
  Slutvärdet var 164,66 MB. Två automatiska textcachetömningar observerades;
  utrymmet återanvändes under följande uppbyggnad.
- Antalet öppna filbeskrivare var konstant: 43 i samtliga mätningar.
- Högsta uppmätta temperatur: 67,75 °C. Pi-status efter provet: throttled=0x0.
- 113 bilder tog mer än 50 ms, av totalt 753 673. Den längsta var 474 ms.
  Korta pauser förekommer bland annat vid start, kontrollbyten och skärmbildssparning;
  resultatet ska inte tolkas som att varje bild tog exakt 16,7 ms.
- Ingen spelkod ändrades under körningen. Alla 25 registrerade källhashar matchade
  leveransmappen vid slutkontrollen.
- Barnprocessen avslutades med **0**; även själva avslutningen är alltså verifierad.

Grafikprov kördes på Raspberry Pi 5, V3D 7.1.7.0, med 4× MSAA.
En sen skärmbild från provet granskades också: hälsomätare, figurer och knapphjälp
visades korrekt. Testspelet är nu stängt.

## Fel som hittades och rättades

- Menyknappar kunde orsaka oavsiktliga attacker efter en skärmväxling.
- Korta attacktryck kunde försvinna under slutet av återhämtningen.
- Helskärmsväxling kunde lämna fel fönsterstorlek och öka grafikminnet.
- Figurers hukstatus och synliga position kunde skilja sig åt.
- Låga attacker kunde undvikas innan ett hopp faktiskt lämnat marken.
- Nedslagna figurer kunde träffas innan de rest sig.
- Rekyl under poängpausen kunde föra en figur utanför mattan.
- Felaktiga försök i teknikskolan kunde skapa för stort avstånd för ett nytt försök.
- Bakgrundsinmatning kunde påverka spelet efter byte till ett annat fönster.
- Trasig sparfil kunde hindra fortsatt sparning.
- Rekordtabellen visade inte alla tio sparade rader.

## Praktiska begränsningar

Xbox Series X-kontrollen identifierades av SDL när den var ansluten. Automatiska
knapp- och återanslutningsprov använder SDL:s virtuella kontroll **inne i processen**.
Inga Linux uinput-enheter eller globala kontrollmappningar skapades. Den fysiska
kontrollens känsla och vibration behöver fortfarande bedömas av en människa.
SPEEDLINK-enheterna låg kvar som js0/js1 vid slutkontrollen.

Verktyget kunde inte ta emot ljud för personlig provlyssning. Ljudgranskningen är
teknisk. De tre bearbetade inspelade effekterna är 98–300 ms långa, med anslag
inom 1,2 ms och utan klippning. Filanslag är inte ett mått på hela ljudkedjans
latens. Långprovet var tystat; mixern och ljudhändelserna kördes ändå.
Kontrolltestet låter dig lyssna separat med X, Y, LB och RB. Licenser och
källor finns i CREDITS.md.

## Spårbarhet och ren användardata

Rådata och bilder finns i userdata/. Viktiga rapporter:

- unit-tests.log
- candidate-validation/integration/report.json
- candidate-validation/display-test/report.json
- candidate-validation/focus-test/report.json
- candidate-validation/balance-candidate-v5-fair.json
- launcher-test.json
- soak-final-210min/report.json, process.json och source-hashes.json
- retro-config-check.json

Äldre rapporter är sparade för felsökning. soak-second-2h och soak-third-2h
avbröts avsiktligt efter cirka åtta respektive 63 minuter och räknas inte som
fulla tvåtimmarsprov. Det första 30-minutersprovet skrev sin rapport men gav
signalstatus 143 efteråt; dess rena avslutning kunde inte styrkas. Slutprovet
ovan använder en wrapper som separat registrerar processens riktiga exitkod.

Alla testprocesser är avslutade. Inga provrekord eller testinställningar har
lagts i spelarens riktiga records.json/settings.json; de skapas när du spelar.
