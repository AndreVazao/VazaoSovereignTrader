from __future__ import annotations

import json
from pathlib import Path

import requests
from kivy.app import App
from kivy.clock import Clock
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.uix.textinput import TextInput


class MobileCockpit(App):
    """Remote cockpit. The PC remains the only trading executor."""

    def build(self):
        self.lang = self._load_lang("pt")
        self.pc_url = "http://127.0.0.1:8765"

        root = BoxLayout(orientation="vertical", padding=12, spacing=8)
        self.status = Label(text="Estado: ---", font_size=20)
        self.balance = Label(text="Saldo: ---", font_size=18)
        self.risk = Label(text="Risco: ---", font_size=15)
        self.validation = Label(text="Validação: ---", font_size=14)
        self.logs = Label(text="Pronto", font_size=12)

        self.ip_input = TextInput(text=self.pc_url, hint_text="URL do PC (ex.: http://100.x.y.z:8765)", multiline=False, size_hint_y=0.08)
        self.token_input = TextInput(text="", hint_text="Token de controlo", multiline=False, password=True, size_hint_y=0.08)
        self.real_phrase = TextInput(text="", hint_text="Frase REAL: EU ACEITO O RISCO", multiline=False, password=True, size_hint_y=0.08)

        row1 = BoxLayout(orientation="horizontal", spacing=6, size_hint_y=0.10)
        for label, endpoint in (("INICIAR", "/start"), ("PAUSAR", "/pause"), ("RETOMAR", "/resume"), ("PARAR", "/stop")):
            row1.add_widget(Button(text=label, on_press=lambda _, e=endpoint: self.command(e)))

        row2 = BoxLayout(orientation="horizontal", spacing=6, size_hint_y=0.10)
        row2.add_widget(Button(text="PAPER", on_press=lambda _: self.set_mode("PAPER")))
        row2.add_widget(Button(text="ARM REAL", on_press=lambda _: self.arm_real()))
        row2.add_widget(Button(text="REAL", on_press=lambda _: self.set_mode("REAL")))
        row2.add_widget(Button(text="DESARMAR", on_press=lambda _: self.command("/real/disarm")))

        for widget in (self.ip_input, self.token_input, self.real_phrase, self.status, self.balance, self.risk, self.validation, row1, row2, self.logs):
            root.add_widget(widget)

        Clock.schedule_interval(self.refresh, 5)
        return root

    def _load_lang(self, code: str) -> dict:
        path = Path(__file__).parent / "lang" / f"{code}.json"
        return json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}

    def headers(self) -> dict:
        return {"X-Token": self.token_input.text.strip()}

    def base_url(self) -> str:
        return self.ip_input.text.strip().rstrip("/")

    def command(self, endpoint: str) -> None:
        try:
            response = requests.post(self.base_url() + endpoint, headers=self.headers(), timeout=8)
            self.logs.text = f"{endpoint}: HTTP {response.status_code}"
            self.refresh(0)
        except Exception as exc:
            self.logs.text = f"Erro comando: {exc}"

    def arm_real(self) -> None:
        try:
            response = requests.post(self.base_url() + "/real/arm", headers=self.headers(), json={"phrase": self.real_phrase.text.strip()}, timeout=8)
            self.logs.text = f"ARM REAL: HTTP {response.status_code}"
            self.refresh(0)
        except Exception as exc:
            self.logs.text = f"Erro ARM REAL: {exc}"

    def set_mode(self, mode: str) -> None:
        try:
            response = requests.post(self.base_url() + "/mode", headers=self.headers(), json={"mode": mode}, timeout=8)
            self.logs.text = f"MODO {mode}: HTTP {response.status_code}"
            self.refresh(0)
        except Exception as exc:
            self.logs.text = f"Erro modo: {exc}"

    def refresh(self, _dt) -> None:
        try:
            response = requests.get(self.base_url() + "/status", headers=self.headers(), timeout=8)
            if response.status_code != 200:
                self.status.text = f"Estado: acesso recusado ({response.status_code})"
                return
            data = response.json()
            self.status.text = f"Estado: {data.get('status')} | Modo: {data.get('mode')}"
            self.balance.text = f"Saldo: {float(data.get('balance', 0)):.2f} | Equity: {float(data.get('equity', 0)):.2f}"
            self.risk.text = f"Dia: {float(data.get('pnl_today_pct', 0))*100:.2f}% | Semana: {float(data.get('pnl_week_pct', 0))*100:.2f}% | DD: {float(data.get('drawdown_pct', 0))*100:.2f}%"
            guard = data.get("real_mode_guard", {})
            self.validation.text = f"REAL guard: {'ARMADO' if guard.get('armed') else 'desarmado'} | Watchdog: {data.get('watchdog', {}).get('ok', '---')}"
            logs = data.get("logs", [])[-5:]
            self.logs.text = "\n".join(logs) if logs else "Sem logs"
        except Exception as exc:
            self.status.text = "Estado: PC offline"
            self.logs.text = f"Erro status: {exc}"


if __name__ == "__main__":
    MobileCockpit().run()
