"""Widget de card de jogo moderno com capa, badges, preço e botões de ação."""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from PySide6.QtCore import QPoint, Qt, Signal
from PySide6.QtGui import QColor, QCursor, QFont, QPainter, QPainterPath, QPixmap
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QMenu,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from ...models import Post
from ...services.covers import CoverCacheService, get_cover_url_for_post
from ...sources.stores import (
    STORE_LABELS,
    TYPE_BETA,
    TYPE_GAME,
    TYPE_LABELS,
    TYPE_LOOT,
    get_store_style,
)
from ..util import fmt_price, open_url

COVER_WIDTH = 290
COVER_HEIGHT = 135


def _create_placeholder_pixmap(title: str, store_slug: str) -> QPixmap:
    """Cria um banner de fallback estilizado com as cores da loja."""
    pixmap = QPixmap(COVER_WIDTH, COVER_HEIGHT)
    style = get_store_style(store_slug)
    bg_color = QColor(style.get("bg", "#1b2838"))

    pixmap.fill(bg_color)
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)

    # Desenhar gradiente suave
    symbol = style.get("icon_symbol", "🎮")
    font_symbol = QFont("Segoe UI Emoji", 32)
    painter.setFont(font_symbol)
    painter.setPen(QColor(style.get("text", "#66c0f4")))
    painter.drawText(pixmap.rect(), Qt.AlignmentFlag.AlignCenter, symbol)

    # Nome da loja no rodapé do placeholder
    painter.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
    painter.setPen(QColor(255, 255, 255, 140))
    rect = pixmap.rect().adjusted(10, 10, -10, -10)
    painter.drawText(rect, Qt.AlignmentFlag.AlignBottom | Qt.AlignmentFlag.AlignHCenter, style.get("short", "Jogo"))
    painter.end()

    return pixmap


