import sys
import json
import threading
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Tuple, Optional

import requests
from PySide6.QtCore import (
    Qt, QTimer, QPropertyAnimation, QEasingCurve, Signal, QObject,
    QStandardPaths, QPoint, QSize, QRect, QSequentialAnimationGroup,
    QParallelAnimationGroup, Property
)
from PySide6.QtGui import (
    QFont, QAction, QIcon, QCursor, QColor, QPainter, QPainterPath,
    QLinearGradient, QBrush, QPen, QPixmap
)
from PySide6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QCheckBox, QLineEdit, QMessageBox, QFrame,
    QSystemTrayIcon, QMenu, QStyle, QGridLayout, QGraphicsDropShadowEffect,
    QGraphicsOpacityEffect, QSpacerItem, QSizePolicy, QScrollArea
)

AVAILABLE_COINS = [
    ("USD", "Dólar Americano", "🇺🇸"),
    ("EUR", "Euro", "🇪🇺"),
    ("GBP", "Libra Esterlina", "🇬🇧"),
    ("ARS", "Peso Argentino", "🇦🇷"),
    ("JPY", "Iene Japonês", "🇯🇵"),
    ("CAD", "Dólar Canadense", "🇨🇦"),
    ("AUD", "Dólar Australiano", "🇦🇺"),
    ("BTC", "Bitcoin", "₿"),
]

COIN_CODES = [c[0] for c in AVAILABLE_COINS]
APP_NAME = "CotacaoBRLTray"

# ──────────────────── Cores do tema ────────────────────
ACCENT = "#7c8aff"
ACCENT_LIGHT = "#a0b4ff"
ACCENT_GLOW = "rgba(124,138,255,0.35)"
BG_DARK = "#0c0e14"
BG_CARD = "rgba(255,255,255,0.035)"
BG_CARD_HOVER = "rgba(255,255,255,0.055)"
BORDER = "rgba(255,255,255,0.07)"
BORDER_FOCUS = "rgba(124,138,255,0.6)"
TEXT_PRIMARY = "#eef0f6"
TEXT_SECONDARY = "rgba(238,240,246,0.55)"
TEXT_DIM = "rgba(238,240,246,0.35)"
SUCCESS = "#5ae4a7"
DANGER = "#ff7b7b"
WARNING = "#ffc857"

