"""Continuity checks connecting scene prose, Universe records, and timeline data."""

import re
from collections import Counter, defaultdict
from html import unescape

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import (
    QDialog,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QTreeWidget,
    QTreeWidgetItem,
    QVBoxLayout,
)

from compendium.timeline import TimelineManager


class ContinuityChecker:
    """Find concrete loose ends without deciding creative choices for the writer."""

    IGNORED_PROPER_NOUNS = {
        "A", "O", "As", "Os", "Um", "Uma", "Ele", "Ela", "Eles", "Elas", "Eu", "Nós",
        "No", "Na", "Nos", "Nas", "Em", "Mas", "Se", "Quando", "Então", "Depois",
    }

    def __init__(self, project_model):
        self.model = project_model

    def analyze(self):
        entries = self.model.compendium.get_entry_index()
        entry_names = {entry["name"].casefold() for entry in entries}
        compendium_data = self.model.compendium.load_data()
        issues = []
        scene_mentions = defaultdict(list)
        candidate_mentions = defaultdict(list)

        for hierarchy in self._scene_hierarchies(self.model.structure):
            content = self._plain_text(self.model.load_scene_content(hierarchy) or "")
            if not content.strip():
                continue
            scene_path = " › ".join(hierarchy)
            for entry in entries:
                name = entry["name"]
                if len(name) > 1 and re.search(r"(?<!\w){}(?!\w)".format(re.escape(name)), content, re.IGNORECASE):
                    scene_mentions[name.casefold()].append(scene_path)
            for match in re.finditer(r"\b[A-ZÀ-ÖØ-Þ][\wÀ-ÖØ-öø-ÿ'-]{2,}\b", content):
                candidate = match.group()
                if candidate not in self.IGNORED_PROPER_NOUNS and candidate.casefold() not in entry_names:
                    candidate_mentions[candidate.casefold()].append(scene_path)

        for candidate, paths in candidate_mentions.items():
            unique_paths = list(dict.fromkeys(paths))
            if len(unique_paths) >= 2:
                issues.append({
                    "kind": "Sem ficha",
                    "title": candidate.capitalize(),
                    "detail": "Aparece em {} cenas e ainda não tem ficha no Universo.".format(len(unique_paths)),
                    "scene_path": unique_paths[0],
                    "entry_name": "",
                })

        metadata = compendium_data.get("extensions", {}).get("entries", {})
        for entry in entries:
            name = entry["name"]
            record = metadata.get(name, {})
            has_detail = bool(entry.get("content", "").strip() or record.get("notebook") or record.get("details", "").strip())
            mentioned_in = list(dict.fromkeys(scene_mentions.get(name.casefold(), [])))
            if mentioned_in and not has_detail:
                issues.append({
                    "kind": "Ficha incompleta",
                    "title": name,
                    "detail": "É citado em {} cena(s), mas a ficha ainda não tem detalhes.".format(len(mentioned_in)),
                    "scene_path": mentioned_in[0],
                    "entry_name": name,
                })
            for relationship in record.get("relationships", []):
                target = relationship.get("name", "").casefold()
                if target and target not in entry_names:
                    issues.append({
                        "kind": "Relação quebrada",
                        "title": name,
                        "detail": "A relação aponta para “{}”, que não está mais no Universo.".format(relationship.get("name")),
                        "scene_path": "",
                        "entry_name": name,
                    })

        issues.extend(self._timeline_issues())
        return issues

    def _timeline_issues(self):
        issues = []
        events = TimelineManager(self.model.project_name).load().get("events", [])
        orders = Counter(
            event.get("universe_order", 0)
            for event in events
            if event.get("universe_order", 0) > 0
        )
        for order, count in orders.items():
            if count > 1:
                issues.append({
                    "kind": "Linha do tempo",
                    "title": "Ordem {}".format(order),
                    "detail": "{} eventos usam a mesma posição no tempo do universo.".format(count),
                    "scene_path": "",
                    "entry_name": "",
                })
        return issues

    @staticmethod
    def _plain_text(content):
        return unescape(re.sub(r"<[^>]+>", " ", content))

    @staticmethod
    def _scene_hierarchies(structure):
        for act in structure.get("acts", []):
            act_path = [act.get("name", "Ato")]
            for chapter in act.get("chapters", []):
                chapter_path = act_path + [chapter.get("name", "Capítulo")]
                for scene in chapter.get("scenes", []):
                    yield chapter_path + [scene.get("name", "Cena")]
            for scene in act.get("scenes", []):
                yield act_path + [scene.get("name", "Cena")]


class ContinuityDialog(QDialog):
    """Present actionable continuity findings and navigate to their source."""

    def __init__(self, controller, parent=None):
        super().__init__(parent or controller)
        self.controller = controller
        self.issues = []
        self.setWindowTitle("Juvion — Continuidade")
        self.resize(760, 510)
        self._build_ui()
        self.refresh()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 18, 18, 18)
        self.summary = QLabel()
        self.summary.setWordWrap(True)
        layout.addWidget(self.summary)
        self.tree = QTreeWidget()
        self.tree.setHeaderLabels(["Tipo", "Item", "Onde verificar"])
        self.tree.itemSelectionChanged.connect(self._update_actions)
        self.tree.itemDoubleClicked.connect(lambda *_args: self.open_scene())
        layout.addWidget(self.tree, 1)
        actions = QHBoxLayout()
        refresh_button = QPushButton("Verificar novamente")
        refresh_button.clicked.connect(self.refresh)
        actions.addWidget(refresh_button)
        actions.addStretch()
        self.scene_button = QPushButton("Abrir cena")
        self.scene_button.clicked.connect(self.open_scene)
        actions.addWidget(self.scene_button)
        self.universe_button = QPushButton("Abrir ficha")
        self.universe_button.setProperty("primary", True)
        self.universe_button.clicked.connect(self.open_universe)
        actions.addWidget(self.universe_button)
        layout.addLayout(actions)

    def refresh(self):
        self.issues = ContinuityChecker(self.controller.model).analyze()
        self.tree.clear()
        for issue in self.issues:
            item = QTreeWidgetItem([
                issue["kind"], issue["title"], issue["scene_path"] or "Universo / Linha do tempo",
            ])
            item.setToolTip(1, issue["detail"])
            item.setData(0, Qt.UserRole, issue)
            self.tree.addTopLevelItem(item)
        if self.issues:
            self.summary.setText("{} ponto(s) merecem sua decisão. Eles são alertas de consistência, não mudanças automáticas.".format(len(self.issues)))
            self.tree.setCurrentItem(self.tree.topLevelItem(0))
        else:
            self.summary.setText("Nenhum ponto de continuidade foi encontrado nas cenas e fichas atuais.")
        self._update_actions()

    def _selected_issue(self):
        item = self.tree.currentItem()
        return item.data(0, Qt.UserRole) if item else {}

    def _update_actions(self):
        issue = self._selected_issue()
        self.scene_button.setEnabled(bool(issue.get("scene_path")))
        self.universe_button.setEnabled(bool(issue.get("entry_name")))

    def open_scene(self):
        issue = self._selected_issue()
        if issue.get("scene_path"):
            self.controller.load_scene_from_hierarchy(issue["scene_path"].split(" › "))

    def open_universe(self):
        issue = self._selected_issue()
        if issue.get("entry_name") and self.controller.enhanced_window:
            self.controller.enhanced_window.open_with_entry(self.controller.model.project_name, issue["entry_name"])
