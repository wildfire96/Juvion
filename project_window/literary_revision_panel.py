"""Literary Revision Panel for Juvion.

Provides automated literary analysis (repetitions, rhythm, dialogues vs narrative,
POV consistency, estimated reading time, style alerts) and an integrated LLM assistant
that proposes concrete rewrites with user customization and one-click replacement confirmation.
"""

import math
import re
from collections import Counter
from html import unescape

from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QTextCursor
from PyQt5.QtWidgets import (
    QComboBox,
    QDialog,
    QFrame,
    QGroupBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QScrollArea,
    QSplitter,
    QTabWidget,
    QTableWidget,
    QTableWidgetItem,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from settings.llm_worker import LLMWorker
from settings.settings_manager import WWSettingsManager


# Portuguese stopwords list to ignore common filler words when detecting repetitions
STOPWORDS_PT = {
    "a", "ao", "aos", "aquela", "aquelas", "aquele", "aqueles", "aquilo", "as", "até",
    "com", "como", "da", "das", "de", "dela", "delas", "dele", "deles", "depois",
    "do", "dos", "e", "é", "ela", "elas", "ele", "eles", "em", "entre", "era", "eram",
    "éramos", "essa", "essas", "esse", "esses", "esta", "estas", "este", "estes", "estou",
    "está", "estamos", "estão", "estive", "esteve", "estivemos", "estiveram", "eu", "foi",
    "fomos", "foram", "isso", "isto", "já", "lhe", "lhes", "mais", "mas", "me", "mesmo",
    "meu", "meus", "minha", "minhas", "muito", "na", "não", "nas", "nem", "no", "nos",
    "nós", "nossa", "nossas", "nosso", "nossos", "num", "numa", "o", "os", "ou", "para",
    "pela", "pelas", "pelo", "pelos", "por", "qual", "quando", "que", "quem", "se", "sem",
    "ser", "seu", "seus", "só", "sua", "suas", "também", "te", "tem", "temos", "têm",
    "tenho", "ter", "teu", "teus", "tinha", "tinham", "tínhamos", "tu", "tua", "tuas",
    "um", "uma", "você", "vocês"
}


class LiteraryRevisionPanel(QWidget):
    """Panel dedicated to literary revision, rhythm, dialogue ratio, and LLM-assisted fixes."""

    def __init__(self, controller, parent=None):
        super().__init__(parent)
        self.controller = controller
        self.model = controller.model
        self.setObjectName("LiteraryRevisionPanel")
        self.active_worker = None
        self.last_analysis = {}
        self._build_ui()

    def _build_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(14, 14, 14, 14)
        main_layout.setSpacing(10)

        # Header
        header_layout = QHBoxLayout()
        title = QLabel("Revisão Literária")
        title.setStyleSheet("font-size: 18px; font-weight: 700;")
        header_layout.addWidget(title)
        header_layout.addStretch()

        self.btn_analyze = QPushButton("Analisar cena aberta")
        self.btn_analyze.setProperty("primary", True)
        self.btn_analyze.setToolTip("Executa análise de ritmo, repetições, equilíbrio de diálogos e alertas na cena atual.")
        self.btn_analyze.clicked.connect(self.run_analysis)
        header_layout.addWidget(self.btn_analyze)
        main_layout.addLayout(header_layout)

        # Subtitle / reading time banner
        self.metrics_banner = QLabel("Abra uma cena e clique em 'Analisar cena aberta' para calcular ritmo, métricas e alertas.")
        self.metrics_banner.setWordWrap(True)
        self.metrics_banner.setStyleSheet("padding: 8px; border-radius: 6px; background-color: rgba(255,255,255,0.05); font-size: 13px;")
        main_layout.addWidget(self.metrics_banner)

        # Tabs for categorized analysis
        self.tabs = QTabWidget()
        main_layout.addWidget(self.tabs, stretch=1)

        # Tab 1: Alertas e Diagnóstico Geral
        self.tab_diagnostics = QWidget()
        self._build_diagnostics_tab()
        self.tabs.addTab(self.tab_diagnostics, "Diagnóstico & Alertas")

        # Tab 2: Repetições de Palavras
        self.tab_repetitions = QWidget()
        self._build_repetitions_tab()
        self.tabs.addTab(self.tab_repetitions, "Repetições")

        # Tab 3: Ritmo e Parágrafos
        self.tab_rhythm = QWidget()
        self._build_rhythm_tab()
        self.tabs.addTab(self.tab_rhythm, "Ritmo & Diálogos")

        # Tab 4: Assistente LLM com Confirmação
        self.tab_llm_fix = QWidget()
        self._build_llm_fix_tab()
        self.tabs.addTab(self.tab_llm_fix, "Aprimoramento com IA")

    def _build_diagnostics_tab(self):
        layout = QVBoxLayout(self.tab_diagnostics)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(8)

        lbl = QLabel("Alertas Literários e Ponto de Vista:")
        lbl.setStyleSheet("font-weight: 600;")
        layout.addWidget(lbl)

        self.alerts_list = QTextEdit()
        self.alerts_list.setReadOnly(True)
        self.alerts_list.setPlaceholderText("Nenhum alerta gerado. Execute a análise na cena aberta.")
        layout.addWidget(self.alerts_list)

        # Action button to send flagged issues to the LLM tab
        self.btn_send_to_ai = QPushButton("Enviar trechos com alerta para o Aprimoramento com IA")
        self.btn_send_to_ai.clicked.connect(self._send_alerts_to_ai)
        layout.addWidget(self.btn_send_to_ai)

    def _build_repetitions_tab(self):
        layout = QVBoxLayout(self.tab_repetitions)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(8)

        desc = QLabel("Palavras mais repetidas (excluindo artigos e preposições). Clique duas vezes em uma palavra para buscá-la ou enviá-la para revisão.")
        desc.setWordWrap(True)
        layout.addWidget(desc)

        self.rep_table = QTableWidget(0, 3)
        self.rep_table.setHorizontalHeaderLabels(["Palavra", "Ocorrências", "Ação rápida"])
        self.rep_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.rep_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        self.rep_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        self.rep_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        layout.addWidget(self.rep_table)

    def _build_rhythm_tab(self):
        layout = QVBoxLayout(self.tab_rhythm)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(8)

        # Dialogues vs Narrative
        group_balance = QGroupBox("Equilíbrio de Diálogos vs. Narrativa")
        balance_layout = QVBoxLayout(group_balance)
        self.dialogue_ratio_label = QLabel("Diálogos: 0% | Narrativa/Descrição: 0%")
        balance_layout.addWidget(self.dialogue_ratio_label)
        self.dialogue_bar = QProgressBar()
        self.dialogue_bar.setRange(0, 100)
        self.dialogue_bar.setValue(0)
        self.dialogue_bar.setFormat("Diálogo: %v%")
        balance_layout.addWidget(self.dialogue_bar)
        layout.addWidget(group_balance)

        # Sentence/Paragraph Length Variance
        group_rhythm = QGroupBox("Variância de Ritmo")
        rhythm_layout = QVBoxLayout(group_rhythm)
        self.rhythm_details_label = QLabel("Aguardando análise...")
        self.rhythm_details_label.setWordWrap(True)
        rhythm_layout.addWidget(self.rhythm_details_label)
        layout.addWidget(group_rhythm)

        layout.addStretch()

    def _build_llm_fix_tab(self):
        layout = QVBoxLayout(self.tab_llm_fix)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(8)

        # Objective / Mode combo
        mode_layout = QHBoxLayout()
        mode_layout.addWidget(QLabel("Objetivo da revisão:"))
        self.revision_mode = QComboBox()
        self.revision_mode.addItems([
            "Eliminar repetições e enriquecer vocabulário",
            "Ajustar ritmo (alternar frases curtas e longas)",
            "Aprimorar diálogos e naturalidade",
            "Uniformizar ponto de vista (POV) e tempo verbal",
            "Polir estilo e fluidez narrativa",
            "Personalizado"
        ])
        mode_layout.addWidget(self.revision_mode, stretch=1)
        layout.addLayout(mode_layout)

        # Custom Instructions
        custom_layout = QHBoxLayout()
        custom_layout.addWidget(QLabel("Instrução personalizada:"))
        self.custom_instruction = QLineEdit()
        self.custom_instruction.setPlaceholderText("Ex: Deixe o tom mais sombrio, troque 'caminhou' por sinônimos mais vivos...")
        custom_layout.addWidget(self.custom_instruction, stretch=1)
        layout.addLayout(custom_layout)

        # Splitter with Source text and Proposed rewrite
        splitter = QSplitter(Qt.Orientation.Vertical)

        # Source / Selection
        source_widget = QWidget()
        source_layout = QVBoxLayout(source_widget)
        source_layout.setContentsMargins(0, 0, 0, 0)
        source_header = QHBoxLayout()
        source_header.addWidget(QLabel("Texto original a revisar:"))
        btn_load_selection = QPushButton("Pegar seleção do editor")
        btn_load_selection.clicked.connect(self._load_selection_from_editor)
        btn_load_scene = QPushButton("Pegar cena inteira")
        btn_load_scene.clicked.connect(self._load_full_scene_text)
        source_header.addWidget(btn_load_selection)
        source_header.addWidget(btn_load_scene)
        source_layout.addLayout(source_header)

        self.text_source = QTextEdit()
        self.text_source.setPlaceholderText("Cole ou selecione o trecho que passará pela revisão...")
        source_layout.addWidget(self.text_source)
        splitter.addWidget(source_widget)

        # Proposed / AI Rewrite
        ai_widget = QWidget()
        ai_layout = QVBoxLayout(ai_widget)
        ai_layout.setContentsMargins(0, 0, 0, 0)
        ai_header = QHBoxLayout()
        ai_header.addWidget(QLabel("Proposta da IA (personalize e edite livremente antes de aplicar):"))
        self.btn_run_ai = QPushButton("Sugerir com IA")
        self.btn_run_ai.setProperty("primary", True)
        self.btn_run_ai.clicked.connect(self.request_ai_suggestions)
        self.btn_stop_ai = QPushButton("Parar")
        self.btn_stop_ai.setEnabled(False)
        self.btn_stop_ai.clicked.connect(self.stop_ai)
        ai_header.addWidget(self.btn_run_ai)
        ai_header.addWidget(self.btn_stop_ai)
        ai_layout.addLayout(ai_header)

        self.text_proposed = QTextEdit()
        self.text_proposed.setPlaceholderText("A sugestão de reescrita da IA aparecerá aqui em tempo real. Você poderá editá-la antes de confirmar...")
        ai_layout.addWidget(self.text_proposed)
        splitter.addWidget(ai_widget)

        layout.addWidget(splitter, stretch=1)

        # Confirmation & Replacement controls
        bottom_actions = QHBoxLayout()
        self.btn_confirm_replace = QPushButton("Confirmar e Substituir no Editor")
        self.btn_confirm_replace.setProperty("primary", True)
        self.btn_confirm_replace.setStyleSheet("font-weight: bold; padding: 8px;")
        self.btn_confirm_replace.clicked.connect(self.apply_replacement_with_confirmation)
        bottom_actions.addWidget(self.btn_confirm_replace)

        btn_clear = QPushButton("Limpar")
        btn_clear.clicked.connect(lambda: (self.text_source.clear(), self.text_proposed.clear()))
        bottom_actions.addWidget(btn_clear)
        layout.addLayout(bottom_actions)

    # -------------------------------------------------------------------------
    # Analysis Engine
    # -------------------------------------------------------------------------
    def run_analysis(self):
        text = self.controller.scene_editor.editor.toPlainText().strip()
        if not text:
            self.metrics_banner.setText("Abra ou escreva algum texto na cena e clique em 'Atualizar Análise'.")
            self.rep_table.setRowCount(0)
            self.alerts_list.clear()
            self.dialogue_bar.setValue(0)
            self.dialogue_ratio_label.setText("Diálogos: 0% | Narrativa/Descrição: 0%")
            self.rhythm_details_label.setText("Aguardando texto na cena...")
            return

        words = re.findall(r"\b[A-Za-zÀ-ÖØ-öø-ÿ\d_'-]+\b", text)
        word_count = len(words)
        paragraphs = [p.strip() for p in text.split("\n") if p.strip()]
        paragraph_count = len(paragraphs)
        sentences = [s.strip() for s in re.split(r"[.!?]+", text) if s.strip()]
        sentence_count = len(sentences)

        # 1. Reading Time Estimate (average 200 words per minute for fiction)
        reading_time_min = math.ceil(word_count / 200) if word_count else 0
        self.metrics_banner.setText(
            f"<b>{word_count}</b> palavras · <b>{paragraph_count}</b> parágrafos · <b>{sentence_count}</b> frases · "
            f"Tempo estimado de leitura: ~<b>{reading_time_min} min</b> (a 200 ppm)"
        )

        # 2. Word Repetitions (filter out stopwords and short tokens)
        content_words = [w.lower() for w in words if len(w) > 3 and w.lower() not in STOPWORDS_PT]
        counter = Counter(content_words)
        frequent = [item for item in counter.most_common(30) if item[1] >= 3]

        self.rep_table.setRowCount(0)
        for row, (word, count) in enumerate(frequent):
            self.rep_table.insertRow(row)
            self.rep_table.setItem(row, 0, QTableWidgetItem(word))
            self.rep_table.setItem(row, 1, QTableWidgetItem(str(count)))
            btn = QPushButton("Revisar com IA")
            btn.clicked.connect(lambda _checked, w=word: self._prepare_ai_repetition_fix(w))
            self.rep_table.setCellWidget(row, 2, btn)

        # 3. Dialogue vs Narrative Balance
        # Detect dialogue lines (starting with dash — or - or quotes)
        dialogue_words = 0
        narrative_words = 0
        for p in paragraphs:
            p_clean = p.lstrip()
            if p_clean.startswith("—") or p_clean.startswith("-") or p_clean.startswith('"') or p_clean.startswith("“"):
                dialogue_words += len(re.findall(r"\b\w+\b", p))
            else:
                # Inside paragraph dialogue checks
                in_quote = re.findall(r'[“"][^"”]+[”"]', p)
                in_dash = re.findall(r"—[^—]+—", p)
                dialogue_inside_words = sum(len(re.findall(r"\b\w+\b", match)) for match in (in_quote + in_dash))
                total_p = len(re.findall(r"\b\w+\b", p))
                dialogue_words += dialogue_inside_words
                narrative_words += max(0, total_p - dialogue_inside_words)

        total_analyzed = dialogue_words + narrative_words
        dialogue_pct = round((dialogue_words / total_analyzed * 100)) if total_analyzed else 0
        narrative_pct = 100 - dialogue_pct if total_analyzed else 0

        self.dialogue_bar.setValue(dialogue_pct)
        self.dialogue_ratio_label.setText(
            f"Diálogos: <b>{dialogue_pct}%</b> ({dialogue_words} palavras) | "
            f"Narrativa/Descrição: <b>{narrative_pct}%</b> ({narrative_words} palavras)"
        )

        # 4. Rhythm and Sentence Variety
        sentence_lengths = [len(re.findall(r"\b\w+\b", s)) for s in sentences if s]
        avg_sentence = round(sum(sentence_lengths) / len(sentence_lengths), 1) if sentence_lengths else 0
        long_sentences = [s for s in sentences if len(re.findall(r"\b\w+\b", s)) > 35]

        rhythm_report = (
            f"• Comprimento médio das frases: <b>{avg_sentence}</b> palavras.\n"
            f"• Frases muito longas (>35 palavras): <b>{len(long_sentences)}</b> identificada(s).\n"
        )
        if len(long_sentences) > 3:
            rhythm_report += "⚠️ Frases excessivamente extensas podem cansar a leitura. Considere quebrar períodos.\n"
        elif avg_sentence < 8 and sentence_count > 10:
            rhythm_report += "⚠️ Muitas frases curtas em sequência podem soar telegráficas. Varie o ritmo.\n"
        else:
            rhythm_report += "✓ Boa cadência geral identificada.\n"

        self.rhythm_details_label.setText(rhythm_report)

        # 5. Alerts & POV Consistency
        alerts = []
        # Check POV hints from project settings
        global_pov = self.model.settings.get("global_pov", "").lower()
        first_person_cues = len(re.findall(r"\b(eu|me|mim|comigo|meu|minha|meus|minhas|pensei|olhei|disse|vi|senti)\b", text, re.IGNORECASE))
        third_person_cues = len(re.findall(r"\b(ele|ela|eles|elas|dele|dela|deles|delas|pensou|olhou|disse|viu|sentiu)\b", text, re.IGNORECASE))

        if "primeira" in global_pov or "first" in global_pov:
            if third_person_cues > first_person_cues * 2 and first_person_cues < 5:
                alerts.append("⚠️ <b>Ponto de Vista (POV):</b> O projeto está configurado para 1ª Pessoa, mas o texto parece estar predominantemente em 3ª pessoa.")
        elif "terceira" in global_pov or "third" in global_pov:
            if first_person_cues > third_person_cues and dialogue_pct < 30:
                alerts.append("⚠️ <b>Ponto de Vista (POV):</b> O projeto está configurado para 3ª Pessoa, mas há muitos marcadores de 1ª pessoa fora de diálogos.")

        # Gerundism check
        gerunds = re.findall(r"\b\w+ando\b|\b\w+endo\b|\b\w+indo\b", text, re.IGNORECASE)
        if len(gerunds) > word_count * 0.05 and len(gerunds) > 8:
            alerts.append(f"⚠️ <b>Uso excessivo de gerúndios:</b> Encontrados {len(gerunds)} gerúndios. Reduzir verbos em -ndo dá mais agilidade à prosa.")

        # Adverb in -mente check
        adverbs_mente = re.findall(r"\b\w+mente\b", text, re.IGNORECASE)
        if len(adverbs_mente) > 8:
            alerts.append(f"⚠️ <b>Advérbios em -mente ({len(adverbs_mente)}):</b> Pode enfraquecer verbos de ação. Considere substituir por ações descritivas.")

        # Extreme repetitive words alert
        if frequent and frequent[0][1] >= 6:
            alerts.append(f"⚠️ <b>Repetição intensa:</b> A palavra '<b>{frequent[0][0]}</b>' apareceu {frequent[0][1]} vezes nesta cena.")

        if not alerts:
            alerts.append("✓ Nenhum problema crítico de consistência ou vícios estilísticos detectado. Excelente trabalho!")

        self.alerts_list.setHtml("<br><br>".join(alerts))
        self.last_analysis = {
            "text": text,
            "frequent": frequent,
            "alerts": alerts,
            "long_sentences": long_sentences
        }

    # -------------------------------------------------------------------------
    # Quick Actions from analysis
    # -------------------------------------------------------------------------
    def _prepare_ai_repetition_fix(self, word):
        self.tabs.setCurrentWidget(self.tab_llm_fix)
        self.revision_mode.setCurrentText("Eliminar repetições e enriquecer vocabulário")
        self.custom_instruction.setText(f"Substitua ou varie o uso repetido da palavra '{word}', mantendo a fluidez e naturalidade.")
        # Load selection or context
        self._load_selection_or_full_scene()

    def _send_alerts_to_ai(self):
        if not self.last_analysis.get("text"):
            self.run_analysis()
        self.tabs.setCurrentWidget(self.tab_llm_fix)
        self.revision_mode.setCurrentText("Polir estilo e fluidez narrativa")
        instructions = []
        for alert in self.last_analysis.get("alerts", []):
            clean = re.sub(r"<[^>]+>", "", alert).replace("⚠️", "").replace("✓", "").strip()
            if clean:
                instructions.append(clean)
        self.custom_instruction.setText("; ".join(instructions[:3]))
        self._load_selection_or_full_scene()

    def _load_selection_from_editor(self):
        cursor = self.controller.scene_editor.editor.textCursor()
        if cursor.hasSelection():
            self.text_source.setPlainText(cursor.selectedText().replace("\u2029", "\n"))
        else:
            QMessageBox.information(self, "Seleção", "Nenhum trecho selecionado no editor. Selecione um trecho ou clique em 'Pegar cena inteira'.")

    def _load_full_scene_text(self):
        text = self.controller.scene_editor.editor.toPlainText().strip()
        self.text_source.setPlainText(text)

    def _load_selection_or_full_scene(self):
        cursor = self.controller.scene_editor.editor.textCursor()
        if cursor.hasSelection():
            self.text_source.setPlainText(cursor.selectedText().replace("\u2029", "\n"))
        elif not self.text_source.toPlainText().strip():
            self.text_source.setPlainText(self.controller.scene_editor.editor.toPlainText().strip())

    # -------------------------------------------------------------------------
    # LLM Interaction
    # -------------------------------------------------------------------------
    def request_ai_suggestions(self):
        source_text = self.text_source.toPlainText().strip()
        if not source_text:
            QMessageBox.warning(self, "Revisão Literária", "Insira ou selecione um trecho de texto para revisar.")
            return

        mode = self.revision_mode.currentText()
        user_notes = self.custom_instruction.text().strip()

        # Build precise authorial prompt
        prompt = (
            "Você é um editor literário profissional assistindo o autor no software Juvion.\n"
            f"Objetivo da revisão: {mode}\n"
        )
        if user_notes:
            prompt += f"Instruções específicas do autor: {user_notes}\n"

        prompt += (
            "\nDiretrizes cruciais:\n"
            "1. Reescreva o trecho original solucionando problemas de repetição excessiva, cadência de ritmo e consistência.\n"
            "2. Mantenha fielmente o estilo, tom, personagens e intenção do autor.\n"
            "3. Entregue DIRETAMENTE a versão reescrita e aprimorada, pronta para substituir o original no manuscrito.\n"
            "4. Não adicione saudações, introduções ou explicações fora do texto literário.\n\n"
            f"--- TRECHO ORIGINAL ---\n{source_text}\n--- FIM DO ORIGINAL ---\n\n"
            "Versão Aprimorada:"
        )

        # Retrieve active LLM config
        llm_configs = WWSettingsManager.get_llm_configs()
        active_name = WWSettingsManager.get_active_llm_name()
        config = llm_configs.get(active_name, {})

        overrides = {
            "provider": config.get("provider", "Local"),
            "model": config.get("current_model") or config.get("model", "Local Model"),
            "max_tokens": 2048,
            "temperature": 0.7
        }

        self.text_proposed.clear()
        self.btn_run_ai.setEnabled(False)
        self.btn_stop_ai.setEnabled(True)

        self.active_worker = LLMWorker(prompt, overrides)
        self.active_worker.data_received.connect(self._on_ai_chunk)
        self.active_worker.finished.connect(self._on_ai_finished)
        self.active_worker.start()

    def _on_ai_chunk(self, chunk):
        cursor = self.text_proposed.textCursor()
        cursor.movePosition(QTextCursor.MoveOperation.End)
        cursor.insertText(chunk)
        self.text_proposed.setTextCursor(cursor)

    def _on_ai_finished(self):
        self.btn_run_ai.setEnabled(True)
        self.btn_stop_ai.setEnabled(False)
        self.active_worker = None

    def stop_ai(self):
        if self.active_worker and self.active_worker.isRunning():
            self.active_worker.stop()
        self.btn_run_ai.setEnabled(True)
        self.btn_stop_ai.setEnabled(False)

    # -------------------------------------------------------------------------
    # Confirmation & Replacement
    # -------------------------------------------------------------------------
    def apply_replacement_with_confirmation(self):
        proposed_text = self.text_proposed.toPlainText().strip()
        source_text = self.text_source.toPlainText().strip()

        if not proposed_text:
            QMessageBox.warning(self, "Substituição", "Não há texto aprimorado para substituir.")
            return

        editor = self.controller.scene_editor.editor
        current_full_text = editor.toPlainText()

        cursor = editor.textCursor()
        selected_text = cursor.selectedText().replace("\u2029", "\n")

        # Decide whether we replace the current editor selection or the matching source text
        is_selection_target = (cursor.hasSelection() and selected_text.strip() == source_text)

        confirm_msg = (
            "Deseja confirmar a substituição no manuscrito?\n\n"
            f"• Trecho a ser substituído: {len(source_text)} caracteres\n"
            f"• Nova versão do texto: {len(proposed_text)} caracteres\n\n"
            "A alteração pode ser desfeita a qualquer momento pelo atalho Ctrl+Z."
        )

        reply = QMessageBox.question(
            self,
            "Confirmar Substituição Literária",
            confirm_msg,
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.Yes
        )

        if reply != QMessageBox.StandardButton.Yes:
            return

        if is_selection_target:
            cursor.insertText(proposed_text)
            editor.setTextCursor(cursor)
            self.controller.model.unsaved_changes = True
            self.controller.statusBar().showMessage("Trecho substituído com sucesso na cena.", 4000)
            return

        # If source_text is present in current_full_text
        if source_text and source_text in current_full_text:
            # Replace only the original span, retaining other formatting and undo.
            cursor = editor.document().find(source_text)
            if cursor.isNull():
                start = current_full_text.index(source_text)
                # Qt cursor positions count UTF-16 units, including emoji pairs.
                cursor = QTextCursor(editor.document())
                cursor.setPosition(len(current_full_text[:start].encode("utf-16-le")) // 2)
                cursor.setPosition(len(current_full_text[:start + len(source_text)].encode("utf-16-le")) // 2, QTextCursor.KeepAnchor)
            cursor.beginEditBlock()
            cursor.insertText(proposed_text)
            cursor.endEditBlock()
            editor.setTextCursor(cursor)
            self.controller.model.unsaved_changes = True
            self.controller.statusBar().showMessage("Texto substituído e atualizado no manuscrito.", 4000)
        else:
            # Offer to replace open scene completely if user intended to review the whole scene
            sub_all = QMessageBox.question(
                self,
                "Texto original não localizado exatamente",
                "O trecho original exato não foi encontrado como seleção ativa. Deseja substituir TODO o texto da cena aberta pela nova versão aprimorada?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No
            )
            if sub_all == QMessageBox.StandardButton.Yes:
                cursor = QTextCursor(editor.document())
                cursor.select(QTextCursor.Document)
                cursor.beginEditBlock()
                cursor.insertText(proposed_text)
                cursor.endEditBlock()
                editor.setTextCursor(cursor)
                self.controller.model.unsaved_changes = True
                self.controller.statusBar().showMessage("Cena inteira atualizada com a versão revisada.", 4000)
