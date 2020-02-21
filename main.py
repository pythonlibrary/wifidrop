import sys, os, socket


from PyQt5.QtWidgets import QApplication, QMainWindow, QLabel, QSpacerItem, QSizePolicy, QFileDialog, QDialog, QTableWidgetItem, QMessageBox
from PyQt5.QtGui import QPixmap
from PyQt5.QtCore import pyqtSignal, pyqtSlot, QThread

# only import loadUi when using ui file to create UI
# from PyQt5.uic import loadUi

from mainwindow import Ui_MainWindow
from dialog import Ui_dialog

def get_files_in_folder(folder):
    for root, dirs, files in os.walk(folder):
        for file_name in files:
            _, ext = os.path.splitext(file_name)
            yield os.path.join(root, file_name)

class DeviceDiscoverThread(QThread):

    found_a_device = pyqtSignal(str, str, str)
    allow_sending = pyqtSignal(bool)
    device_discover_pack_received = pyqtSignal(str, str)

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
                print("timeout")
                pass

            if m and address:
                print(m)
                recv_str = m.decode("utf-8")  # pythonlibrary 192.168.1.100 on
                recv_items = recv_str.split()
                ip = address[0]
                if recv_items[0] == 'Init':
                    self.device_discover_pack_received.emit('Init', ip)
                elif recv_items[0] == 'SendConfirm': 
                    self.device_discover_pack_received.emit('SendConfirm', ip)
                elif recv_items[0] == 'SendMe':
                    self.allow_sending.emit(True)
                elif recv_items[0] == 'NotSendMe':
                    self.allow_sending.emit(False)
                else:
                    name = recv_items[1]
                    status = recv_items[2]
                    if name != socket.gethostname():
                        self.found_a_device.emit(name, ip, status)
        self.s.close()
        self.s = None

class SocketServerThread(QThread):

    def __init__(self):
        super(SocketServerThread, self).__init__()
        self.running = True
        self.connected = False

    def run(self):
        while True:
            while self.running:
                s = socket.socket() 
                s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                host = socket.gethostname()
                port = 12345               
                s.settimeout(1)
                s.bind(('', port))
                s.listen(5)            
                try:
                    c, addr = s.accept()    
                    self.connected = True
                except socket.timeout:
                    self.connected = False
                while self.running and self.connected:
                    size = c.recv(16) # Note that you limit your filename length to 255 bytes.
                    if not size:
                        break
                    size = int(size.decode(), 2)
                    filename = c.recv(size)
                    filesize = c.recv(32)
                    filesize = int(filesize.decode(), 2)
                    file_to_write = open(filename, 'wb')
                    chunksize = 4096
                    while filesize > 0:
                        if filesize < chunksize:
                            chunksize = filesize
                        data = c.recv(chunksize)
                        file_to_write.write(data)
                        filesize -= len(data)

                    file_to_write.close()
                    print('File received successfully')
                s.close()


class SocketClientThread(QThread):

    progress_updated = pyqtSignal(int)

    def __init__(self):
        super(SocketClientThread, self).__init__()
        self.running = False
        self.progressbar = None

    def pass_para(self, url_list, ip):
        self.url_list = url_list
        self.target_ip = ip

    def run(self):
        need_to_send = list()
        # find files
        for url in self.url_list:
            if os.path.isfile(url):
                need_to_send.append(url)
            else:
                for f in get_files_in_folder(url):
                    need_to_send.append(f)
        
        # setup socket client for sending the files
        s = socket.socket()         
        port = 12345                
        s.connect((self.target_ip, port))

        for i, fname in enumerate(need_to_send):
            progress = (100.0*i)/len(need_to_send)
            # sending file with socket
            filename = os.path.basename(fname)
            size = len(filename)
            size = bin(size)[2:].zfill(16) # encode filename size as 16 bit binary
            s.send(size.encode())
            s.send(filename.encode())

            filename = fname
            filesize = os.path.getsize(filename)
            filesize = bin(filesize)[2:].zfill(32) # encode filesize as 32 bit binary
            s.send(filesize.encode())
            file_to_send = open(filename, 'rb')

            l = file_to_send.read()
            s.sendall(l)
            file_to_send.close()
            print('File Sent ' + filename)
            # s.shutdown(socket.SHUT_WR)
            self.progress_updated.emit(progress)
        self.progress_updated.emit(100)
        s.close()



