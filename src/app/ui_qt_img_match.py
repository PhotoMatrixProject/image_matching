import sys
import os
from PySide6 import QtCore, QtWidgets, QtGui
import manager_img_match as manager
import shutil
from pathlib import Path

HOW_TO_EN = '' \
'1. CSV file input: CSV file with at least two fields: ' \
'"item" - ID of the reproduction in the database, "imageAddr" - address of an image, ' \
'might be an URL address of an image in a digital library, or an address in a ' \
'file system of a locally stored image. ' \
'\nThe application processes only fields "item" and "imageAddr" and ignores the rest of the fields if present.' \
'\n\n2. Directory input: Directory that contains directories that contain images. The following schema illustrates expected input structure:' \
'\ninput_dir/\n\t├── dir1/\n\t│   \t├── img1.jpeg\n\t│   \t├── img2.jpeg\n\t├── dir2/\n\t\t├── img3.jpeg\n\t\t└── img4.jpeg' \
'\nThe input in the above example is input_dir.'\
'\nThe application works with PNG, JPEG and JPG images. ' \
'\nThe applicateion ignores files in input_dir and works only with folders.' \
'\nThe application ignores non-images in dir1, dir2 etc. and works only with images of the formats stated above.' \
'\n\n3. Output: CSV file with fields: "item", "imageAddr", "class1", "prob1" - the name and corresponding probability of the most probable class, ' \
'"class2", "prob2" - the name and corresponding probability of the second most probable class, ' \
'"class3", "prob3" - the name and corresponding probability of the third most probable class.' \
'In case of CSV input (1.) the fields "item" and "imageAddr" are copied from the input CSV file, ' \
'in case of directory input (2.) "item" is a name of the image, "imageAddr" is a path to the image in the file system.' \
'\n\nAfter all the input is processed the application shows a Finish window. ' \
'The result CSV files will be stored in the folder with the name "result" that is ' \
'created in the same folder where the application is. Each output CSV file is named in ' \
'the following way: the name of the input CSV file or folder appended with "_result" suffix. ' \
'\nInput CSV file - "query1.csv", corresponding output file - "query1_result.csv".' \
'\nInput folder - "image_folder1", corresponding output CSV file - "image_folder1_result.csv".'\
'\n4. Errors:'\
'\nCSV file input: In case of errors in the input CSV file, the application processes the file until it encounters an error. After that, it stops processing the input file, closes the result CSV file with the content the application was able to produce before it encountered the error, and proceeds to process the next input CSV file, if there is any.'\
'\nDirectory input: In case of errors while working with images, the application stops processing images in the current inside directory and closes the result CSV file once it encounters an error. After that, it proceeds to process next inside directory, if there is any.'

