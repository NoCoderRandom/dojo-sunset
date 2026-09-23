"""Application states, fixed-step simulation, and controller-first navigation."""
import argparse
import json
import time
from collections import deque
from pathlib import Path

import pygame

from .audio import Audio
from .competition import ClassicMatch, Tournament, opponent_match
from .controls import Controls
from .input_buffer import InputBuffer
from .model import Command, Fighter, Match, clamp
from .renderer import Renderer
from .storage import ROOT, Storage
from .tutorial import Tutorial
from .ui import UI

TITLE_ENTRIES = ['Spela match', 'Träna karate', 'Så spelar du', 'Inställningar', 'Rekord', 'Avsluta']
PAUSE_ENTRIES = ['Fortsätt', 'Så spelar du', 'Kontrolltest', 'Till huvudmenyn']
RESULT_ENTRIES = ['Spela igen', 'Träna karate', 'Till huvudmenyn']
PLAY_ENTRIES = ['1 spelare — Karateresan', '1 spelare — Poängmatch mot CPU',
                '1 spelare — Hälsoduell mot CPU', '2 spelare — Poängmatch',
                '2 spelare — Hälsoduell', 'Tillbaka']
TRAIN_ENTRIES = ['Fri träning — karate', 'Teknikskola — tolv lektioner', 'Kontrolltest',
                 'Träna mot ninja', 'Träna mot sumo', 'Tillbaka']


