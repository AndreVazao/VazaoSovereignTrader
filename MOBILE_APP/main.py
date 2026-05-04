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
    def build(self):
        self.lang = self._load_lang("pt")
        self.pc_url = "http://127.0.0.1:8765"
        self.token = "change-this-local-token"

        root = BoxLayout(orientation="vertical", padding=12, spacing=8)
        self.status = Label(text="Estado: ---", font_size=20)
        self.balance = Label(text="Saldo: ---", font_size=18)
        self.week = Label(text="Semana: ---", font_size=18)
        self.assets = Label(text="Ativos: ---", font_size=14)
        self.logs = Label(text="Logs", font_size=12)

        self.ip_input = TextInput(text=self.pc_url, hint_text="URL do PC", multiline=False, size_hint_y=0.08)
        self.token_input = TextInput(text=self.token, hint_text="Token local", multiline=False, password=True, size_hint_y=0.08)

        buttons = BoxLayout(orientation="horizontal", spacing=6, size_hint_y=0.12)
        buttons.add_widget(Button(text="INICIAR", on_press=lambda _: self.command("/start")))
        buttons.add_widget(Button(text="PAUSAR", on_press=lambda _: self.command("/pause")))
        buttons.add_widget(Button(text="PARAR", on_press=lambda _: self.command("/stop")))

        root.add_widget(self.ip_input)
        root.add_widget(self.token_input)
        root.add_widget(self.status)
        root.add_widget(self.balance)
        root.add_widget(self.week)
        root.add_widget(self.assets)
        root.add_widget(buttons)
        root.add_widget(self.logs)

        Clock.schedule_interval(self.refresh, 5)
        return root

    def _load_lang(self, code: str) -> dict:
        path = Path(__file__).parent / "lang" / f"{code}.json"
        if path.exists():
            return json.loads(path.read_text(encoding="utf-8"))
        return {}

    def headers(self) -> dict:
        return {"X-Token": self.token_input.text.strip()}

    def command(self, endpoint: str) -> None:
        self.pc_url = self.ip_input.text.strip().rstrip("/")
        try:
            response = requests.post(self.pc_url + endpoint, headers=self.headers(), timeout=5)
            self.logs.text = f"Comando {endpoint}: {response.status_code}"
            self.refresh(0)
        except Exception as exc:
            self.logs.text = f"Erro comando: {exc}"

    def refresh(self, _dt) -> None:
        self.pc_url = self.ip_input.text.strip().rstrip("/")
        try:
            response = requests.get(self.pc_url + "/status", headers=self.headers(), timeout=5)
            data = response.json()
            self.status.text = f"Estado: {data.get('status')} | Modo: {data.get('mode')}"
            self.balance.text = f"Saldo: {float(data.get('balance', 0)):.2f} | Equity: {float(data.get('equity', 0)):.2f}"
            self.week.text = f"Semana: {float(data.get('pnl_week_pct', 0))*100:.2f}% | DD: {float(data.get('drawdown_pct', 0))*100:.2f}%"
            scores = data.get("asset_scores", {})
            self.assets.text = "Ativos: " + ", ".join(f"{k}:{v:.1f}" for k, v in scores.items())
            logs = data.get("logs", [])[-5:]
            self.logs.text = "\n".join(logs) if logs else "Sem logs"
        except Exception as exc:
            self.status.text = "Estado: PC offline"
            self.logs.text = f"Erro status: {exc}"


if __name__ == "__main__":
    MobileCockpit().run()