HOW_TO_CZ = '' \
'1. Vstupní soubor CSV: CSV soubor s alespoň dvěma poli: ' \
'"item" - ID reprodukce v databázi, "imageAddr" - adresa obrázku, ' \
'může to být adresa URL obrázku v digitální knihovně nebo adresa v' \
'souborovém systému lokálně uloženého obrázku. ' \
'\nAplikace zpracovává pouze pole "item" a "imageAddr" a ignoruje ostatní pole, pokud jsou přítomna.' \
'\n\n2. Vstupní adresář: Adresář, který obsahuje adresáře obsahující obrázky. Následující schéma znázorňuje očekávanou strukturu vstupu:' \
'\ninput_dir/\n\t├── dir1/\n\t│   \t├── img1.jpeg\n\t│   \t├── img2.jpeg\n\t├── dir2/\n\t\t├── img3.jpeg\n\t\t└── img4.jpeg' \
'\nVe výše uvedeném příkladu je vstupní adresář input_dir.' \
'\nAplikace pracuje s obrázky PNG, JPEG a JPG. ' \
'\nAplikace ignoruje soubory ve input_dir a pracuje pouze se složkami.' \
'\nAplikace ignoruje jiné položky než obrázky v adresářích dir1, dir2 atd. a pracuje pouze s obrázky výše uvedených formátů.' \
'3. Výstup: CSV soubor s poli: "item",  "imageAddr", "class1", "prob1" - název a odpovídající pravděpodobnost nejpravděpodobnější třídy, ' \
'"class2", "prob2" - název a odpovídající pravděpodobnost druhé nejpravděpodobnější třídy, ' \
'"class3", "prob3" - název a odpovídající pravděpodobnost třetí nejpravděpodobnější třídy. '\
'V případě vstupu CSV (1.) se pole "item" a "imageAddr" zkopírují ze vstupního souboru CSV, ' \
'v případě adresářového vstupu (2.) je "item" název obrázku, "imageAddr" je cesta k obrázku v souborovém systému.' \
'\n\nPo zpracování všech vstupů se zobrazí okno Finish. ' \
'Výsledné soubory CSV se uloží do složky s názvem "result", která je ' \
'vytvořena ve stejné složce, v níž se nachází aplikace. Každý výstupní soubor CSV je pojmenován ' \
'následujícím způsobem: název vstupního souboru CSV nebo složky doplněný příponou „_result“. ' \
'\nVstupní CSV soubor - "query1.csv", odpovídající výstupní soubor - "query1_result.csv".' \
'\nVstupní složka - "image_folder1", odpovídající výstupní CSV soubor - "image_folder1_result.csv".'\
'\n4. Chyby:'\
'\nVstupní soubor CSV: V případě chyb ve vstupním souboru CSV aplikace zpracovává soubor, dokud nenarazí na chybu. Poté zpracování vstupního souboru ukončí, uzavře výsledný soubor CSV s obsahem, který byla aplikace schopna vytvořit předtím, než narazila na chybu, a pokračuje ve zpracování dalšího vstupního souboru CSV, pokud nějaký existuje.'\
'\nVstupní adresář: V případě chyb při práci s obrázky aplikace zastaví zpracování obrázků v aktuálním vnitřním adresáři a po výskytu chyby uzavře výsledný soubor CSV. Poté pokračuje ve zpracování dalšího vnitřního adresáře, pokud nějaký existuje.'


lang_button1 = {'en':'Upload csv file', 'cz':'Nahrát soubor csv'}
lang_button2 = {'en':'Upload directory', 'cz':'Nahrát adresář'}
lang_help_button = {'en':'Help', 'cz':'Nápověda'}
lang_finish_label = {'en':'Images have been processed.\ncsv files with results are in the current directory.', 
                     'cz':'Obrázky byly zpracovány.\ncsv soubory s výsledky jsou v aktuálním adresáři.'}
lang_help = {'en':HOW_TO_EN, 'cz':HOW_TO_CZ}
lang_author_label = {'en':'The author is Daria Korop.', 'cz':'Autorem je Daria Korop.'}


def resource_path(relative_path):
    """ Get absolute path to resource, works for dev and for PyInstaller """
    base_path = getattr(sys, '_MEIPASS', os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base_path, relative_path)

DATA_PATH = resource_path("bakalarkaAppAvatar.ico")

