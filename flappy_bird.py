"""A touch-friendly Flappy Bird-style game for Python 3 and Tkinter.
Tap/click or press Space to flap. Esc exits. No external assets required.
"""
import math
import os
import random
import time
import tkinter as tk
import tkinter.font as tkfont
import io
import json
import struct
import wave

W, H = 360, 640
GROUND = 560
SAVE = os.path.join(os.path.dirname(os.path.abspath(__file__)), '.flappy_best')
PROFILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), '.flappy_profile.json')

class Audio:
    """Optional pygame audio; the game remains playable without pygame."""
    def __init__(self):
        self.available = False
        self.music_volume = 0.35
        self.sfx_volume = 0.55
        self.music_on = True
        self.sfx_on = True
        self.track_index = 0
        self.track_names = ("SKY", "BREEZE")
        self.failed = False

    def enable(self):
        if self.available:
            return
        try:
            import pygame
            self.pg = pygame
            pygame.mixer.init(frequency=22050, size=-16, channels=1, buffer=512)
            self.sounds = {
                'flap': pygame.mixer.Sound(file=self.tone([620, 820], .11)),
                'score': pygame.mixer.Sound(file=self.tone([660, 880], .22)),
                'hit': pygame.mixer.Sound(file=self.tone([180, 95], .25)),
            }
            self.music_data = self.tone([392, 494, 587, 494, 440, 523, 659, 523,
                                         349, 440, 523, 440, 392, 494, 587, 494], 8.0, True)
            self.tracks = [self.music_data, self.tone(
                [330, 392, 440, 523, 494, 440, 392, 330,
                 294, 370, 440, 494, 440, 392, 370, 294], 8.0, True)]
            pygame.mixer.music.load(self.tracks[self.track_index])
            self.available = True
            self.apply()
            pygame.mixer.music.play(-1)
        except Exception:
            self.available = False
            self.failed = True

    def tone(self, notes, duration, music=False):
        rate = 22050
        count = int(rate * duration)
        samples = bytearray()
        segment = duration / len(notes)
        for i in range(count):
            t = i / rate
            idx = min(len(notes)-1, int(t / segment))
            local = t - idx * segment
            envelope = min(1.0, local*35) * max(0.0, 1-local/segment)**0.7
            freq = notes[idx]
            signal = math.sin(2*math.pi*freq*t) + .22*math.sin(4*math.pi*freq*t)
            samples.extend(struct.pack('<h', int(6500 * signal * envelope)))
        stream = io.BytesIO()
        with wave.open(stream, 'wb') as wav:
            wav.setnchannels(1)
            wav.setsampwidth(2)
            wav.setframerate(rate)
            wav.writeframes(samples)
        stream.seek(0)
        return stream

    def apply(self):
        if not self.available:
            return
        self.pg.mixer.music.set_volume(self.music_volume if self.music_on else 0)
        for sound in self.sounds.values():
            sound.set_volume(self.sfx_volume if self.sfx_on else 0)

    def next_track(self):
        self.track_index = (self.track_index + 1) % len(self.track_names)
        if self.available:
            try:
                self.tracks[self.track_index].seek(0)
                self.pg.mixer.music.load(self.tracks[self.track_index])
                self.apply()
                self.pg.mixer.music.play(-1)
            except Exception:
                self.available = False

    def play(self, name):
        if self.available and self.sfx_on:
            self.sounds[name].play()