class Application:
    def __init__(self, arguments):
        self.arguments = arguments
        self.storage = Storage(arguments.data_dir) if arguments.data_dir else Storage()
        if arguments.windowed:
            self.storage.settings['fullscreen'] = False
        pygame.display.init()
        self.renderer = Renderer(self.storage.settings)
        self.controls = Controls(self.storage.settings)
        self.controls2 = Controls(self.storage.settings,
                                  excluded_instances=lambda: {self.controls.instance})
        self.controls.excluded_instances = lambda: {self.controls2.instance}
        self.controls.secondary = self.controls2
        self.audio = Audio(0 if arguments.mute else self.storage.settings['volume'])
        self.ui = UI()
        self.clock = pygame.time.Clock()
        self.running = True
        self.screen = 'title'
        self.parent_screen = 'title'
        self.selected = 0
        self.help_page = 0
        self.match = None
        self.tutorial = None
        self.tournament = None
        self.result_saved = False
        self.demo_fighters = [
            Fighter('BRUCE PI', 1.15, 1, (.91, .93, .87)),
            Fighter('AKIRA', 3.6, -1, (.73, .16, .19)),
        ]
        self.elapsed = 0.0
        self.accumulator = 0.0
        self.input_buffer = InputBuffer()
        self.input_buffer2 = InputBuffer()
        self.ready = [False, False]
        self.ready_instances = [None, None]
        self.versus_rules = 0
        self.demo_timer = 1.3
        self.frame_count = 0
        self.started = time.monotonic()
        self.frame_times = deque(maxlen=36000)
        self.smoke_stage = -1
        self.suppress_game_action = False
        self.screenshot_requested = False
        self.smoke_output = ROOT / 'userdata' / 'smoke'
        if arguments.smoke:
            self.smoke_output.mkdir(exist_ok=True)
        if arguments.practice:
            self.new_match(True)
        elif arguments.demo:
            self.new_match(False)
            self.match.brain.difficulty = 1

    def new_match(self, practice=False, opponent='karate', two_player=False):
        self.input_buffer.clear()
        self.input_buffer2.clear()
        self.tutorial = None
        self.tournament = None
        if two_player:
            self.match = ClassicMatch() if self.versus_rules == 0 else Match()
            self.match.two_player = True
            self.match.player.name = 'SPELARE 1'
            self.match.enemy.name = 'SPELARE 2'
        elif opponent != 'karate':
            self.match = opponent_match(opponent, self.storage.settings['difficulty'], practice)
            self.match.practice_ai = practice
        elif not practice and self.storage.settings['rules'] == 0:
            self.match = ClassicMatch(self.storage.settings['difficulty'])
        else:
            self.match = Match(self.storage.settings['difficulty'], practice, seed=None)
        self.screen = 'game'
        self.selected = 0
        self.accumulator = 0
        self.result_saved = False
        self.audio.play('accept')

    def open_screen(self, name, parent=None):
        self.input_buffer.clear()
        self.input_buffer2.clear()
        self.controls.reset_menu_navigation()
        self.controls2.reset_menu_navigation()
        if parent:
            self.parent_screen = parent
        self.screen = name
        self.selected = 0
        self.audio.play('accept')

    def go_back(self):
        self.controls.reset_menu_navigation()
        self.controls2.reset_menu_navigation()
        self.screen = self.parent_screen
        self.selected = 0
        self.audio.play('menu')

    def menu_controls(self):
        if (self.match and self.match.two_player and self.screen in ('pause', 'result')
                and (self.controls2.held or self.controls2.pressed)):
            return self.controls2
        return self.controls

    def navigate(self, entries):
        controls = self.menu_controls()
        step = controls.menu_step()
        if step:
            self.selected = (self.selected + step) % len(entries)
            self.audio.play('menu')
        return controls.accept()

    def versus_connected(self):
        return bool(self.controls.pad and self.controls2.pad)

    def resume_match(self):
        if not self.controls.pad or (self.match.two_player and not self.versus_connected()):
            message = ('Anslut båda kontrollerna för att fortsätta.' if self.match.two_player
                       else 'Anslut din Xbox-kontroll för att fortsätta.')
            self.ui.notify(message, 5)
            return
        self.screen = 'game'
        self.accumulator = 0
        self.input_buffer.clear()
        self.input_buffer2.clear()

    def open_versus(self, rules):
        self.versus_rules = rules
        self.ready = [False, False]
        self.ready_instances = [self.controls.instance, self.controls2.instance]
        self.open_screen('versus_ready', 'play_select')

    def handle_versus(self):
        if self.controls.cancel() or self.controls2.cancel():
            self.open_screen('play_select', 'title')
            return
        for index, controls in enumerate((self.controls, self.controls2)):
            if controls.instance != self.ready_instances[index] or controls.disconnect or not controls.pad:
                self.ready[index] = False
            self.ready_instances[index] = controls.instance
            if controls.pad and controls.hit('a'):
                self.ready[index] = True
        if all(self.ready) and self.versus_connected():
            self.new_match(two_player=True)

    def handle_title(self):
        if self.navigate(TITLE_ENTRIES):
            choice = self.selected
            if choice == 0:
                self.open_screen('play_select', 'title')
            elif choice == 1:
                self.open_screen('train_select', 'title')
            elif choice == 2:
                self.help_page = 0
                self.open_screen('help', 'title')
            elif choice == 3:
                self.open_screen('options', 'title')
            elif choice == 4:
                self.open_screen('records', 'title')
            else:
                self.open_screen('quit', 'title')
        elif self.controls.hit('start'):
            self.open_screen('quit', 'title')
        elif self.controls.hit('back'):
            self.open_screen('controller', 'title')

    def handle_pause(self):
        if self.menu_controls().cancel():
            self.resume_match()
            self.audio.play('menu')
            return
        if not self.navigate(PAUSE_ENTRIES):
            return
        if self.selected == 0:
            self.resume_match()
        elif self.selected == 1:
            self.help_page = 0
            self.open_screen('help', 'pause')
        elif self.selected == 2:
            self.open_screen('controller', 'pause')
        else:
            self.open_screen('title')
            self.match = None

    def alter_setting(self, direction):
        settings = self.storage.settings
        selected = self.selected
        if selected == 0:
            settings['difficulty'] = (settings['difficulty'] + direction) % 3
        elif selected == 1:
            settings['volume'] = round(clamp(settings['volume'] + direction * .05, 0, 1), 2)
            self.audio.set_volume(0 if self.arguments.mute else settings['volume'])
        elif selected == 2:
            settings['arena'] = (settings['arena'] + direction) % 2
            self.renderer.change_arena()
        elif selected == 3:
            settings['quality'] = 1 - settings['quality']
        elif selected == 4:
            settings['rumble'] = not settings['rumble']
            if settings['rumble']:
                self.controls.rumble(.3, 120)
        elif selected == 5:
            settings['deadzone'] = round(clamp(settings['deadzone'] + direction * .02, .12, .4), 2)
        elif selected == 6:
            self.renderer.toggle_fullscreen()
        elif selected == 7:
            settings['rules'] = 1 - settings['rules']
        elif selected == 8:
            self.go_back()
        self.audio.play('menu')
        if not self.storage.save_settings():
            self.ui.notify(self.storage.error)

    def handle_options(self):
        if self.controls.cancel():
            self.go_back()
            return
        step = self.controls.menu_step()
        if step:
            self.selected = (self.selected + step) % 9
            self.audio.play('menu')
        if self.controls.hit('left'):
            self.alter_setting(-1)
        elif self.controls.hit('right') or self.controls.accept():
            self.alter_setting(1)

    def handle_help(self):
        if self.controls.cancel():
            self.go_back()
        elif self.controls.hit('left') or self.controls.hit('right') or self.controls.accept():
            direction = -1 if self.controls.hit('left') else 1
            self.help_page = (self.help_page + direction) % 3
            self.audio.play('menu')

    def handle_result(self):
        if self.menu_controls().cancel():
            self.open_screen('title')
            self.match = None
            self.tournament = None
            return
        if self.navigate(RESULT_ENTRIES):
            if self.selected == 0:
                if self.match.two_player:
                    self.open_versus(self.versus_rules)
                elif self.tournament and not self.tournament.finished:
                    self.match = self.tournament.start_stage()
                    self.storage.settings['arena'] = self.tournament.stage % 2
                    self.renderer.change_arena()
                    self.screen = 'game'
                    self.accumulator = 0
                elif self.tournament:
                    self.start_tournament()
                else:
                    self.new_match(False)
            elif self.selected == 1:
                self.new_match(True)
            else:
                self.open_screen('title')
                self.match = None
                self.tournament = None

    def start_tournament(self):
        self.input_buffer.clear()
        self.input_buffer2.clear()
        self.tutorial = None
        self.tournament = Tournament(self.storage.settings['difficulty'])
        self.match = self.tournament.start_stage()
        self.screen = 'game'
        self.accumulator = 0
        self.selected = 0
        self.result_saved = False
        self.audio.play('accept')

    def start_tutorial(self):
        self.input_buffer.clear()
        self.input_buffer2.clear()
        self.tournament = None
        self.tutorial = Tutorial()
        self.match = self.tutorial.match
        self.screen = 'game'
        self.accumulator = 0
        self.selected = 0
        self.audio.play('accept')

    def handle_selection(self, training):
        entries = TRAIN_ENTRIES if training else PLAY_ENTRIES
        if self.controls.cancel():
            self.open_screen('title')
            return
        if not self.navigate(entries):
            return
        choice = self.selected
        if training:
            if choice == 0:
                self.new_match(True)
            elif choice == 1:
                self.start_tutorial()
            elif choice == 2:
                self.open_screen('controller', 'train_select')
            elif choice == 3:
                self.new_match(True, 'ninja')
            elif choice == 4:
                self.new_match(True, 'sumo')
            else:
                self.open_screen('title')
        else:
            if choice == 0:
                self.start_tournament()
            elif choice == 1:
                self.storage.settings['rules'] = 0
                self.new_match(False)
            elif choice == 2:
                self.storage.settings['rules'] = 1
                self.new_match(False)
            elif choice in (3, 4):
                self.open_versus(choice - 3)
            else:
                self.open_screen('title')


    def handle_quit(self):
        if self.controls.cancel():
            self.go_back()
        elif self.navigate(['Fortsätt', 'Avsluta']):
            if self.selected == 0:
                self.go_back()
            else:
                self.running = False

    def handle_input(self, dt):
        previous_screen = self.screen
        was_focused = self.controls.has_focus
        events = pygame.event.get()
        self.controls.poll(dt, events)
        self.controls2.poll(dt, events)
        if self.controls.quit_requested:
            self.running = False
            return
        if self.controls.has_focus != was_focused:
            volume = self.storage.settings['volume'] if self.controls.has_focus else 0
            self.audio.set_volume(0 if self.arguments.mute else volume)
        if not self.controls.has_focus:
            if self.screen == 'game':
                self.open_screen('pause')
            return
        if not was_focused:
            # Returning from another app must require a fresh button press.
            self.controls.pressed.clear()
            self.controls2.pressed.clear()
            self.controls.reset_menu_navigation()
            self.controls2.reset_menu_navigation()
            return
        if self.controls.screenshot_requested:
            self.screenshot_requested = True
        if self.controls.fullscreen_requested:
            self.renderer.toggle_fullscreen()
            self.storage.save_settings()
        if self.screen == 'game':
            disconnected = self.controls.disconnect or not self.controls.pad or (
                self.match.two_player and (self.controls2.disconnect or not self.versus_connected()))
            if disconnected or self.controls.focus_lost:
                self.open_screen('pause')
                if disconnected:
                    self.ui.notify('Kontrollen kopplades bort. Matchen är pausad.', 6)
            elif self.controls.hit('start') or (self.match.two_player and self.controls2.hit('start')):
                self.open_screen('pause')
            elif self.tutorial and self.controls.hit('back'):
                if self.tutorial.skip_lesson():
                    self.match = self.tutorial.match
                    self.input_buffer.clear()
                else:
                    self.open_screen('title')
                    self.tutorial = None
                    self.match = None
                    self.ui.notify('Teknikskolan avslutad. Du kan öva igen när du vill.')
            elif self.match.practice and self.controls.hit('back'):
                self.match.practice_ai = not self.match.practice_ai
                self.audio.play('menu')
        elif self.screen == 'title':
            self.handle_title()
        elif self.screen == 'play_select':
            self.handle_selection(False)
        elif self.screen == 'versus_ready':
            self.handle_versus()
        elif self.screen == 'train_select':
            self.handle_selection(True)
        elif self.screen == 'pause':
            self.handle_pause()
        elif self.screen == 'options':
            self.handle_options()
        elif self.screen == 'help':
            self.handle_help()
        elif self.screen == 'records':
            if self.controls.cancel() or self.controls.accept():
                self.go_back()
        elif self.screen == 'controller':
            if self.controls.hit('start'):
                self.go_back()
            elif self.controls.hit('x'):
                self.audio.play('hit_light')
            elif self.controls.hit('y'):
                self.audio.play('hit_heavy')
            elif self.controls.hit('lb'):
                self.audio.play('block')
            elif self.controls.hit('rb'):
                self.audio.play('swing')
            elif self.controls.hit('a'):
                self.audio.play('round_swing')
            elif self.controls.hit('b'):
                self.audio.play('nunchaku_spin')
            elif self.controls.hit('up'):
                self.audio.play('kiai')
            elif self.controls.hit('down'):
                self.audio.play('defeat')
            elif self.controls.hit('left'):
                self.audio.play('miss')
            elif self.controls.hit('right'):
                self.audio.play('hit_chop')
        elif self.screen == 'result':
            self.handle_result()
        elif self.screen == 'quit':
            self.handle_quit()
        if previous_screen != 'game' and self.screen == 'game':
            self.suppress_game_action = True

    def demo_command(self):
        fighter = self.match.player
        enemy = self.match.enemy
        distance = abs(fighter.x - enemy.x)
        phase = int(self.elapsed * 2.0)
        attacks = ['jab', 'front_kick', 'round_kick', 'cross', 'sweep', 'high_kick', 'jump_kick']
        attack = attacks[phase % len(attacks)] if phase != getattr(self, 'demo_phase', -1) else ''
        self.demo_phase = phase
        return Command(move=fighter.facing if distance > 1.5 else 0,
                       attack=attack if distance < 2.1 else '',
                       guard=phase % 7 == 5)

    def tick_match(self, dt):
        if (self.tutorial and self.tutorial.lesson_done
                and self.controls.accept() and self.tutorial.success_time > .4):
            if not self.tutorial.next_lesson():
                self.ui.notify('Teknikskolan klar! Prova en klassisk match.', 5)
                self.open_screen('title')
                self.match = None
                self.tutorial = None
                return
            self.match = self.tutorial.match
            self.suppress_game_action = True
        command = self.demo_command() if self.arguments.demo else self.controls.command()
        command2 = self.controls2.command() if self.match.two_player else Command()
        if self.suppress_game_action:
            command = Command()
            command2 = Command()
            self.suppress_game_action = False
            self.input_buffer.clear()
            self.input_buffer2.clear()
        if self.match.phase == 'fight':
            self.input_buffer.offer(command, self.match.elapsed)
            if self.match.two_player:
                self.input_buffer2.offer(command2, self.match.elapsed)
        self.accumulator = min(self.accumulator + dt, .1)
        while self.accumulator >= 1 / 120:
            if self.match.phase != 'fight':
                self.input_buffer.clear()
                self.input_buffer2.clear()
            step_command = self.input_buffer.take(self.match.player, command, self.match.elapsed)
            step_command2 = self.input_buffer2.take(self.match.enemy, command2, self.match.elapsed)
            if self.tutorial:
                self.tutorial.update(1 / 120, step_command)
            else:
                self.match.update(1 / 120, step_command, step_command2)
            for event in self.match.events:
                if event != 'hit':
                    self.audio.play(event)
                if event == 'hit':
                    self.controls.rumble(.35, 80)
                    if self.match.two_player:
                        self.controls2.rumble(.35, 80)
                elif event == 'block':
                    self.controls.rumble(.15, 45)
                    if self.match.two_player:
                        self.controls2.rumble(.15, 45)
            self.accumulator -= 1 / 120
        if self.match.phase == 'finished':
            if self.tournament:
                self.tournament.complete_stage()
            save_result = not (self.arguments.demo or self.arguments.smoke or self.match.two_player)
            save_result = save_result and (not self.tournament or self.tournament.finished)
            self.result_saved = self.storage.add_record(self.match) if save_result else False
            self.open_screen('result')
            if self.match.two_player or self.match.winner is self.match.player:
                self.audio.play('win')

    def tick_demo_background(self, dt):
        self.demo_timer -= dt
        if self.demo_timer <= 0:
            self.demo_timer = 2.2
            fighter = self.demo_fighters[int(self.elapsed) % 2]
            moves = ['round_kick', 'front_kick', 'high_kick', 'jab', 'spin_kick']
            fighter.start_attack(moves[int(self.elapsed) % len(moves)])
        for fighter in self.demo_fighters:
            fighter.tick(dt, Command())
        self.demo_fighters[0].x = 1.15
        self.demo_fighters[1].x = 3.6

    def smoke(self):
        stage = int(self.elapsed // 1.5)
        if stage == self.smoke_stage:
            return
        self.smoke_stage = stage
        if stage == 1:
            self.new_match(True)
            self.match.phase = 'fight'
            self.match.player.x = -.7
            self.match.enemy.x = .8
            self.match.player.start_attack('round_kick')
        elif stage == 2:
            self.match.player.start_attack('sweep')
        elif stage == 3:
            self.open_screen('help', 'title')
        elif stage == 4:
            self.help_page = 1
        elif stage == 5:
            self.open_screen('options', 'title')
        elif stage == 6:
            self.open_screen('controller', 'title')
        elif stage == 7:
            self.open_screen('records', 'title')
        elif stage >= 8:
            self.running = False
        self.screenshot_requested = True

    def draw(self, dt):
        has_match = self.match and self.screen not in (
            'title', 'options', 'records', 'quit', 'play_select', 'train_select', 'versus_ready')
        fighters = [self.match.player, self.match.enemy] if has_match else self.demo_fighters
        self.renderer.draw_world(fighters, self.elapsed, self.match if has_match else None)
        self.ui.begin(dt)
        if self.screen == 'title':
            self.ui.title(self.controls, self.storage, TITLE_ENTRIES, self.selected)
        elif self.screen == 'play_select':
            self.ui.mode_select('VÄLJ DIN MATCH', PLAY_ENTRIES, self.selected, False)
        elif self.screen == 'versus_ready':
            self.ui.versus_ready((self.controls, self.controls2), self.ready, self.versus_rules)
        elif self.screen == 'train_select':
            self.ui.mode_select('TRÄNA KARATE', TRAIN_ENTRIES, self.selected, True)
        elif self.screen == 'game':
            self.ui.hud(self.match, self.controls)
            self.ui.impact_labels(self.match, self.renderer)
            if self.tutorial:
                self.ui.tutorial(self.tutorial)
            elif self.tournament:
                self.ui.tournament_badge(self.tournament)
        elif self.screen == 'pause':
            self.ui.hud(self.match, self.controls)
            self.ui.pause(PAUSE_ENTRIES, self.selected)
        elif self.screen == 'help':
            self.ui.help(self.help_page)
        elif self.screen == 'options':
            self.ui.options(self.storage.settings, self.selected)
        elif self.screen == 'records':
            self.ui.records(self.storage)
        elif self.screen == 'controller':
            self.ui.controller_test(self.controls)
        elif self.screen == 'result':
            self.ui.result(self.match, RESULT_ENTRIES, self.selected, self.result_saved, self.tournament)
        elif self.screen == 'quit':
            self.ui.confirm_quit(self.selected)
        self.renderer.draw_hud(self.ui.finish())
        if self.screenshot_requested:
            directory = self.smoke_output if self.arguments.smoke else ROOT / 'userdata'
            path = directory / f'{self.screen}-{time.time_ns()}.png'
            self.renderer.screenshot(path)
            self.screenshot_requested = False
            if not self.arguments.smoke:
                self.ui.notify('Skärmbild sparad i spelets userdata-mapp.')
        self.renderer.present()

    def write_metrics(self):
        elapsed = max(.001, time.monotonic() - self.started)
        sorted_times = sorted(self.frame_times)
        metrics = {
            'gpu': self.renderer.gpu,
            'frames': self.frame_count,
            'seconds': round(elapsed, 2),
            'average_fps': round(self.frame_count / elapsed, 1),
            'p95_frame_ms': round(sorted_times[int(len(sorted_times) * .95)] * 1000, 2) if sorted_times else 0,
            'controller': self.controls.name,
            'audio_enabled': self.audio.enabled,
            'screen': self.screen,
        }
        if self.arguments.smoke or self.arguments.seconds:
            (ROOT / 'userdata' / 'last-test.json').write_text(json.dumps(metrics, indent=2), encoding='utf-8')
        print(json.dumps(metrics, ensure_ascii=False), flush=True)

    def run(self):
        try:
            while self.running:
                frame_limit = 60 if self.controls.has_focus else 15
                dt = min(self.clock.tick(frame_limit) / 1000, .1)
                self.elapsed += dt
                self.handle_input(dt)
                if self.arguments.smoke:
                    self.smoke()
                if self.screen == 'game':
                    self.tick_match(dt)
                elif self.screen in ('title', 'options', 'records', 'quit', 'play_select', 'train_select',
                                     'versus_ready'):
                    self.tick_demo_background(dt)
                self.draw(dt)
                self.frame_count += 1
                self.frame_times.append(dt)
                if self.arguments.seconds and time.monotonic() - self.started >= self.arguments.seconds:
                    self.running = False
            self.write_metrics()
        finally:
            self.controls.close()
            self.audio.close()
            self.renderer.close()
            pygame.quit()


def main():
    parser = argparse.ArgumentParser(description='Dojo Sunset — original Python karate game')
    parser.add_argument('--mute', action='store_true')
    parser.add_argument('--windowed', action='store_true')
    parser.add_argument('--practice', action='store_true')
    parser.add_argument('--demo', action='store_true')
    parser.add_argument('--smoke', action='store_true')
    parser.add_argument('--data-dir', type=Path, default=None)
    parser.add_argument('--seconds', type=float, default=0)
    args = parser.parse_args()
    app = Application(args)
    app.run()