class MyWidget(QtWidgets.QWidget):
    def __init__(self):
        super().__init__()

        self.help_win_open = False
        self.manual = lang_help['en']
        self.fin_win = None
        self.text_edit = None

        self.language = 'en'
        # self.color = "color: #00FF00"
        self.big_font = QtGui.QFont("Bodoni MT", 20, QtGui.QFont.Bold)
        self.small_font = QtGui.QFont("Bodoni MT", 10, QtGui.QFont.Bold)

        self.button1 = QtWidgets.QPushButton("Upload csv file")
        self.button2 = QtWidgets.QPushButton("Upload directory")
        self.language_selector = QtWidgets.QComboBox()
        self.button_help = QtWidgets.QPushButton("Help")
        self.author_label = QtWidgets.QLabel(lang_author_label[self.language])
        self.gallery_button = QtWidgets.QPushButton("Gallery")

        self.top_layout = QtWidgets.QGridLayout()
        self.top_layout.addWidget(self.language_selector, 0, 0)
        self.top_layout.addWidget(self.button_help, 0, 2)
        self.language_selector.addItem("English", "en")
        self.language_selector.addItem("Česky", "cz")
        self.language_selector.currentIndexChanged.connect(self.change_language)
        

        self.change_language()

        self.center_layout = QtWidgets.QVBoxLayout()        
        self.center_layout.addWidget(self.button1, alignment=QtCore.Qt.AlignCenter)
        self.center_layout.addWidget(self.button2, alignment=QtCore.Qt.AlignCenter)
        self.center_layout.addWidget(self.gallery_button, alignment=QtCore.Qt.AlignCenter)
        self.center_layout.addWidget(self.author_label, alignment=QtCore.Qt.AlignCenter)


        self.button1.clicked.connect(self.work_with_csv)
        self.button2.clicked.connect(self.work_with_dir)
        self.gallery_button.clicked.connect(self.open_gallery)
        self.button_help.clicked.connect(self.open_help_window)


        # self.button1.setStyleSheet(self.color)
        self.button1.setFont(self.big_font)
        self.button1.setFixedSize(250, 150)

        # self.button2.setStyleSheet(self.color)
        self.button2.setFont(self.big_font)
        self.button2.setFixedSize(250, 150)

        # self.gallery_button.setStyleSheet(self.color)
        self.gallery_button.setFont(self.big_font)
        self.gallery_button.setFixedSize(250, 50)

        # self.button_help.setStyleSheet(self.color)
        self.button_help.setFont(self.small_font)
        self.button_help.setFixedSize(100, 25)

        # self.language_selector.setStyleSheet(self.color)
        self.language_selector.setFont(self.small_font)
        self.language_selector.setFixedSize(100, 25)

        # self.author_label.setStyleSheet(self.color)
        self.author_label.setFont(self.small_font)
        self.author_label.setFixedSize(500, 50)
        self.author_label.setAlignment(QtCore.Qt.AlignCenter) 

        main_layout = QtWidgets.QVBoxLayout()
        main_layout.addLayout(self.top_layout)  # Add top row layout
        main_layout.addStretch()  # Push big buttons to the center
        main_layout.addLayout(self.center_layout)  # Add centered big buttons
        main_layout.addStretch()  # Push big buttons upward (center them)

        self.setLayout(main_layout)  #

    def open_gallery(self):
        if os.path.exists(r'result\matching') and len(os.listdir(r'result\matching'))>0:
            self.gallery_win = GalleryWindow()
            self.gallery_win.show()
        else:
            print('NO CLASSIFICATION FOLDER YET')


    def work_with_csv(self):
        '''Opens file system for the user to choose CSV files. Sends the chosen files to the processing.'''
        dialog = QtWidgets.QFileDialog(self)
        dialog.setNameFilter("Files (*.csv)")
        dialog.setFileMode(QtWidgets.QFileDialog.ExistingFiles) 

        if dialog.exec():
            fileNames = dialog.selectedFiles()
            print(fileNames)
            m = manager.CSVManager() 
            m.work_with_csv(fileNames)
            self.fin_win = FinishWindow(self.language)
            self.fin_win.show()

    def work_with_dir(self):
        '''Opens file system for the user to choose a directory. Sends the chosen directory to the processing.'''
        dialog = QtWidgets.QFileDialog(self)
        directory = dialog.getExistingDirectory(None, "Select a Directory", "")

        if directory:
            print("Selected directory:", directory)
            m = manager.DIRManager() 
            m.work_with_dir(directory)
            self.fin_win = FinishWindow(self.language)
            self.fin_win.show()

    def change_language(self):
        """Loads the selected language"""
        lang_code = self.language_selector.currentData()
        print(lang_code)
        self.language = lang_code
        self.button1.setText(lang_button1[lang_code])
        self.button2.setText(lang_button2[lang_code])
        self.button_help.setText(lang_help_button[lang_code])
        self.author_label.setText(lang_author_label[lang_code])
        self.manual = lang_help[lang_code]
        
        if self.help_win_open:
            self.text_edit.setPlainText(self.manual)
        
        if self.fin_win: # not needed for now because when fin_win is open main window is frozen
            self.fin_win.change_language(lang_code)

    
    def open_help_window(self):
        '''Opens help window.'''
        self.help_win_open = True
        self.text_edit = QtWidgets.QTextEdit()
        self.text_edit.resize(600, 300)
        # self.text_edit.setStyleSheet(self.color)
        self.text_edit.setFont(self.big_font)
        self.text_edit.setReadOnly(True)
        self.text_edit.setPlainText(self.manual)
        self.text_edit.setWindowTitle("Help")
        self.text_edit.show()
    
    def closeEvent(self, event):
        if self.text_edit is not None:
            self.text_edit.close()  # Manually close the text editor
        event.accept()