class Game:
    def __init__(self, root):
        self.root = root
        root.title('Flappy Flight')
        root.configure(bg='#12283b')
        self.canvas = tk.Canvas(root, bg='#70c5ce', highlightthickness=0)
        self.canvas.pack(fill='both', expand=True)
        root.geometry('360x640')
        root.bind('<space>', self.action)
        root.bind('<Up>', self.action)
        root.bind('<Escape>', lambda e: root.destroy())
        self.canvas.bind('<Button-1>', self.action)
        self.canvas.bind('<Configure>', self.resize)
        self.fonts = {}
        self.text_widths = {}
        self.items = []
        self.frame = []
        self.scale = 1
        self.ox = self.oy = 0
        self.audio = Audio()
        self.settings_open = False
        self.stats_open = False
        self.bird_menu_open = False
        self.background_menu_open = False
        self.menu_dirty = True
        self.background_page = 0
        self.bird_page = 0
        self.difficulty_index = 1
        # Name, pipe speed, gap, interval, gravity, and flap velocity.
        self.difficulties = [("EASY", 80, 190, 2.1, 740, -280), ("MEDIUM", 120, 160, 1.65, 850, -300), ("HARD", 165, 140, 1.35, 980, -325)]
        self.background_index = 0
        self.bird_index = 0
        self.backgrounds = [
            ("DAY", (76,174,200), (142,218,226)),
            ("SUNSET", (166,104,157), (255,203,143)),
            ("DUSK", (47,72,121), (118,153,184)),
            ("DAWN", (139,116,176), (255,196,178)),
            ("OCEAN", (37,124,166), (133,211,219)),
            ("MEADOW", (93,166,154), (196,226,179)),
            ("LAVENDER", (127,113,183), (212,191,225)),
            ("PEACH", (218,142,123), (255,218,175))]
        self.birds = [
            ("GOLD", "#ffdb4d"), ("BLUE", "#72c9ee"),
            ("PINK", "#f39db5"), ("GREEN", "#a6dc73"),
            ("CORAL", "#f28d78"), ("LAVENDER", "#bda3e6"),
            ("MINT", "#8be0be"), ("SKY", "#a9ddf5"),
            ("PEACH", "#ffc697"), ("LIME", "#c5df67"),
            ("RED", "#ed6966"), ("ORANGE", "#f5a34b"),
            ("VIOLET", "#a987cf"), ("TEAL", "#58c5ba"),
            ("CREAM", "#f9e8b5"), ("ROSE", "#d981a1"),
            ("OLIVE", "#abc474"), ("INDIGO", "#8e9ad8"),
            ("AQUA", "#6fd5da"), ("AMBER", "#efbc55"),
            ("LEMON", "#eee980"), ("SILVER", "#c5d1db"),
            ("PLUM", "#bb87aa"), ("SAND", "#d8ba88"),
            ("COBALT", "#5888c6"), ("FIRE", "#ea7853"),
            ("FROST", "#b9e8ed"), ("ORCHID", "#d494d7"),
            ("JUNGLE", "#65b782"), ("HONEY", "#eabf68"),
            ("BERRY", "#ce6f92"), ("STORM", "#90a6be"),
            ("MANGO", "#ffb93f"), ("CRIMSON", "#db5b69"),
            ("AZURE", "#63abe0"), ("EMERALD", "#55bc87"),
            ("CLOUD", "#dce9f4"), ("TANGERINE", "#f28d50"),
            ("PERIWINKLE", "#a6aaf0"), ("BLOSSOM", "#f5b1cf")]
        self.best = self.load_best()
        self.profile = self.load_profile()
        self.difficulty_index = max(0, min(len(self.difficulties)-1, self.profile_int('difficulty', 1)))
        bird = max(0, min(len(self.birds)-1, self.profile_int('bird', 0)))
        background = max(0, min(len(self.backgrounds)-1, self.profile_int('background', 0)))
        self.bird_index = bird if self.best >= self.bird_unlock_score(bird) else 0
        self.background_index = background if self.best >= self.background_unlock_score(background) else 0
        self.audio.music_volume = max(0, min(1, self.profile_number('music_volume', .35)))
        self.audio.sfx_volume = max(0, min(1, self.profile_number('sfx_volume', .55)))
        self.audio.music_on = bool(self.profile.get('music_on', True))
        self.audio.sfx_on = bool(self.profile.get('sfx_on', True))
        self.state = 'ready'
        self.reset()
        self.last = time.monotonic()
        self.tick()

    def load_profile(self):
        try:
            with open(PROFILE, 'r') as f:
                data = json.load(f)
            return data if isinstance(data, dict) else {}
        except (OSError, ValueError):
            return {}

    def profile_int(self, key, default=0):
        try:
            return int(self.profile.get(key, default))
        except (TypeError, ValueError, OverflowError):
            return default

    def profile_number(self, key, default):
        try:
            value = float(self.profile.get(key, default))
            return value if math.isfinite(value) else default
        except (TypeError, ValueError, OverflowError):
            return default

    def save_profile(self):
        self.profile.update(difficulty=self.difficulty_index, bird=self.bird_index,
                            background=self.background_index,
                            music_volume=self.audio.music_volume, sfx_volume=self.audio.sfx_volume,
                            music_on=self.audio.music_on, sfx_on=self.audio.sfx_on)
        try:
            with open(PROFILE, 'w') as f:
                json.dump(self.profile, f)
        except OSError:
            pass

    def load_best(self):
        try:
            with open(SAVE, 'r') as f:
                return max(0, int(f.read()))
        except (OSError, ValueError):
            return 0

    def save_best(self):
        try:
            with open(SAVE, 'w') as f:
                f.write(str(self.best))
        except OSError:
            pass

    def reset(self):
        self.y = 270.0
        self.vy = 0.0
        self.bird_angle = -5.0
        self.pipes = []
        self.spawn = 0.0
        self.score = 0
        self.score_pop = 0.0
        self.elapsed = 0.0
        self.ground_offset = 0.0
        self.particles = []
        self.explosion = []
        self.explosion_age = 0.0
        self.flash = 0.0
        self.over_time = 0.0

    def resize(self, event):
        self.menu_dirty = True
        self.scale = min(event.width / W, event.height / H)
        self.ox = (event.width - W * self.scale) / 2
        self.oy = (event.height - H * self.scale) / 2

    def bird_unlock_score(self, index):
        return 0 if index < 5 else 3 + (index - 5) * 2

    def background_unlock_score(self, index):
        return index * 10

    def action(self, event=None):
        is_pointer = event is not None and getattr(event, 'keysym', '') not in ('space', 'Up')
        self.menu_dirty = True
        if self.stats_open:
            if is_pointer:
                x = (event.x - self.ox) / self.scale
                y = (event.y - self.oy) / self.scale
                if 100 <= x <= 260 and 480 <= y <= 525:
                    self.stats_open = False
            return
        if self.background_menu_open:
            if is_pointer:
                x = (event.x - self.ox) / self.scale
                y = (event.y - self.oy) / self.scale
                if 16 <= x < 344 and 82 <= y < 538:
                    col, row = int((x-16)//164), int((y-82)//114)
                    index = row * 2 + col
                    if index < len(self.backgrounds) and self.best >= self.background_unlock_score(index):
                        self.background_index = index
                        self.background_menu_open = False
                        self.save_profile()
                elif 100 <= x <= 260 and 580 <= y <= 625:
                    self.background_menu_open = False
            return
        if self.bird_menu_open:
            if is_pointer:
                x = (event.x - self.ox) / self.scale
                y = (event.y - self.oy) / self.scale
                if 12 <= x < 348 and 65 <= y < 565:
                    col, row = int((x-12)//84), int((y-65)//50)
                    index = row * 4 + col
                    if index < len(self.birds) and self.best >= self.bird_unlock_score(index):
                        self.bird_index = index
                        self.bird_menu_open = False
                        self.save_profile()
                elif 100 <= x <= 260 and 580 <= y <= 625:
                    self.bird_menu_open = False
            return
        if self.settings_open:
            if not is_pointer:
                return
            x = (event.x - self.ox) / self.scale
            y = (event.y - self.oy) / self.scale
            if 90 <= x <= 270 and 333 <= y <= 358 and not self.audio.available:
                self.audio.enable()
            elif 83 <= x <= 277 and 411 <= y <= 448:
                self.audio.next_track()
            elif 112 <= x <= 248 and 365 <= y <= 405:
                self.settings_open = False
            elif 90 <= x <= 270 and 225 <= y <= 265:
                if x < 150: self.audio.music_volume = max(0, round(self.audio.music_volume - .1, 2))
                elif x > 210: self.audio.music_volume = min(1, round(self.audio.music_volume + .1, 2))
                else: self.audio.music_on = not self.audio.music_on
                self.audio.apply()
                self.save_profile()
            elif 90 <= x <= 270 and 290 <= y <= 330:
                if x < 150: self.audio.sfx_volume = max(0, round(self.audio.sfx_volume - .1, 2))
                elif x > 210: self.audio.sfx_volume = min(1, round(self.audio.sfx_volume + .1, 2))
                else: self.audio.sfx_on = not self.audio.sfx_on
                self.audio.apply()
                self.audio.play('score')
                self.save_profile()
            return
        if self.state == 'paused':
            if is_pointer:
                x = (event.x - self.ox) / self.scale
                y = (event.y - self.oy) / self.scale
                if 105 <= x <= 255 and 275 <= y <= 318:
                    self.state = 'playing'
                elif 105 <= x <= 255 and 335 <= y <= 378:
                    if self.score > self.best:
                        self.best = self.score
                        self.save_best()
                    self.reset()
                    self.state = 'ready'
            return
        if self.state == 'playing' and is_pointer:
            x = (event.x - self.ox) / self.scale
            y = (event.y - self.oy) / self.scale
            if 275 <= x <= 345 and 20 <= y <= 60:
                self.state = 'paused'
                return
        if self.state in ('ready', 'over') and is_pointer:
            x = (event.x - self.ox) / self.scale
            y = (event.y - self.oy) / self.scale
            if 15 <= x <= 105 and 20 <= y <= 55:
                self.stats_open = True
                return
            if 255 <= x <= 345 and 20 <= y <= 55:
                self.settings_open = True
                return
        if self.state == 'ready':
            if event is not None and getattr(event, 'keysym', '') not in ('space', 'Up'):
                x = (event.x - self.ox) / self.scale
                y = (event.y - self.oy) / self.scale
                if 90 <= x <= 270 and 520 <= y <= 553:
                    self.difficulty_index = (self.difficulty_index + 1) % len(self.difficulties)
                    self.save_profile()
                    return
                if 40 <= x <= 175 and 470 <= y <= 510:
                    self.background_page = self.background_index // 4
                    self.background_menu_open = True
                    return
                if 185 <= x <= 320 and 470 <= y <= 510:
                    self.bird_page = self.bird_index // 4
                    self.bird_menu_open = True
                    return
            self.state = 'playing'
            self.vy = self.difficulties[self.difficulty_index][5]
            self.audio.play('flap')
        elif self.state == 'playing':
            self.vy = self.difficulties[self.difficulty_index][5]
            self.audio.play('flap')
            for _ in range(3):
                self.particles.append([75, self.y + random.uniform(-6, 6), random.uniform(-85, -25), random.uniform(-45, 45), random.uniform(.25, .5)])
            self.particles = self.particles[-12:]
        elif self.state == 'over' and self.over_time > .4:
            # Only the button restarts: tapping elsewhere cannot dismiss results.
            if event is not None and getattr(event, 'keysym', '') not in ('space', 'Up'):
                x = (event.x - self.ox) / self.scale
                y = (event.y - self.oy) / self.scale
                if not (112 <= x <= 248 and 318 <= y <= 362):
                    return
            elif event is not None and getattr(event, 'keysym', '') not in ('space', 'Up'):
                return
            self.reset()
            self.state = 'ready'

    def end(self):
        self.profile['games'] = max(0, self.profile_int('games')) + 1
        self.profile['total_points'] = max(0, self.profile_int('total_points')) + self.score
        level_key = 'best_' + self.difficulties[self.difficulty_index][0].lower()
        self.profile[level_key] = max(self.score, self.profile_int(level_key))
        self.save_profile()
        self.state = 'dying'
        self.audio.play('hit')
        self.explosion_age = 0.0
        self.explosion = []
        for i in range(14):
            angle = 2 * math.pi * i / 14 + random.uniform(-.12, .12)
            speed = random.uniform(75, 170)
            self.explosion.append((90, self.y, math.cos(angle)*speed,
                                   math.sin(angle)*speed, random.uniform(3, 6),
                                   random.choice(('#fff3ae', '#ffd34e', '#ff9a3e', '#f26c48'))))
        self.vy = max(80, self.vy)
        self.flash = 0.18
        self.over_time = 0
        if self.score > self.best:
            self.best = self.score
            self.save_best()

    def update(self, dt):
        if self.state == 'paused' or self.bird_menu_open or self.background_menu_open or self.stats_open:
            return
        self.elapsed += dt
        self.score_pop = max(0.0, self.score_pop - dt)
        _, pipe_speed, gap, interval, gravity, _ = self.difficulties[self.difficulty_index]
        self.flash = max(0, self.flash - dt)
        if self.explosion:
            self.explosion_age += dt
            if self.explosion_age > 0.65:
                self.explosion = []
        if self.state == 'over':
            self.over_time += dt
        if self.state == 'dying':
            self.vy += 1050 * dt
            self.y += self.vy * dt
            if self.y >= GROUND - 12:
                self.y = GROUND - 12
                self.vy = 0
                self.state = 'over'
                self.over_time = 0
        for particle in self.particles:
            particle[0] += particle[2] * dt
            particle[1] += particle[3] * dt
            particle[4] -= dt
        self.particles = [p for p in self.particles if p[4] > 0]
        if self.state in ('ready', 'playing'):
            self.ground_offset = (self.ground_offset + pipe_speed * dt) % 24
        if self.state in ('playing', 'dying', 'over'):
            target = 75 if self.state in ('dying', 'over') else max(-25, min(75, self.vy * .13))
            self.bird_angle += (target - self.bird_angle) * (1 - math.exp(-10 * dt))
        else:
            self.bird_angle += (-5 - self.bird_angle) * (1 - math.exp(-10 * dt))
        if self.state != 'playing':
            return
        self.vy += gravity * dt
        self.y += self.vy * dt
        self.spawn -= dt
        if self.spawn <= 0:
            # Randomize the center while leaving safe margins at both edges.
            self.pipes.append([W + 40, random.randint(195, 385), False])
            self.spawn = interval
        for p in self.pipes:
            p[0] -= pipe_speed * dt
            if not p[2] and p[0] + 64 < 90:
                p[2] = True
                self.score += 1
                self.score_pop = 0.3
                self.audio.play('score')
            if p[0] > 105 or p[0] + 68 < 75:
                continue
            # Circle-to-rectangle collision follows the visible pipe caps
            # more closely than a large rectangular hitbox.
            top, bottom = p[1] - gap/2, p[1] + gap/2
            rectangles = ((p[0], 0, p[0]+64, top-25),
                          (p[0]-4, top-25, p[0]+68, top),
                          (p[0]-4, bottom, p[0]+68, bottom+25),
                          (p[0], bottom+25, p[0]+64, GROUND))
            for left, upper, right, lower in rectangles:
                nearest_x = max(left, min(90, right))
                nearest_y = max(upper, min(self.y, lower))
                if (90-nearest_x)**2 + (self.y-nearest_y)**2 < 11**2:
                    self.end()
                    return
        self.pipes = [p for p in self.pipes if p[0] > -90]
        if self.y + 12 >= GROUND or self.y - 12 <= 0:
            self.y = max(12, min(GROUND - 12, self.y))
            self.end()

    def coords(self, *xy):
        return [round((v * self.scale + (self.ox if i % 2 == 0 else self.oy)) * 4) / 4 for i, v in enumerate(xy)]
    def queue(self, kind, coords, options):
        self.frame.append((kind, tuple(coords), options))

    def flush_frame(self):
        # Retain canvas objects between frames; only create/delete them when
        # the scene structure actually changes (for example, a new pipe).
        if len(self.items) != len(self.frame) or any(old[0] != new[0] for old, new in zip(self.items, self.frame)):
            self.canvas.delete('all')
            self.items = []
            for kind, coords, options in self.frame:
                item = getattr(self.canvas, 'create_' + kind)(*coords, **options)
                self.items.append((kind, item, coords, options.copy()))
            return
        for index, (kind, coords, options) in enumerate(self.frame):
            _, item, previous_coords, previous_options = self.items[index]
            if coords != previous_coords:
                self.canvas.coords(item, *coords)
            changed = {k: v for k, v in options.items() if previous_options.get(k) != v}
            if changed:
                self.canvas.itemconfigure(item, **changed)
            self.items[index] = (kind, item, coords, options.copy())

    def rect(self, x1, y1, x2, y2, **kw):
        self.queue('rectangle', self.coords(x1,y1,x2,y2), kw)
    def oval(self, x1, y1, x2, y2, **kw):
        self.queue('oval', self.coords(x1,y1,x2,y2), kw)
    def poly(self, *xy, **kw):
        self.queue('polygon', self.coords(*xy), kw)
    def text(self, x, y, text, size, fill='white', max_width=None, **kw):
        # Negative font sizes are pixels, so measurement matches canvas scaling
        # even on Android devices with unusual display density settings.
        pixels = max(1, int(size * self.scale * 0.68))
        while True:
            if pixels not in self.fonts:
                self.fonts[pixels] = tkfont.Font(root=self.root, family='Helvetica', size=-pixels, weight='bold')
            font = self.fonts[pixels]
            if max_width is None or pixels <= 1:
                break
            key = (pixels, str(text))
            if key not in self.text_widths:
                if len(self.text_widths) > 512:
                    self.text_widths.clear()
                self.text_widths[key] = font.measure(str(text))
            if self.text_widths[key] <= max_width * self.scale:
                break
            pixels -= 1
        self.queue('text', self.coords(x,y), dict(text=text, fill=fill, font=font, **kw))
    def outlined_text(self, x, y, text, size, color='white'):
        for dx, dy in [(-1,0),(1,0),(0,-1),(0,1)]:
            self.text(x+dx,y+dy,text,size,'#31404a')
        self.text(x,y,text,size,color)

    def draw(self):
        self.frame = []
        # Layered sky, drifting clouds and distant scenery.
        _, top_color, bottom_color = self.backgrounds[self.background_index]
        for i in range(8):
            t = i / 7
            color = '#%02x%02x%02x' % tuple(int(a + (b-a)*t) for a,b in zip(top_color,bottom_color))
            self.rect(0, i*64, W, (i+1)*64+1, fill=color, outline='')
        self.oval(268,55,322,109,fill='#ffe8a5',outline='')
        for bx,y in [(25,125),(245,88),(155,220)]:
            x = ((bx - self.elapsed*7*self.difficulties[self.difficulty_index][1]/105 + 100) % 470)-100
            self.oval(x,y,x+76,y+23,fill='#c5edeb',outline='')
            self.oval(x+18,y-14,x+50,y+20,fill='#c5edeb',outline='')
            self.oval(x+40,y-8,x+65,y+20,fill='#c5edeb',outline='')
        self.rect(0,480,360,GROUND, fill='#a8d9ae', outline='')
        for i in range(13):
            x = i*31
            h = 30 + (i*37 % 55)
            self.rect(x,GROUND-h,x+24,GROUND,fill='#8ac99b',outline='')
            self.rect(x+5,GROUND-h+8,x+9,GROUND-h+15,fill='#c8e7c2',outline='')
            self.rect(x+15,GROUND-h+8,x+19,GROUND-h+15,fill='#c8e7c2',outline='')
        for x, center, _ in self.pipes:
            gap = self.difficulties[self.difficulty_index][2]
            top, bottom = center - gap/2, center + gap/2
            self.pipe(x, -10, top, True)
            self.pipe(x, bottom, GROUND+10, False)
        self.rect(0,GROUND,W,H,fill='#ded18c',outline='')
        self.rect(0,GROUND+29,W,GROUND+32,fill='#d0c27b',outline='')
        self.rect(0,GROUND,W,GROUND+10,fill='#74bc52',outline='#426a3c',width=max(1,2*self.scale))
        for i in range(-2, 18):
            x = i*24-self.ground_offset
            self.poly(x,GROUND+11,x+12,GROUND+11,x+1,GROUND+21,x-11,GROUND+21,fill='#c2b56c',outline='')
        y = self.y + (math.sin(self.elapsed*5)*5 if self.state == 'ready' else 0)
        # Fixed effect slots keep the canvas structure stable while particles
        # appear and disappear, avoiding expensive whole-scene rebuilds.
        for i in range(12):
            if i < len(self.particles):
                px, py, vx, vy, life = self.particles[i]
                r = max(1, life * 6)
                self.oval(px-r,py-r,px+r,py+r,fill='#fff4c2',outline='')
            else:
                self.oval(-10,-10,-10,-10,fill='',outline='')
        self.bird(90, y)
        for i in range(14):
            if i < len(self.explosion):
                ex, ey, vx, vy, radius, color = self.explosion[i]
                t = self.explosion_age
                px = ex + vx*t
                py = ey + vy*t + 100*t*t
                r = max(0.5, radius*(1-t/0.65))
                self.oval(px-r,py-r,px+r,py+r,fill=color,outline='')
            else:
                self.oval(-10,-10,-10,-10,fill='',outline='')
        self.rect(0,0,W if self.flash > 0 else 0,GROUND if self.flash > 0 else 0,
                  fill='#ffffff' if self.flash > 0 else '',outline='',stipple='gray50')
        if self.state == 'ready':
            # Separate bordered panels keep labels distinct and easy to read.
            self.rect(70,116,290,157,fill='#fff0bd',outline='#79583f',width=max(1,2*self.scale))
            self.text(180,136,'FLAPPY FLIGHT',19,'#503d35',max_width=200)
            self.rect(100,324,260,365,fill='#f7e8bd',outline='#79583f',width=max(1,2*self.scale))
            self.text(180,344,'TAP TO START',14,'#503d35',max_width=140)
            self.rect(81,377,279,409,fill='#e3f3de',outline='#528165',width=max(1,self.scale))
            self.text(180,393,'Tap anywhere to flap',11,'#315567',max_width=100)
            if self.best:
                self.rect(120,420,240,451,fill='#e3f3de',outline='#528165',width=max(1,self.scale))
                self.text(180,435,'BEST  '+str(self.best),11,'#315567',max_width=100)
            self.rect(40,470,175,510,fill='#e3f3de',outline='#528165',width=max(1,self.scale))
            self.rect(185,470,320,510,fill='#e3f3de',outline='#528165',width=max(1,self.scale))
            self.text(107.5,480,'BACKGROUND',10,'#315567',max_width=120)
            self.text(107.5,497,self.backgrounds[self.background_index][0]+'  >',11,'#315567',max_width=120)
            self.text(252.5,480,'BIRD',10,'#315567',max_width=120)
            self.text(252.5,497,self.birds[self.bird_index][0]+'  >',11,'#315567',max_width=120)
            self.rect(90,520,270,553,fill='#e3f3de',outline='#528165',width=max(1,self.scale))
            self.text(180,536,'LEVEL: ' + self.difficulties[self.difficulty_index][0] + '  >',11,'#315567',max_width=160)
        elif self.state in ('playing', 'paused'):
            pop = math.sin(math.pi * self.score_pop / .3) if self.score_pop else 0
            self.outlined_text(180,65,str(self.score),30 + 4*pop)
            if self.score > self.best:
                self.outlined_text(180,92,'NEW RECORD',12,'#fff3a0')
            self.rect(275,20,345,60,fill='#e3f3de',outline='#528165',width=max(1,self.scale))
            self.text(310,40,'PAUSE',11,'#315567',max_width=60)
            self.rect(15,20,85,60,fill='#e3f3de',outline='#528165',width=max(1,self.scale))
            self.text(50,32,'BEST',9,'#315567',max_width=58)
            self.text(50,48,str(self.best),11,'#315567',max_width=58)
        elif self.state == 'over':
            self.rect(0,0,W,GROUND,fill='#203c48',outline='',stipple='gray50')
            self.rect(85,143,275,184,fill='#fff0bd',outline='#79583f',width=max(1,2*self.scale))
            self.text(180,163,'GAME OVER',18,'#503d35',max_width=170)
            self.rect(65,205,170,296,fill='#f7e8bd',outline='#79583f',width=max(1,2*self.scale))
            self.rect(190,205,295,296,fill='#f7e8bd',outline='#79583f',width=max(1,2*self.scale))
            self.text(117,228,'SCORE',11,'#9a694d',max_width=85)
            self.text(117,265,str(self.score),20,'#503d35',max_width=85)
            self.text(242,228,'BEST',11,'#9a694d',max_width=85)
            self.text(242,265,str(self.best),20,'#503d35',max_width=85)
            self.rect(112,322,248,365,fill='#315b35',outline='')
            self.rect(112,318,248,360,fill='#76bf56',outline='#315b35',width=max(1,2*self.scale))
            self.text(180,339,'RESTART',13,'white',max_width=116)
        if self.state in ('ready', 'over'):
            self.rect(15,20,105,55,fill='#e3f3de',outline='#528165',width=max(1,self.scale))
            self.text(60,37,'STATS',11,'#315567',max_width=78)
            self.rect(255,20,345,55,fill='#e3f3de',outline='#528165',width=max(1,self.scale))
            self.text(300,37,'SETTINGS',11,'#315567',max_width=78)
        if self.state == 'paused':
            self.rect(0,0,W,GROUND,fill='#203c48',outline='',stipple='gray50')
            self.rect(70,190,290,410,fill='#f7e8bd',outline='#79583f',width=max(1,2*self.scale))
            self.text(180,220,'PAUSED',18,'#503d35',max_width=180)
            self.text(180,248,'SCORE: ' + str(self.score),12,'#79583f',max_width=160)
            self.rect(105,275,255,318,fill='#76bf56',outline='#315b35',width=max(1,2*self.scale))
            self.text(180,296,'RESUME',12,'white',max_width=130)
            self.rect(105,335,255,378,fill='#e3f3de',outline='#528165',width=max(1,self.scale))
            self.text(180,356,'END RUN',12,'#315567',max_width=130)
        if self.settings_open:
            self.rect(0,0,W,GROUND,fill='#203c48',outline='',stipple='gray50')
            self.rect(55,142,305,460,fill='#f7e8bd',outline='#79583f',width=max(1,2*self.scale))
            self.text(180,170,'SOUND SETTINGS',16,'#503d35',max_width=220)
            self.text(180,207,'MUSIC',11,'#79583f',max_width=170)
            self.rect(90,225,270,265,fill='#e3f3de',outline='#528165',width=max(1,self.scale))
            self.text(120,245,'-',16,'#315567')
            self.text(180,245,('ON ' + str(round(self.audio.music_volume*100)) + '%') if self.audio.music_on else 'OFF',11,'#315567',max_width=60)
            self.text(240,245,'+',16,'#315567')
            self.text(180,272,'SOUND EFFECTS',11,'#79583f',max_width=170)
            self.rect(90,290,270,330,fill='#e3f3de',outline='#528165',width=max(1,self.scale))
            self.text(120,310,'-',16,'#315567')
            self.text(180,310,('ON ' + str(round(self.audio.sfx_volume*100)) + '%') if self.audio.sfx_on else 'OFF',11,'#315567',max_width=60)
            self.text(240,310,'+',16,'#315567')
            self.rect(112,365,248,405,fill='#76bf56',outline='#315b35',width=max(1,2*self.scale))
            self.text(180,385,'DONE',12,'white',max_width=115)
            self.rect(83,411,277,448,fill='#e3f3de',outline='#528165',width=max(1,self.scale))
            self.text(180,429,'TRACK: ' + self.audio.track_names[self.audio.track_index] + '  >',11,'#315567',max_width=175)
            if not self.audio.available:
                self.rect(90,333,270,358,fill='#fff0bd',outline='#79583f',width=max(1,self.scale))
                self.text(180,345,'RETRY AUDIO' if self.audio.failed else 'ENABLE AUDIO',10,'#a14d40',max_width=160)
        if self.stats_open:
            self.rect(0,0,W,GROUND,fill='#203c48',outline='',stipple='gray50')
            self.rect(35,90,325,545,fill='#f7e8bd',outline='#79583f',width=max(1,2*self.scale))
            self.text(180,120,'YOUR FLIGHT STATS',16,'#503d35',max_width=260)
            self.text(180,155,'COMPLETED RUNS: ' + str(max(0,self.profile_int('games'))),11,'#315567',max_width=250)
            self.text(180,180,'TOTAL POINTS: ' + str(max(0,self.profile_int('total_points'))),11,'#315567',max_width=250)
            for i, level in enumerate(('easy','medium','hard')):
                top = 202+i*37
                self.rect(65,top,295,top+31,fill='#e3f3de',outline='#528165',width=max(1,self.scale))
                self.text(180,top+15,level.upper()+' BEST: '+str(max(0,self.profile_int('best_'+level))),11,'#315567',max_width=210)
            self.text(180,336,'ACHIEVEMENTS',13,'#503d35',max_width=240)
            for i, (goal, label) in enumerate(((1,'FIRST POINT'),(10,'HIGH FLYER'),(25,'SKY MASTER'))):
                top=355+i*33
                self.rect(65,top,295,top+28,fill='#bfdfa9' if self.best >= goal else '#e0d7bd',outline='#79583f',width=max(1,self.scale))
                self.text(180,top+14,label + ('  -  EARNED' if self.best >= goal else '  -  BEST ' + str(goal)),10,'#503d35',max_width=210)
            self.rect(100,480,260,525,fill='#76bf56',outline='#315b35',width=max(1,2*self.scale))
            self.text(180,502,'CLOSE',12,'white',max_width=140)
        if self.bird_menu_open:
            self.rect(0,0,W,GROUND,fill='#203c48',outline='',stipple='gray50')
            self.rect(3,4,357,636,fill='#f7e8bd',outline='#79583f',width=max(1,2*self.scale))
            self.text(180,25,'CHOOSE A BIRD',16,'#503d35',max_width=310)
            self.text(180,44,'Unlock with best score: '+str(self.best),10,'#79583f',max_width=310)
            for index, (name, color) in enumerate(self.birds):
                col, row = index % 4, index // 4
                left, top = 12+col*84, 65+row*50
                self.rect(left+2,top+1,left+82,top+49,fill='#bfdfa9' if index == self.bird_index else '#e3f3de',outline='#528165',width=max(1,self.scale))
                self.bird(left+41, top+20, color=color, preview=True, model=index % 6)
                required = self.bird_unlock_score(index)
                if self.best < required:
                    self.rect(left+3,top+32,left+81,top+48,fill='#d8d1b9',outline='')
                    self.text(left+42,top+40,'LOCKED: '+str(required),9,'#79583f',max_width=72)
                else:
                    self.text(left+42,top+41,name,9,'#315567',max_width=72)
            self.rect(100,580,260,625,fill='#76bf56',outline='#315b35',width=max(1,2*self.scale))
            self.text(180,602,'CLOSE',12,'white',max_width=115)
        if self.background_menu_open:
            self.rect(0,0,W,GROUND,fill='#203c48',outline='',stipple='gray50')
            self.rect(3,4,357,636,fill='#f7e8bd',outline='#79583f',width=max(1,2*self.scale))
            self.text(180,25,'CHOOSE A BACKGROUND',16,'#503d35',max_width=310)
            self.text(180,44,'Unlock with best score: '+str(self.best),10,'#79583f',max_width=310)
            for index, (name, sky, horizon) in enumerate(self.backgrounds):
                col, row = index % 2, index // 2
                left, top = 16+col*164, 82+row*114
                self.rect(left+3,top+3,left+161,top+108,fill='#bfdfa9' if index == self.background_index else '#e3f3de',outline='#528165',width=max(1,self.scale))
                self.rect(left+12,top+9,left+152,top+39,fill='#%02x%02x%02x' % sky,outline='')
                self.rect(left+12,top+39,left+152,top+70,fill='#%02x%02x%02x' % horizon,outline='')
                self.oval(left+120,top+16,left+138,top+34,fill='#ffe8a5',outline='')
                required = self.background_unlock_score(index)
                label = 'LOCKED: ' + str(required) if self.best < required else name
                self.text(left+82,top+89,label,11,'#79583f' if self.best < required else '#315567',max_width=130)
            self.rect(100,580,260,625,fill='#76bf56',outline='#315b35',width=max(1,2*self.scale))
            self.text(180,602,'CLOSE',12,'white',max_width=115)
        self.flush_frame()

    def pipe(self, x, y1, y2, top):
        self.rect(x,y1,x+64,y2,fill='#70c943',outline='#305a32',width=max(1,2*self.scale))
        self.rect(x+7,y1,x+15,y2,fill='#a4e676',outline='')
        self.rect(x+53,y1,x+61,y2,fill='#4ca735',outline='')
        self.rect(x+18,y1,x+20,y2,fill='#88d75a',outline='')
        cy = y2-25 if top else y1
        self.rect(x-4,cy,x+68,cy+25,fill='#70c943',outline='#305a32',width=max(1,2*self.scale))
        self.rect(x+3,cy+4,x+12,cy+21,fill='#a4e676',outline='')
        self.rect(x+15,cy+3,x+62,cy+5,fill='#95de68',outline='')
        self.rect(x+4,cy+21,x+64,cy+23,fill='#4ca735',outline='')

    def bird(self, x, y, color=None, preview=False, model=None):
        # Six distinct silhouettes, in addition to the color choices.
        model = self.bird_index % 6 if model is None else model
        plumage = color or self.birds[self.bird_index][1]
        # Rotate the whole bird around its center to follow its flight arc.
        angle = 0 if preview else self.bird_angle
        a = math.radians(angle)
        ca, sa = math.cos(a), math.sin(a)
        def point(px, py):
            return (x + px*ca - py*sa, y + px*sa + py*ca)
        def shape(points, fill, outline='', width=1):
            xy = []
            for px, py in points:
                xy.extend(point(px, py))
            self.poly(*xy, fill=fill, outline=outline, width=max(1,width*self.scale), smooth=True)
        def ellipse(cx, cy, rx, ry, fill, outline='', width=1):
            shape([(cx+rx*math.cos(i*math.pi/8), cy+ry*math.sin(i*math.pi/8)) for i in range(16)], fill, outline, width)
        # Layered tail, body and feather shapes give the bird more depth.
        if model == 1:
            shape([(-12,-3),(-25,-12),(-21,-1),(-25,5),(-12,5)], plumage, '#78522d')
        elif model == 2:
            shape([(-12,-3),(-23,-6),(-25,1),(-19,7),(-12,5)], plumage, '#78522d')
        else:
            shape([(-12,-3),(-23,-9),(-20,-1),(-23,4),(-12,5)], '#b87937', '#78522d')
        ellipse(0,0,17 if model == 2 else 16,14 if model == 2 else 13,plumage,'#78522d',2)
        if model == 1:
            shape([(-7,-10),(-3,-19),(0,-12),(5,-17),(5,-10)],plumage,'#78522d')
        elif model == 2:
            ellipse(7,-6,8,8,'#f9e0a0')
        elif model == 3:
            shape([(-8,-11),(-10,-18),(-4,-14),(0,-18),(1,-11)],plumage,'#78522d')
        elif model == 4:
            shape([(-9,-10),(-13,-16),(-7,-14),(-4,-19),(0,-12)],'#ffb459','#78522d')
            ellipse(-5,5,5,3,'#ffe4a5')
        elif model == 5:
            ellipse(7,-6,8,7,'#d7b37a')
            shape([(-9,-11),(-12,-16),(-4,-12)],plumage,'#78522d')
        ellipse(0,7,11,4,'#f4c867')
        ellipse(-3,-6,8,3,'#fff1ab')
        wing = math.sin(self.elapsed * (19*self.difficulties[self.difficulty_index][1]/105 if self.state == 'playing' else 10)) * 3 if not preview and self.state != 'over' else 0
        shape([(-15,wing-2),(-7,wing-4),(-2,wing),(-5,wing+5),(-12,wing+7),(-16,wing+4)], '#fff0a3','#b88535')
        ellipse(-8,wing+2,5 if model == 1 else 4,2,'#ffdb72')
        if model == 3:
            ellipse(-10,wing+1,2,2,'#d9a852')
        ellipse(9,-6,6,6,'white','#78522d')
        ellipse(11,-6,2,2.7,'#26333a')
        ellipse(11.5,-7,0.7,0.8,'white')
        shape([(12,1),(23,3),(18,6),(12,5)],'#f5a343','#78522d')
        shape([(12,5),(18,6),(13,8)],'#dc7739','#78522d')

    def tick(self):
        now = time.monotonic()
        dt = min(now-self.last, 0.10)
        self.last = now
        # Small physics steps keep collisions and flight consistent even if a
        # frame takes longer to draw on a slower phone.
        remaining = dt
        while remaining > 0:
            step = min(remaining, 1/120)
            self.update(step)
            remaining -= step
        if not (self.bird_menu_open or self.background_menu_open or self.stats_open) or self.menu_dirty:
            self.draw()
            self.menu_dirty = False
        # Account for rendering time rather than adding it to every frame.
        delay = max(1, int((1/60 - (time.monotonic()-now)) * 1000))
        self.root.after(delay, self.tick)

if __name__ == '__main__':
    root = tk.Tk()
    Game(root)
    root.mainloop()
