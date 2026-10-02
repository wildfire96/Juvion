"""In-app orientation for the main Juvion writing workspace."""

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QFrame,
    QHBoxLayout,
    QLabel,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)


class FeatureGuideDialog(QDialog):
    """Explain the visible controls in the writing workspace in plain language."""

    SECTIONS = (
        (
            "Escrever e organizar",
            (
                ("Estrutura", "Abre a árvore de atos, capítulos e cenas. Clique com o botão direito em um item para criar, renomear, mover ou mudar seu status."),
                ("A obra", "Guarda capa, sinopse, série, categorias, tags e o estágio atual do livro."),
                ("Buscar", "Encontra palavras na cena aberta. As opções permitem usar expressão regular e substituir ocorrências."),
                ("Editor", "Use os controles de formatação para o trecho selecionado. Salvar cena grava o texto atual; Versões e backups permite recuperar cópias anteriores."),
            ),
        ),
        (
            "Escrever com IA",
            (
                ("Musa IA", "Abre os prompts usados pela assistência de escrita. Escolha um prompt antes de gerar."),
                ("Instruções para a cena", "Descreva o que deve acontecer. Gerar com IA cria uma proposta; revise o resultado e use Inserir no texto somente quando quiser colocá-lo na cena."),
                ("Contexto", "Escolhe cenas, resumos e fichas do Universo que a IA poderá consultar para escrever com consistência."),
                ("Resumo", "Com um ato ou capítulo selecionado, gera ou atualiza um resumo para preservar o contexto da história."),
            ),
        ),
        (
            "Universo e pesquisa",
            (
                ("Universo", "Mostra personagens, lugares, regras e outras fichas da obra. A janela completa permite criar subcategorias, relacionar fichas e definir o cânone."),
                ("Mapa de relações", "Na janela completa do Universo, mostra visualmente as conexões entre fichas."),
                ("Conversar com a Musa", "Abre uma conversa de pesquisa e planejamento ligada ao projeto."),
                ("Transcrever áudio", "Converte uma gravação em texto. Pesquisar com IA e Pesquisar no acervo abrem ferramentas de pesquisa externas."),
            ),
        ),
        (
            "Leitura e foco",
            (
                ("Modo foco", "Amplia a escrita e reduz distrações. Também pode ser aberto com F11."),
                ("Ouvir texto", "Lê em voz alta a seleção atual ou a cena inteira quando não houver seleção."),
                ("Ver prompt", "Mostra o texto final enviado à IA antes da geração."),
            ),
        ),
    )

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Guia de recursos — Juvion")
        self.setMinimumSize(660, 560)
        self.resize(760, 640)
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        heading = QLabel("Como usar o Juvion")
        heading.setObjectName("PanelTitle")
        layout.addWidget(heading)
        introduction = QLabel("Cada comando usa palavras diretas. Passe o cursor sobre ícones para ver uma explicação curta.")
        introduction.setObjectName("PanelDescription")
        introduction.setWordWrap(True)
        layout.addWidget(introduction)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        content = QWidget()
        content_layout = QVBoxLayout(content)
        content_layout.setContentsMargins(14, 14, 14, 14)
        content_layout.setSpacing(16)
        for title, items in self.SECTIONS:
            content_layout.addWidget(self._section(title, items))
        content_layout.addStretch()
        scroll.setWidget(content)
        layout.addWidget(scroll, 1)

        buttons = QDialogButtonBox(QDialogButtonBox.Close)
        buttons.rejected.connect(self.reject)
        buttons.accepted.connect(self.accept)
        layout.addWidget(buttons)

    def _section(self, title, items):
        frame = QFrame()
        frame.setFrameShape(QFrame.StyledPanel)
        layout = QVBoxLayout(frame)
        section_title = QLabel(title)
        section_title.setStyleSheet("font-weight: 700; font-size: 15px;")
        layout.addWidget(section_title)
        for label, description in items:
            row = QWidget()
            row_layout = QHBoxLayout(row)
            row_layout.setContentsMargins(0, 2, 0, 2)
            name = QLabel(label)
            name.setMinimumWidth(170)
            name.setStyleSheet("font-weight: 600;")
            text = QLabel(description)
            text.setWordWrap(True)
            text.setAlignment(Qt.AlignLeft | Qt.AlignTop)
            row_layout.addWidget(name)
            row_layout.addWidget(text, 1)
            layout.addWidget(row)
        return frame
