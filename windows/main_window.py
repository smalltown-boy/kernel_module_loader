from PyQt6.QtWidgets import QMainWindow, QFileDialog, QHeaderView
from PyQt6.QtGui import QStandardItemModel, QStandardItem
from PyQt6.QtCore import Qt, QSettings
from ui.ui_main import Ui_mainWindow
from pathlib import Path
import subprocess
import os


class MainWindow(QMainWindow, Ui_mainWindow):
    def __init__(self):
        super().__init__()
        self.setupUi(self)

        # Variables
        self.directory = None
        self.kernel_modules = []

        self.settings = QSettings("app_settings.ini", QSettings.Format.IniFormat)

        # Table configuration
        self.tableView.setSelectionBehavior(self.tableView.SelectionBehavior.SelectItems)
        self.tableView.setSelectionMode(self.tableView.SelectionMode.SingleSelection)

        # Buttons
        self.buttonOpenDir.clicked.connect(self.on_openDir_clicked)
        self.buttonLoad.clicked.connect(self.on_loadModule_clicked)
        self.buttonUpload.clicked.connect(self.on_unloadModule_clicked)
        self.buttonUploadAll.clicked.connect(self.on_unloadAllModule_clicked)

        # CheckBox
        self.checkBox.stateChanged.connect(self.save_settings)
    
        # Load settings 
        self.load_settings()

    def save_settings(self):
        if self.directory:
            self.settings.setValue("modules_path", self.directory)

        self.settings.setValue("autoload_enabled", self.checkBox.isChecked())
        self.settings.sync()
        

    def load_settings(self):
        saved_path = self.settings.value("modules_path", "")
        autoload = self.settings.value("autoload_enabled", False, type=bool)

        self.checkBox.setChecked(autoload)

        if autoload and saved_path and os.path.isdir(saved_path):
            self.directory = saved_path
            self.load_modules_from_directory(saved_path)

    def load_modules_from_directory(self, directory):
        self.kernel_modules.clear()

        model = QStandardItemModel()
        model.setHorizontalHeaderLabels(["Module", "Status"])

        for filename in os.listdir(directory):
            filepath = os.path.join(directory, filename)

            if os.path.isfile(filepath) and filename.endswith(".ko"):
                self.kernel_modules.append(filepath)

                module_item = QStandardItem(Path(filepath).name)
                module_item.setEditable(False)

                status_item = QStandardItem("Checking...")
                status_item.setEditable(False)
                status_item.setFlags(status_item.flags() & ~Qt.ItemFlag.ItemIsSelectable)

                model.appendRow([module_item, status_item])

        self.tableView.setModel(model)
        self.tableView.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)

        self.linePath.setText(directory)

        self.refresh_statuses()

    def on_openDir_clicked(self):
        directory = QFileDialog.getExistingDirectory(None,"Choose directory with Linux kernel modules","",QFileDialog.Option.ShowDirsOnly)

        if not directory:
            return

        self.directory = directory
        self.load_modules_from_directory(directory)
        self.save_settings()

    def get_loaded_modules(self) -> set:
        try:
            result = subprocess.run(["lsmod"], capture_output=True, text=True)

            if result.returncode != 0:
                return set()

            lines = result.stdout.splitlines()[1:]
            loaded = set()

            for line in lines:
                parts = line.split()
                if parts:
                    loaded.add(parts[0])

            return loaded

        except Exception as e:
            print(f"lsmod error: {e}")
            return set()

    def refresh_statuses(self):
        loaded_modules = self.get_loaded_modules()
        model = self.tableView.model()

        if not model:
            return

        for row in range(len(self.kernel_modules)):
            status_item = model.item(row, 1)
            module_name = Path(self.kernel_modules[row]).stem

            if module_name in loaded_modules:
                status_item.setText("Loaded")
                status_item.setForeground(Qt.GlobalColor.darkGreen)
            else:
                status_item.setText("Not loaded")
                status_item.setForeground(Qt.GlobalColor.black)

    def on_loadModule_clicked(self):
        index = self.tableView.currentIndex()

        if not index.isValid() or index.column() != 0:
            return

        row = index.row()
        module_path = self.kernel_modules[row]

        try:
            subprocess.run(["insmod", module_path],capture_output=True,text=True)
        except Exception as e:
            print(f"Load error: {e}")

        self.refresh_statuses()

    def on_unloadModule_clicked(self):
        index = self.tableView.currentIndex()

        if not index.isValid() or index.column() != 0:
            return

        row = index.row()
        module_name = Path(self.kernel_modules[row]).stem

        try:
            subprocess.run(["rmmod", module_name],capture_output=True,text=True)
        except Exception as e:
            print(f"Unload error: {e}")

        self.refresh_statuses()

    def on_unloadAllModule_clicked(self):
        for module_path in self.kernel_modules:
            module_name = Path(module_path).stem

            try:
                subprocess.run(["rmmod", module_name],capture_output=True,text=True)
            except Exception as e:
                print(f"Unload error: {e}")

        self.refresh_statuses()
