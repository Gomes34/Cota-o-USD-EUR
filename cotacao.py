
# app.py
# Windows (desktop) - Python + PySide6
# App com interface para escolher horário/moedas e rodar em segundo plano no System Tray.
# No horário agendado, abre uma janela flutuante (topmost) com as cotações (base BRL).
#
# Instale:
#   pip install PySide6 requests
#
# Execute:
#   python app.py

import sys
import json
import threading
from datetime import datetime, timedelta

from pathlib import Path

import requests
from PySide6.QtCore import Qt, QTimer, QPropertyAnimation, QEasingCurve, Signal, QObject
from PySide6.QtGui import QFont, QAction, QIcon
from PySide6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QCheckBox, QLineEdit, QMessageBox, QFrame,
    QSystemTrayIcon, QMenu, QStyle
)

CONFIG_FILE = "config.json"
AVAILABLE_COINS = ["USD", "EUR", "GBP", "ARS", "JPY", "CAD", "AUD", "BTC"]


def load_config():
    try:
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            cfg = json.load(f)
        if "time" not in cfg:
            cfg["time"] = "09:00"
        if "coins" not in cfg or not isinstance(cfg["coins"], list):
            cfg["coins"] = ["USD", "EUR"]
        return cfg
    except Exception:
        return {"time": "09:00", "coins": ["USD", "EUR"]}


def save_config(cfg):
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(cfg, f, ensure_ascii=False, indent=2)


def fetch_quotes(coins):
    pairs = ",".join([f"{c}-BRL" for c in coins])
    url = f"https://economia.awesomeapi.com.br/json/last/{pairs}"
    data = requests.get(url, timeout=10).json()

    rows = []
    for c in coins:
        key = f"{c}BRL"
        q = data.get(key)
        if not q:
            continue
        bid = float(q.get("bid"))
        rows.append((c, bid))
    return rows


import sys
import json
import threading
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Tuple, Optional

import requests
from PySide6.QtCore import (
    Qt, QTimer, QPropertyAnimation, QEasingCurve, Signal, QObject, QStandardPaths
)
from PySide6.QtGui import (
    QFont, QAction, QIcon, QCursor
)
from PySide6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QCheckBox, QLineEdit, QMessageBox, QFrame,
    QSystemTrayIcon, QMenu, QStyle, QGridLayout, QGraphicsDropShadowEffect, QSizePolicy
)

AVAILABLE_COINS = ["USD", "EUR", "GBP", "ARS", "JPY", "CAD", "AUD", "BTC"]
APP_NAME = "CotacaoBRLTray"