# ──────────────────── QSS Global ────────────────────
QSS = f"""
/* ─── Base ─── */
QWidget {{
    background: {BG_DARK};
    color: {TEXT_PRIMARY};
    font-family: "Segoe UI", "Inter", "SF Pro Display", sans-serif;
    font-size: 10.5pt;
}}

QScrollArea {{
    border: none;
    background: transparent;
}}
QScrollBar:vertical {{
    background: transparent;
    width: 6px;
    margin: 4px 2px;
}}
QScrollBar::handle:vertical {{
    background: rgba(255,255,255,0.12);
    border-radius: 3px;
    min-height: 30px;
}}
QScrollBar::handle:vertical:hover {{
    background: rgba(255,255,255,0.22);
}}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
    height: 0px;
}}
QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {{
    background: none;
}}

/* ─── Labels ─── */
QLabel#Title {{
    font-size: 17pt;
    font-weight: 800;
    color: {TEXT_PRIMARY};
    letter-spacing: -0.3px;
}}
QLabel#Subtitle {{
    color: {TEXT_SECONDARY};
    font-size: 9.5pt;
    line-height: 1.5;
}}
QLabel#Section {{
    font-size: 9pt;
    font-weight: 700;
    color: {TEXT_SECONDARY};
    letter-spacing: 1.2px;
    text-transform: uppercase;
    margin-top: 4px;
}}
QLabel#Status {{
    padding: 12px 16px;
    border-radius: 14px;
    background: rgba(90,228,167,0.06);
    border: 1px solid rgba(90,228,167,0.15);
    color: {SUCCESS};
    font-size: 9.5pt;
    font-weight: 600;
}}
QLabel#Hint {{
    color: {TEXT_DIM};
    font-size: 8.5pt;
}}

/* ─── Cards ─── */
QFrame#Card {{
    background: {BG_CARD};
    border: 1px solid {BORDER};
    border-radius: 18px;
}}
QFrame#HeaderCard {{
    background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                                stop:0 rgba(124,138,255,0.08),
                                stop:1 rgba(110,231,255,0.04));
    border: 1px solid rgba(124,138,255,0.12);
    border-radius: 20px;
}}

/* ─── Inputs ─── */
QLineEdit {{
    background: rgba(255,255,255,0.045);
    border: 1.5px solid {BORDER};
    padding: 12px 16px;
    border-radius: 14px;
    font-size: 11pt;
    font-weight: 600;
    color: {TEXT_PRIMARY};
    selection-background-color: {ACCENT_GLOW};
}}
QLineEdit:focus {{
    border: 1.5px solid {BORDER_FOCUS};
    background: rgba(255,255,255,0.06);
}}
QLineEdit::placeholder {{
    color: {TEXT_DIM};
}}

/* ─── Checkboxes (coin cards) ─── */
QCheckBox {{
    spacing: 0px;
    padding: 0px;
    border: none;
    background: transparent;
}}
QCheckBox::indicator {{
    width: 0px;
    height: 0px;
}}

/* ─── Buttons ─── */
QPushButton {{
    padding: 12px 20px;
    border-radius: 14px;
    border: 1.5px solid {BORDER};
    background: rgba(255,255,255,0.04);
    color: {TEXT_PRIMARY};
    font-weight: 700;
    font-size: 10pt;
    letter-spacing: 0.2px;
}}
QPushButton:hover {{
    background: rgba(255,255,255,0.08);
    border: 1.5px solid rgba(255,255,255,0.15);
}}
QPushButton:pressed {{
    background: rgba(255,255,255,0.06);
}}

QPushButton#Primary {{
    border: 1.5px solid rgba(124,138,255,0.5);
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                                stop:0 rgba(124,138,255,0.2),
                                stop:1 rgba(110,231,255,0.12));
    color: {ACCENT_LIGHT};
}}
QPushButton#Primary:hover {{
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                                stop:0 rgba(124,138,255,0.3),
                                stop:1 rgba(110,231,255,0.18));
    border: 1.5px solid rgba(124,138,255,0.65);
}}

QPushButton#Danger {{
    border: 1.5px solid rgba(255,123,123,0.45);
    background: rgba(255,123,123,0.1);
    color: {DANGER};
}}
QPushButton#Danger:hover {{
    background: rgba(255,123,123,0.18);
}}

QPushButton#Ghost {{
    border: none;
    background: transparent;
    color: {TEXT_SECONDARY};
    padding: 8px 12px;
}}
QPushButton#Ghost:hover {{
    color: {TEXT_PRIMARY};
    background: rgba(255,255,255,0.04);
}}

/* ─── Tooltip ─── */
QToolTip {{
    background: #1a1c24;
    color: {TEXT_PRIMARY};
    border: 1px solid rgba(255,255,255,0.1);
    border-radius: 8px;
    padding: 6px 10px;
    font-size: 9pt;
}}

/* ─── Menu (Tray) ─── */
QMenu {{
    background: #14161e;
    border: 1px solid rgba(255,255,255,0.1);
    border-radius: 12px;
    padding: 6px;
}}
QMenu::item {{
    padding: 8px 20px;
    border-radius: 8px;
    color: {TEXT_PRIMARY};
}}
QMenu::item:selected {{
    background: rgba(124,138,255,0.15);
}}
QMenu::separator {{
    height: 1px;
    background: rgba(255,255,255,0.08);
    margin: 4px 8px;
}}
"""

# ──────────────────── Config ────────────────────
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
        coins = [c for c in coins if c in COIN_CODES]
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

# ──────────────────── Helpers ────────────────────
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

def time_until(dt: datetime) -> str:
    delta = dt - datetime.now()
    if delta.total_seconds() <= 0:
        return "agora"
    hours, remainder = divmod(int(delta.total_seconds()), 3600)
    minutes, _ = divmod(remainder, 60)
    if hours > 0:
        return f"{hours}h {minutes}min"
    return f"{minutes}min"

# ──────────────────── API Client ────────────────────
class QuotesClient:
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({"User-Agent": f"{APP_NAME}/2.0"})

    def fetch_quotes(self, coins: List[str]) -> List[Tuple[str, float, float]]:
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
            pct_raw = q.get("pctChange", "0")
            if bid_raw is None:
                continue
            rows.append((c, float(bid_raw), float(pct_raw)))
        return rows

