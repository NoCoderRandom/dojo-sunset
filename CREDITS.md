# Material och referenser

Dojo Sunset använder originalkod, originalgeometri, egna skelettanimationer
och en kombination av egna syntetiserade ljud, ett CC0-blockljud och lokalt
tillhandahållna ljudfiler. Inga C64-sprites, ROM-filer, originalmusik
eller andra resurser från International Karate ingår. Namnet International
Karate används endast för att beskriva inspirationen; spelet är fristående.

## Referens för klassiskt spelläge

Originalmanualen, återgiven av Lemon64 / Project 64:
https://www.lemon64.com/doc/international-karate/306

## Programmeringsbibliotek

- Pygame / SDL: https://www.pygame.org/docs/
- PyOpenGL: https://pyopengl.sourceforge.net/
- NumPy: https://numpy.org/
- DejaVu Sans: systemets installerade typsnitt.

## Ljudgranskning

Under utvecklingen granskades https://pixabay.com/sound-effects/search/karate/.
Granskade kandidatsidor: Karate Chop (6357), Power Punch (192118),
Blocking Arm With Hand (6941). Sidorna anger Pixabay Content License.
Själva filhämtningen gav HTTP 403 och webbläsaren visade en åtkomstkontroll.
Ingen direkt Pixabay-nedladdning användes. Två original hittades senare på Freesound, se nedan.

## CC0-ljud från grundversionen

Originalen bakom två av Pixabay-träffarna gick att nå via Freesound:

- **Blocking Arm With Hand**, mmasonghi, CC0 1.0.
  https://freesound.org/people/mmasonghi/sounds/321810/
  Offentlig HQ-preview från cdn.freesound.org; anslaget klippt till ett kort blockljud.
- **Karate Chop.m4a**, ccolbert70Eagles23, CC0 1.0 enligt källsidan.
  https://freesound.org/people/ccolbert70Eagles23/sounds/423526/
  Offentlig HQ-preview; två åtskilda transienter klippta till ett lätt och ett tungt träffljud.

Licens: https://creativecommons.org/publicdomain/zero/1.0/
Bearbetning: anslagsklippning, DC-korrigering, nivåjustering och kort in/uttoning.
Källkopior i assets/audio/source, exakta klipp och mätningar i assets/audio/audio-review.json.
Det importerade blockljudet används fortfarande. De tidigare lätta/tunga
träffklippen har ersatts av de användarlevererade filerna nedan; gamla original
och granskningsmanifest finns kvar för spårbarhet.
Ljudinmatning stöds inte av agentverktyget: ingen personlig provlyssning påstås.
Ljuden har tekniskt granskats för anslagstid, dubbla transienter, nivå och klippning.

## Åtta lokalt tillhandahållna ljud

Importerade från en privat lokal källmapp den 18 september 2026. Filnamnen och
beskrivningarna användes för att välja händelse. Dessa filer är inte märkta som
CC0; deras licens har inte verifierats separat. Spelets MIT-licens omfattar
inte automatiskt användarlevererade inspelningar.

| Färdig effekt | Användning |
|---|---|
| hit_chop.wav | Nunchaku- eller handflateträff |
| hit_light.wav | Lätt träff |
| hit_heavy.wav | Tung träff |
| round_swing.wav | Sparkens rörelse |
| miss.wav | Missad attack |
| nunchaku_spin.wav | Nunchakusving, separat från träff |
| kiai.wav | Lyckad spark |
| defeat.wav | Avgjord rond med en förlorare |

Originalkopior och manifest med ursprungliga filnamn behålls endast lokalt och
undantas uttryckligen från Git. `tools/import_user_audio.py` kan reproducera
bearbetningen med ffmpeg när de privata källfilerna finns tillgängliga.
De färdiga WAV-filerna är stereo, 44 100 Hz, PCM16 och förladdas vid spelstart.
Inledande tystnad har klippts bort, DC-offset korrigerats och nivåer samt
kort in/uttoning justerats. Anslaget ligger under 3 ms i de färdiga filerna;
detta beskriver filinnehållet, inte hela ljudsystemets latens.
Inga privata källfiler ändrades. Spelet är inte beroende av källmappen.

Nunchaku och kaststjärnor har egen modellerad geometri och egna animationer.
Inga externa vapenmodeller eller sprites har importerats.