class SendDialog(QDialog):
    def __init__(self, url_list, socket_server_thread, device_discover_thread, socket_broadcast):
        super(SendDialog, self).__init__()

        # UI setup - 1 option
        # dynamic load ui for development purpose
        # self.ui = loadUi('./dialog.ui', self)

        # Use py to setup UI - 2 option
        self.ui = Ui_dialog()
        self.ui.setupUi(self)

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

        self.device_discover_thread = device_discover_thread
        self.device_discover_thread.found_a_device.connect(self.update_devices)
        self.device_discover_thread.allow_sending.connect(self.send_permission)
        
        self.socket_broadcast = socket_broadcast 
        self.socket_broadcast.sendto('Init'.encode('utf-8'), ('255.255.255.255', 54545)) 

        self.socket_server_thread = socket_server_thread

    def closeEvent(self, event):
        self.socket_server_thread.running = True
        try:
            self.socket_client_thread.running = False
        except:
            pass
    
    @pyqtSlot(bool)
    def send_permission(self, allow):
        if allow:
            self.socket_server_thread.running = False
            self.socket_client_thread = SocketClientThread()
            self.socket_client_thread.pass_para(self.url_list, self.target_ip)
            self.socket_client_thread.progress_updated.connect(self.update_progress)
            self.socket_client_thread.start()
        else:
            msg = QMessageBox()
            msg.setIcon(QMessageBox.Information)
            msg.setWindowTitle("WiFi Drop 拒绝接收")
            msg.setText("拒绝接受")
            msg.exec_()

    def send_out(self, row, col):
        name = self.ui.tableWidget.item(row, 0).text()
        self.target_ip = self.ui.tableWidget.item(row, 1).text()
        # ask for permission from target
        message = 'SendConfirm'
        self.socket_broadcast.sendto(message.encode('utf-8'), (self.target_ip, 54545)) 

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
        # self.ui = loadUi('./mainwindow.ui', self)

        # Use py to setup UI - 2 option
        self.ui = Ui_MainWindow()
        self.ui.setupUi(self)

        self.setStatusBar(None)  # https://doc.qt.io/qt-5/qmainwindow.html#setStatusBar

        self.ui.pushButtonChoose.setStyleSheet("background-color:#ffffff;")
        self.ui.pushButtonChoose.clicked.connect(self.pushButtonChoose_clicked)

        self.ui.dropArea = DropArea("或 拖动文件或文件夹到这里", self)
        self.ui.dropArea.files_dropped.connect(self.prepare_sending)
        self.ui.horizontalLayout.addWidget(self.ui.dropArea)
        spacerItem = QSpacerItem(40, 20, QSizePolicy.Expanding, QSizePolicy.Minimum) # QtWidgets
        self.ui.horizontalLayout.addItem(spacerItem)

        self.socket_server_thread = SocketServerThread()
        self.socket_server_thread.start()

        self.device_discover_thread = DeviceDiscoverThread()
        self.device_discover_thread.device_discover_pack_received.connect(self.device_discover_pack_received)
        self.device_discover_thread.start()
        
        self.socket_broadcast = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.socket_broadcast.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.socket_broadcast.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)

    @pyqtSlot(str, str)
    def device_discover_pack_received(self, command, ip):
        if command == 'Init':
            self.target_ip = ip
            hostname = socket.gethostname()
            message = 'Exchange {} ServerOn'.format(hostname)
            self.socket_broadcast.sendto(message.encode('utf-8'), (self.target_ip, 54545)) 
        elif command == 'SendConfirm':
            msg = QMessageBox()
            msg.setIcon(QMessageBox.Information)
            msg.setWindowTitle("WiFi Drop 接收确认")
            msg.setText("确认接收?")
            msg.setStandardButtons(QMessageBox.Ok | QMessageBox.Cancel)
            msg.buttonClicked.connect(self.msgbtn)
            msg.exec_()
    
    def msgbtn(self, i):
        if i.text() == 'OK':
            message = 'SendMe'
            self.socket_broadcast.sendto(message.encode('utf-8'), (self.target_ip, 54545)) 
        else:
            message = 'NotSendMe'
            self.socket_broadcast.sendto(message.encode('utf-8'), (self.target_ip, 54545)) 

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

        senddiag = SendDialog(url_list, self.socket_server_thread, self.device_discover_thread, self.socket_broadcast)
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