# ──────────────────── Coin Card Widget ────────────────────
class CoinCard(QFrame):
    """Card selecionável para cada moeda."""
    toggled = Signal(str, bool)

    def __init__(self, code: str, name: str, flag: str, checked: bool = False):
        super().__init__()
        self.code = code
        self._checked = checked
        self.setCursor(Qt.PointingHandCursor)
        self.setFixedHeight(64)
        self.setMinimumWidth(150)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(14, 10, 14, 10)
        layout.setSpacing(12)

        # Flag / icon
        flag_label = QLabel(flag)
        flag_label.setFont(QFont("Segoe UI Emoji", 18))
        flag_label.setFixedWidth(32)
        flag_label.setAlignment(Qt.AlignCenter)
        flag_label.setStyleSheet("background: transparent; border: none;")
        layout.addWidget(flag_label)

        # Text
        text_layout = QVBoxLayout()
        text_layout.setSpacing(1)
        text_layout.setContentsMargins(0, 0, 0, 0)

        code_label = QLabel(code)
        code_label.setFont(QFont("Segoe UI", 11, QFont.Bold))
        code_label.setStyleSheet(f"color: {TEXT_PRIMARY}; background: transparent; border: none;")

        name_label = QLabel(name)
        name_label.setFont(QFont("Segoe UI", 8))
        name_label.setStyleSheet(f"color: {TEXT_SECONDARY}; background: transparent; border: none;")

        text_layout.addWidget(code_label)
        text_layout.addWidget(name_label)
        layout.addLayout(text_layout)
        layout.addStretch()

        # Check indicator
        self.indicator = QLabel("✓")
        self.indicator.setFont(QFont("Segoe UI", 11, QFont.Bold))
        self.indicator.setFixedSize(28, 28)
        self.indicator.setAlignment(Qt.AlignCenter)
        self.indicator.setStyleSheet("background: transparent; border: none;")
        layout.addWidget(self.indicator)

        self._update_style()

    def _update_style(self):
        if self._checked:
            self.setStyleSheet(f"""
                CoinCard {{
                    background: rgba(124,138,255,0.1);
                    border: 1.5px solid rgba(124,138,255,0.4);
                    border-radius: 14px;
                }}
                CoinCard:hover {{
                    background: rgba(124,138,255,0.14);
                }}
            """)
            self.indicator.setStyleSheet(f"""
                background: {ACCENT};
                border: none;
                border-radius: 14px;
                color: #0c0e14;
                font-weight: 800;
            """)
        else:
            self.setStyleSheet(f"""
                CoinCard {{
                    background: {BG_CARD};
                    border: 1.5px solid {BORDER};
                    border-radius: 14px;
                }}
                CoinCard:hover {{
                    background: {BG_CARD_HOVER};
                    border: 1.5px solid rgba(255,255,255,0.12);
                }}
            """)
            self.indicator.setStyleSheet(f"""
                background: rgba(255,255,255,0.05);
                border: 1.5px solid rgba(255,255,255,0.12);
                border-radius: 14px;
                color: transparent;
            """)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self._checked = not self._checked
            self._update_style()
            self.toggled.emit(self.code, self._checked)

    def isChecked(self):
        return self._checked

    def setChecked(self, val: bool):
        self._checked = val
        self._update_style()

