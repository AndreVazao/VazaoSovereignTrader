from __future__ import annotations

import json
from pathlib import Path

import urllib.error
import urllib.request
from kivy.app import App
from kivy.clock import Clock
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.popup import Popup
from kivy.uix.label import Label
from kivy.uix.scrollview import ScrollView
from kivy.uix.textinput import TextInput



class _MobileHTTPResponse:
    def __init__(self, status_code, content):
        self.status_code = status_code
        self.content = content

    def json(self):
        return json.loads(self.content.decode("utf-8"))


REAL_PHRASE = "EU ACEITO O RISCO"

class MobileCockpit(App):
    """Remote cockpit. Exchange credentials never live in this app."""
    def build(self):
        self.lang = self._load_lang("pt")
        self.pc_url = self._load_connection_url()
        self._saved_pc_url = self.pc_url
        self.connection_state = "NOT_TESTED"
        self.human_widgets = {}
        self.exchange_box = BoxLayout(orientation="vertical", spacing=4, size_hint_y=None)
        self.exchange_box.bind(minimum_height=self.exchange_box.setter("height"))
        self._android_activity_bound = False
        self._pending_download = None
        root = BoxLayout(orientation="vertical", padding=8, spacing=5)
        self.status = Label(text="PC: ---", font_size=19, size_hint_y=None, height=35)
        self.balance = Label(text="Saldo/equity: ---", size_hint_y=None, height=28)
        self.risk = Label(text="Risco: ---", size_hint_y=None, height=28)
        self.readiness = Label(text="REAL: ---", size_hint_y=None, height=28)
        self.ip_input = TextInput(text=self.pc_url, hint_text="PC local/Tailscale: http://100.x.y.z:8765", multiline=False, size_hint_y=None, height=42)
        self.ip_input.bind(text=self._on_url_changed)
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
        exchange_row = BoxLayout(orientation="horizontal", spacing=4, size_hint_y=None, height=42)
        exchange_row.add_widget(Button(text="FICHEIROS", on_press=lambda _: self.refresh_exchange()))
        exchange_row.add_widget(Button(text="ENVIAR FICHEIRO AO PC", on_press=lambda _: self.open_upload_picker()))
        exchange_scroll = ScrollView(size_hint_y=0.22)
        exchange_scroll.add_widget(self.exchange_box)
        self.human_box = BoxLayout(orientation="vertical", spacing=5, size_hint_y=None)
        self.human_box.bind(minimum_height=self.human_box.setter("height"))
        human_scroll = ScrollView(size_hint_y=0.35)
        human_scroll.add_widget(self.human_box)
        for w in (self.ip_input, self.token_input, row_conn, self.status, self.balance, self.risk, self.readiness, row1, row2, exchange_row, exchange_scroll, human_scroll):
            root.add_widget(w)
        Clock.schedule_interval(self.refresh, 5)
        Clock.schedule_interval(self.refresh_human, 3)
        self._bind_android_activity()
        Clock.schedule_interval(self.heartbeat, 10)
        return root

    def _bind_android_activity(self):
        try:
            from android import activity
            activity.bind(on_activity_result=self._on_android_activity_result)
            self._android_activity_bound = True
        except Exception:
            self._android_activity_bound = False

    def _android_intent(self, action: str, filename: str | None = None):
        from jnius import autoclass
        Intent = autoclass("android.content.Intent")
        intent = Intent(action)
        intent.addCategory(Intent.CATEGORY_OPENABLE)
        intent.setType("*/*")
        if filename:
            intent.putExtra(Intent.EXTRA_TITLE, filename)
        return intent

    def open_upload_picker(self):
        try:
            from android import activity
            activity.startActivityForResult(self._android_intent("android.intent.action.OPEN_DOCUMENT"), 4101)
        except Exception as exc:
            self.status.text = f"Seletor Android indisponível: {exc}"

    def _on_android_activity_result(self, request_code, result_code, intent):
        try:
            from jnius import autoclass
            Activity = autoclass("android.app.Activity")
            if result_code != Activity.RESULT_OK or intent is None:
                return
            uri = intent.getData()
            if request_code == 4101:
                self._upload_android_uri(uri)
            elif request_code == 4102 and self._pending_download:
                self._write_android_download(uri, self._pending_download)
        except Exception as exc:
            self.status.text = f"Ficheiro Android: {exc}"

    @staticmethod
    def _read_android_uri(uri):
        from jnius import autoclass
        PythonActivity = autoclass("org.renpy.android.PythonActivity")
        resolver = PythonActivity.mActivity.getContentResolver()
        stream = resolver.openInputStream(uri)
        chunks = []
        buffer = bytearray(64 * 1024)
        try:
            while True:
                count = stream.read(buffer)
                if count is None or int(count) <= 0:
                    break
                chunks.append(bytes(buffer[:int(count)]))
        finally:
            stream.close()
        return b"".join(chunks)

    def _upload_android_uri(self, uri):
        try:
            data = self._read_android_uri(uri)
            name = str(uri.getLastPathSegment() or "mobile-upload.bin").split("/")[-1]
            response = self._request(
                "POST",
                "/operator-files/upload",
                files={"file": (name, data)},
                timeout=30,
            )
            if response.status_code == 200:
                self.status.text = f"INBOX: {name} enviado ao PC"
                self.refresh_exchange()
            else:
                self.status.text = f"Upload recusado: HTTP {response.status_code}"
        except Exception as exc:
            self.status.text = f"Upload falhou: {exc}"

    def refresh_exchange(self):
        try:
            response = self._request("GET", "/operator-files")
            if response.status_code != 200:
                self.status.text = f"Ficheiros: HTTP {response.status_code}"
                return
            payload = response.json()
            self.exchange_box.clear_widgets()
            self.exchange_box.add_widget(Label(text="OUTBOX — ficheiros preparados pelo PC", size_hint_y=None, height=30))
            files = payload.get("folders", {}).get("OUTBOX", [])
            if not files:
                self.exchange_box.add_widget(Label(text="Sem ficheiros no OUTBOX.", size_hint_y=None, height=28))
            for item in files:
                row = BoxLayout(orientation="horizontal", spacing=4, size_hint_y=None, height=38)
                row.add_widget(Label(text=f"{item.get('name')} ({item.get('size', 0)} B)"))
                row.add_widget(Button(text="BAIXAR", size_hint_x=0.28, on_press=lambda _, x=item: self.download_exchange_file("OUTBOX", x["name"])))
                self.exchange_box.add_widget(row)
            self.exchange_box.add_widget(Label(text="INBOX — ficheiros enviados do telemóvel", size_hint_y=None, height=30))
            inbox = payload.get("folders", {}).get("INBOX", [])
            if not inbox:
                self.exchange_box.add_widget(Label(text="Sem ficheiros no INBOX.", size_hint_y=None, height=28))
            for item in inbox[-20:]:
                self.exchange_box.add_widget(Label(text=f"✓ {item.get('name')} ({item.get('size', 0)} B)", size_hint_y=None, height=28))
        except Exception as exc:
            self.status.text = f"Ficheiros: {exc}"

    def download_exchange_file(self, folder, name):
        try:
            response = self._request("GET", f"/operator-files/{folder}/{name}", timeout=30)
            if response.status_code != 200:
                self.status.text = f"Download recusado: HTTP {response.status_code}"
                return
            self._pending_download = (name, response.content)
            from android import activity
            activity.startActivityForResult(self._android_intent("android.intent.action.CREATE_DOCUMENT", name), 4102)
        except Exception as exc:
            self.status.text = f"Download falhou: {exc}"

    def _write_android_download(self, uri, payload):
        name, data = payload
        try:
            from jnius import autoclass
            PythonActivity = autoclass("org.renpy.android.PythonActivity")
            resolver = PythonActivity.mActivity.getContentResolver()
            stream = resolver.openOutputStream(uri)
            try:
                stream.write(data)
                stream.flush()
            finally:
                stream.close()
            self.status.text = f"Guardado no telemóvel: {name}"
        finally:
            self._pending_download = None

    def _load_lang(self, code):
        path = Path(__file__).parent / "lang" / f"{code}.json"
        return json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}

    def _connection_config_path(self):
        return Path(self.user_data_dir) / "connection.json"

    def _load_connection_url(self):
        default = "http://127.0.0.1:8765"
        try:
            path = self._connection_config_path()
            if path.exists():
                payload = json.loads(path.read_text(encoding="utf-8"))
                url = str(payload.get("pc_url", "")).strip().rstrip("/")
                if url.startswith(("http://", "https://")):
                    return url
        except (OSError, ValueError, TypeError):
            pass
        return default

    def _save_connection_url(self, url=None):
        value = (url if url is not None else self.ip_input.text).strip().rstrip("/")
        if not value.startswith(("http://", "https://")):
            return
        try:
            path = self._connection_config_path()
            path.parent.mkdir(parents=True, exist_ok=True)
            if value != getattr(self, "_saved_pc_url", None):
                path.write_text(json.dumps({"pc_url": value}, indent=2), encoding="utf-8")
                self._saved_pc_url = value
            self.pc_url = value
        except OSError:
            # Connection still works for this session if Android storage is unavailable.
            pass

    def _on_url_changed(self, _widget, value):
        self.pc_url = value.strip().rstrip("/")

    def headers(self):
        # Deliberately do not persist the local control token in the app config.
        return {"X-Token": self.token_input.text.strip()}

    def base_url(self):
        return self.ip_input.text.strip().rstrip("/")

    def _request(self, method, endpoint, **kwargs):
        headers = self.headers()
        timeout = kwargs.pop("timeout", 8)
        payload = None
        if "json" in kwargs:
            payload = json.dumps(kwargs.pop("json")).encode("utf-8")
            headers["Content-Type"] = "application/json"
        elif "files" in kwargs:
            files = kwargs.pop("files")
            boundary = "----VazaoMobileBoundary7MA4YWxkTrZu0gW"
            chunks = []
            for field, (filename, data) in files.items():
                chunks.append(
                    f"--{boundary}\r\n"
                    f'Content-Disposition: form-data; name="{field}"; filename="{filename}"\r\n'
                    "Content-Type: application/octet-stream\r\n\r\n".encode("utf-8")
                )
                chunks.append(data)
                chunks.append(b"\r\n")
            chunks.append(f"--{boundary}--\r\n".encode("utf-8"))
            payload = b"".join(chunks)
            headers["Content-Type"] = f"multipart/form-data; boundary={boundary}"
        if kwargs:
            raise ValueError(f"Opções HTTP não suportadas: {', '.join(kwargs)}")
        request = urllib.request.Request(
            self.base_url() + endpoint,
            data=payload,
            headers=headers,
            method=method.upper(),
        )
        try:
            with urllib.request.urlopen(request, timeout=timeout) as result:
                return _MobileHTTPResponse(result.status, result.read())
        except urllib.error.HTTPError as exc:
            return _MobileHTTPResponse(exc.code, exc.read())


    def test_connection(self):
        try:
            response = self._request("GET", "/health", timeout=5)
            if response.status_code == 200:
                self._save_connection_url(self.base_url())
                self.connection_state = "CONNECTED"
                self.status.text = f"PC: ligado | {self.base_url()}"
                self.refresh(0)
            else:
                self.connection_state = "RETRYING"
                self.status.text = f"PC: resposta HTTP {response.status_code}"
        except Exception as exc:
            self.connection_state = "OFFLINE"
            self.status.text = "PC: offline — vou tentar novamente automaticamente"
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

    def heartbeat(self, _dt=0):
        try:
            self._request("POST", "/human-interaction/heartbeat", json={"source": "mobile"})
        except Exception:
            pass
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
            self._request("POST", "/human-interaction/respond", json={"request_id": item["request_id"], "claim_token": item.get("claim_token", ""), "action": "fill", "values": values})
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
            self.connection_state = "CONNECTED"
            self._save_connection_url(self.base_url())
            self.status.text = f"PC: ligado | {data.get('status', '---')} | Modo: {data.get('mode', '---')}"
            self.balance.text = f"Saldo: {float(data.get('balance', 0)):.2f} | Equity: {float(data.get('equity', 0)):.2f}"
            self.risk.text = f"Dia: {float(data.get('pnl_today_pct', 0))*100:.2f}% | Semana: {float(data.get('pnl_week_pct', 0))*100:.2f}% | DD: {float(data.get('drawdown_pct', 0))*100:.2f}%"
            guard = data.get("real_mode_guard", {})
            self.readiness.text = f"REAL: {'ARMADO' if guard.get('armed') else 'bloqueado'} | {guard.get('remaining_seconds', 0)}s"
        except Exception:
            self.connection_state = "OFFLINE"
            self.status.text = "PC: offline — reconexão automática a cada 5 s"

if __name__ == "__main__":
    MobileCockpit().run()
