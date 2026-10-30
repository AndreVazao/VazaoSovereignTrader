from __future__ import annotations

import os
from kivy.core.window import Window
from kivy.clock import Clock
from kivy.animation import Animation
from kivy.uix.floatlayout import FloatLayout
from kivy.storage.jsonstore import JsonStore
from kivy.graphics import Color, RoundedRectangle, Rectangle
from kivy.metrics import dp
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.gridlayout import GridLayout
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.uix.scrollview import ScrollView
from kivy.uix.spinner import Spinner
from kivy.uix.textinput import TextInput
from kivy.uix.widget import Widget


BG = (0.035, 0.043, 0.060, 1)
PANEL = (0.065, 0.078, 0.105, 1)
PANEL_2 = (0.090, 0.105, 0.140, 1)
TEXT = (0.92, 0.94, 0.98, 1)
MUTED = (0.56, 0.61, 0.70, 1)
ACCENT = (0.33, 0.76, 0.98, 1)
GREEN = (0.26, 0.82, 0.60, 1)
RED = (0.98, 0.38, 0.48, 1)


class RoundedButton(Button):
    def __init__(self, fill=PANEL_2, **kwargs):
        super().__init__(**kwargs)
        self.background_normal = ""
        self.background_down = ""
        self.background_color = (0, 0, 0, 0)
        self.color = TEXT
        self.font_size = dp(13)
        self.bold = True
        self._fill = fill
        with self.canvas.before:
            Color(*fill)
            self._rect = RoundedRectangle(pos=self.pos, size=self.size, radius=[dp(13)])
        self.bind(pos=self._sync, size=self._sync)

    def _sync(self, *_):
        self._rect.pos = self.pos
        self._rect.size = self.size


class Surface(BoxLayout):
    def __init__(self, fill=PANEL, radius=18, **kwargs):
        super().__init__(**kwargs)
        with self.canvas.before:
            Color(*fill)
            self._rect = RoundedRectangle(pos=self.pos, size=self.size, radius=[dp(radius)])
        self.bind(pos=self._sync, size=self._sync)

    def _sync(self, *_):
        self._rect.pos = self.pos
        self._rect.size = self.size


def _label(text="", size=14, color=TEXT, bold=False, **kwargs):
    # Callers may override alignment (e.g. centered sidebar logo). Set defaults
    # in kwargs first so Label never receives duplicate halign/valign arguments.
    kwargs.setdefault("halign", "left")
    kwargs.setdefault("valign", "middle")
    label = Label(
        text=text,
        color=color,
        font_size=dp(size),
        bold=bold,
        **kwargs,
    )
    # Kivy labels do not wrap by default. Bind the text box to the actual
    # allocated width so long Portuguese copy remains readable on phones.
    label.bind(size=lambda instance, value: setattr(instance, "text_size", (value[0], None)))
    label.text_size = (label.width, None)
    return label


def _spacer(height=8):
    return Widget(size_hint_y=None, height=dp(height))



class PixelAgent(Widget):
    """Tiny low-cost pixel-art avatar drawn with a few rectangles."""
    def __init__(self, tint=ACCENT, **kwargs):
        super().__init__(**kwargs)
        self.tint = tint
        self.bind(pos=self._draw, size=self._draw)
        self._draw()

    def _draw(self, *_):
        self.canvas.clear()
        if self.width <= 1 or self.height <= 1:
            return
        unit = min(self.width / 12, self.height / 16)
        ox = self.x + (self.width - unit * 12) / 2
        oy = self.y + (self.height - unit * 16) / 2
        with self.canvas:
            Color(0.91, 0.72, 0.53, 1)
            Rectangle(pos=(ox + 4*unit, oy + 11*unit), size=(4*unit, 4*unit))
            Color(0.12, 0.15, 0.20, 1)
            Rectangle(pos=(ox + 4*unit, oy + 14*unit), size=(4*unit, unit))
            Color(*self.tint)
            Rectangle(pos=(ox + 3*unit, oy + 6*unit), size=(6*unit, 5*unit))
            Rectangle(pos=(ox + unit, oy + 6*unit), size=(2*unit, 5*unit))
            Rectangle(pos=(ox + 9*unit, oy + 6*unit), size=(2*unit, 5*unit))
            Color(0.13, 0.17, 0.23, 1)
            Rectangle(pos=(ox + 3*unit, oy + 2*unit), size=(2*unit, 4*unit))
            Rectangle(pos=(ox + 7*unit, oy + 2*unit), size=(2*unit, 4*unit))


