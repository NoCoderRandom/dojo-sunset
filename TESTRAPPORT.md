# Testprotokoll — karate, ninja och sumo

Utbyggnaden startade 18 september 2026 kl.11:41:16 UTC / 13:41:16 svensk tid.
Projektets slutliga långprov dokumenteras nedan.
Grundversionens tester finns i [TESTRAPPORT-GRUNDVERSION.md](TESTRAPPORT-GRUNDVERSION.md).
Dess 3,5-timmarsprov och 3 600 matcher gäller grundversionen, inte de nya ninjorna.

## Verifierat i utbyggnaden

| Område | Prov | Resultat |
|---|---|---|
| Regler, kontroller, lagring och ljud | 146 enhetstester | Godkända |
| Befintliga menyflöden | 33 SDL/OpenGL-kontrollprov | Godkända |
| Ninja, sumo och karateresa | 80 nya SDL/OpenGL-kontrollprov | Godkända |
| Motståndare och svårighetsgrader | 3 600 matcher, nya seedar, 120 Hz | Alla avslutade; inga kontrollerade spelgränser överträdda |
| Animation och vapen | 13 OpenGL-poseprov, sex kapitel och hjälpsida | Inga GL-fel; utvalda bilder visuellt granskade |
| Åtta användarljud | Originalhashar, PCM-format, anslag, nivå och förladdning | Godkända; anslag under 3 ms, ingen klippning i filerna |
| Grafikstabilitet | 151 minuter med alla tre motståndartyper; separat fortsättning pågår | 129 matcher, inga registrerade spel-/GL-fel; avsiktligt fokusstopp |
| Verklig mixad ljudutdata | SDL-diskmixer, maxvolym, samtidiga effekter | Godkänt: ingen klippning, topp −1,05 dBFS |
| Retroinstallation | Mellankontroll av 1 406 konfigurationer | Samtliga oförändrade |

Spelkoden omfattar 4 244 Python-rader i dojo/, main.py och launcher.py,
utan testverktygen. Grafik och kod är egen; ljudkällorna finns i CREDITS.md.

## Nya kontrollfall

Spelaren kan inte starta vapen- eller sumoattacker. Karateresan har två karate-,
två ninja- och två sumomatcher. Stjärnorna har flygtid, livslängd, ammunition och
kastpaus. Hukning, blockering, undanmanöver och avbrutet kast testas, liksom att
projektilerna försvinner mellan ronder. Träningen fyller på övningsstjärnor;
vanliga matcher behåller gränsen fyra per rond.

Nunchakuns höga slag kan undvikas med hukning; den låga svepningen kräver lågt
block eller hopp. Kaststjärnor kräver en passiv spelare som inte närmar sig.
Sumon är långsammare, tål mer och trycks undan mindre. Stampen kan hoppas över.
Roundkick återgår genom böjt knä. Samtliga nya poser och vapensegment har
ändliga koordinater.

De grafiska proven använder processlokal SDL-kontroll och riktig OpenGL:
träningsval, B-roundkick, ner+B-legsweep, AI av/på, pausad stjärna, hjälpsidor,
ljudprov, alla sex resultatövergångar och sparning. Resultat injiceras i
övergångsproven för att testa menyer/sparning; de är inte påstådda mänskliga
segrar. Testerna sparar i temporära kataloger.

## Balansmatris

Två motståndartyper, alla nio kombinationer av spelar-/motståndar-AI på tre
nivåer, med/utan särskilda försvar, 100 seedar per kombination: 3 600 matcher.
Seedarna 1 000–1 099 skiljer sig från det första 240-matchersprovet. Spelar-AI
har begränsad reaktionstid och uppdateras bara under aktiv strid. Ingen match
blev oavslutad vid gränsen 300 simulerade sekunder.

Med spelar-AI på medelnivå och särskilda försvar blev vinsterna 100/98/97 av
100 mot ninja på lätt/medel/svår nivå, och 96/91/83 mot sumo. Utan extra
försvar: 80/83/60 respektive 76/67/63. Detta visar användbara motmedel;
AI-resultaten mäter inte mänsklig spelglädje eller upplevd svårighet.

## Ljudgranskning

Åtta privata original och deras SHA-256-manifest bevaras endast lokalt. Spelet
förladdar PCM16 i 44 100 Hz stereo. Karatehugget är klippt till ett slag,
cirka 114 ms, och roundkick till ett svep, cirka 103 ms. Toppar vid cirka 22/25 ms.
Övriga effekter är 310–1561 ms. Röst och nunchaku har egna mixerkanaler,
träffar får separata slagljud och avbruten nunchaku tonas ut.

Personlig provlyssning stöds inte av verktyget. Korta filanslag mäter inte
hela ljudsystemets latens. Mixerprovet fångar verklig SDL-utdata till en privat
fil och mäter digital klippning; diskdrivrutinens klockning skiljer sig från
ett fysiskt ljudkort. Slutprovet fångade 262,54 sekunder PCM vid maxvolym, med topp −1,05 dBFS och noll klippta kanalsampel. Ljuden kan provlyssnas separat i kontrolltestet.

## Långprov och spårbarhet

