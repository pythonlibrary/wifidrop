import sys

from PyQt5.QtWidgets import QApplication, QMainWindow, QLabel, QSpacerItem, QSizePolicy, QFileDialog
from PyQt5.uic import loadUi



class DropArea(QLabel):


    def __init__(self, *args, **kwargs):
        super(DropArea, self).__init__(*args, **kwargs)
        self.setAcceptDrops(True)

    def dragEnterEvent(self, event):
        print("drag event")
        if event.mimeData().hasUrls():
            event.accept()
        else:
            event.ignore()

    def dropEvent(self, event):
        print("drop event")
        files = list()
        urls = [u for u in event.mimeData().urls()]
        for url in urls:
            print(url.path())
            files.append(url.toLocalFile())
        print(files)




class MainWindow(QMainWindow):
    """Main window"""
    def __init__(self):
        super(MainWindow, self).__init__()

        # UI setup - 1 option
        # dynamic load ui for development purpose
        self.ui = loadUi('./mainwindow.ui', self)
        self.ui.setStatusBar(None)  # https://doc.qt.io/qt-5/qmainwindow.html#setStatusBar

        self.ui.pushButtonChoose.setStyleSheet("background-color:#ffffff;")
        self.ui.pushButtonChoose.clicked.connect(self.pushButtonChoose_clicked)

        self.ui.dropArea = DropArea("或 拖动文件或文件夹到这里", self)
        self.ui.horizontalLayout.addWidget(self.ui.dropArea)
        spacerItem = QSpacerItem(40, 20, QSizePolicy.Expanding, QSizePolicy.Minimum) # QtWidgets
        self.ui.horizontalLayout.addItem(spacerItem)

    def pushButtonChoose_clicked(self):
        options = QFileDialog.Options()
        #options |= QFileDialog.DontUseNativeDialog
        file_names, _ = QFileDialog.getOpenFileNames(self,"选择文件", "","Files (*.*)", options=options)
        files = [u for u in file_names]
        print(files)





def main():
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    excode = app.exec_()
    return excode


if __name__ == '__main__':
    excode = main()
    sys.exit(excode)
