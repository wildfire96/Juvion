"""Project progress dashboard for word, structure, and completion goals."""

import re
from html import unescape

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import (
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QProgressBar,
    QPushButton,
    QSpinBox,
    QTreeWidget,
    QTreeWidgetItem,
    QVBoxLayout,
    QWidget,
)


class ProgressDashboard(QWidget):
    """Give the writer a useful overview without turning the manuscript into a spreadsheet."""

    def __init__(self, controller, parent=None):
        super().__init__(parent)
        self.controller = controller
        self.model = controller.model
        self.setObjectName("ProgressPanel")
        self._build_ui()
        self.refresh()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 18, 18, 18)
        layout.setSpacing(12)

        title = QLabel("Progresso da obra")
        title.setStyleSheet("font-size: 20px; font-weight: 700;")
        layout.addWidget(title)
        intro = QLabel("Acompanhe o manuscrito, defina uma meta realista e veja o próximo trecho que precisa de atenção.")
        intro.setWordWrap(True)
        intro.setObjectName("PanelDescription")
        layout.addWidget(intro)

        goals = QGroupBox("Meta do manuscrito")
        goal_layout = QHBoxLayout(goals)
        goal_layout.addWidget(QLabel("Palavras desejadas:"))
        self.word_goal = QSpinBox()
        self.word_goal.setRange(0, 9_999_999)
        self.word_goal.setSingleStep(1_000)
        self.word_goal.setSuffix(" palavras")
        goal_layout.addWidget(self.word_goal)
        self.save_goal_button = QPushButton("Salvar meta")
        self.save_goal_button.setProperty("primary", True)
        self.save_goal_button.clicked.connect(self.save_goal)
        goal_layout.addWidget(self.save_goal_button)
        goal_layout.addStretch()
        layout.addWidget(goals)

        self.word_label = QLabel()
        self.word_label.setStyleSheet("font-size: 17px; font-weight: 650;")
        layout.addWidget(self.word_label)
        self.word_progress = QProgressBar()
        self.word_progress.setTextVisible(True)
        layout.addWidget(self.word_progress)

        self.structure_label = QLabel()
        self.structure_label.setWordWrap(True)
        layout.addWidget(self.structure_label)

        self.scene_tree = QTreeWidget()
        self.scene_tree.setHeaderLabels(["Estrutura", "Etapa", "Palavras"])
        self.scene_tree.setToolTip("Cenas concluídas aparecem com a etapa Final Draft.")
        layout.addWidget(self.scene_tree, 1)

        footer = QHBoxLayout()
        footer.addStretch()
        refresh_button = QPushButton("Atualizar")
        refresh_button.clicked.connect(self.refresh)
        footer.addWidget(refresh_button)
        layout.addLayout(footer)

    def save_goal(self):
        self.model.settings.setdefault("progress", {})["word_goal"] = self.word_goal.value()
        self.model.save_settings()
        self.refresh()

    def refresh(self):
        goal = self.model.settings.get("progress", {}).get("word_goal", 80_000)
        self.word_goal.blockSignals(True)
        self.word_goal.setValue(goal)
        self.word_goal.blockSignals(False)
        scenes = list(self._scene_nodes())
        words_by_path = {path: self._scene_word_count(path) for path, _scene in scenes}
        total_words = sum(words_by_path.values())
        completed_scenes = sum(scene.get("status") == "Final Draft" for _path, scene in scenes)
        in_progress = sum(scene.get("status") == "In Progress" for _path, scene in scenes)
        planned = len(scenes) - completed_scenes - in_progress
        chapters = list(self._chapter_nodes())
        completed_chapters = sum(chapter.get("status") == "Final Draft" for _path, chapter in chapters)
        acts = self.model.structure.get("acts", [])
        completed_acts = sum(act.get("status") == "Final Draft" for act in acts)

        if goal > 0:
            percentage = min(100, round(total_words * 100 / goal))
            self.word_progress.setRange(0, goal)
            self.word_progress.setValue(min(total_words, goal))
            self.word_progress.setFormat("{}% da meta".format(percentage))
            remaining = max(0, goal - total_words)
            self.word_label.setText("{} palavras de {} · faltam {}".format(
                self._format_number(total_words), self._format_number(goal), self._format_number(remaining)
            ))
        else:
            self.word_progress.setRange(0, 1)
            self.word_progress.setValue(0)
            self.word_progress.setFormat("Defina uma meta de palavras")
            self.word_label.setText("{} palavras escritas".format(self._format_number(total_words)))

        self.structure_label.setText(
            "{} ato(s), {} capítulo(s) e {} cena(s) · {} concluída(s), {} em andamento, {} em planejamento · "
            "{} ato(s) e {} capítulo(s) marcados como concluídos.".format(
                len(acts), len(chapters), len(scenes), completed_scenes, in_progress, planned,
                completed_acts, completed_chapters,
            )
        )
        self._populate_scene_tree(words_by_path)

    def _populate_scene_tree(self, words_by_path):
        self.scene_tree.clear()
        for act in self.model.structure.get("acts", []):
            act_item = QTreeWidgetItem([act.get("name", "Ato"), self._status_label(act), ""])
            self.scene_tree.addTopLevelItem(act_item)
            for chapter in act.get("chapters", []):
                chapter_item = QTreeWidgetItem([chapter.get("name", "Capítulo"), self._status_label(chapter), ""])
                act_item.addChild(chapter_item)
                for scene in chapter.get("scenes", []):
                    path = (act.get("name", "Ato"), chapter.get("name", "Capítulo"), scene.get("name", "Cena"))
                    chapter_item.addChild(QTreeWidgetItem([
                        scene.get("name", "Cena"), self._status_label(scene),
                        self._format_number(words_by_path.get(path, 0)),
                    ]))
                chapter_item.setExpanded(True)
            for scene in act.get("scenes", []):
                path = (act.get("name", "Ato"), scene.get("name", "Cena"))
                act_item.addChild(QTreeWidgetItem([
                    scene.get("name", "Cena"), self._status_label(scene),
                    self._format_number(words_by_path.get(path, 0)),
                ]))
            act_item.setExpanded(True)

    def _scene_nodes(self):
        for act in self.model.structure.get("acts", []):
            act_path = (act.get("name", "Ato"),)
            for chapter in act.get("chapters", []):
                chapter_path = act_path + (chapter.get("name", "Capítulo"),)
                for scene in chapter.get("scenes", []):
                    yield chapter_path + (scene.get("name", "Cena"),), scene
            for scene in act.get("scenes", []):
                yield act_path + (scene.get("name", "Cena"),), scene

    def _chapter_nodes(self):
        for act in self.model.structure.get("acts", []):
            for chapter in act.get("chapters", []):
                yield (act.get("name", "Ato"), chapter.get("name", "Capítulo")), chapter

    def _scene_word_count(self, path):
        current_path = self.controller.get_current_scene_hierarchy()
        if current_path and tuple(current_path) == path:
            return len(self.controller.scene_editor.editor.toPlainText().split())
        content = self.model.load_scene_content(list(path)) or ""
        plain_text = unescape(re.sub(r"<[^>]+>", " ", content))
        return len(plain_text.split())

    @staticmethod
    def _status_label(item):
        return "Concluído" if item.get("status") == "Final Draft" else "Em andamento" if item.get("status") == "In Progress" else "Planejamento"

    @staticmethod
    def _format_number(number):
        return "{:,.0f}".format(number).replace(",", ".")