class BuildingPreview(Widget):
    """Lightweight architectural schematic; scales uniformly to preserve proportions."""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.bind(pos=self._draw_building, size=self._draw_building)
        self._draw_building()

    def _draw_building(self, *_):
        self.canvas.clear()
        if self.width <= 1 or self.height <= 1:
            return
        base_w, base_h = 360.0, 190.0
        scale = min(self.width / base_w, self.height / base_h)
        ox = self.x + (self.width - base_w * scale) / 2
        oy = self.y + (self.height - base_h * scale) / 2

        def box(x, y, w, h, rgba, radius=4):
            Color(*rgba)
            RoundedRectangle(
                pos=(ox + x * scale, oy + y * scale),
                size=(w * scale, h * scale),
                radius=[radius * scale],
            )

        with self.canvas:
            # Roof and structural frame remain in a fixed 360:190 coordinate system.
            box(110, 158, 140, 20, (0.20, 0.48, 0.62, 1), 5)
            box(122, 178, 116, 5, (0.33, 0.76, 0.98, 1), 2)
            # CEO top floor
            box(70, 126, 220, 27, (0.09, 0.19, 0.27, 1))
            box(80, 131, 94, 17, (0.16, 0.34, 0.43, 1))
            box(186, 131, 94, 17, (0.16, 0.34, 0.43, 1))
            # Research floor: separate market radar, exchange comparison, investigation and analysis
            box(35, 87, 290, 32, (0.07, 0.14, 0.20, 1))
            for x in (43, 114, 185, 256):
                box(x, 93, 62, 20, (0.12, 0.25, 0.32, 1))
            # Central memory / rapid response / risk-control lower floor
            box(55, 48, 250, 31, (0.08, 0.17, 0.20, 1))
            for x, color in ((63, (0.13, 0.30, 0.28, 1)),
                             (145, (0.13, 0.25, 0.35, 1)),
                             (227, (0.30, 0.20, 0.13, 1))):
                box(x, 54, 74, 19, color)
            # Foundations and pillars
            box(45, 34, 270, 8, (0.19, 0.24, 0.31, 1), 2)
            for x in (68, 132, 196, 260):
                box(x, 20, 8, 14, (0.20, 0.29, 0.37, 1), 2)
            box(32, 10, 296, 8, (0.13, 0.18, 0.25, 1), 2)