# ──────────────────── Toast / Notification Overlay ────────────────────
class ToastOverlay(QWidget):
    def __init__(self, title: str, lines: List[Tuple[str, str, str, str]],
                 timestamp: str = "", duration_ms: int = 15000):
        """
        lines: lista de tuplas (flag, code, value, pct_change)
        Se vazio, exibe mensagem de erro/info.
        """
        super().__init__()
        self.setWindowFlags(
            Qt.FramelessWindowHint | Qt.Tool | Qt.WindowStaysOnTopHint
        )
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self.setMinimumWidth(380)
        self.setMaximumWidth(440)

        root = QVBoxLayout(self)
        root.setContentsMargins(12, 12, 12, 12)

        card = QFrame()
        card.setObjectName("ToastCard")
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(0, 0, 0, 0)
        card_layout.setSpacing(0)

        # ─── Header do toast ───
        toast_header = QFrame()
        toast_header.setStyleSheet(f"""
            QFrame {{
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 rgba(124,138,255,0.12),
                    stop:1 rgba(110,231,255,0.06));
                border: none;
                border-top-left-radius: 18px;
                border-top-right-radius: 18px;
                padding: 0px;
            }}
        """)
        header_layout = QHBoxLayout(toast_header)
        header_layout.setContentsMargins(20, 16, 20, 12)

        # Ícone de sino/notificação
        bell_icon = QLabel("📊")
        bell_icon.setFont(QFont("Segoe UI Emoji", 16))
        bell_icon.setStyleSheet("background: transparent; border: none;")
        header_layout.addWidget(bell_icon)

        header_text = QVBoxLayout()
        header_text.setSpacing(2)

        t = QLabel(title)
        t.setFont(QFont("Segoe UI", 13, QFont.Bold))
        t.setStyleSheet(f"color: {TEXT_PRIMARY}; background: transparent; border: none;")

        ts_label = QLabel(timestamp if timestamp else datetime.now().strftime("%d/%m/%Y • %H:%M"))
        ts_label.setFont(QFont("Segoe UI", 8))
        ts_label.setStyleSheet(f"color: {TEXT_DIM}; background: transparent; border: none;")

        header_text.addWidget(t)
        header_text.addWidget(ts_label)
        header_layout.addLayout(header_text)
        header_layout.addStretch()

        close_btn = QPushButton("✕")
        close_btn.setFixedSize(32, 32)
        close_btn.setCursor(Qt.PointingHandCursor)
        close_btn.setStyleSheet(f"""
            QPushButton {{
                background: rgba(255,255,255,0.06);
                border: 1px solid rgba(255,255,255,0.08);
                border-radius: 16px;
                color: {TEXT_SECONDARY};
                font-size: 12pt;
                font-weight: 600;
                padding: 0px;
            }}
            QPushButton:hover {{
                background: rgba(255,123,123,0.15);
                color: {DANGER};
                border-color: rgba(255,123,123,0.3);
            }}
        """)
        close_btn.clicked.connect(self.fade_out)
        header_layout.addWidget(close_btn)

        card_layout.addWidget(toast_header)

        # ─── Body do toast ───
        body_frame = QFrame()
        body_frame.setStyleSheet("""
            QFrame {
                background: transparent;
                border: none;
            }
        """)
        body_layout = QVBoxLayout(body_frame)
        body_layout.setContentsMargins(20, 16, 20, 16)
        body_layout.setSpacing(8)

        if isinstance(lines, list) and lines and isinstance(lines[0], tuple):
            for flag, code, value, pct in lines:
                row = self._create_quote_row(flag, code, value, pct)
                body_layout.addWidget(row)
        elif isinstance(lines, list):
            for line in lines:
                lbl = QLabel(str(line))
                lbl.setFont(QFont("Segoe UI", 10))
                lbl.setStyleSheet(f"color: {TEXT_SECONDARY}; background: transparent; border: none;")
                lbl.setWordWrap(True)
                body_layout.addWidget(lbl)
        else:
            lbl = QLabel("Sem dados disponíveis.")
            lbl.setStyleSheet(f"color: {TEXT_DIM}; background: transparent; border: none;")
            body_layout.addWidget(lbl)

        card_layout.addWidget(body_frame)

        # ─── Footer do toast ───
        footer = QFrame()
        footer.setFixedHeight(6)
        footer.setStyleSheet(f"""
            QFrame {{
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 {ACCENT}, stop:0.5 #6ee7ff, stop:1 {SUCCESS});
                border: none;
                border-bottom-left-radius: 18px;
                border-bottom-right-radius: 18px;
            }}
        """)
        card_layout.addWidget(footer)

        root.addWidget(card)

        # Sombra
        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(50)
        shadow.setOffset(0, 15)
        shadow.setColor(QColor(0, 0, 0, 160))
        card.setGraphicsEffect(shadow)

        card.setStyleSheet("""
            QFrame#ToastCard {
                background: #12141c;
                border: 1px solid rgba(255,255,255,0.09);
                border-radius: 18px;
            }
        """)

        # Animações
        QTimer.singleShot(duration_ms, self.fade_out)

        self.setWindowOpacity(0.0)
        self.anim_in = QPropertyAnimation(self, b"windowOpacity")
        self.anim_in.setDuration(280)
        self.anim_in.setStartValue(0.0)
        self.anim_in.setEndValue(1.0)
        self.anim_in.setEasingCurve(QEasingCurve.OutCubic)

        self.anim_out = QPropertyAnimation(self, b"windowOpacity")
        self.anim_out.setDuration(250)
        self.anim_out.setStartValue(1.0)
        self.anim_out.setEndValue(0.0)
        self.anim_out.setEasingCurve(QEasingCurve.InCubic)
        self.anim_out.finished.connect(self.close)

        self._fading_out = False

    def _create_quote_row(self, flag: str, code: str, value: str, pct: str) -> QFrame:
        row = QFrame()
        row.setStyleSheet(f"""
            QFrame {{
                background: rgba(255,255,255,0.03);
                border: 1px solid rgba(255,255,255,0.05);
                border-radius: 12px;
            }}
        """)
        row_layout = QHBoxLayout(row)
        row_layout.setContentsMargins(14, 10, 14, 10)
        row_layout.setSpacing(12)

        # Flag
        flag_lbl = QLabel(flag)
        flag_lbl.setFont(QFont("Segoe UI Emoji", 14))
        flag_lbl.setFixedWidth(28)
        flag_lbl.setStyleSheet("background: transparent; border: none;")
        row_layout.addWidget(flag_lbl)

        # Code
        code_lbl = QLabel(code)
        code_lbl.setFont(QFont("Segoe UI", 10, QFont.Bold))
        code_lbl.setFixedWidth(38)
        code_lbl.setStyleSheet(f"color: {TEXT_PRIMARY}; background: transparent; border: none;")
        row_layout.addWidget(code_lbl)

        row_layout.addStretch()

        # Value
        val_lbl = QLabel(value)
        val_lbl.setFont(QFont("Segoe UI", 10, QFont.Bold))
        val_lbl.setStyleSheet(f"color: {TEXT_PRIMARY}; background: transparent; border: none;")
        row_layout.addWidget(val_lbl)

        # Percentage
        try:
            pct_val = float(pct.replace("%", "").replace(",", ".").strip()) if pct else 0
        except ValueError:
            pct_val = 0

        if pct_val > 0:
            pct_color = SUCCESS
            arrow = "▲"
        elif pct_val < 0:
            pct_color = DANGER
            arrow = "▼"
        else:
            pct_color = TEXT_DIM
            arrow = "─"

        pct_lbl = QLabel(f"{arrow} {pct}")
        pct_lbl.setFont(QFont("Segoe UI", 9, QFont.Bold))
        pct_lbl.setStyleSheet(f"""
            color: {pct_color};
            background: rgba({pct_color.strip('#')
            if pct_color.startswith('#') else '255,255,255'}, 0.08);
            border: none;
            border-radius: 8px;
            padding: 3px 8px;
        """)
        # Fix the rgba for non-hex colors
        if pct_val > 0:
            pct_lbl.setStyleSheet(f"""
                color: {SUCCESS};
                background: rgba(90,228,167,0.1);
                border: none;
                border-radius: 8px;
                padding: 3px 8px;
            """)
        elif pct_val < 0:
            pct_lbl.setStyleSheet(f"""
                color: {DANGER};
                background: rgba(255,123,123,0.1);
                border: none;
                border-radius: 8px;
                padding: 3px 8px;
            """)
        else:
            pct_lbl.setStyleSheet(f"""
                color: {TEXT_DIM};
                background: rgba(255,255,255,0.04);
                border: none;
                border-radius: 8px;
                padding: 3px 8px;
            """)

        row_layout.addWidget(pct_lbl)

        return row

    def showEvent(self, event):
        super().showEvent(event)
        self.adjustSize()
        pos = QCursor.pos()
        screen = QApplication.screenAt(pos)
        if screen is None:
            screen = QApplication.primaryScreen()
        geo = screen.availableGeometry()
        x = geo.x() + geo.width() - self.width() - 20
        y = geo.y() + 20
        self.move(x, y)
        self.raise_()
        self.activateWindow()
        self.anim_in.start()

    def fade_out(self):
        if self.isVisible() and not self._fading_out:
            self._fading_out = True
            self.anim_out.start()