# ------------------ Visual (QSS) ------------------
QSS = """
/* Base */
QWidget {
    background: #0f1115;
    color: #e8eaf0;
    font-family: "Segoe UI";
    font-size: 11pt;
}

/* Labels */
QLabel#Title {
    font-size: 15pt;
    font-weight: 700;
    color: #f2f4f8;
}
QLabel#Subtitle {
    color: rgba(232,234,240,170);
    font-size: 10.5pt;
}
QLabel#Section {
    font-size: 10.5pt;
    font-weight: 600;
    color: rgba(232,234,240,200);
    margin-top: 8px;
}
QLabel#Status {
    padding: 10px 12px;
    border-radius: 12px;
    background: rgba(255,255,255,0.06);
    border: 1px solid rgba(255,255,255,0.08);
    color: rgba(232,234,240,210);
}

/* Card container */
QFrame#Card {
    background: rgba(255,255,255,0.04);
    border: 1px solid rgba(255,255,255,0.09);
    border-radius: 16px;
}

/* Inputs */
QLineEdit {
    background: rgba(255,255,255,0.06);
    border: 1px solid rgba(255,255,255,0.12);
    padding: 10px 12px;
    border-radius: 12px;
    selection-background-color: rgba(125, 167, 255, 0.35);
}
QLineEdit:focus {
    border: 1px solid rgba(125, 167, 255, 0.65);
    background: rgba(255,255,255,0.07);
}

/* Checkboxes */
QCheckBox {
    spacing: 10px;
    padding: 6px 8px;
    border-radius: 10px;
    background: rgba(255,255,255,0.03);
    border: 1px solid rgba(255,255,255,0.06);
}
QCheckBox:hover {
    background: rgba(255,255,255,0.05);
    border: 1px solid rgba(255,255,255,0.10);
}
QCheckBox::indicator {
    width: 18px;
    height: 18px;
    border-radius: 6px;
    border: 1px solid rgba(255,255,255,0.20);
    background: rgba(0,0,0,0.25);
}
QCheckBox::indicator:checked {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                                stop:0 #7da7ff, stop:1 #6ee7ff);
    border: 1px solid rgba(255,255,255,0.35);
}

/* Buttons */
QPushButton {
    padding: 10px 14px;
    border-radius: 12px;
    border: 1px solid rgba(255,255,255,0.14);
    background: rgba(255,255,255,0.06);
    color: #f2f4f8;
    font-weight: 600;
}
QPushButton:hover {
    background: rgba(255,255,255,0.10);
    border: 1px solid rgba(255,255,255,0.18);
}
QPushButton:pressed {
    background: rgba(255,255,255,0.08);
}
QPushButton#Primary {
    border: 1px solid rgba(125,167,255,0.55);
    background: rgba(125,167,255,0.18);
}
QPushButton#Primary:hover {
    background: rgba(125,167,255,0.25);
}
QPushButton#Danger {
    border: 1px solid rgba(255,120,120,0.50);
    background: rgba(255,120,120,0.14);
}
QPushButton#Danger:hover {
    background: rgba(255,120,120,0.20);
}
"""

# ------------------ Config ------------------
def config_path() -> Path:
    base = Path(QStandardPaths.writableLocation(QStandardPaths.AppDataLocation))
    base.mkdir(parents=True, exist_ok=True)
    return base / "config.json"

@dataclass
class AppConfig:
    time: str = "09:00"
    coins: List[str] = None

    def __post_init__(self):
        if self.coins is None:
            self.coins = ["USD", "EUR"]

def load_config() -> AppConfig:
    p = config_path()
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
        time = data.get("time", "09:00")
        coins = data.get("coins", ["USD", "EUR"])
        if not isinstance(coins, list):
            coins = ["USD", "EUR"]
        coins = [c for c in coins if c in AVAILABLE_COINS]
        if not coins:
            coins = ["USD", "EUR"]
        return AppConfig(time=time, coins=coins)
    except Exception:
        return AppConfig()