def build_chat_cockpit(app):
    app.lang = getattr(app, "lang", {})
    # Persist the first-run experience choice privately; it can be changed later.
    try:
        ui_preferences = JsonStore(os.path.join(app.user_data_dir, "ui_preferences.json"))
        saved_experience = ui_preferences.get("experience").get("mode", "") if ui_preferences.exists("experience") else ""
    except Exception:
        ui_preferences = None
        saved_experience = ""
    if saved_experience not in {"chat", "office"}:
        saved_experience = ""
    phone_layout = Window.width <= dp(520)
    sidebar_width = dp(54) if phone_layout else dp(78)
    root = BoxLayout(orientation="horizontal", spacing=0, padding=[0, dp(4), 0, dp(4)])
    sidebar = Surface(orientation="vertical", size_hint_x=None, width=sidebar_width, padding=[dp(10), dp(14)], spacing=dp(10), fill=(0.025, 0.030, 0.045, 1), radius=0)
    root.add_widget(sidebar)

    logo = _label("VST", size=20, bold=True, halign="center", size_hint_y=None, height=dp(44))
    logo.color = ACCENT
    sidebar.add_widget(logo)

    page_area = BoxLayout(orientation="vertical", padding=[dp(10), dp(10)], spacing=dp(8))
    root.add_widget(page_area)
    app.page_area = page_area
    app.sidebar = sidebar

    pages = {}
    nav_buttons = {}

    def nav(label, key, icon):
        btn = RoundedButton(text=icon + "\n" + label, fill=PANEL, size_hint_y=None, height=dp(58))
        btn.font_size = dp(10)
        btn.bind(on_release=lambda *_: show_page(key))
        sidebar.add_widget(btn)
        nav_buttons[key] = btn

    nav("Chat", "chat", "C")
    nav("Escritório", "office", "E")
    nav("Modo", "experience", "M")
    nav("PC", "pc", "P")
    nav("Ficheiros", "files", "F")
    nav("Humano", "human", "!")
    nav("Readiness", "ready", "R")
    sidebar_spacer = Widget()
    sidebar.add_widget(sidebar_spacer)
    paper_button = RoundedButton(text="PAPER", fill=(0.12, 0.18, 0.17, 1), size_hint_y=None, height=dp(42))
    sidebar.add_widget(paper_button)

    app.status = _label("PC: offline", size=12, color=MUTED, size_hint_y=None, height=dp(30))

    def header(title, subtitle):
        bar = BoxLayout(orientation="horizontal", size_hint_y=None, height=dp(48 if not phone_layout else 54), spacing=dp(5))
        menu = RoundedButton(text="☰" if phone_layout else "MENU", fill=PANEL, size_hint_x=None, width=dp(38 if phone_layout else 46))
        menu.bind(on_release=lambda *_: toggle_sidebar())
        bar.add_widget(menu)
        col = BoxLayout(orientation="vertical")
        col.add_widget(_label(title, size=17, bold=True, size_hint_y=None, height=dp(25)))
        col.add_widget(_label(subtitle, size=11, color=MUTED))
        bar.add_widget(col)
        # app.status is the canonical model label; never reparent one Kivy widget
        # into multiple lazily-created page headers.
        status_label = _label(app.status.text, size=10, color=MUTED, size_hint_x=None, width=dp(74))
        app.status.bind(text=lambda _instance, value, target=status_label: setattr(target, "text", value))
        if not phone_layout:
            bar.add_widget(status_label)
        return bar

    def chat_page():
        page = BoxLayout(orientation="vertical", spacing=dp(8))
        page.add_widget(header("VST", "Vazão Sovereign Trader · cockpit conversacional — PAPER por defeito"))
        card = Surface(orientation="vertical", padding=dp(16), spacing=dp(5), size_hint_y=None, height=dp(78), fill=(0.055, 0.065, 0.090, 1))
        card.add_widget(_label("Como posso ajudar?", size=19, bold=True, size_hint_y=None, height=dp(32)))
        card.add_widget(_label("Envia uma ordem de trabalho, cola um link, pergunta pelo estado ou fala comigo.", size=12, color=MUTED))
        page.add_widget(card)

        scroll = ScrollView(do_scroll_x=False, bar_width=dp(3))
        history = BoxLayout(orientation="vertical", spacing=dp(10), padding=[dp(4), dp(8)], size_hint_y=None)
        history.bind(minimum_height=history.setter("height"))
        app.chat_history_box = history
        app._chat_scroll = scroll
        scroll.add_widget(history)
        page.add_widget(scroll)

        composer = Surface(orientation="horizontal", padding=dp(7), spacing=dp(7), size_hint_y=None, height=dp(62), fill=(0.055, 0.065, 0.090, 1))
        app.chat_input = TextInput(
            hint_text="Escreve uma mensagem…",
            multiline=False,
            background_color=(0.04, 0.048, 0.068, 1),
            foreground_color=TEXT,
            cursor_color=ACCENT,
            padding=[dp(14), dp(10)],
            font_size=dp(14),
        )
        app.chat_input.bind(on_text_validate=lambda *_: app.send_chat_message())
        mic = RoundedButton(text="◉", fill=(0.11, 0.13, 0.18, 1), size_hint_x=None, width=dp(48))
        mic.bind(on_release=lambda *_: app.start_voice_input())
        send = RoundedButton(text="↑", fill=ACCENT, size_hint_x=None, width=dp(52))
        send.color = BG
        send.bind(on_release=lambda *_: app.send_chat_message())
        composer.add_widget(app.chat_input)
        composer.add_widget(mic)
        composer.add_widget(send)
        page.add_widget(composer)
        app._append_chat_message("assistant", "Estou pronto. Podes escrever, colar um link ou tocar no microfone.")
        return page

    def pc_page():
        page = BoxLayout(orientation="vertical", spacing=dp(8))
        page.add_widget(header("PC & Ligação", "Rede privada, emparelhamento e controlo PAPER"))
        card = Surface(orientation="vertical", padding=dp(14), spacing=dp(8), size_hint_y=None, height=dp(310))
        card.add_widget(_label("Endereço do PC em casa (LAN)", size=12, color=MUTED, size_hint_y=None, height=dp(22)))
        app.lan_input = TextInput(text=app.lan_url, multiline=False, hint_text="http://192.168.1.20:8765", size_hint_y=None, height=dp(40), background_color=(0.04, 0.048, 0.068, 1), foreground_color=TEXT)
        app.lan_input.route_kind = "lan"
        app.lan_input.bind(text=app._on_url_changed)
        card.add_widget(app.lan_input)
        card.add_widget(_label("Endereço privado fora de casa (Tailscale)", size=12, color=MUTED, size_hint_y=None, height=dp(22)))
        app.tailscale_input = TextInput(text=app.tailscale_url, multiline=False, hint_text="http://100.x.y.z:8765", size_hint_y=None, height=dp(40), background_color=(0.04, 0.048, 0.068, 1), foreground_color=TEXT)
        app.tailscale_input.route_kind = "tailscale"
        app.tailscale_input.bind(text=app._on_url_changed)
        card.add_widget(app.tailscale_input)
        card.add_widget(_label("Token proprietário (apenas para emparelhar)", size=12, color=MUTED, size_hint_y=None, height=dp(22)))
        app.token_input = TextInput(hint_text="Token temporário", password=True, multiline=False, size_hint_y=None, height=dp(44), background_color=(0.04, 0.048, 0.068, 1), foreground_color=TEXT)
        card.add_widget(app.token_input)
        row = BoxLayout(spacing=dp(7), size_hint_y=None, height=dp(46))
        b = RoundedButton(text="TESTAR", fill=ACCENT); b.color = BG; b.bind(on_release=lambda *_: app.test_connection())
        row.add_widget(b)
        row.add_widget(RoundedButton(text="ATUALIZAR", fill=PANEL_2, on_release=lambda *_: app.refresh(0)))
        card.add_widget(row)
        page.add_widget(card)

        pair = Surface(orientation="vertical", padding=dp(14), spacing=dp(7), size_hint_y=None, height=dp(170))
        pair.add_widget(_label("Emparelhamento seguro", size=15, bold=True, size_hint_y=None, height=dp(26)))
        pair.add_widget(_label("O PC aprova um código de utilização única. O token do dispositivo fica protegido pelo Android Keystore.", size=11, color=MUTED))
        row2 = BoxLayout(spacing=dp(7), size_hint_y=None, height=dp(44))
        row2.add_widget(RoundedButton(text="EMPARELHAR", fill=PANEL_2, on_release=lambda *_: app.begin_pairing()))
        row2.add_widget(RoundedButton(text="CONCLUIR", fill=ACCENT, on_release=lambda *_: app.complete_pairing()))
        pair.add_widget(row2)
        pair.add_widget(RoundedButton(text="ESQUECER DISPOSITIVO", fill=(0.16, 0.07, 0.09, 1), on_release=lambda *_: app.forget_device(), size_hint_y=None, height=dp(42)))
        page.add_widget(pair)

        control = Surface(orientation="vertical", padding=dp(14), spacing=dp(7), size_hint_y=None, height=dp(252))
        control.add_widget(_label("Controlo rápido", size=15, bold=True, size_hint_y=None, height=dp(26)))
        for labels in (("INICIAR","/start"),("PAUSAR","/pause"),("RETOMAR","/resume"),("PARAR","/stop")):
            rowc=BoxLayout(spacing=dp(6), size_hint_y=None, height=dp(44))
            rowc.add_widget(RoundedButton(text=labels[0], fill=PANEL_2, on_release=lambda _,e=labels[1]: app.command(e)))
            control.add_widget(rowc)
        # Keep the page header visible while making all connection and control
        # actions reachable on short phone screens.
        page.remove_widget(card)
        page.remove_widget(pair)
        page.remove_widget(control)
        content = BoxLayout(
            orientation="vertical",
            spacing=dp(8),
            padding=[0, 0, 0, dp(8)],
            size_hint_y=None,
        )
        content.bind(minimum_height=content.setter("height"))
        content.add_widget(card)
        content.add_widget(pair)
        content.add_widget(control)
        scroll = ScrollView(do_scroll_x=False, bar_width=dp(3), scroll_type=["content", "bars"])
        scroll.add_widget(content)
        page.add_widget(scroll)
        app.pc_scroll = scroll
        return page

    def office_page():
        page = BoxLayout(orientation="vertical", spacing=dp(8))
        page.add_widget(header("Escritório Virtual", "Exploração visual local — não depende do cérebro"))

        content = BoxLayout(
            orientation="vertical",
            spacing=dp(9),
            padding=[0, 0, 0, dp(10)],
            size_hint_y=None,
        )
        content.bind(minimum_height=content.setter("height"))

        banner = Surface(
            orientation="vertical",
            padding=dp(12),
            spacing=dp(4),
            size_hint_y=None,
            height=dp(82),
            fill=(0.12, 0.10, 0.055, 1),
        )
        banner.add_widget(_label(
            "DEMO OFFLINE · ESCRITÓRIO SEM MOTOR",
            size=12,
            color=(1.0, 0.78, 0.32, 1),
            bold=True,
            size_hint_y=None,
            height=dp(24),
        ))
        banner.add_widget(_label(
            "Podes explorar as salas e trocar o estilo visual. Não são apresentados agentes, preços ou atividade reais.",
            size=11,
            color=MUTED,
        ))
        content.add_widget(banner)

        # Architectural preview uses a fixed internal coordinate system and uniform scaling.
        # The building itself is never stretched to fill a portrait or landscape viewport.
        building_card = Surface(
            orientation="vertical",
            padding=dp(8),
            spacing=dp(3),
            size_hint_y=None,
            height=dp(188),
            fill=(0.025, 0.045, 0.065, 1),
        )
        building_card.add_widget(_label(
            "EDIFÍCIO · PLANTA PROPORCIONAL",
            size=10,
            color=ACCENT,
            bold=True,
            size_hint_y=None,
            height=dp(20),
        ))
        building_preview = BuildingPreview(size_hint=(1, 1))
        building_card.add_widget(building_preview)
        content.add_widget(building_card)

        # Animated offline scene: visual-only agents move between department stations.
        # It deliberately runs without the backend and never claims real work is happening.
        scene = Surface(
            orientation="vertical",
            padding=dp(8),
            spacing=dp(4),
            size_hint_y=None,
            height=dp(170),
            fill=(0.025, 0.045, 0.065, 1),
        )
        scene.add_widget(_label(
            "VIDA DO ESCRITÓRIO · ANIMAÇÃO LOCAL",
            size=10,
            color=ACCENT,
            bold=True,
            size_hint_y=None,
            height=dp(20),
        ))
        stage = FloatLayout(size_hint_y=1)
        scene.add_widget(stage)
        stage.bind(size=lambda *_: place_agents())
        stage.bind(pos=lambda *_: place_agents())

        stations = [
            ("CEO", "ceo", 0.04),
            ("RADAR", "radar", 0.28),
            ("ANÁLISE", "analysis", 0.52),
            ("MEMÓRIA", "memory", 0.76),
        ]
        for station_name, _room_key, x_fraction in stations:
            marker = _label(station_name, size=8, color=MUTED)
            marker.size_hint = (None, None)
            marker.size = (dp(64), dp(18))
            marker.pos_hint = {"x": x_fraction, "y": 0.03}
            stage.add_widget(marker)

        agents = []
        agent_specs = [
            ("o\n/|\\\n/ \\", "CEO", "ceo", ACCENT, 0.0),
            ("o\n/|\\\n/ \\", "RADAR", "radar", GREEN, 0.7),
            ("o\n/|\\\n/ \\", "ANÁLISE", "analysis", (1.0, 0.72, 0.30, 1), 1.4),
        ]

        def place_agents(*_):
            if not stage.width or not stage.height:
                return
            for index, agent in enumerate(agents):
                if agent.get("moving"):
                    continue
                lane_centres = (0.16, 0.50, 0.84)
                widget = agent["widget"]
                # Keep avatars on one baseline; the former vertical offsets overlapped
                # 64dp text cards inside the short mobile scene.
                widget.x = stage.x + stage.width * lane_centres[index] - widget.width / 2
                widget.y = stage.y + max(dp(4), (stage.height - widget.height) * 0.58)
                label = agent.get("label")
                if label is not None:
                    label.center_x = widget.center_x
                    label.y = max(stage.y, widget.y - dp(17))

        for figure, role, room_key, tint, delay in agent_specs:
            avatar = PixelAgent(tint=tint, size_hint=(None, None), size=(dp(36), dp(48)))
            stage.add_widget(avatar)
            role_label = _label(role, size=8, color=tint, halign="center",
                                 size_hint=(None, None), size=(dp(70), dp(16)))
            stage.add_widget(role_label)
            agents.append({"widget": avatar, "label": role_label, "role": role,
                           "room": room_key, "delay": delay, "moving": False})

        def animate_agents(*_):
            if stage.width <= dp(80):
                return
            for index, agent in enumerate(agents):
                widget = agent["widget"]
                if agent["moving"]:
                    continue
                agent["moving"] = True
                start_x = stage.x + dp(8) + index * dp(18)
                end_x = max(stage.x + dp(8), stage.right - widget.width - dp(8))
                widget.x = start_x
                widget.y = stage.y + stage.height * (0.35 + index * 0.13)
                def begin(_dt, item=agent, w=widget, left=start_x, right=end_x):
                    if not w.parent:
                        item["moving"] = False
                        return
                    forward = Animation(x=right, duration=4.0 + index, t="in_out_sine")
                    backward = Animation(x=left, duration=4.0 + index, t="in_out_sine")
                    def again(*_args):
                        if w.parent:
                            (backward if w.x >= right - dp(2) else forward).start(w)
                    forward.bind(on_complete=lambda *_args: backward.start(w))
                    backward.bind(on_complete=lambda *_args: forward.start(w))
                    forward.start(w)
                Clock.schedule_once(begin, agent["delay"])
        # The offline illustration keeps each avatar within its own lane; avoid
        # continuous cross-stage movement that caused visual collisions on phones.
        Clock.schedule_once(place_agents, 0.3)
        content.add_widget(scene)

        mode_row = BoxLayout(
            orientation="horizontal",
            spacing=dp(7),
            size_hint_y=None,
            height=dp(44),
        )
        mode_row.add_widget(_label("Visualização", size=12, bold=True, size_hint_x=0.8))
        mode_values = ("2.5D leve", "Pixel / 8-bit", "Palitinhos", "Compacta", "HD 3D (futuro)")
        # Keep this preference in private app storage; narrow screens start compact.
        default_mode = "Compacta" if Window.width <= dp(420) else "2.5D leve"
        try:
            office_preferences = JsonStore(os.path.join(app.user_data_dir, "office_preferences.json"))
            saved_mode = office_preferences.get("display").get("mode", default_mode) if office_preferences.exists("display") else default_mode
        except Exception:
            office_preferences = None
            saved_mode = default_mode
        if saved_mode not in mode_values:
            saved_mode = default_mode

        mode = Spinner(
            text=saved_mode,
            values=mode_values,
            size_hint_x=1.6,
            size_hint_y=None,
            height=dp(42),
            background_normal="",
            background_color=PANEL_2,
            color=TEXT,
            font_size=dp(11),
        )
        mode_row.add_widget(mode)
        content.add_widget(mode_row)

        rooms = (
            ("ceo", "CEO · DIREÇÃO", "Topo do edifício", "Direção central e comunicação com os chefes dos departamentos."),
            ("radar", "MARKET RADAR", "Observação de mercado", "Deteção e acompanhamento de movimentos e eventos de mercado."),
            ("compare", "COMPARAÇÃO", "Exchanges separadas", "Comparação independente entre exchanges, custos, liquidez e condições."),
            ("investigation", "INVESTIGAÇÃO", "Recolha de evidência", "Pesquisa de fontes, timestamps e validação do que foi observado."),
            ("analysis", "ANÁLISE", "Hipóteses e estudos", "Análise de dados e hipóteses; resultados reais só aparecem quando ligados ao motor."),
            ("memory", "MEMÓRIA CENTRAL", "Serviço transversal", "Memória partilhada entre departamentos, representada como sala e serviço transversal."),
            ("fast", "RESPOSTA RÁPIDA", "Com limites de risco", "Via de resposta rápida subordinada aos controlos de risco do cérebro."),
            ("risk", "CONTROLO DE RISCO", "Limites e bloqueios", "A interface nunca contorna nem altera os limites de segurança do motor."),
            ("paper", "PAPER LAB", "Testes e simulação", "Área para replay e validação em PAPER, sem executar ordens reais."),
        )

        grid = GridLayout(
            cols=1 if phone_layout else 2,
            spacing=dp(8),
            size_hint_y=None,
            row_default_height=dp(82),
            row_force_default=True,
        )
        grid.bind(minimum_height=grid.setter("height"))
        content.add_widget(grid)

        details = Surface(
            orientation="vertical",
            padding=dp(12),
            spacing=dp(5),
            size_hint_y=None,
            height=dp(126),
        )
        detail_title = _label("CEO · Direção", size=15, bold=True, size_hint_y=None, height=dp(28))
        detail_body = _label(
            "Seleciona uma sala para ver a sua função. Esta é uma demonstração local, sem ligação ao motor.",
            size=11,
            color=MUTED,
        )
        details.add_widget(detail_title)
        details.add_widget(detail_body)
        content.add_widget(details)

        render_status = _label(
            "Modo visual: 2.5D leve · dados reais desligados",
            size=10,
            color=MUTED,
            size_hint_y=None,
            height=dp(24),
        )
        content.add_widget(render_status)

        def select_room(room):
            detail_title.text = room[1].replace("·", "—").title()
            detail_body.text = room[3]

        def render_rooms(selected_mode):
            grid.clear_widgets()
            effective_mode = selected_mode
            fallback_note = ""
            if selected_mode == "HD 3D (futuro)":
                effective_mode = "2.5D leve"
                fallback_note = " · 3D real ainda não integrado; fallback seguro"
            if effective_mode == "Pixel / 8-bit":
                labels = {key: f"[{name.split('·')[0].strip()}]\n{subtitle.upper()}" for key, name, subtitle, _ in rooms}
                fill = (0.10, 0.15, 0.20, 1)
                height = 82
                font_size = 10
            elif effective_mode == "Palitinhos":
                labels = {key: f"o/ {name.split('·')[0].strip()}\n{subtitle}" for key, name, subtitle, _ in rooms}
                fill = (0.045, 0.075, 0.09, 1)
                height = 74
                font_size = 10
            elif effective_mode == "Compacta":
                labels = {key: f"{name.split('·')[0].strip()}\n{subtitle}" for key, name, subtitle, _ in rooms}
                fill = (0.08, 0.10, 0.13, 1)
                height = 58
                font_size = 9
            else:
                labels = {key: f"▣  {name}\n{subtitle}" for key, name, subtitle, _ in rooms}
                fill = (0.075, 0.14, 0.20, 1)
                height = 82
                font_size = 10
            viewport_width = Window.width
            grid.cols = 1 if viewport_width <= dp(520) else (3 if viewport_width >= dp(1000) else 2)
            if viewport_width <= dp(520):
                height = max(height, 70)
            elif viewport_width >= dp(1000):
                height = max(height, 88)
            grid.row_default_height = dp(height)
            for room in rooms:
                button = RoundedButton(
                    text=labels[room[0]],
                    fill=fill,
                    size_hint_y=None,
                    height=dp(height),
                )
                button.font_size = dp(font_size)
                button.bind(on_release=lambda _button, selected=room: select_room(selected))
                grid.add_widget(button)
            render_status.text = (
                f"Modo visual: {effective_mode} · dados reais desligados"
                f"{fallback_note}"
            )
            if selected_mode == "HD 3D (futuro)":
                detail_title.text = "Pré-visualização 3D"
                detail_body.text = "O renderer 3D verdadeiro ainda não está integrado. A demonstração mantém o modo 2.5D leve para não simular uma capacidade inexistente."

        def on_mode_changed(_spinner, value):
            render_rooms(value)
            if office_preferences is not None:
                try:
                    office_preferences.put("display", mode=value)
                except Exception:
                    render_status.text = "Modo visual: " + value + " · preferência não guardada · dados reais desligados"

        mode.bind(text=on_mode_changed)
        render_rooms(mode.text)

        scroll = ScrollView(do_scroll_x=False, bar_width=dp(3), scroll_type=["content", "bars"])
        scroll.add_widget(content)
        page.add_widget(scroll)
        app.office_mode_selector = mode
        app.office_room_grid = grid
        return page

    def files_page():
        page=BoxLayout(orientation="vertical",spacing=dp(8))
        page.add_widget(header("Ficheiros", "INBOX / OUTBOX entre Android e PC"))
        top=Surface(orientation="horizontal",padding=dp(8),spacing=dp(7),size_hint_y=None,height=dp(52))
        top.add_widget(RoundedButton(text="ATUALIZAR",fill=PANEL_2,on_release=lambda *_: app.refresh_exchange()))
        top.add_widget(RoundedButton(text="ENVIAR PARA PC",fill=ACCENT,on_release=lambda *_: app.open_upload_picker()))
        page.add_widget(top)
        app.exchange_box=BoxLayout(orientation="vertical",spacing=dp(6),size_hint_y=None)
        app.exchange_box.bind(minimum_height=app.exchange_box.setter("height"))
        scroll=ScrollView(do_scroll_x=False,bar_width=dp(3)); scroll.add_widget(app.exchange_box); page.add_widget(scroll)
        return page

    def human_page():
        page=BoxLayout(orientation="vertical",spacing=dp(8))
        page.add_widget(header("Intervenção humana", "Login, 2FA, CAPTCHA e confirmações permanecem manuais"))
        info=Surface(orientation="vertical",padding=dp(14),size_hint_y=None,height=dp(82))
        info.add_widget(_label("Quando o PC precisar de ti, o pedido aparece aqui.",size=15,bold=True,size_hint_y=None,height=dp(30)))
        info.add_widget(_label("Não existe bypass automático de CAPTCHA/2FA.",size=11,color=MUTED))
        page.add_widget(info)
        app.human_box=BoxLayout(orientation="vertical",spacing=dp(7),size_hint_y=None)
        app.human_box.bind(minimum_height=app.human_box.setter("height"))
        scroll=ScrollView(do_scroll_x=False,bar_width=dp(3)); scroll.add_widget(app.human_box); page.add_widget(scroll)
        return page

    def ready_page():
        page=BoxLayout(orientation="vertical",spacing=dp(8))
        page.add_widget(header("Readiness", "Evidência e saúde operacional — nunca autorização REAL"))
        card=Surface(orientation="vertical",padding=dp(14),spacing=dp(7))
        app.readiness_card=_label("A consultar…",size=16,bold=True)
        card.add_widget(app.readiness_card)
        card.add_widget(_label("Os indicadores abaixo são informativos e não autorizam execução.",size=11,color=MUTED))
        btn=RoundedButton(text="ATUALIZAR ESTADO",fill=PANEL_2,size_hint_y=None,height=dp(46))
        btn.bind(on_release=lambda *_: app.refresh(0))
        card.add_widget(btn)
        page.add_widget(card)
        return page

    pages["chat"]=chat_page
    pages["office"]=office_page
    pages["pc"]=pc_page
    pages["files"]=files_page
    pages["human"]=human_page
    pages["ready"]=ready_page
    page_instances = {}

    def show_page(key):
        page_area.clear_widgets()
        if key not in page_instances:
            page_instances[key] = pages[key]()
        page=page_instances[key]
        page_area.add_widget(page)
        app.current_page=key
        if key=="files":
            app.refresh_exchange()
        elif key=="human":
            app.refresh_human(0)

    def toggle_sidebar():
        sidebar.width = dp(220) if sidebar.width < dp(100) else dp(78)

    def experience_page():
        page = BoxLayout(orientation="vertical", spacing=dp(10))
        page.add_widget(header("Escolher experiência", "A escolha fica guardada neste dispositivo e pode ser alterada depois."))
        content = BoxLayout(orientation="vertical", spacing=dp(10), padding=[0, 0, 0, dp(8)], size_hint_y=None)
        content.bind(minimum_height=content.setter("height"))
        intro = Surface(orientation="vertical", padding=dp(16), spacing=dp(8), size_hint_y=None, height=dp(118))
        intro.add_widget(_label("Como queres usar o Trader?", size=18, bold=True, size_hint_y=None, height=dp(34)))
        intro.add_widget(_label("A interface visual é opcional. O cérebro corre separado e não depende do escritório.", size=12, color=MUTED))
        content.add_widget(intro)

        def choose_experience(value):
            nonlocal saved_experience
            saved_experience = value
            if ui_preferences is not None:
                try:
                    ui_preferences.put("experience", mode=value)
                except Exception:
                    app.status.text = "Preferência não guardada · dados reais desligados"
            set_navigation_experience(value)
            show_page(value)

        simple = Surface(orientation="vertical", padding=dp(14), spacing=dp(7), size_hint_y=None, height=dp(166))
        simple.add_widget(_label("1 · Chat simples", size=16, bold=True, size_hint_y=None, height=dp(30)))
        simple.add_widget(_label("Interface mais leve; conversa direta com o Trader. Recomendada para aparelhos antigos.", size=12, color=MUTED))
        simple.add_widget(RoundedButton(text="USAR CHAT SIMPLES", fill=ACCENT, size_hint_y=None, height=dp(48), on_release=lambda *_: choose_experience("chat")))
        content.add_widget(simple)

        visual = Surface(orientation="vertical", padding=dp(14), spacing=dp(7), size_hint_y=None, height=dp(166))
        visual.add_widget(_label("2 · Escritório virtual", size=16, bold=True, size_hint_y=None, height=dp(30)))
        visual.add_widget(_label("Abre a planta ilustrada dos departamentos. A renderização continua leve; HD 3D é futuro e usa fallback 2.5D.", size=12, color=MUTED))
        visual.add_widget(RoundedButton(text="USAR ESCRITÓRIO VIRTUAL", fill=PANEL_2, size_hint_y=None, height=dp(48), on_release=lambda *_: choose_experience("office")))
        content.add_widget(visual)
        content.add_widget(_label("Podes mudar esta escolha quando quiseres através de Modo. O escritório não é necessário para o cérebro funcionar.", size=11, color=MUTED, size_hint_y=None, height=dp(46)))
        scroll = ScrollView(do_scroll_x=False, bar_width=dp(3), scroll_type=["content", "bars"])
        scroll.add_widget(content)
        page.add_widget(scroll)
        return page

    pages["experience"] = experience_page

    def set_navigation_experience(value):
        # Chat-only mode hides nonessential navigation to reduce visual clutter.
        # The Modo entry remains visible so the user can switch back at any time.
        for key, button in nav_buttons.items():
            visible = value != "chat" or key in {"chat", "experience"}
            button.height = dp(58) if visible else 0
            button.opacity = 1 if visible else 0
            button.disabled = not visible
        # Hide the spacer and PAPER status action as well in chat-only mode.
        if value == "chat":
            sidebar_spacer.size_hint_y = None
            sidebar_spacer.height = 0
            paper_button.height = 0
            paper_button.opacity = 0
            paper_button.disabled = True
        else:
            sidebar_spacer.size_hint_y = 1
            sidebar_spacer.height = 0
            paper_button.height = dp(42)
            paper_button.opacity = 1
            paper_button.disabled = False

    if saved_experience:
        set_navigation_experience(saved_experience)
        show_page(saved_experience)
    else:
        show_page("experience")

    # Recalculate responsive navigation and office grid after Android rotates.
    def adapt_to_viewport(_window, width, height):
        nonlocal phone_layout
        phone_layout = width <= dp(520)
        sidebar.width = dp(54) if phone_layout else dp(78)
        for button in nav_buttons.values():
            button.font_size = dp(9 if phone_layout else 10)
        office_grid = getattr(app, "office_room_grid", None)
        if office_grid is not None:
            office_grid.cols = 1 if width <= dp(520) else (3 if width >= dp(1000) else 2)
            office_grid.spacing = dp(6 if phone_layout else 8)
        if hasattr(app, "office_mode_selector"):
            app.office_mode_selector.font_size = dp(10 if phone_layout else 12)
        # Refresh the currently displayed page so it measures against the new width.
        if app.current_page in page_instances:
            current = page_instances[app.current_page]
            page_area.remove_widget(current)
            page_area.add_widget(current)
    Window.bind(on_resize=adapt_to_viewport)
    return root