specialist-soak-260min körde verklig grafik och mixer, tystat, med separat
sparplats. Motståndare, regler, svårighetsgrad, arena och kontroll växlas.
Spelarroll, ammunition, projektiler, hälsa, uthållighet och arenagränser
kontrolleras. En wrapper registrerar processens exitkod. Python-källor och
alla färdiga WAV-filer har hashats vid start.

Provet stannade korrekt när användaren bytte fönster efter 9 067,56 sekunder
(cirka 151 minuter). Det är inte ett färdigt 260-minutersprov trots katalognamnet.
129 matcher (43 av varje typ), 25 återanslutningar och 43 arenabyten hanns med.
Inga registrerade spel-/GL-fel, processens exitkod 0. Median 59,9 fps,
RSS 155,81→165,81 MB, högst 166,02 MB, 43 filbeskrivare genom hela provet.
Alla 41 kod-/ljudhashar stämde efter avslut.

Användaren gav därefter klartecken till fortsatt grafiktest på skärmen.
Ett separat 105-minutersprov startade 14:58:07 UTC i
specialist-soak-resumed-105min. Det pågår; resultat återstår. Körningarna
redovisas separat eftersom den första avbröts vid fokusförlust.

Fortsättningen höll median 59,86 fps under de första drygt 30 minuterna,
med 26 matcher och inga GL-fel. Cirka 31,5 minuter in blev HDMI-A-1
inaktiverad i skrivbordsmiljön (wlr-randr: enabled=false; sysfs: disabled,
DPMS Off). Därefter gick processen ner till cirka 1 fps men fortsatte leva.
Denna period är **inte normal grafikprestanda med TV-bild**. Ingen permanent
skärmprofil ändrades; en dryrun av befintligt 1080p/60-läge misslyckades.
Händelsen finns i hdmi-disabled-event.json och hdmi-kernel-observation.log.
Slutresultatet och eventuell återgång när bilden kommer tillbaka återstår.


Första specialist-soak-final avbröts avsiktligt efter 341 sekunder för kortare
ljudklipp och räknas inte som ett komplett långprov. Första audio-mix-probe
använde äldre förladdade ljud; audio-mix-final provar de nya. Kandidatdata
finns kvar för felsökning.

Rapporter i userdata/:

- specialist-tests-fourth.log
- integration/report.json och specialist-integration/report.json
- ninja-gallery/report.json och skärmbilder
- specialist-matrix.json
- audio-mix-final/report.json
- specialist-soak-260min/report.json, process.json och source-hashes.json
- specialist-soak-resumed-105min/report.json, process.json och source-hashes.json
- player-save-preservation.json

En befintlig lokal rekordfil, skapad före förbättringsomgången, bevaras.
Testerna skapar inga globala inputprofiler, udev-regler eller retroinställningar.
Fysisk Xbox-känsla och vibration behöver fortfarande bedömas av spelaren.


## 22 september 2026 — Xbox för en eller två spelare

- Nya menyval för två spelare, poängmatch och hälsoduell, med separat klarskärm.
- Stabil tilldelning av två Xbox-kontroller inom SDL-processen, separata inputbuffertar,
  paus/återanslutning, vinnare för båda spelarna och rematch. CPU-lägen bevarade.
- Endast Xbox styr spelet; tangentbordets spelbindningar borttagna. F10/F11 är verktyg.
- 8 nya riktade tester och 22 befintliga kontroll-/CPU-kontroller godkända; ruff och
  diff-kontroll godkända. Menyer renderade och granskade. Inga långtester.
- 1 407 befintliga retro-/systemkonfigurationer och spelarrekord oförändrade enligt
  userdata/two-player-verification.json. Alla skrivningar inom spelmappen.
- Kvar för användarprov: två fysiska Xbox-kontroller över Bluetooth och faktisk spelbild.
- Äldre shutdown-fix finns kvar: sparade rapporter visar 8/8 godkända fall och exit 0
  efter sista korta provet. Ingen ny långkörning gjord för den historiska ändringen.


## 22 september — Elite Series 2 över Bluetooth

Fysisk kontroll 045e:0b22 / version 0513 var ansluten men saknade
ID_INPUT_JOYSTICK; udev klassade den som tangentbord. SDL räknade upp
SPEEDLINK ×2 och vanliga Xbox, men inte Elite. Ny dojo/elite_input.py läser
endast denna Elite-modells befintliga evdev-enhet med O_RDONLY, utan grab,
udev-regler, inputenheter, Bluetooth-ändringar eller globala mappningar.
Saknade kontroller söks igen varje sekund; SDL-kontroller har företräde.
Vibration stöds inte på reservvägen. Klarskärmen visar kontrollens namn.

Verifierat på verkliga anslutna enheter: spelare 1 Xbox Series X Controller,
spelare 2 Xbox Elite Series 2 (Bluetooth), neutrala spakar/triggers, ren exit.
9 korta tvåspelartester godkända, inklusive ny blandad SDL/Elite-regression
för A på klarskärmen, separat X-attack, triggers och paus vid bortkoppling.
Ruff och diff-kontroll godkända. Inga långtester eller systemändringar.
Fysiska knapptryckningar återstår att prova i spelet efter omstart.