def save_config(cfg: AppConfig) -> None:
    p = config_path()
    p.write_text(
        json.dumps({"time": cfg.time, "coins": cfg.coins}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

# ------------------ Helpers ------------------
def normalize_hhmm(text: str) -> str:
    text = text.strip()
    parts = text.split(":")
    if len(parts) != 2:
        raise ValueError("Formato inválido")
    h = int(parts[0])
    m = int(parts[1])
    if not (0 <= h <= 23 and 0 <= m <= 59):
        raise ValueError("Hora/minuto fora do intervalo")
    return f"{h:02d}:{m:02d}"
def next_trigger_datetime(hhmm: str) -> datetime:
    now = datetime.now()
    hour, minute = map(int, hhmm.split(":"))
    target = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
    if target <= now:
        target += timedelta(days=1)
    return target
def fmt_brl(v: float) -> str:
    s = f"{v:,.4f}"
    s = s.replace(",", "X").replace(".", ",").replace("X", ".")
    return f"R$ {s}"

class ToastOverlay(QWidget):
    def __init__(self, title: str, lines: list[str], duration_ms: int = 12000):
        super().__init__()

        self.setWindowFlags(
            Qt.FramelessWindowHint |
            Qt.WindowStaysOnTopHint
        )
        self.setAttribute(Qt.WA_TranslucentBackground, True)

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)

        card = QFrame()
        card.setObjectName("card")
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(16, 14, 16, 14)
        card_layout.setSpacing(8)

        t = QLabel(title)
        t.setFont(QFont("Segoe UI", 12, QFont.Bold))
        t.setObjectName("title")

        body = QLabel("\n".join(lines) if lines else "Sem dados.")
        body.setFont(QFont("Segoe UI", 11))
        body.setObjectName("body")
        body.setTextInteractionFlags(Qt.TextSelectableByMouse)

        btn_row = QHBoxLayout()
        btn_row.addStretch(1)
        close_btn = QPushButton("Fechar")
        close_btn.setObjectName("closeBtn")
        close_btn.clicked.connect(self.close)
        btn_row.addWidget(close_btn)

        card_layout.addWidget(t)
        card_layout.addWidget(body)
        card_layout.addLayout(btn_row)

        root.addWidget(card)

        self.setStyleSheet("""
            QFrame#card {
                background: rgba(22, 22, 28, 245);
                border: 2px solid rgba(255,255,255,60);
                border-radius: 14px;
            }
            QLabel#title { color: white; }
            QLabel#body  { color: rgba(255,255,255,220); }
            QPushButton#closeBtn {
                background: rgba(255,255,255,22);
                color: white;
                border: 1px solid rgba(255,255,255,35);
                padding: 6px 12px;
                border-radius: 10px;
            }
            QPushButton#closeBtn:hover { background: rgba(255,255,255,32); }
        """)
# ------------------ API Client ------------------
class QuotesClient:
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({"User-Agent": f"{APP_NAME}/1.0"})

    def fetch_quotes(self, coins: List[str]) -> List[Tuple[str, float]]:
        pairs = ",".join([f"{c}-BRL" for c in coins])
        url = f"https://economia.awesomeapi.com.br/json/last/{pairs}"

        r = self.session.get(url, timeout=10)
        r.raise_for_status()
        data = r.json()

        rows = []
        for c in coins:
            key = f"{c}BRL"
            q = data.get(key)
            if not q:
                continue
            bid_raw = q.get("bid")
            if bid_raw is None:
                continue
            rows.append((c, float(bid_raw)))
        return rows

# ------------------ Toast Overlay ------------------
class ToastOverlay(QWidget):
    def __init__(self, title: str, lines: list[str], duration_ms: int = 12000):
        super().__init__()
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.Tool | Qt.WindowStaysOnTopHint)
        self.setAttribute(Qt.WA_TranslucentBackground, True)

        # ===== Container externo (para sombra respirar) =====
        outer = QVBoxLayout(self)
        outer.setContentsMargins(14, 14, 14, 14)  # margem para a sombra aparecer
        outer.setSpacing(0)

        card = QFrame()
        card.setObjectName("ToastCard")
        card.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Minimum)
        card.setMinimumWidth(320)

        # Sombra suave
        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(34)
        shadow.setOffset(0, 12)
        shadow.setColor(Qt.black)
        card.setGraphicsEffect(shadow)

        outer.addWidget(card)

        layout = QVBoxLayout(card)
        layout.setContentsMargins(16, 14, 16, 14)
        layout.setSpacing(12)

        # ===== Header =====
        header_row = QHBoxLayout()
        header_row.setSpacing(10)

        title_lbl = QLabel(title)
        title_lbl.setObjectName("ToastTitle")
        title_lbl.setFont(QFont("Segoe UI", 11, QFont.Bold))

        # Botão X pequeno no topo (opcional, além do "Fechar")
        x_btn = QPushButton("×")
        x_btn.setObjectName("ToastX")
        x_btn.setFixedSize(28, 28)
        x_btn.clicked.connect(self.close)

        header_row.addWidget(title_lbl, 1)
        header_row.addWidget(x_btn, 0, Qt.AlignRight)
        layout.addLayout(header_row)

        # ===== Conteúdo =====
        content = QFrame()
        content.setObjectName("ToastContent")
        content_layout = QVBoxLayout(content)
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.setSpacing(8)

        # Interpreta lines no formato "USD/BRL: R$ x" e alinha bonito
        # Se não bater o padrão, mostra como texto simples.
        parsed_any = False
        for s in (lines or []):
            if "/BRL:" in s:
                parsed_any = True
                left, right = s.split(":", 1)
                pair = left.strip()           # ex "USD/BRL"
                value = right.strip()         # ex "R$ 5,1707"

                row = QHBoxLayout()
                row.setSpacing(10)

                # Badge do par
                badge = QLabel(pair)
                badge.setObjectName("ToastBadge")

                val = QLabel(value)
                val.setObjectName("ToastValue")
                val.setAlignment(Qt.AlignRight | Qt.AlignVCenter)

                row.addWidget(badge, 0)
                row.addWidget(val, 1)
                content_layout.addLayout(row)
            else:
                # fallback (linha simples)
                lbl = QLabel(s)
                lbl.setObjectName("ToastLine")
                lbl.setWordWrap(True)
                content_layout.addWidget(lbl)

        if not lines:
            lbl = QLabel("Sem dados.")
            lbl.setObjectName("ToastLine")
            content_layout.addWidget(lbl)

        layout.addWidget(content)

        # ===== Rodapé =====
        footer = QHBoxLayout()
        footer.addStretch(1)

        close_btn = QPushButton("Fechar")
        close_btn.setObjectName("ToastClose")
        close_btn.setFixedHeight(34)
        close_btn.clicked.connect(self.close)
        footer.addWidget(close_btn)

        layout.addLayout(footer)

        # ===== Estilo do toast (só dele) =====
        self.setStyleSheet("""
            QFrame#ToastCard {
                background: rgba(18, 20, 26, 245);
                border: 1px solid rgba(255,255,255,0.10);
                border-radius: 18px;
            }

            QLabel#ToastTitle {
                color: rgba(255,255,255,235);
                letter-spacing: 0.2px;
            }

            QPushButton#ToastX {
                background: rgba(255,255,255,0.06);
                border: 1px solid rgba(255,255,255,0.10);
                border-radius: 10px;
                color: rgba(255,255,255,200);
                font-size: 14pt;
                padding-bottom: 2px;
            }
            QPushButton#ToastX:hover {
                background: rgba(255,255,255,0.10);
                border: 1px solid rgba(255,255,255,0.14);
            }

            QFrame#ToastContent {
                background: rgba(255,255,255,0.03);
                border: 1px solid rgba(255,255,255,0.06);
                border-radius: 14px;
                padding: 10px;
            }

            QLabel#ToastBadge {
                background: rgba(125,167,255,0.16);
                border: 1px solid rgba(125,167,255,0.28);
                color: rgba(230,240,255,235);
                padding: 6px 10px;
                border-radius: 999px;
                font-weight: 700;
                font-size: 10pt;
            }

            QLabel#ToastValue {
                color: rgba(255,255,255,220);
                font-weight: 600;
                font-size: 10.5pt;
            }

            QLabel#ToastLine {
                color: rgba(255,255,255,210);
            }

            QPushButton#ToastClose {
                background: rgba(255,255,255,0.06);
                border: 1px solid rgba(255,255,255,0.12);
                border-radius: 12px;
                padding: 6px 14px;
                color: rgba(255,255,255,230);
                font-weight: 600;
            }
            QPushButton#ToastClose:hover {
                background: rgba(255,255,255,0.10);
                border: 1px solid rgba(255,255,255,0.16);
            }
        """)

        # ===== Animações =====
        QTimer.singleShot(duration_ms, self.fade_out)

        self.setWindowOpacity(0.0)
        self.anim_in = QPropertyAnimation(self, b"windowOpacity")
        self.anim_in.setDuration(220)
        self.anim_in.setStartValue(0.0)
        self.anim_in.setEndValue(1.0)
        self.anim_in.setEasingCurve(QEasingCurve.OutCubic)

        self.anim_out = QPropertyAnimation(self, b"windowOpacity")
        self.anim_out.setDuration(220)
        self.anim_out.setStartValue(1.0)
        self.anim_out.setEndValue(0.0)
        self.anim_out.setEasingCurve(QEasingCurve.InCubic)
        self.anim_out.finished.connect(self.close)

    def showEvent(self, event):
        super().showEvent(event)
        self.adjustSize()

        screen = QApplication.primaryScreen().availableGeometry()
        x = screen.x() + screen.width() - self.width() - 16
        y = screen.y() + 16
        # posiciona no monitor do mouse (sem usar QGuiApplication.cursor())
        pos = QCursor.pos()
        screen = QApplication.screenAt(pos)
        if screen is None:
            screen = QApplication.primaryScreen()
        geo = screen.availableGeometry()

        x = geo.x() + geo.width() - self.width() - 18
        y = geo.y() + 18
        self.move(x, y)

        self.raise_()
        self.activateWindow()
        self.anim_in.start()

    def fade_out(self):
        if self.isVisible():
            self.anim_out.start()