class Bridge(QObject):
    toast = Signal(str, list)

# ──────────────────── Separator ────────────────────
class Separator(QFrame):
    def __init__(self):
        super().__init__()
        self.setFixedHeight(1)
        self.setStyleSheet(f"background: {BORDER}; border: none;")

# ──────────────────── Main Window ────────────────────
class Main(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Cotações BRL")
        self.resize(520, 680)
        self.setMinimumSize(420, 560)
        self.bridge = Bridge()
        self.bridge.toast.connect(self.show_overlay)
        self.client = QuotesClient()
        cfg = load_config()

        # Layout raiz com scroll
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)

        content = QWidget()
        layout = QVBoxLayout(content)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(16)

        # ─── Header ───
        header = QFrame()
        header.setObjectName("HeaderCard")
        hl = QVBoxLayout(header)
        hl.setContentsMargins(24, 22, 24, 22)
        hl.setSpacing(8)

        # Header top row
        h_top = QHBoxLayout()
        h_top.setSpacing(14)

        icon_label = QLabel("💱")
        icon_label.setFont(QFont("Segoe UI Emoji", 28))
        icon_label.setStyleSheet("background: transparent; border: none;")
        h_top.addWidget(icon_label)

        h_text = QVBoxLayout()
        h_text.setSpacing(4)
        title = QLabel("Cotações BRL")
        title.setObjectName("Title")
        subtitle = QLabel("Acompanhe câmbios automaticamente.\nNotificações no horário programado.")
        subtitle.setObjectName("Subtitle")
        h_text.addWidget(title)
        h_text.addWidget(subtitle)
        h_top.addLayout(h_text)
        h_top.addStretch()

        hl.addLayout(h_top)
        layout.addWidget(header)

        # ─── Time section ───
        time_card = QFrame()
        time_card.setObjectName("Card")
        time_layout = QVBoxLayout(time_card)
        time_layout.setContentsMargins(20, 18, 20, 18)
        time_layout.setSpacing(12)

        time_header = QHBoxLayout()
        clock_icon = QLabel("⏰")
        clock_icon.setFont(QFont("Segoe UI Emoji", 13))
        clock_icon.setStyleSheet("background: transparent; border: none;")
        time_header.addWidget(clock_icon)

        lab_time = QLabel("HORÁRIO DIÁRIO")
        lab_time.setObjectName("Section")
        time_header.addWidget(lab_time)
        time_header.addStretch()
        time_layout.addLayout(time_header)

        time_input_row = QHBoxLayout()
        time_input_row.setSpacing(10)
        self.time_edit = QLineEdit(cfg.time)
        self.time_edit.setPlaceholderText("Ex: 09:30")
        self.time_edit.setMaximumWidth(160)
        self.time_edit.setAlignment(Qt.AlignCenter)
        time_input_row.addWidget(self.time_edit)

        time_hint = QLabel("Formato 24h (HH:MM)")
        time_hint.setObjectName("Hint")
        time_input_row.addWidget(time_hint)
        time_input_row.addStretch()

        time_layout.addLayout(time_input_row)
        layout.addWidget(time_card)

        # ─── Coins section ───
        coins_card = QFrame()
        coins_card.setObjectName("Card")
        coins_layout = QVBoxLayout(coins_card)
        coins_layout.setContentsMargins(20, 18, 20, 18)
        coins_layout.setSpacing(14)

        coins_header = QHBoxLayout()
        coins_icon = QLabel("🪙")
        coins_icon.setFont(QFont("Segoe UI Emoji", 13))
        coins_icon.setStyleSheet("background: transparent; border: none;")
        coins_header.addWidget(coins_icon)

        lab_coins = QLabel("MOEDAS")
        lab_coins.setObjectName("Section")
        coins_header.addWidget(lab_coins)
        coins_header.addStretch()

        # Contador de selecionados
        self.coin_count = QLabel(f"{len(cfg.coins)} selecionadas")
        self.coin_count.setFont(QFont("Segoe UI", 8, QFont.Bold))
        self.coin_count.setStyleSheet(f"""
            color: {ACCENT_LIGHT};
            background: rgba(124,138,255,0.12);
            border: none;
            border-radius: 10px;
            padding: 4px 10px;
        """)
        coins_header.addWidget(self.coin_count)

        coins_layout.addLayout(coins_header)

        # Grid de coin cards
        grid = QGridLayout()
        grid.setHorizontalSpacing(10)
        grid.setVerticalSpacing(10)
        self.coin_cards = {}
        cols = 2
        for i, (code, name, flag) in enumerate(AVAILABLE_COINS):
            card_w = CoinCard(code, name, flag, checked=(code in cfg.coins))
            card_w.toggled.connect(self._on_coin_toggled)
            self.coin_cards[code] = card_w
            grid.addWidget(card_w, i // cols, i % cols)
        coins_layout.addLayout(grid)
        layout.addWidget(coins_card)

        # ─── Buttons ───
        btns_card = QFrame()
        btns_card.setObjectName("Card")
        btns_layout = QVBoxLayout(btns_card)
        btns_layout.setContentsMargins(20, 16, 20, 16)
        btns_layout.setSpacing(10)

        btns = QHBoxLayout()
        btns.setSpacing(10)

        self.save_btn = QPushButton("💾  Salvar e Agendar")
        self.save_btn.setObjectName("Primary")
        self.save_btn.setCursor(Qt.PointingHandCursor)
        self.save_btn.setMinimumHeight(48)

        self.test_btn = QPushButton("🔍  Testar Agora")
        self.test_btn.setCursor(Qt.PointingHandCursor)
        self.test_btn.setMinimumHeight(48)

        btns.addWidget(self.save_btn)
        btns.addWidget(self.test_btn)
        btns_layout.addLayout(btns)

        layout.addWidget(btns_card)

        # ─── Status ───
        self.status = QLabel("")
        self.status.setObjectName("Status")
        layout.addWidget(self.status)

        # ─── Footer hint ───
        footer_row = QHBoxLayout()
        footer_row.setContentsMargins(4, 0, 4, 0)
        hint_icon = QLabel("ℹ️")
        hint_icon.setFont(QFont("Segoe UI Emoji", 9))
        hint_icon.setStyleSheet("background: transparent; border: none;")
        footer_row.addWidget(hint_icon)
        hint = QLabel("Fechar a janela minimiza para a bandeja do sistema.")
        hint.setObjectName("Hint")
        footer_row.addWidget(hint)
        footer_row.addStretch()
        layout.addLayout(footer_row)

        layout.addStretch()

        scroll.setWidget(content)
        outer.addWidget(scroll)

        # Connects
        self.save_btn.clicked.connect(self.save_and_schedule)
        self.test_btn.clicked.connect(self.test_now)

        self.next_dt: Optional[datetime] = None
        self.last_fire_key: Optional[str] = None
        self.refresh_next()

        # Timer principal (1s)
        self.tick = QTimer(self)
        self.tick.timeout.connect(self.check_schedule)
        self.tick.start(1000)

        # Timer para atualizar status (countdown)
        self.status_tick = QTimer(self)
        self.status_tick.timeout.connect(self._update_status_display)
        self.status_tick.start(30000)  # 30s

        self.toast_widget = None

        # ─── Tray ───
        if not QSystemTrayIcon.isSystemTrayAvailable():
            QMessageBox.warning(self, "Aviso", "System Tray não disponível.")
            self.tray = None
        else:
            self.tray = QSystemTrayIcon(self)
            icon = QApplication.style().standardIcon(QStyle.SP_ComputerIcon)
            self.tray.setIcon(icon)
            self.tray.setToolTip("Cotações BRL — rodando em segundo plano")

            menu = QMenu()
            menu.setStyleSheet(QSS)  # Aplica estilo ao menu

            act_show = QAction("📂  Abrir", self)
            act_test = QAction("🔍  Testar agora", self)
            act_quit = QAction("⏻  Sair", self)

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

    # ─── Callbacks ───
    def _on_coin_toggled(self, code: str, checked: bool):
        count = sum(1 for c in self.coin_cards.values() if c.isChecked())
        self.coin_count.setText(f"{count} selecionada{'s' if count != 1 else ''}")

    def _update_status_display(self):
        if self.next_dt:
            remaining = time_until(self.next_dt)
            self.status.setText(
                f"⏱ Próximo disparo: {self.next_dt.strftime('%d/%m %H:%M')}  •  em {remaining}"
            )

    def closeEvent(self, event):
        if self.tray:
            event.ignore()
            self.hide()
            self.tray.showMessage(
                "Cotações BRL",
                "Rodando em segundo plano.\nClique com botão direito para opções.",
                QSystemTrayIcon.Information,
                4000,
            )
        else:
            super().closeEvent(event)

    def on_tray_activated(self, reason):
        if reason == QSystemTrayIcon.Trigger:
            self.show_main()

    def show_main(self):
        self.show()
        self.raise_()
        self.activateWindow()

    def exit_app(self):
        if self.tray:
            self.tray.hide()
        QApplication.quit()

    def selected_coins(self) -> List[str]:
        return [code for code, card in self.coin_cards.items() if card.isChecked()]

    def refresh_next(self):
        cfg = load_config()
        try:
            hhmm = normalize_hhmm(cfg.time)
        except Exception:
            hhmm = "09:00"
        self.next_dt = next_trigger_datetime(hhmm)
        remaining = time_until(self.next_dt)
        self.status.setText(
            f"⏱ Próximo disparo: {self.next_dt.strftime('%d/%m %H:%M')}  •  em {remaining}"
        )
        self.last_fire_key = None

    def save_and_schedule(self):
        try:
            hhmm = normalize_hhmm(self.time_edit.text())
        except ValueError:
            QMessageBox.critical(self, "Erro", "Horário inválido. Use HH:MM (ex: 09:30).")
            return
        coins = self.selected_coins()
        if not coins:
            QMessageBox.critical(self, "Erro", "Selecione pelo menos uma moeda.")
            return
        save_config(AppConfig(time=hhmm, coins=coins))
        self.time_edit.setText(hhmm)
        self.refresh_next()

        # Feedback visual no botão
        self.save_btn.setText("✅  Salvo!")
        self.save_btn.setEnabled(False)
        QTimer.singleShot(2000, lambda: (
            self.save_btn.setText("💾  Salvar e Agendar"),
            self.save_btn.setEnabled(True)
        ))

        if self.tray:
            self.tray.showMessage(
                "Agendamento salvo",
                f"Horário: {hhmm}\nMoedas: {', '.join(coins)}",
                QSystemTrayIcon.Information,
                3000,
            )

    def show_overlay(self, title: str, lines: list):
        if self.toast_widget is not None and self.toast_widget.isVisible():
            self.toast_widget.close()
        self.toast_widget = ToastOverlay(title, lines, duration_ms=15000)
        self.toast_widget.show()

    def test_now(self):
        # Feedback visual
        original_text = self.test_btn.text()
        self.test_btn.setText("⏳  Buscando...")
        self.test_btn.setEnabled(False)
        QTimer.singleShot(3000, lambda: (
            self.test_btn.setText(original_text),
            self.test_btn.setEnabled(True)
        ))
        threading.Thread(target=self.run_job, daemon=True).start()

    def run_job(self):
        cfg = load_config()
        coins = cfg.coins
        if not coins:
            self.bridge.toast.emit("Configuração", ["Nenhuma moeda selecionada."])
            return
        try:
            rows = self.client.fetch_quotes(coins)
            # Montar linhas como tuplas (flag, code, value, pct)
            coin_dict = {c[0]: c[2] for c in AVAILABLE_COINS}
            lines = []
            for code, bid, pct in rows:
                flag = coin_dict.get(code, "💰")
                lines.append((flag, code, fmt_brl(bid), f"{pct:+.2f}%"))
            if not lines:
                self.bridge.toast.emit("Cotações", ["Sem dados retornados pela API."])
                return
            self.bridge.toast.emit("Cotações BRL", lines)
        except requests.RequestException as e:
            self.bridge.toast.emit("Erro de rede", [str(e)])
        except Exception as e:
            self.bridge.toast.emit("Erro", [repr(e)])

    def check_schedule(self):
        if not self.next_dt:
            return
        now = datetime.now()
        if now >= self.next_dt:
            fire_key = self.next_dt.strftime("%Y-%m-%d %H:%M")
            if self.last_fire_key != fire_key:
                self.last_fire_key = fire_key
                threading.Thread(target=self.run_job, daemon=True).start()
            self.refresh_next()

def resource_path(relative: str) -> Path:
    if hasattr(sys, "_MEIPASS"):
        return Path(sys._MEIPASS) / relative
    return Path(__file__).resolve().parent / relative

if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)
    app.setStyleSheet(QSS)

    icon_path = resource_path("icon.ico")
    if icon_path.exists():
        app.setWindowIcon(QIcon(str(icon_path)))

    w = Main()
    w.show()
    sys.exit(app.exec())