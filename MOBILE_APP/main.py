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


REAL_PHRASE = "EU ACEITO O RISCO"


class MobileCockpit(App):
    """Authenticated remote cockpit; exchange credentials stay on the PC."""

    def build(self):
        self.lang = self._load_lang("pt")
        self.pc_url = "http://127.0.0.1:8765"

        root = BoxLayout(orientation="vertical", padding=10, spacing=6)

        self.status = Label(text="PC: ---", font_size=20, size_hint_y=0.07)
        self.balance = Label(text="Saldo/equity: ---", font_size=16, size_hint_y=0.06)
        self.risk = Label(text="Risco: ---", font_size=14, size_hint_y=0.06)
        self.readiness = Label(text="REAL: ---", font_size=14, size_hint_y=0.06)
        self.logs = Label(text="Pronto", font_size=12, size_hint_y=0.16)

        self.ip_input = TextInput(
            text=self.pc_url,
            hint_text="PC: http://100.x.y.z:8765",
            multiline=False,
            size_hint_y=0.08,
        )
        self.token_input = TextInput(
            text="",
            hint_text="Token VST_LOCAL_TOKEN",
            multiline=False,
            password=True,
            size_hint_y=0.08,
        )

        row_conn = BoxLayout(orientation="horizontal", spacing=6, size_hint_y=0.09)
        row_conn.add_widget(Button(text="TESTAR LIGAÇÃO", on_press=lambda _: self.test_connection()))
        row_conn.add_widget(Button(text="ATUALIZAR", on_press=lambda _: self.refresh(0)))

        row1 = BoxLayout(orientation="horizontal", spacing=5, size_hint_y=0.09)
        for label, endpoint in (
            ("INICIAR", "/start"),
            ("PAUSAR", "/pause"),
            ("RETOMAR", "/resume"),
            ("PARAR", "/stop"),
        ):
            row1.add_widget(Button(text=label, on_press=lambda _, e=endpoint: self.command(e)))

        row2 = BoxLayout(orientation="horizontal", spacing=5, size_hint_y=0.09)
        row2.add_widget(Button(text="PAPER", on_press=lambda _: self.set_mode("PAPER")))
        row2.add_widget(Button(text="ARM REAL", on_press=lambda _: self.arm_real()))
        row2.add_widget(Button(text="REAL", on_press=lambda _: self.set_mode("REAL")))
        row2.add_widget(Button(text="DESARMAR", on_press=lambda _: self.command("/real/disarm")))

        row3 = BoxLayout(orientation="horizontal", spacing=5, size_hint_y=0.09)
        row3.add_widget(Button(text="PREFLIGHT", on_press=lambda _: self.command("/preflight")))
        row3.add_widget(Button(text="VALIDAR PAPER", on_press=lambda _: self.refresh_readiness_run()))
        row3.add_widget(Button(text="READINESS", on_press=lambda _: self.refresh_readiness()))

        for widget in (
            self.ip_input,
            self.token_input,
            row_conn,
            self.status,
            self.balance,
            self.risk,
            self.readiness,
            row1,
            row2,
            row3,
            self.logs,
        ):
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

    def _request(self, method: str, endpoint: str, **kwargs):
        return requests.request(
            method,
            self.base_url() + endpoint,
            headers=self.headers(),
            timeout=8,
            **kwargs,
        )

    def test_connection(self) -> None:
        try:
            response = requests.get(self.base_url() + "/health", timeout=5)
            self.logs.text = f"Ligação: HTTP {response.status_code} — {response.text[:120]}"
            self.refresh(0)
        except Exception as exc:
            self.status.text = "PC: offline"
            self.logs.text = f"Falha de ligação: {exc}"

    def command(self, endpoint: str) -> None:
        try:
            response = self._request("POST", endpoint)
            self.logs.text = f"{endpoint}: HTTP {response.status_code}"
            self.refresh(0)
        except Exception as exc:
            self.logs.text = f"Erro comando: {exc}"

    def arm_real(self) -> None:
        try:
            response = self._request("POST", "/real/arm", json={"phrase": REAL_PHRASE})
            self.logs.text = f"ARM REAL: HTTP {response.status_code}"
            self.refresh(0)
        except Exception as exc:
            self.logs.text = f"Erro ARM REAL: {exc}"

    def set_mode(self, mode: str) -> None:
        try:
            response = self._request("POST", "/mode", json={"mode": mode})
            self.logs.text = f"MODO {mode}: HTTP {response.status_code}"
            self.refresh(0)
        except Exception as exc:
            self.logs.text = f"Erro modo: {exc}"

    def refresh_readiness_run(self) -> None:
        try:
            response = self._request("POST", "/readiness/run")
            self.logs.text = f"Validação PAPER: HTTP {response.status_code}"
            self.refresh_readiness()
        except Exception as exc:
            self.logs.text = f"Erro validação: {exc}"

    def refresh_readiness(self) -> None:
        try:
            response = self._request("GET", "/readiness")
            if response.status_code != 200:
                self.readiness.text = f"REAL: acesso recusado ({response.status_code})"
                return
            data = response.json()
            evidence = data.get("evidence", {})
            self.readiness.text = (
                f"REAL: {'PRONTO PARA REVISÃO' if data.get('ready') else 'BLOQUEADO'} | "
                f"States {evidence.get('market_state_rows', 0)}/{evidence.get('required_market_state_rows', 0)} | "
                f"Outcomes {evidence.get('outcome_samples', 0)}/{evidence.get('required_outcome_samples', 0)}"
            )
        except Exception as exc:
            self.readiness.text = f"REAL: erro readiness ({exc})"

    def refresh(self, _dt) -> None:
        try:
            response = self._request("GET", "/status")
            if response.status_code != 200:
                self.status.text = f"PC: acesso recusado ({response.status_code})"
                return
            data = response.json()
            self.status.text = f"PC: {data.get('status', '---')} | Modo: {data.get('mode', '---')}"
            self.balance.text = (
                f"Saldo: {float(data.get('balance', 0)):.2f} | "
                f"Equity: {float(data.get('equity', 0)):.2f}"
            )
            self.risk.text = (
                f"Dia: {float(data.get('pnl_today_pct', 0))*100:.2f}% | "
                f"Semana: {float(data.get('pnl_week_pct', 0))*100:.2f}% | "
                f"DD: {float(data.get('drawdown_pct', 0))*100:.2f}%"
            )
            guard = data.get("real_mode_guard", {})
            self.readiness.text = (
                f"REAL guard: {'ARMADO' if guard.get('armed') else 'desarmado'}"
                f" | {guard.get('remaining_seconds', 0)}s"
            )
            logs = data.get("logs", [])[-5:]
            self.logs.text = "\\n".join(logs) if logs else "Sem logs"
        except Exception as exc:
            self.status.text = "PC: offline"
            self.logs.text = f"Erro status: {exc}"


if __name__ == "__main__":
    MobileCockpit().run()