class Bridge(QObject):
    toast = Signal(str, list)

class Bridge(QObject):
    toast = Signal(str, list)

# ------------------ Main Window ------------------
class Main(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Cotação em BRL - Agendador (Tray)")
        self.resize(520, 580)
        self.resize(560, 620)

        self.bridge = Bridge()
        self.bridge.toast.connect(self.show_overlay)

        cfg = load_config()

        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 18, 18, 18)
        layout.setSpacing(12)

        title = QLabel("Agendar janela flutuante com cotações (base BRL)")
        title.setFont(QFont("Segoe UI", 12, QFont.Bold))
        layout.addWidget(title)

        layout.addWidget(QLabel("Horário diário (HH:MM):"))
        self.time_edit = QLineEdit(cfg["time"])
        self.time_edit.setPlaceholderText("Ex: 09:30")
        layout.addWidget(self.time_edit)

        layout.addWidget(QLabel("Moedas:"))
        self.checks = {}
        for c in AVAILABLE_COINS:
            cb = QCheckBox(c)
            cb.setChecked(c in cfg["coins"])
            self.checks[c] = cb
            layout.addWidget(cb)

        btns = QHBoxLayout()
        self.save_btn = QPushButton("Salvar e Agendar")
        self.test_btn = QPushButton("Testar Agora")
        btns.addWidget(self.save_btn)
        btns.addWidget(self.test_btn)
        layout.addLayout(btns)

        self.status = QLabel("")
        layout.addWidget(self.status)

        layout.addWidget(QLabel(
            "Dica: ao fechar (X), o app vai para a bandeja do sistema e continua rodando."
        ))

        self.save_btn.clicked.connect(self.save_and_schedule)
        self.test_btn.clicked.connect(self.test_now)

        self.next_dt = None
        self.refresh_next()

        self.tick = QTimer(self)
        self.tick.timeout.connect(self.check_schedule)
        self.tick.start(1000)

        self.toast_widget = None

        # --- System Tray ---
        if not QSystemTrayIcon.isSystemTrayAvailable():
            QMessageBox.warning(self, "Aviso", "System Tray não disponível neste sistema.")
            self.tray = None
        else:
            self.tray = QSystemTrayIcon(self)
            # Ícone padrão do sistema (não precisa arquivo .ico)
            icon = QApplication.style().standardIcon(QStyle.SP_ComputerIcon)
            self.tray.setIcon(icon)
            self.tray.setToolTip("Cotação em BRL (rodando em segundo plano)")

            menu = QMenu()
            act_show = QAction("Abrir", self)
            act_test = QAction("Testar agora", self)
            act_quit = QAction("Sair", self)

            act_show.triggered.connect(self.show_main)
            act_test.triggered.connect(self.test_now)
            act_quit.triggered.connect(self.exit_app)

            menu.addAction(act_show)
            menu.addAction(act_test)
            menu.addSeparator()
            menu.addAction(act_quit)

            self.tray.setContextMenu(menu)
            self.tray.activated.connect(self.on_tray_activated)
            self.tray.show()

    # ---- Tray behavior ----
    def closeEvent(self, event):
        # Em vez de fechar, esconde e deixa no tray
        if self.tray:
            event.ignore()
            self.hide()
            self.tray.showMessage(
                "Rodando em segundo plano",
                "O app continua ativo na bandeja do sistema.\nClique com o botão direito no ícone para opções.",
                QSystemTrayIcon.Information,
                4000
            )
        else:
            super().closeEvent(event)

    def on_tray_activated(self, reason):
        # Clique esquerdo: abrir/mostrar
        if reason == QSystemTrayIcon.Trigger:
            self.show_main()

    def show_main(self):
        self.show()
        self.raise_()
        self.activateWindow()

    def exit_app(self):
        # Fechar de verdade
        if self.tray:
            self.tray.hide()
        QApplication.quit()

    # ---- App logic ----
    def selected_coins(self):
        return [c for c, cb in self.checks.items() if cb.isChecked()]

    def refresh_next(self):
        cfg = load_config()
        self.next_dt = next_trigger_datetime(cfg["time"])
        self.status.setText(f"Próximo disparo: {self.next_dt.strftime('%d/%m %H:%M')}")

    def save_and_schedule(self):
        hhmm = self.time_edit.text().strip()
        try:
            datetime.strptime(hhmm, "%H:%M")
        except ValueError:
            QMessageBox.critical(self, "Erro", "Horário inválido. Use HH:MM (ex: 09:30).")
            return

        coins = self.selected_coins()
        if not coins:
            QMessageBox.critical(self, "Erro", "Selecione pelo menos uma moeda.")
            return

        save_config({"time": hhmm, "coins": coins})
        self.refresh_next()

        if self.tray:
            self.tray.showMessage(
                "Agendado",
                f"Horário: {hhmm}\nMoedas: {', '.join(coins)}",
                QSystemTrayIcon.Information,
                3000
            )
        else:
            QMessageBox.information(self, "OK", "Agendamento salvo.")

    def show_overlay(self, title: str, lines: list):
        if self.toast_widget is not None and self.toast_widget.isVisible():
            self.toast_widget.close()
        self.toast_widget = ToastOverlay(title, [str(x) for x in lines], duration_ms=12000)
        self.toast_widget.show()

    def test_now(self):
        threading.Thread(target=self.run_job, daemon=True).start()

    def run_job(self):
        cfg = load_config()
        coins = cfg.get("coins", [])
        now = datetime.now().strftime("%H:%M")

        if not coins:
            self.bridge.toast.emit("Configuração", ["Nenhuma moeda selecionada."])
            return

        try:
            rows = fetch_quotes(coins)
            lines = [f"{c}/BRL: {fmt_brl(v)}" for c, v in rows]
            if not lines:
                lines = ["Sem dados retornados pela API."]
            self.bridge.toast.emit(f"Cotações ({now})", lines)
        except Exception as e:
            self.bridge.toast.emit("Erro ao buscar cotações", [repr(e)])

    def check_schedule(self):
        if not self.next_dt:
            return

        if datetime.now() >= self.next_dt:
            threading.Thread(target=self.run_job, daemon=True).start()
            self.refresh_next()
def resource_path(relative: str) -> Path:
    if hasattr(sys, "_MEIPASS"):
        return Path(sys._MEIPASS) / relative
    # Aqui a base é src/
    return Path(__file__).resolve().parent / relative

if __name__ == "__main__":
    app = QApplication(sys.argv)

    # Em apps com tray, isso evita fechar quando todas janelas são escondidas.
    app.setQuitOnLastWindowClosed(False)
    
    icon_path = resource_path("icon.ico")
    if icon_path.exists():
        app.setWindowIcon(QIcon(str(icon_path)))
    else:
        print(f"[WARN] Ícone global não encontrado: {icon_path}")

    w = Main()
    w.show()

    sys.exit(app.exec())