from __future__ import annotations

from kivy.graphics import Color, RoundedRectangle
from kivy.metrics import dp
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.uix.scrollview import ScrollView
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
    return Label(
        text=text,
        color=color,
        font_size=dp(size),
        bold=bold,
        halign="left",
        valign="middle",
        **kwargs,
    )


def _spacer(height=8):
    return Widget(size_hint_y=None, height=dp(height))


def build_chat_cockpit(app):
    app.lang = getattr(app, "lang", {})
    root = BoxLayout(orientation="horizontal", spacing=0)
    sidebar = Surface(orientation="vertical", size_hint_x=None, width=dp(78), padding=[dp(10), dp(14)], spacing=dp(10), fill=(0.025, 0.030, 0.045, 1), radius=0)
    root.add_widget(sidebar)

    logo = _label("VST", size=20, bold=True, halign="center", size_hint_y=None, height=dp(44))
    logo.color = ACCENT
    sidebar.add_widget(logo)

    page_area = BoxLayout(orientation="vertical", padding=[dp(10), dp(10)], spacing=dp(8))
    root.add_widget(page_area)
    app.page_area = page_area
    app.sidebar = sidebar

    pages = {}

    def nav(label, key, icon):
        btn = RoundedButton(text=icon + "\n" + label, fill=PANEL, size_hint_y=None, height=dp(58))
        btn.font_size = dp(10)
        btn.bind(on_release=lambda *_: show_page(key))
        sidebar.add_widget(btn)

    nav("Chat", "chat", "✦")
    nav("PC", "pc", "⌂")
    nav("Ficheiros", "files", "□")
    nav("Humano", "human", "!")
    nav("Readiness", "ready", "◌")
    sidebar.add_widget(Widget())
    sidebar.add_widget(RoundedButton(text="PAPER", fill=(0.12, 0.18, 0.17, 1), size_hint_y=None, height=dp(42)))

    app.status = _label("PC: offline", size=12, color=MUTED, size_hint_y=None, height=dp(30))

    def header(title, subtitle):
        bar = BoxLayout(orientation="horizontal", size_hint_y=None, height=dp(48), spacing=dp(8))
        menu = RoundedButton(text="☰", fill=PANEL, size_hint_x=None, width=dp(46))
        menu.bind(on_release=lambda *_: toggle_sidebar())
        bar.add_widget(menu)
        col = BoxLayout(orientation="vertical")
        col.add_widget(_label(title, size=17, bold=True, size_hint_y=None, height=dp(25)))
        col.add_widget(_label(subtitle, size=11, color=MUTED))
        bar.add_widget(col)
        bar.add_widget(app.status)
        return bar

    def chat_page():
        page = BoxLayout(orientation="vertical", spacing=dp(8))
        page.add_widget(header("Sovereign Assistant", "O teu cockpit conversacional — PAPER por defeito"))
        card = Surface(orientation="vertical", padding=dp(16), spacing=dp(5), size_hint_y=None, height=dp(78), fill=(0.055, 0.065, 0.090, 1))
        card.add_widget(_label("Como posso ajudar?", size=19, bold=True, size_hint_y=None, height=dp(32)))
        card.add_widget(_label("Envia uma ordem de trabalho, cola um link, pergunta pelo estado ou fala comigo.", size=12, color=MUTED))
        page.add_widget(card)

        scroll = ScrollView(do_scroll_x=False, bar_width=dp(3))
        history = BoxLayout(orientation="vertical", spacing=dp(10), padding=[dp(4), dp(8)], size_hint_y=None)
        history.bind(minimum_height=history.setter("height"))
        app.chat_history_box = history
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
        card = Surface(orientation="vertical", padding=dp(14), spacing=dp(8))
        card.add_widget(_label("Endereço do PC", size=12, color=MUTED, size_hint_y=None, height=dp(22)))
        app.ip_input = TextInput(text=app.pc_url, multiline=False, hint_text="http://100.x.y.z:8765", size_hint_y=None, height=dp(44), background_color=(0.04, 0.048, 0.068, 1), foreground_color=TEXT)
        app.ip_input.bind(text=app._on_url_changed)
        card.add_widget(app.ip_input)
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

        control = Surface(orientation="vertical", padding=dp(14), spacing=dp(7))
        control.add_widget(_label("Controlo rápido", size=15, bold=True, size_hint_y=None, height=dp(26)))
        for labels in (("INICIAR","/start"),("PAUSAR","/pause"),("RETOMAR","/resume"),("PARAR","/stop")):
            rowc=BoxLayout(spacing=dp(6), size_hint_y=None, height=dp(44))
            rowc.add_widget(RoundedButton(text=labels[0], fill=PANEL_2, on_release=lambda _,e=labels[1]: app.command(e)))
            control.add_widget(rowc)
        page.add_widget(control)
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

    show_page("chat")
    return root
