"""Open the library briefly using temporary data and the offscreen Qt driver."""
import os
import shutil
import sys
import tempfile
from pathlib import Path
from unittest.mock import patch

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
repository = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(repository))

with tempfile.TemporaryDirectory(prefix="juvion-smoke-") as temporary:
    root = Path(temporary)
    shutil.copytree(repository / "assets", root / "assets")
    shutil.copy2(repository / "version.json", root / "version.json")
    (root / "Projects").mkdir()
    import runtime_paths
    runtime_paths.initialize_runtime = lambda: os.chdir(root)
    import main
    from PyQt5.QtCore import QTimer
    from PyQt5.QtWidgets import QApplication
    original_exec = QApplication.exec_
    failures = []
    original_exception_hook = sys.excepthook

    def capture_qt_exception(exception_type, value, traceback):
        failures.append(value)
        original_exception_hook(exception_type, value, traceback)
        if QApplication.instance():
            QApplication.instance().quit()

    sys.excepthook = capture_qt_exception

    def open_book():
        try:
            from project_window.project_window import ProjectWindow
            from project_window.tree_manager import save_structure
            from project_window.templates_data import TEMPLATES, populate_template_structure
            structure = populate_template_structure(TEMPLATES["short_story"])
            save_structure("SmokeBook", structure)
            library = next(widget for widget in QApplication.topLevelWidgets() if isinstance(widget, main.WorkbenchWindow))
            library._smoke_book = ProjectWindow("SmokeBook", library.enhanced_compendium)
            library._smoke_book.show()
            hierarchy = [structure["acts"][0]["name"], structure["acts"][0]["chapters"][0]["name"], structure["acts"][0]["chapters"][0]["scenes"][0]["name"]]
            library._smoke_book.load_scene_from_hierarchy(hierarchy)
            library._smoke_book.scene_editor.editor.setPlainText("Rascunho final do teste")
            with patch("exporter.export_dialog.show_export_dialog") as export_dialog:
                library._smoke_book.open_export_dialog()
                if not export_dialog.called or "Rascunho final do teste" not in library._smoke_book.model.load_scene_content(hierarchy):
                    raise RuntimeError("The open scene was not saved before export")
            print("Juvion project window startup OK (temporary book)")
        except Exception as error:
            failures.append(error)
            QApplication.instance().quit()

    def brief_exec(app):
        QTimer.singleShot(0, open_book)
        QTimer.singleShot(1500, app.quit)
        result = original_exec()
        if failures:
            raise failures[0]
        return result

    QApplication.exec_ = brief_exec
    try:
        main.main()
    except SystemExit as exit_status:
        if exit_status.code:
            raise
    finally:
        os.chdir(repository)
    print("Juvion library startup OK (temporary data)")
