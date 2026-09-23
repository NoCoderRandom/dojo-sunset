"""Readable, controller-first Swedish UI at a fixed 1280×720 design size."""
import math

import pygame

from .competition import ARCHETYPE_NAMES, OPPONENT_HINTS
from .scenery import PALETTES

INK = (14, 22, 32)
PAPER = (239, 234, 216)
MUTED = (166, 184, 187)
GOLD = (232, 188, 112)
TEAL = (100, 210, 185)
RED = (222, 103, 100)
BLUE = (97, 172, 224)


class UI:
    def __init__(self):
        pygame.font.init()
        self.surface = pygame.Surface((1280, 720), pygame.SRCALPHA)
        self.fonts = {}
        self.cache = {}
        self.toast = ''
        self.toast_time = 0.0
        self.elapsed = 0.0
        for size in (14, 16, 18, 20, 22, 24, 28, 32, 40, 48, 64, 78):
            self.fonts[(size, False)] = pygame.font.SysFont('DejaVu Sans', size)
            self.fonts[(size, True)] = pygame.font.SysFont('DejaVu Sans', size, bold=True)

    def font(self, size, bold=False):
        key = (size, bold)
        if key not in self.fonts:
            self.fonts[key] = pygame.font.SysFont('DejaVu Sans', size, bold=bold)
        return self.fonts[key]

    def text(self, text, x, y, size=20, color=PAPER, bold=False, anchor='left'):
        text = str(text)
        key = (text, size, color, bold)
        if key not in self.cache:
            if len(self.cache) > 700:
                self.cache.clear()
            self.cache[key] = self.font(size, bold).render(text, True, color)
        image = self.cache[key]
        rect = image.get_rect()
        if anchor == 'center':
            rect.midtop = (x, y)
        elif anchor == 'right':
            rect.topright = (x, y)
        else:
            rect.topleft = (x, y)
        self.surface.blit(image, rect)
        return rect

    def panel(self, rect, alpha=225, border=False):
        pygame.draw.rect(self.surface, (*INK, alpha), rect, border_radius=14)
        if border:
            pygame.draw.rect(self.surface, (*GOLD, 120), rect, width=1, border_radius=14)

    def line(self, x1, y1, x2, y2, color=GOLD, width=1):
        pygame.draw.line(self.surface, color, (x1, y1), (x2, y2), width)

    def button(self, label, x, y, color=TEAL, small=False):
        radius = 13 if small else 16
        pygame.draw.circle(self.surface, color, (x, y), radius)
        self.text(label, x, y - (10 if small else 12), 14 if small else 16,
                  INK, True, 'center')

    def pill(self, text, x, y, color=GOLD):
        width = self.font(14, True).size(text)[0] + 22
        pygame.draw.rect(self.surface, (*color, 28), (x, y, width, 27), border_radius=6)
        self.text(text, x + 11, y + 4, 14, color, True)
        return width

    def notify(self, text, seconds=3):
        self.toast = text
        self.toast_time = seconds

    def begin(self, dt):
        self.surface.fill((0, 0, 0, 0))
        self.elapsed += dt
        self.toast_time = max(0, self.toast_time - dt)

    def finish(self):
        if self.toast_time > 0:
            width = min(1140, self.font(18).size(self.toast)[0] + 48)
            self.panel((640 - width // 2, 606, width, 48), 245, True)
            self.text(self.toast, 640, 617, 18, PAPER, anchor='center')
        return self.surface

    def footer(self, left='A  Välj', right='B  Tillbaka'):
        self.panel((40, 668, 1200, 34), 185)
        self.text(left, 58, 675, 14, MUTED)
        self.text(right, 1222, 675, 14, MUTED, anchor='right')

    def connection(self, controls, x=50, y=34):
        connected = bool(controls.pad)
        pygame.draw.circle(self.surface, TEAL if connected else GOLD, (x + 5, y + 9), 4)
        name = 'XBOX ANSLUTEN' if connected else 'ANSLUT EN XBOX-KONTROLL'
        if len(name) > 39:
            name = name[:36] + '...'
        self.text(name, x + 18, y, 14, MUTED)

    def menu(self, entries, selected, x, y, width=340, row_height=48):
        for index, label in enumerate(entries):
            row_y = y + index * row_height
            if index == selected:
                pygame.draw.rect(self.surface, (*GOLD, 230),
                                 (x, row_y, width, row_height - 6), border_radius=8)
                self.text(label, x + 20, row_y + 8, 20, INK, True)
                self.text('›', x + width - 24, row_y + 3, 28, INK, True, 'right')
            else:
                self.text(label, x + 20, row_y + 8, 20, PAPER)

    def title(self, controls, storage, entries, selected):
        self.panel((32, 24, 435, 622), 224)
        self.connection(controls, 57, 44)
        self.pill('ORIGINAL 3D-KARATE', 57, 89)
        self.text('DOJO', 54, 132, 78, PAPER, True)
        self.text('SUNSET', 56, 214, 64, GOLD, True)
        self.line(59, 297, 410, 297, (*GOLD, 125))
        self.text('KARATE  /  TIMING  /  PRECISION', 59, 312, 14, MUTED)
        self.menu(entries, selected, 53, 353, 390, 45)
        self.text(f'PERSONBÄSTA   {storage.best_score:06d}', 60, 611, 14, GOLD, True)
        self.panel((820, 46, 407, 75), 165)
        self.text('KLASSISK KÄNSLA. EN NY ARENA.', 1024, 61, 16, PAPER, True, 'center')
        self.text('Karate • Ninja • Sumo', 1024, 89, 14, MUTED, anchor='center')
        self.footer('Styrspak / styrkors: välj     A: starta',
                    'Start: tillbaka     F11: helskärm')

    def health_bar(self, fighter, x, y, width, mirrored=False):
        self.text(fighter.name, x + width if mirrored else x, y - 32, 24,
                  PAPER, True, 'right' if mirrored else 'left')
        pygame.draw.rect(self.surface, (30, 37, 42, 235), (x, y, width, 24), border_radius=4)
        filled = int(width * fighter.health / 100)
        bar_color = TEAL if fighter.health > 30 else RED
        if filled:
            left = x + width - filled if mirrored else x
            pygame.draw.rect(self.surface, bar_color, (left, y, filled, 24), border_radius=4)
        for step in range(1, 10):
            self.line(x + width * step / 10, y + 2, x + width * step / 10, y + 22, (17, 33, 35, 80))
        pygame.draw.rect(self.surface, (30, 37, 42, 225), (x, y + 31, width, 6), border_radius=2)
        stamina_width = int(width * fighter.stamina / 100)
        left = x + width - stamina_width if mirrored else x
        if stamina_width:
            pygame.draw.rect(self.surface, GOLD, (left, y + 31, stamina_width, 6), border_radius=2)
        self.text(f'{fighter.score:06d}', x + width if mirrored else x, y + 44,
                  18, GOLD, True, 'right' if mirrored else 'left')
        for win in range(2):
            dot_x = x + 12 + win * 24 if mirrored else x + width - 12 - win * 24
            pygame.draw.circle(self.surface, GOLD if win < fighter.wins else (76, 86, 87),
                               (dot_x, y + 55), 7)

    def point_bar(self, fighter, points, x, y, width, mirrored=False):
        self.text(fighter.name, x + width if mirrored else x, y - 32, 24,
                  PAPER, True, 'right' if mirrored else 'left')
        for index in range(4):
            cx = x + width - 20 - index * 48 if mirrored else x + 20 + index * 48
            pygame.draw.circle(self.surface, GOLD if index < points else (51, 64, 70),
                               (cx, y + 11), 14)
            if index < points:
                pygame.draw.circle(self.surface, PAPER, (cx - 4, y + 7), 3)
        self.text('2 POÄNG', x if mirrored else x + width, y + 2, 14, MUTED,
                  anchor='left' if mirrored else 'right')
        pygame.draw.rect(self.surface, (35, 44, 48, 230), (x, y + 31, width, 6), border_radius=2)
        filled = int(width * fighter.stamina / 100)
        left = x + width - filled if mirrored else x
        pygame.draw.rect(self.surface, GOLD, (left, y + 31, filled, 6), border_radius=2)
        self.text(f'{fighter.score:06d}', x + width if mirrored else x, y + 44,
                  18, GOLD, True, 'right' if mirrored else 'left')
        for win in range(2):
            cx = x + 12 + win * 24 if mirrored else x + width - 12 - win * 24
            pygame.draw.circle(self.surface, GOLD if win < fighter.wins else (76, 86, 87),
                               (cx, y + 55), 7)

    def hud(self, match, controls):
        self.panel((28, 20, 1224, 139), 194)
        classic = getattr(match, 'rules', '') == 'classic'
        if classic:
            self.point_bar(match.player, match.player_points, 52, 65, 438)
            self.point_bar(match.enemy, match.enemy_points, 790, 65, 438, True)
        else:
            self.health_bar(match.player, 52, 65, 438)
            self.health_bar(match.enemy, 790, 65, 438, True)
        self.text('TRÄNING' if match.practice else f'ROND {match.round}', 640, 32, 14, GOLD, True, 'center')
        clock_text = '∞' if match.practice else f'{math.ceil(match.remaining):02d}'
        self.text(clock_text, 640, 51, 48, PAPER, True, 'center')
        self.text('BÄST AV TRE' if not match.practice else 'FRIA FÖRSÖK', 640, 116, 12, MUTED, anchor='center')
        self.panel((28, 620, 1224, 82), 214)
        actions = [('X', 'SLAG', BLUE), ('Y', 'RAKT SLAG', GOLD),
                   ('A', 'FRONTSPARK', TEAL), ('B', 'KULLERBYTTA', RED)]
        x = 50
        for button, label, tint in actions:
            self.button(button, x + 15, 643, tint, True)
            self.text(label, x + 36, 633, 14, PAPER)
            x += 193
        self.text('LB  BLOCK     RB  RUNDSPARK', 845, 633, 14, PAPER)
        self.text('Ner + B / RB: LEGSWEEP     Upp + B: HÖG SPARK     RT: HOPPSPARK',
                  50, 674, 14, MUTED)
        self.text('Start: paus', 1225, 674, 14, MUTED, anchor='right')
        if match.practice:
            mode = 'AI PÅ' if match.practice_ai else 'STILLA MOTSTÅNDARE'
            self.pill('BACK: ' + mode, 43, 172, TEAL)
        if match.enemy.archetype == 'ninja':
            self.pill(f'NINJA • {match.enemy.stars} KASTSTJÄRNOR', 915, 171, BLUE)
            if match.practice:
                self.text('Fylls på i träning', 1090, 204, 12, MUTED, anchor='center')
        elif match.enemy.archetype == 'sumo':
            self.pill('SUMO • TUNG OCH STARK', 931, 171, GOLD)
        if match.phase == 'intro':
            title = f'KARATE MOT {ARCHETYPE_NAMES[match.enemy.archetype]}'
            self.banner('HAJIME' if match.phase_time < .85 else title,
                        OPPONENT_HINTS[match.enemy.archetype])
        elif match.phase == 'point':
            self.banner(match.point_message, match.point_winner.name + '  /  ' + match.point_technique, compact=True)
        elif match.phase == 'round_over':
            self.banner(match.result, 'En ren träff börjar med rätt timing.')
        elif match.player.stamina < 18:
            self.text('ÅTERHÄMTA DIG — LÅG UTHÅLLIGHET', 640, 187, 18, GOLD, True, 'center')
        elif match.player.combo > 1 and match.elapsed - match.player.last_hit < 1.4:
            self.text(f'{match.player.combo} TRÄFFAR I FÖLJD', 640, 187, 24, GOLD, True, 'center')
        if match.phase == 'fight':
            self.text(match.last_technique, 640, 581, 18, PAPER, True, 'center')
            enemy = match.enemy
            if enemy.attacking and enemy.elapsed < enemy.move.startup:
                warnings = {'shuriken': 'KASTSTJÄRNA — HUKA ELLER BLOCKERA',
                            'nunchaku': 'NUNCHAKU — HUKA ELLER BLOCKERA',
                            'sumo_stomp': 'STAMP — HOPPA ELLER BLOCKERA LÅGT',
                            'sumo_charge': 'RUSNING — BACKA ELLER UNDVIK'}
                warning = warnings.get(enemy.move_key)
                if warning:
                    self.panel((375, 546, 530, 30), 210)
                    self.text(warning, 640, 552, 16, GOLD, True, 'center')

    def banner(self, title, subtitle, compact=False):
        size = 28 if compact else 40
        top = 163 if compact else 249
        height = 82 if compact else 128
        width = min(1160, max(560, self.font(size, True).size(title)[0] + 70))
        self.panel((640 - width // 2, top, width, height), 220, True)
        self.text(title, 640, top + 14, size, GOLD, True, 'center')
        self.text(subtitle, 640, top + (57 if compact else 80),
                  16 if compact else 18, PAPER, anchor='center')

    def impact_labels(self, match, renderer):
        if getattr(match, 'rules', '') == 'classic':
            return
        for impact in match.impacts:
            age = .65 - impact.life
            x, y = renderer.project(impact.x, impact.y + .20 + age * .7, .38)
            tint = BLUE if impact.kind == 'block' else GOLD
            self.text(impact.text, int(x), int(y), 20, tint, True, 'center')

    def page(self, title, subtitle=''):
        self.panel((74, 36, 1132, 607), 240, True)
        self.text(title, 111, 67, 40, GOLD, True)
        if subtitle:
            self.text(subtitle, 113, 123, 18, MUTED)
        self.line(113, 162, 1166, 162, (*GOLD, 100))

    def pause(self, entries, selected):
        self.panel((0, 0, 1280, 720), 85)
        self.panel((414, 138, 452, 445), 242, True)
        self.text('PAUS', 640, 165, 48, GOLD, True, 'center')
        self.text('Andas. Hitta rytmen.', 640, 229, 18, MUTED, anchor='center')
        self.menu(entries, selected, 438, 283, 404, 51)
        self.footer('A: välj', 'B / Start: fortsätt')

    def help(self, page):
        if page == 0:
            self.page('DIN XBOX-KONTROLL', 'Alla menyer går att styra utan tangentbord.')
            rows = [
                ('Vänster spak / styrkors', 'Rör dig. Ner: huka. Upp: hoppa.'),
                ('X', 'Snabbt slag. Ner + X eller Y: hukslag.'),
                ('Y', 'Kraftigt rakt slag — gyaku zuki'),
                ('A', 'Frontspark — mae geri. Ner + A: låg spark.'),
                ('B', 'Kullerbytta framåt — snabb undanmanöver'),
                ('Upp + B', 'Hög spark — jodan geri'),
                ('Ner + B eller Ner + RB', 'Legsweep — ashi barai'),
                ('RB / RT', 'RB: roterande rundspark. RT: hoppspark.'),
                ('LB / LT', 'LB: blockera. Ner + LB: lågt block. LT: undanmanöver.'),
                ('Start / Back', 'Start: paus. Back: växla träningsmotståndarens AI.'),
            ]
            for index, (button, description) in enumerate(rows):
                y = 187 + index * 40
                self.text(button, 114, y, 16, GOLD, True)
                self.text(description, 418, y, 16, PAPER)
        elif page == 1:
            self.page('LÄR DIG DOJON', 'Räckvidd och återhämtning avgör vem som träffar först.')
            tips = [
                ('01  HITTA AVSTÅNDET', 'Slag når kortare än sparkar. Gå in för ett slag och backa ut igen.'),
                ('02  SE DIN ÖPPNING', 'En missad spark lämnar motståndaren öppen under återhämtningen.'),
                ('03  SKYDDA RÄTT HÖJD', 'Stående block stoppar högt och mitt. Huka + block skyddar benen.'),
                ('04  SPARA UTHÅLLIGHET', 'Den gula mätaren behövs för attacker, block och undanmanövrer.'),
                ('05  KLASSISK POÄNGKARATE', 'Två poäng vinner ronden. Två ronder ger seger. Varje rond varar 30 sekunder.'),
                ('06  TRÄNA UTAN PRESS', 'Träningsläget saknar tidsgräns. Back växlar mellan stilla och aktiv AI.'),
            ]
            for index, (heading, body) in enumerate(tips):
                y = 188 + index * 62
                self.text(heading, 114, y, 18, GOLD, True)
                self.text(body, 114, y + 28, 16, PAPER)
            self.text('2 spelare: välj poängmatch eller hälsoduell under Spela match.',
                      114, 575, 15, MUTED)
            self.text('Tryck A på varsin kontroll. Håll båda små SPEEDLINK-knapparna för paus.',
                      114, 600, 15, MUTED)
        else:
            self.page('KARATE • NINJA • SUMO', 'Bruce Pi är obeväpnad. Bara ninjan bär vapen.')
            tips = [
                ('ETAPP 1–2: KARATE', 'Klassiska poängmatcher. Två hela poäng vinner en rond.'),
                ('ETAPP 3–4: NINJA', 'Hälsoduell. Huka under nunchaku och stjärnor, eller håll LB.'),
                ('FYRA KASTSTJÄRNOR', 'Ninjan laddar kastet synligt och har fyra stjärnor per rond.'),
                ('ETAPP 5–6: SUMO', 'Tung motståndare. Hoppa över stampen och kontra efter rusningen.'),
                ('ÖVA FÖRST', 'Träna mot ninja eller sumo direkt från träningsmenyn.'),
                ('LYSSNA PÅ LJUDEN', 'Kontrolltestet har separata provknappar för dina nya ljudeffekter.'),
            ]
            for index, (heading, body) in enumerate(tips):
                y = 188 + index * 67
                self.text(heading, 114, y, 18, GOLD, True)
                self.text(body, 114, y + 28, 16, PAPER)
        self.footer(f'← / →  Byt sida   {page + 1} / 3', 'B / Start: tillbaka')

    def options(self, settings, selected):
        self.page('INSTÄLLNINGAR', 'Gäller bara Dojo Sunset. Sparas automatiskt i spelets mapp.')
        rows = [
            ('Svårighetsgrad', ['Lugn', 'Normal', 'Utmanande'][settings['difficulty']]),
            ('Ljudvolym', f"{round(settings['volume'] * 100)} %"),
            ('Arena', PALETTES[settings['arena']]['name']),
            ('Partikeleffekter', 'På' if settings['quality'] else 'Av'),
            ('Kontrollvibration', 'På' if settings['rumble'] else 'Av'),
            ('Spakens dödzon', f"{round(settings['deadzone'] * 100)} %"),
            ('Helskärm', 'På' if settings['fullscreen'] else 'Av'),
            ('Matchregler', 'Klassisk poängkarate' if settings['rules'] == 0 else 'Hälsoduell'),
            ('Välj kontroller', 'Öppna'),
            ('Tillbaka', ''),
        ]
        for index, (label, value) in enumerate(rows):
            y = 179 + index * 48
            if index == selected:
                pygame.draw.rect(self.surface, (*GOLD, 38), (103, y - 3, 1073, 45), border_radius=7)
                self.text('›', 111, y - 4, 28, GOLD, True)
            self.text(label, 142, y + 5, 20, PAPER)
            self.text(value, 1133, y + 5, 20, GOLD, anchor='right')
        self.footer('↑ / ↓  Välj     ← / → eller A: ändra', 'B / Start: tillbaka')

    def controller_select(self, settings, controls, controls2, selected):
        self.page('VÄLJ KONTROLLER',
                  'Ändrar bara Dojo Sunset – EmulationStation och RetroArch påverkas inte.')
        labels = {'auto': 'Automatiskt', 'xbox': 'Xbox', 'speedlink': 'SPEEDLINK (4 knappar)'}
        rows = [
            ('Spelare 1', labels[settings['controller_p1']]),
            ('Spelare 2', labels[settings['controller_p2']]),
            ('Aktivera och spara', ''),
            ('Tillbaka', ''),
        ]
        for index, (label, value) in enumerate(rows):
            y = 210 + index * 70
            if index == selected:
                pygame.draw.rect(self.surface, (*GOLD, 38), (180, y - 8, 920, 54), border_radius=7)
                self.text('›', 192, y - 7, 30, GOLD, True)
            self.text(label, 235, y, 23, PAPER)
            self.text(value, 1050, y, 21, GOLD, anchor='right')
        self.text('AKTIV NU', 235, 515, 14, MUTED, True)
        self.text('Spelare 1: ' + controls.name, 235, 548, 18, PAPER)
        self.text('Spelare 2: ' + controls2.name, 235, 579, 18, PAPER)
        self.footer('↑ / ↓  Välj     ← / → eller A: byt', 'Välj Aktivera för att använda valet')

    def records(self, storage):
        self.page('REKORDTAVLAN', 'Matchresultat sparas lokalt. Träning räknas inte som rekord.')
        for text, x in [('PLATS', 118), ('NAMN', 240), ('POÄNG', 610), ('NIVÅ', 830), ('DATUM', 1000)]:
            self.text(text, x, 185, 14, MUTED, True)
        if not storage.records:
            self.text('Ditt första resultat väntar.', 640, 327, 28, PAPER, anchor='center')
            self.text('Spela färdigt en match för att skriva in BRUCE PI här.',
                      640, 378, 18, MUTED, anchor='center')
        for index, row in enumerate(storage.records[:10]):
            y = 224 + index * 36
            tint = GOLD if index == 0 else PAPER
            self.text(f'{index + 1:02d}', 118, y, 22, tint, True)
            self.text(row['name'][:18], 240, y, 20, tint)
            self.text(f"{row['score']:06d}", 610, y, 22, tint, True)
            level = int(row.get('difficulty', 1))
            self.text(['Lugn', 'Normal', 'Svår'][max(0, min(2, level))], 830, y + 2, 18, MUTED)
            self.text(str(row.get('date', '')), 1000, y + 3, 16, MUTED)
        self.footer('BRUCE PI • Sparat på denna dator', 'B / Start: tillbaka')

    def controller_test(self, controls):
        self.page('KONTROLLTEST', 'Tryck på knapparna och rör spakarna. Inga systeminställningar ändras.')
        diagnostic = controls.diagnostics()
        self.text(diagnostic['name'], 115, 186, 22, TEAL if diagnostic['connected'] else GOLD, True)
        center_x, center_y = 318, 368
        pygame.draw.circle(self.surface, (56, 72, 81), (center_x, center_y), 100, 2)
        self.line(center_x - 100, center_y, center_x + 100, center_y, (56, 72, 81))
        self.line(center_x, center_y - 100, center_x, center_y + 100, (56, 72, 81))
        pygame.draw.circle(self.surface, TEAL,
                           (int(center_x + diagnostic['left_x'] * 87),
                            int(center_y + diagnostic['left_y'] * 87)), 16)
        self.text('VÄNSTER SPAK', center_x, 490, 16, MUTED, anchor='center')
        self.text(f"X {diagnostic['left_x']:+.2f}   Y {diagnostic['left_y']:+.2f}",
                  center_x, 520, 18, PAPER, anchor='center')
        positions = [('y', 933, 300, GOLD), ('x', 870, 363, BLUE),
                     ('b', 996, 363, RED), ('a', 933, 426, TEAL)]
        for name, x, y, tint in positions:
            if name in diagnostic['buttons']:
                pygame.draw.circle(self.surface, PAPER, (x, y), 30, 3)
            self.button(name.upper(), x, y, tint)
        for index, name in enumerate(('lb', 'rb', 'back', 'start')):
            tint = GOLD if name in diagnostic['buttons'] else MUTED
            self.pill(name.upper(), 683 + index * 110, 231, tint)
        self.text(f"LT  {diagnostic['lt']:.2f}        RT  {diagnostic['rt']:.2f}", 800, 500, 22, PAPER)
        self.text('Aktiva: ' + ', '.join(diagnostic['buttons']), 115, 575, 16, GOLD)
        self.text('A: roundkick • B: nunchaku • ↑: rop • ↓: förlust • ←: miss • →: karatehugg',
                  115, 611, 14, MUTED)
        self.footer('Ljudprov: X lätt träff • Y tung träff • LB block • RB sving', 'Start: tillbaka')

    def result(self, match, entries, selected, saved, tournament=None):
        won = match.winner is match.player
        if match.two_player:
            self.page(match.winner.name + ' VINNER!', '2 SPELARE • Matchen är avslutad')
        else:
            self.page('SEGER' if won else 'EN NY CHANS VÄNTAR', 'BRUCE PI • Matchen är avslutad')
        fighter = match.winner if match.two_player else match.player
        self.text(f'{fighter.score:06d}', 350, 213, 64, GOLD, True, 'center')
        self.text('POÄNG', 350, 295, 16, MUTED, True, 'center')
        accuracy = round(100 * fighter.hits / max(1, fighter.attacks))
        other = match.enemy if fighter is match.player else match.player
        rows = [('Ronder', f'{fighter.wins} – {other.wins}'),
                ('Träffsäkerhet', f'{accuracy} %'),
                ('Rena träffar', str(fighter.hits)),
                ('Blockeringar', str(fighter.blocks)),
                ('Bästa följd', str(fighter.best_combo))]
        for index, (label, value) in enumerate(rows):
            y = 350 + index * 40
            self.text(label, 151, y, 20, MUTED)
            self.text(value, 556, y, 20, PAPER, True, 'right')
        entries = list(entries)
        if tournament and not tournament.finished:
            entries[0] = 'Nästa motståndare'
        elif tournament:
            entries[0] = 'Ny karateresa'
        self.menu(entries, selected, 705, 263, 402, 57)
        message = 'Rekord sparat' if saved else 'Kunde inte spara resultatet'
        message_color = TEAL if saved else RED
        if match.two_player:
            message = 'Vänskapsmatch — spela igen!'
            message_color = TEAL
        if tournament and not tournament.finished:
            message = 'Etapp klar — resan fortsätter'
            message_color = TEAL
        self.text(message,
                  906, 473, 16, message_color, anchor='center')
        if tournament:
            belt = tournament.belt
            self.text(belt.name + ' BÄLTE', 906, 528, 20, GOLD, True, 'center')
            self.text(belt.motto, 906, 563, 14, MUTED, anchor='center')
        self.footer('A: välj', 'B / Start: huvudmeny')

    def confirm_quit(self, selected):
        self.panel((0, 0, 1280, 720), 150)
        self.panel((400, 213, 480, 286), 245, True)
        self.text('LÄMNA DOJON?', 640, 241, 32, GOLD, True, 'center')
        self.text('Dina sparade rekord finns kvar.', 640, 299, 18, MUTED, anchor='center')
        self.menu(['Fortsätt spela', 'Avsluta till skrivbordet'], selected, 427, 356, 426, 51)
        self.footer('A: välj', 'B / Start: fortsätt')

    def mode_select(self, title, entries, selected, training):
        self.page(title, 'Välj med styrkorset och starta med A.')
        self.menu(entries, selected, 110, 218, 480, 66)
        if training:
            descriptions = [
                ('FRI TRÄNING', 'Öva alla tekniker utan tidsgräns.',
                 'Växla mellan stilla motståndare och AI med Back.'),
                ('TEKNIKSKOLA', 'Tolv korta, praktiska lektioner.',
                 'Rörelse, slag, sparkar, kullerbytta och försvar.'),
                ('KONTROLLTEST', 'Kontrollera knappar, spakar och triggers.',
                 'Prova också dina importerade ljudeffekter.'),
                ('TRÄNA MOT NINJA', 'Öva försvar mot nunchaku och kaststjärnor.',
                 'Back växlar mellan stilla motståndare och AI.'),
                ('TRÄNA MOT SUMO', 'Lär dig läsa stamp, handflata och rusning.',
                 'Du slåss fortfarande med karate.'),
                ('HUVUDMENYN', 'Tillbaka till Dojo Sunset.', ''),
            ]
        else:
            descriptions = [
                ('KARATERESAN', 'Först karate, sedan ninja och till sist sumo.',
                 'Sex etapper. Bruce Pi slåss hela tiden obeväpnad.'),
                ('KLASSISK POÄNGKARATE', 'Hela och halva poäng. Två poäng vinner ronden.',
                 'Två ronder vinner matchen. 30 sekunder per rond.'),
                ('HÄLSODUELL', 'Längre, sammanhängande fighter.',
                 'Töm motståndarens hälsa. Bäst av tre ronder.'),
                ('2 SPELARE • POÄNG', 'Två kontroller, en egen fighter var.',
                 'Två hela poäng vinner ronden. Bäst av tre.'),
                ('2 SPELARE • HÄLSA', 'Utmana en vän med två kontroller.',
                 'Töm motståndarens hälsa. Bäst av tre ronder.'),
                ('HUVUDMENYN', 'Tillbaka till Dojo Sunset.', ''),
            ]
        heading, first, second = descriptions[selected]
        self.pill(heading, 638, 247)
        self.text(first, 638, 310, 16, PAPER)
        self.text(second, 638, 350, 16, MUTED)
        self.text('BRUCE PI', 638, 426, 32, GOLD, True)
        self.text('Din dojo. Ditt tempo.', 638, 473, 18, MUTED)
        self.footer('↑ / ↓  Välj     A: starta', 'B / Start: tillbaka')

    def versus_ready(self, controls, ready, rules):
        rule = 'Poängmatch' if rules == 0 else 'Hälsoduell'
        self.page('2 SPELARE', rule + ' • Tryck A på varsin kontroll.')
        for index, pad in enumerate(controls):
            x = 110 + index * 550
            self.panel((x, 220, 510, 310), 225)
            self.text(f'SPELARE {index + 1}', x + 30, 248, 32, GOLD, True)
            self.text('VIT DRÄKT' if index == 0 else 'RÖD DRÄKT', x + 30, 302, 18, MUTED)
            state = 'KLAR!' if ready[index] else 'TRYCK A FÖR ATT BLI KLAR'
            if not pad.pad:
                state = 'ANSLUT EN XBOX-KONTROLL'
            self.text(state, x + 30, 370, 22, TEAL if ready[index] else PAPER, True)
            self.text(pad.name[:38] if pad.pad else 'Väntar på anslutning…', x + 30, 438, 18, MUTED)
        self.text('Matchen börjar när båda är klara. Håll båda små SPEEDLINK-knapparna för paus.',
                  640, 573, 19, PAPER, anchor='center')
        self.footer('A: redo', 'B / Start: tillbaka')

    def tutorial(self, tutorial):
        self.panel((28, 167, 1224, 98), 238, True)
        lesson = tutorial.lesson
        self.text(lesson.title, 50, 181, 20, GOLD, True)
        self.text(lesson.instruction, 50, 217, 18, PAPER)
        count = f'{tutorial.progress} / {lesson.required}'
        self.text(count, 1223, 188, 28, TEAL, True, 'right')
        self.text('Back: nästa lektion', 1222, 238, 12, MUTED, anchor='right')
        if tutorial.lesson_done:
            self.banner('BRA JOBBAT!', 'Tryck A för nästa lektion.')

    def tournament_badge(self, tournament):
        belt = tournament.belt
        self.panel((40, 170, 363, 58), 213)
        kind = ARCHETYPE_NAMES[tournament.current_match.enemy.archetype]
        self.text(f'{kind}  •  ETAPP {tournament.stage + 1} / 6', 54, 180, 16, GOLD, True)
        self.text(belt.name + ' BÄLTE', 54, 203, 12, PAPER)
        pygame.draw.rect(self.surface, tuple(int(c * 255) for c in belt.color),
                         (306, 190, 80, 12), border_radius=3)