class GameCardWidget(QFrame):
    """Card moderno estilizado representando um jogo gratuito."""

    claim_requested = Signal(str, object)  # (url, app_id)
    mark_in_library_requested = Signal(int, bool)  # (post_id, in_library)

    def __init__(
        self,
        post: Post,
        group_name: Optional[str] = None,
        cover_service: Optional[CoverCacheService] = None,
        parent: Optional[QWidget] = None,
    ) -> None:
        super().__init__(parent)
        self.post = post
        self.group_name = group_name
        self._cover_service = cover_service
        self._cover_url = get_cover_url_for_post(post)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self._build_ui()

        if self._cover_service and self._cover_url:
            self._cover_service.cover_loaded.connect(self._on_cover_loaded)
            cached_pix = self._cover_service.request_cover(self._cover_url)
            if cached_pix:
                self._set_cover_pixmap(cached_pix)

    def _build_ui(self) -> None:
        self.setObjectName("gameCard")
        self.setFixedWidth(300)
        self.setStyleSheet("""
            QFrame#gameCard {
                background-color: #171f2c;
                border: 1px solid #293548;
                border-radius: 10px;
            }
            QFrame#gameCard:hover {
                background-color: #1c2636;
                border: 1px solid #38bdf8;
            }
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 10)
        layout.setSpacing(8)

        # 1. Capa com badges flutuantes
        self._cover_frame = QFrame()
        self._cover_frame.setFixedSize(COVER_WIDTH, COVER_HEIGHT)
        self._cover_frame.setStyleSheet("background-color: #0f172a; border-top-left-radius: 9px; border-top-right-radius: 9px;")
        cover_layout = QVBoxLayout(self._cover_frame)
        cover_layout.setContentsMargins(8, 8, 8, 8)

        # Top badges: Loja (esquerda) e Prazo (direita)
        badges_row = QHBoxLayout()
        badges_row.setSpacing(6)

        store_style = get_store_style(self.post.store)
        store_label = QLabel(f"{store_style.get('icon_symbol', '')} {store_style.get('short', self.post.store.title())}")
        store_label.setStyleSheet(f"""
            background-color: {store_style.get('bg', '#1e293b')};
            color: {store_style.get('text', '#ffffff')};
            border: 1px solid {store_style.get('border', '#475569')};
            border-radius: 10px;
            padding: 2px 8px;
            font-size: 11px;
            font-weight: bold;
        """)
        badges_row.addWidget(store_label)
        badges_row.addStretch(1)

        # Badge de expiração
        exp_text, exp_style = self._format_expiration()
        if exp_text:
            exp_badge = QLabel(exp_text)
            exp_badge.setStyleSheet(exp_style)
            badges_row.addWidget(exp_badge)

        cover_layout.addLayout(badges_row)
        cover_layout.addStretch(1)

        self._cover_label = QLabel(self._cover_frame)
        self._cover_label.setFixedSize(COVER_WIDTH, COVER_HEIGHT)
        self._cover_label.setScaledContents(True)
        self._cover_label.lower()  # Fica atrás dos badges

        # Placeholder inicial
        placeholder = _create_placeholder_pixmap(self.post.title, self.post.store)
        self._set_cover_pixmap(placeholder)

        layout.addWidget(self._cover_frame, 0, Qt.AlignmentFlag.AlignHCenter)

        # 2. Informações da Oferta (Área Interna)
        content_box = QWidget()
        content_layout = QVBoxLayout(content_box)
        content_layout.setContentsMargins(12, 2, 12, 0)
        content_layout.setSpacing(4)

        # Título
        self._title_label = QLabel(self.post.title)
        self._title_label.setWordWrap(True)
        self._title_label.setStyleSheet("font-size: 14px; font-weight: bold; color: #f8fafc;")
        self._title_label.setFixedHeight(40)
        content_layout.addWidget(self._title_label)

        # Subtítulo (Tipo de oferta e Fonte)
        type_desc = TYPE_LABELS.get(self.post.type, "Jogo") if hasattr(self.post, "type") and self.post.type else "Jogo"
        source_name = self.group_name or ("GamerPower" if self.post.source == "gamerpower" else "Steam")
        sub_label = QLabel(f"{type_desc} · {source_name}")
        sub_label.setStyleSheet("font-size: 11px; color: #94a3b8;")
        content_layout.addWidget(sub_label)

        # Preço e Tag 100% Grátis
        price_row = QHBoxLayout()
        price_row.setSpacing(6)

        free_badge = QLabel("100% GRÁTIS")
        free_badge.setStyleSheet("""
            background-color: #15803d;
            color: #dcfce7;
            font-size: 11px;
            font-weight: 800;
            padding: 2px 6px;
            border-radius: 4px;
        """)
        price_row.addWidget(free_badge)

        # Valor original
        worth_text = self._format_original_price()
        if worth_text:
            orig_price_label = QLabel(worth_text)
            orig_price_label.setStyleSheet("color: #64748b; font-size: 11px; text-decoration: line-through;")
            price_row.addWidget(orig_price_label)

        price_row.addStretch(1)
        content_layout.addLayout(price_row)

        layout.addWidget(content_box)

        # 3. Botões de Ação
        actions_box = QWidget()
        actions_layout = QHBoxLayout(actions_box)
        actions_layout.setContentsMargins(12, 4, 12, 0)
        actions_layout.setSpacing(6)

        self._btn_claim = QPushButton("Resgatar ➔")
        self._btn_claim.setObjectName("cardClaimBtn")
        self._btn_claim.setToolTip("Abrir página de resgate na loja")
        self._btn_claim.setStyleSheet("""
            QPushButton#cardClaimBtn {
                background-color: #0284c7;
                color: #ffffff;
                font-weight: bold;
                border-radius: 6px;
                padding: 6px 10px;
                font-size: 12px;
            }
            QPushButton#cardClaimBtn:hover {
                background-color: #38bdf8;
                color: #0f172a;
            }
        """)
        self._btn_claim.clicked.connect(self._on_claim_clicked)
        actions_layout.addWidget(self._btn_claim, 2)

        self._btn_library = QPushButton("✓ Já tenho")
        self._btn_library.setObjectName("cardLibBtn")
        self._btn_library.setToolTip("Marcar como resgatado (remove do painel inicial)")
        self._btn_library.setStyleSheet("""
            QPushButton#cardLibBtn {
                background-color: #1e293b;
                color: #94a3b8;
                border: 1px solid #334155;
                border-radius: 6px;
                padding: 6px 8px;
                font-size: 11px;
            }
            QPushButton#cardLibBtn:hover {
                background-color: #334155;
                color: #f8fafc;
            }
        """)
        self._btn_library.clicked.connect(self._on_library_clicked)
        actions_layout.addWidget(self._btn_library, 1)

        layout.addWidget(actions_box)

    def _set_cover_pixmap(self, pixmap: QPixmap) -> None:
        """Aplica a imagem com cantos arredondados no topo."""
        scaled = pixmap.scaled(
            COVER_WIDTH,
            COVER_HEIGHT,
            Qt.AspectRatioMode.KeepAspectRatioByExpanding,
            Qt.TransformationMode.SmoothTransformation,
        )

        rounded = QPixmap(COVER_WIDTH, COVER_HEIGHT)
        rounded.fill(Qt.GlobalColor.transparent)
        painter = QPainter(rounded)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        path = QPainterPath()
        # Arredondar apenas os cantos superiores
        radius = 9.0
        path.moveTo(0, COVER_HEIGHT)
        path.lineTo(0, radius)
        path.quadTo(0, 0, radius, 0)
        path.lineTo(COVER_WIDTH - radius, 0)
        path.quadTo(COVER_WIDTH, 0, COVER_WIDTH, radius)
        path.lineTo(COVER_WIDTH, COVER_HEIGHT)
        path.closeSubpath()

        painter.setClipPath(path)
        # Centralizar a imagem
        x = (COVER_WIDTH - scaled.width()) // 2
        y = (COVER_HEIGHT - scaled.height()) // 2
        painter.drawPixmap(x, y, scaled)
        painter.end()

        self._cover_label.setPixmap(rounded)

    def _on_cover_loaded(self, url: str, pixmap: QPixmap) -> None:
        if url == self._cover_url:
            self._set_cover_pixmap(pixmap)

    def _format_expiration(self) -> tuple[Optional[str], str]:
        if not getattr(self.post, "ends_at", None):
            return None, ""
        now = datetime.now()
        ends = self.post.ends_at
        if ends <= now:
            return "Expirando", "background-color: #991b1b; color: #fecaca; border-radius: 10px; padding: 2px 6px; font-size: 10px; font-weight: bold;"

        diff = ends - now
        hours = diff.total_seconds() / 3600
        if hours <= 24:
            text = f"⏳ {int(hours)}h restantes"
            style = "background-color: #b91c1c; color: #ffffff; border-radius: 10px; padding: 2px 6px; font-size: 10px; font-weight: bold;"
        elif diff.days <= 3:
            text = f"⏳ {diff.days}d restantes"
            style = "background-color: #d97706; color: #ffffff; border-radius: 10px; padding: 2px 6px; font-size: 10px; font-weight: bold;"
        else:
            text = f"Até {ends.strftime('%d/%m')}"
            style = "background-color: rgba(15, 23, 42, 0.85); color: #cbd5e1; border-radius: 10px; padding: 2px 6px; font-size: 10px;"

        return text, style

    def _format_original_price(self) -> Optional[str]:
        if getattr(self.post, "worth_usd", None) and self.post.worth_usd > 0:
            return f"De ${self.post.worth_usd:.2f}"
        if getattr(self.post, "price_initial_cents", None) and self.post.price_initial_cents > 0:
            return fmt_price(self.post.price_initial_cents, self.post.price_currency)
        return None

    def _on_claim_clicked(self) -> None:
        url = self.post.claim_url or self.post.store_url or self.post.publication_url
        self.claim_requested.emit(url, self.post.store_app_id)

    def _on_library_clicked(self) -> None:
        if self.post.id is not None:
            self.mark_in_library_requested.emit(self.post.id, True)

    def mouseDoubleClickEvent(self, event) -> None:
        self._on_claim_clicked()

    def contextMenuEvent(self, event) -> None:
        menu = QMenu(self)
        act_claim = menu.addAction("Resgatar oferta na loja")
        act_pub = menu.addAction("Abrir link da publicação")
        act_lib = menu.addAction("Marcar como já adicionado à biblioteca")

        action = menu.exec(event.globalPos())
        if action == act_claim:
            self._on_claim_clicked()
        elif action == act_pub and self.post.publication_url:
            open_url(self.post.publication_url)
        elif action == act_lib and self.post.id is not None:
            self.mark_in_library_requested.emit(self.post.id, True)
