from __future__ import annotations

import json
from pathlib import Path

import requests
from kivy.app import App
from kivy.clock import Clock
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.uix.scrollview import ScrollView
from kivy.uix.textinput import TextInput

REAL_PHRASE = "EU ACEITO O RISCO"

class MobileCockpit(App):
    """Remote cockpit. Exchange credentials never live in this app."""
    def build(self):
        self.lang = self._load_lang("pt")
        self.pc_url = "http://127.0.0.1:8765"
        self.human_widgets = {}
        root = BoxLayout(orientation="vertical", padding=8, spacing=5)
        self.status = Label(text="PC: ---", font_size=19, size_hint_y=None, height=35)
        self.balance = Label(text="Saldo/equity: ---", size_hint_y=None, height=28)
        self.risk = Label(text="Risco: ---", size_hint_y=None, height=28)
        self.readiness = Label(text="REAL: ---", size_hint_y=None, height=28)
        self.ip_input = TextInput(text=self.pc_url, hint_text="PC Tailscale: http://100.x.y.z:8765", multiline=False, size_hint_y=None, height=42)
        self.token_input = TextInput(hint_text="Token VST_LOCAL_TOKEN", multiline=False, password=True, size_hint_y=None, height=42)
        row_conn = BoxLayout(orientation="horizontal", spacing=5, size_hint_y=None, height=42)
        row_conn.add_widget(Button(text="TESTAR", on_press=lambda _: self.test_connection()))
        row_conn.add_widget(Button(text="ATUALIZAR", on_press=lambda _: self.refresh(0)))
        row1 = BoxLayout(orientation="horizontal", spacing=4, size_hint_y=None, height=42)
        for label, endpoint in (("INICIAR", "/start"), ("PAUSAR", "/pause"), ("RETOMAR", "/resume"), ("PARAR", "/stop")):
            row1.add_widget(Button(text=label, on_press=lambda _, e=endpoint: self.command(e)))
        row2 = BoxLayout(orientation="horizontal", spacing=4, size_hint_y=None, height=42)
        row2.add_widget(Button(text="PAPER", on_press=lambda _: self.set_mode("PAPER")))
        row2.add_widget(Button(text="ARM REAL", on_press=lambda _: self.arm_real()))
        row2.add_widget(Button(text="REAL", on_press=lambda _: self.set_mode("REAL")))
        row2.add_widget(Button(text="DESARMAR", on_press=lambda _: self.command("/real/disarm")))
        self.human_box = BoxLayout(orientation="vertical", spacing=5, size_hint_y=None)
        self.human_box.bind(minimum_height=self.human_box.setter("height"))
        human_scroll = ScrollView(size_hint_y=0.35)
        human_scroll.add_widget(self.human_box)
        for w in (self.ip_input, self.token_input, row_conn, self.status, self.balance, self.risk, self.readiness, row1, row2, human_scroll):
            root.add_widget(w)
        Clock.schedule_interval(self.refresh, 5)
        Clock.schedule_interval(self.refresh_human, 3)
        return root

    def _load_lang(self, code):
        path = Path(__file__).parent / "lang" / f"{code}.json"
        return json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}

    def headers(self):
        return {"X-Token": self.token_input.text.strip()}

    def base_url(self):
        return self.ip_input.text.strip().rstrip("/")

    def _request(self, method, endpoint, **kwargs):
        return requests.request(method, self.base_url() + endpoint, headers=self.headers(), timeout=8, **kwargs)

    def test_connection(self):
        try:
            response = requests.get(self.base_url() + "/health", timeout=5)
            self.status.text = f"PC: HTTP {response.status_code}"
            self.refresh(0)
        except Exception as exc:
            self.status.text = "PC: offline"
            self.readiness.text = f"Bridge: {exc}"

    def command(self, endpoint):
        try:
            response = self._request("POST", endpoint)
            self.status.text = f"{endpoint}: HTTP {response.status_code}"
            self.refresh(0)
        except Exception as exc:
            self.status.text = f"PC: offline — {exc}"

    def arm_real(self):
        try:
            self._request("POST", "/real/arm", json={"phrase": REAL_PHRASE})
            self.refresh(0)
        except Exception as exc:
            self.status.text = f"ARM erro: {exc}"

    def set_mode(self, mode):
        try:
            self._request("POST", "/mode", json={"mode": mode})
            self.refresh(0)
        except Exception as exc:
            self.status.text = f"Modo erro: {exc}"

    def refresh_human(self, _dt=0):
        try:
            response = self._request("GET", "/human-interaction/pending")
            if response.status_code != 200:
                return
            items = [x for x in response.json().get("requests", []) if x.get("status") in {"PENDING", "RESPONDED", "APPLIED"}]
            self.human_box.clear_widgets()
            self.human_widgets.clear()
            if not items:
                self.human_box.add_widget(Label(text="✓ Sem intervenções humanas pendentes", size_hint_y=None, height=30))
                return
            self.human_box.add_widget(Label(text="⚠ INTERVENÇÃO NO PC — LOGIN / 2FA / CAPTCHA", size_hint_y=None, height=36))
            for item in items:
                box = BoxLayout(orientation="vertical", spacing=3, size_hint_y=None, height=190 + 55 * len(item.get("fields", [])))
                box.add_widget(Label(text=f"{item.get('title')} — {item.get('platform')}", size_hint_y=None, height=30))
                box.add_widget(Label(text=item.get("message", ""), size_hint_y=None, height=45))
                fields = {}
                for field in item.get("fields", []):
                    inp = TextInput(hint_text=field.get("label", field.get("name", "valor")), multiline=False, password=field.get("type") == "secret", size_hint_y=None, height=40)
                    box.add_widget(inp)
                    fields[field.get("name", "value")] = inp
                actions = BoxLayout(orientation="horizontal", spacing=4, size_hint_y=None, height=42)
                label = "ENVIAR AO PC" if item.get("status") == "PENDING" else ("A AGUARDAR PC…" if item.get("status") == "RESPONDED" else "APLICADO")
                actions.add_widget(Button(text=label, disabled=item.get("status") != "PENDING", on_press=lambda _, i=item, f=fields: self.respond_human(i, f)))
                actions.add_widget(Button(text="CANCELAR", on_press=lambda _, i=item: self.cancel_human(i)))
                box.add_widget(actions)
                self.human_box.add_widget(box)
        except Exception:
            pass

    def respond_human(self, item, fields):
        try:
            values = {name: widget.text for name, widget in fields.items()}
            self._request("POST", "/human-interaction/respond", json={"request_id": item["request_id"], "action": "fill", "values": values})
            for widget in fields.values():
                widget.text = ""
            self.refresh_human(0)
        except Exception as exc:
            self.status.text = f"Intervenção não enviada: {exc}"

    def cancel_human(self, item):
        try:
            self._request("POST", "/human-interaction/cancel", json={"request_id": item["request_id"]})
            self.refresh_human(0)
        except Exception as exc:
            self.status.text = f"Cancelamento falhou: {exc}"

    def refresh(self, _dt):
        try:
            response = self._request("GET", "/status")
            if response.status_code != 200:
                self.status.text = f"PC: acesso recusado ({response.status_code})"
                return
            data = response.json()
            self.status.text = f"PC: {data.get('status', '---')} | Modo: {data.get('mode', '---')}"
            self.balance.text = f"Saldo: {float(data.get('balance', 0)):.2f} | Equity: {float(data.get('equity', 0)):.2f}"
            self.risk.text = f"Dia: {float(data.get('pnl_today_pct', 0))*100:.2f}% | Semana: {float(data.get('pnl_week_pct', 0))*100:.2f}% | DD: {float(data.get('drawdown_pct', 0))*100:.2f}%"
            guard = data.get("real_mode_guard", {})
            self.readiness.text = f"REAL: {'ARMADO' if guard.get('armed') else 'bloqueado'} | {guard.get('remaining_seconds', 0)}s"
        except Exception:
            self.status.text = "PC: offline — Tailscale/API indisponível"

if __name__ == "__main__":
    MobileCockpit().run()