class FinishWindow(QtWidgets.QWidget):
    def __init__(self, lang:str):
        super().__init__()
        self.setWindowTitle("Finish")
        self.setWindowIcon(QtGui.QIcon(DATA_PATH))

        self.resize(800, 600)

        self.font = QtGui.QFont("Bodoni MT", 20, QtGui.QFont.Bold)

        self.layout = QtWidgets.QVBoxLayout()
        self.label = QtWidgets.QLabel(lang_finish_label[lang])
        # self.label.setStyleSheet("color: #00FF00")
        self.label.setFont(self.font)

        self.layout.addWidget(self.label, alignment=QtCore.Qt.AlignCenter)
        self.setLayout(self.layout)
        self.setWindowModality(QtCore.Qt.ApplicationModal)
    
    def change_language(self, lang:str):
        '''Loads the selected language'''
        self.label.setText(lang_finish_label[lang])

class GalleryWindow(QtWidgets.QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Image Gallery")
        self.setWindowIcon(QtGui.QIcon(DATA_PATH))

        self.resize(800, 600)

        self.font = QtGui.QFont("Bodoni MT", 20, QtGui.QFont.Bold)
        self.classfication_path = r'result\matching'
        self.imgs_to_class = self.find_dirs_with_classification()
        # self.color = "color: #00FF00"
        self.small_font = QtGui.QFont("Bodoni MT", 15, QtGui.QFont.Bold)
        # self.small_font = QtGui.QFont("Bodoni MT", 10, QtGui.QFont.Bold)
        self.WIDTH = 630
        self.HEIGHT = 350

        self.counter = 0
        self.dir_counter = 0

        # self.image_list = [
        #     f for f in os.listdir(self.INPUT_DIR)
        #     if f.lower().endswith((".png", ".jpg", ".jpeg", ".bmp", ".gif"))
        # ]


        self.init_ui()
        self.show_image()
        self.setWindowModality(QtCore.Qt.ApplicationModal)
    
    def closeEvent(self, event: QtGui.QCloseEvent) -> None:
        print('SAVING CHANGES')

        for key, value in self.imgs_to_class.items():
            img1, img2 = key
            self.move_image(img1, img2, value)
        
        print('ALL CHANGES ARE SAVED')
    
    def move_image(self, src1, src2, to_label):
        # src = os.path.join(base_dir, str(from_label), image_name)
        p1 = Path(src1)
        p2 = Path(src2)
        from_label = p1.parent.name 
        if from_label == to_label: return
        image_name1 = p1.name
        image_name2 = p2.name
        dst_dir = os.path.join(self.classfication_path, str(to_label))
        dst1 = os.path.join(dst_dir, image_name1)  # or image_name2, depending on your logic
        dst2 = os.path.join(dst_dir, image_name2)

        os.makedirs(dst_dir, exist_ok=True)  # ensure folder exists
        shutil.move(src1, dst1)
        shutil.move(src2, dst2)
    
    def find_dirs_with_classification(self):
        # path_ = r'result\classification'
        imgs_to_class = {}
        if os.path.exists(self.classfication_path):
            class_dirs = [os.path.join(self.classfication_path, d ) for d  in os.listdir(self.classfication_path)]
            for cl in class_dirs:
                imgs = os.listdir(cl)
                imgs_0 = [img for img in imgs if img.endswith('_0.jpeg')]
                imgs_1 = [img for img in imgs if img.endswith('_1.jpeg')]
                class_ = os.path.basename(cl)
                for img0, img1 in zip(imgs_0, imgs_1):
                    imgs_to_class[(os.path.join(cl, img0), os.path.join(cl, img1))] = class_
        return imgs_to_class

    def init_ui(self):
        self.left_image_label = QtWidgets.QLabel()
        self.right_image_label = QtWidgets.QLabel()
        for image_label in (self.left_image_label, self.right_image_label):
            image_label.setFixedSize(self.WIDTH // 2, self.HEIGHT)
            image_label.setAlignment(QtCore.Qt.AlignCenter)

        self.info_label = QtWidgets.QLabel()
        self.info_label.setAlignment(QtCore.Qt.AlignCenter)
        # self.info_label.setStyleSheet(self.color)
        self.info_label.setFont(self.small_font)

        self.label_label = QtWidgets.QLabel("Current label")
        # self.label_label.setAlignment(QtCore.Qt.AlignCenter)
        # self.label_label.setStyleSheet(self.color)
        self.label_label.setFont(self.small_font)
        self.class_labels =  ['sim', 'dif']
        self.label_combo = QtWidgets.QComboBox()
        for i, l in enumerate(self.class_labels):
            self.label_combo.addItem(l,i)
        # self.label_combo.addItems(self.class_labels)
        self.label_combo.currentIndexChanged.connect(self.label_change)
        # self.label_combo.setStyleSheet(self.color)
        self.label_combo.setFont(self.small_font)

        label_layout = QtWidgets.QHBoxLayout()
        label_layout.addStretch()
        label_layout.addWidget(self.label_label)
        label_layout.addSpacing(20)
        label_layout.addWidget(self.label_combo)
        label_layout.addStretch()

        # --- buttons ---
        self.prev_btn = QtWidgets.QPushButton("<< Previous")
        self.next_btn = QtWidgets.QPushButton("Next >>")

        for btn in (self.prev_btn, self.next_btn):
            btn.setFixedSize(140, 40)
            # btn.setStyleSheet(self.color)
            btn.setFont(self.small_font)

        self.prev_btn.clicked.connect(self.prev_image)
        self.next_btn.clicked.connect(self.next_image)

        # --- layouts ---
        btn_layout = QtWidgets.QHBoxLayout()
        btn_layout.addStretch()
        btn_layout.addWidget(self.prev_btn)
        btn_layout.addSpacing(20)
        btn_layout.addWidget(self.next_btn)
        btn_layout.addStretch()

        image_layout = QtWidgets.QHBoxLayout()
        image_layout.addWidget(self.left_image_label)
        image_layout.addWidget(self.right_image_label)

        main_layout = QtWidgets.QVBoxLayout(self)
        main_layout.addWidget(self.info_label)
        main_layout.addLayout(image_layout)
        # main_layout.addWidget(self.label_label)
        main_layout.addLayout(label_layout)
        main_layout.addLayout(btn_layout)
    
    def label_change(self, index):
        index_label = self.label_combo.itemData(index)
        print(self.class_labels[index_label])
        curr_img1, curr_img2 = list(self.imgs_to_class.keys())[self.counter]
        self.imgs_to_class[(curr_img1, curr_img2)] = self.class_labels[index_label]


    def show_image(self):
        img_path1, img_path2 = list(self.imgs_to_class.keys())[self.counter]#os.path.join(self.INPUT_DIR, self.image_list[self.counter])

        self.left_image_label.setPixmap(self.load_pixmap(img_path1))
        self.right_image_label.setPixmap(self.load_pixmap(img_path2))
        self.info_label.setText(
            f"Match {self.counter + 1} of {len(self.imgs_to_class.items())}"
        )
        # index = self.label_combo.findData(self.imgs_to_class[img_path])
        # print('Current label', self.imgs_to_class[img_path])
        # self.label_combo.setCurrentText(self.imgs_to_class[img_path])
        label = self.imgs_to_class[(img_path1, img_path2)]
        index = self.label_combo.findData(self.class_labels.index(label))
        if index != -1:
            self.label_combo.blockSignals(True)
            self.label_combo.setCurrentIndex(index)
            self.label_combo.blockSignals(False)

    def load_pixmap(self, image_path: str):
        pixmap = QtGui.QPixmap(image_path)
        if pixmap.isNull():
            placeholder = QtGui.QPixmap(self.WIDTH // 2, self.HEIGHT)
            placeholder.fill(QtCore.Qt.black)
            return placeholder

        return pixmap.scaled(
            self.WIDTH // 2,
            self.HEIGHT,
            QtCore.Qt.KeepAspectRatio,
            QtCore.Qt.SmoothTransformation,
        )

    def next_image(self):
        self.counter = (self.counter + 1) % len(self.imgs_to_class.items())
        self.show_image()

    def prev_image(self):
        self.counter = (self.counter - 1) % len(self.imgs_to_class.items())
        self.show_image()




if __name__ == "__main__":
    print(os.getcwd())
    app = QtWidgets.QApplication([])
    app.setQuitOnLastWindowClosed(True)

    app.setWindowIcon(QtGui.QIcon(DATA_PATH))

    widget = MyWidget()
    widget.setWindowIcon(QtGui.QIcon(DATA_PATH))
    widget.setWindowTitle('ClassArt')
    widget.resize(800, 600)
    widget.show()

    sys.exit(app.exec())
