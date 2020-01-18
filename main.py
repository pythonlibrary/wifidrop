import sys, os, socket


from PyQt5.QtWidgets import QApplication, QMainWindow, QLabel, QSpacerItem, QSizePolicy, QFileDialog, QDialog, QTableWidgetItem 
from PyQt5.QtGui import QPixmap
from PyQt5.QtCore import pyqtSignal, pyqtSlot, QThread
from PyQt5.uic import loadUi

def get_files_in_folder(folder):
    for root, dirs, files in os.walk(folder):
        for file_name in files:
            _, ext = os.path.splitext(file_name)
            yield os.path.join(root, file_name)


class DeviceDiscoverThread(QThread):

    found_a_device = pyqtSignal(str, str, str)

    def __init__(self):
        super(DeviceDiscoverThread, self).__init__()
        self.s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.s.settimeout(1)
        self.s.bind(('',54545))  # port 54545 to receive broadcast message
        self.running = True

    def run(self):
        while self.running:
            m = None
            address = None
            try:
                m, address = self.s.recvfrom(1024)
            except socket.timeout:
                pass

            if m and address:
                recv_str = m.decode("utf-8")  # pythonlibrary 192.168.1.100 on
                recv_items = recv_str.split()
                if recv_items[0] == 'Init':
                    pass
                else:
                    name = recv_items[1]
                    status = recv_items[2]
                    ip = address[0]
                    self.found_a_device.emit(name, ip, status)
        self.s.close()
        self.s = None

class SocketClientThread(QThread):

    progress_updated = pyqtSignal(int)

    def __init__(self):
        super(SocketClientThread, self).__init__()
        self.running = False
        self.progressbar = None

    def pass_para(self, url_list):
        self.url_list = url_list

    def run(self):
        need_to_send = list()
        # find files
        for url in self.url_list:
            if os.path.isfile(url):
                need_to_send.append(url)
            else:
                for f in get_files_in_folder(url):
                    need_to_send.append(f)
        #print(need_to_send)
        import time
        for i, f in enumerate(need_to_send):
            progress = (100.0*i)/len(need_to_send)
            # sending file with socket
            # 
            self.progress_updated.emit(progress)
            time.sleep(0.5)
        self.progress_updated.emit(100)



class SendDialog(QDialog):
    def __init__(self, url_list):
        super(SendDialog, self).__init__()

        # UI setup - 1 option
        # dynamic load ui for development purpose
        self.ui = loadUi('./dialog.ui', self)
        self.ui.pushButtonClose.setStyleSheet("background-color:#ffffff;");
        self.ui.pushButtonClose.setText("取消");
        self.ui.pushButtonClose.clicked.connect(self.close)

        self.ui.progressBar.setValue(0)

        # set the properties in Qt Creator
        # set editTriggers to NoEditTriggers 
        # set selectionMode to SingleSelection
        # set selectionBehavior to SelectRows
        for i in range(0,2):
            self.ui.tableWidget.insertColumn(0)
        self.ui.tableWidget.setHorizontalHeaderItem(0, QTableWidgetItem("计算机名"))
        self.ui.tableWidget.setHorizontalHeaderItem(1, QTableWidgetItem("IP地址"))
        self.ui.tableWidget.setColumnWidth(0, 160)
        self.ui.tableWidget.setColumnWidth(1, 160)
        self.ui.tableWidget.cellDoubleClicked.connect(self.send_out)

        self.url_list = url_list

        self.device_discover_thread = DeviceDiscoverThread()
        self.device_discover_thread.found_a_device.connect(self.update_devices)
        self.device_discover_thread.start()

        self.socket_broadcast = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.socket_broadcast.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.socket_broadcast.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        self.socket_broadcast.sendto(b'Init', ('255.255.255.255', 54545))  # send broadcast message on 54545
    
    def closeEvent(self, event):
        self.device_discover_thread.running = False

    def send_out(self, row, col):
        name = self.ui.tableWidget.item(row, 0).text()
        ip = self.ui.tableWidget.item(row, 1).text()

        self.socket_client_thread = SocketClientThread()
        self.socket_client_thread.pass_para(self.url_list)
        self.socket_client_thread.progress_updated.connect(self.update_progress)
        self.socket_client_thread.start()

    @pyqtSlot(str,str,str)
    def update_devices(self, name, ip, status):
        if status == 'ServerOn':
            rowPosition = self.ui.tableWidget.rowCount()
            self.ui.tableWidget.insertRow(rowPosition)
            self.ui.tableWidget.setItem(rowPosition , 0, QTableWidgetItem(name))
            self.ui.tableWidget.setItem(rowPosition , 1, QTableWidgetItem(ip))

    @pyqtSlot(int)
    def update_progress(self, progress):
        self.ui.progressBar.setValue(progress)
        if progress == 100:
            self.ui.pushButtonClose.setText("确认");
            self.ui.pushButtonClose.setStyleSheet("background-color:#03fc8c;");


class DropArea(QLabel):

    files_dropped = pyqtSignal(list)

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
            files.append(url.toLocalFile())

        self.files_dropped.emit(files)




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
        self.ui.dropArea.files_dropped.connect(self.prepare_sending)
        self.ui.horizontalLayout.addWidget(self.ui.dropArea)
        spacerItem = QSpacerItem(40, 20, QSizePolicy.Expanding, QSizePolicy.Minimum) # QtWidgets
        self.ui.horizontalLayout.addItem(spacerItem)

    @pyqtSlot(list)
    def prepare_sending(self, files):
        url_list = list()
        num_of_files = len(files)
        if num_of_files != 0:
            if num_of_files > 1:
                # more than one files, show folder icon
                icon = './Treetog-I-Documents.ico'
            else:
                # only one file, show file icon
                icon = './Treetog-I-Text-File.ico'
            pixmap = QPixmap(icon)
            self.ui.dropArea.setPixmap(pixmap)
            for f in files:
                url_list.append(f)

        senddiag = SendDialog(url_list)
        senddiag.exec() 

    def pushButtonChoose_clicked(self):
        options = QFileDialog.Options()
        #options |= QFileDialog.DontUseNativeDialog
        file_names, _ = QFileDialog.getOpenFileNames(self,"选择文件", "","Files (*.*)", options=options)
        files = [u for u in file_names]

        if len(files) > 0:
            self.prepare_sending(files)





def main():
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    excode = app.exec_()
    return excode


if __name__ == '__main__':
    excode = main()
    sys.exit(excode)
