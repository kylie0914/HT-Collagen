'''
    25.08.21 main_v3
    - 전체 UI 초안 작성 시작 :
    Image processing -> Phase correction -> Area Fraction/Diff results -> PIVLAB

    [완료 사항]
    1. ImageJ macro 그대로 사용해서 이미지처리 (모든 이미지)
        - 여기에 preview 기능 하나 넣기 (선택된 폴더의 첫번째 이미지로에 대해 현재 값 으로 이미지처리된 결과 보여주기, 값 바꾸면  preview업데이트, run 누르면 그때 전체 이미지 프로세싱)
    2. dirft correction (4점 찍기 -> 2점 찍기로 변경, 모든 이미지)
    3. density analysis
        - 이미지 하나하나 하게 하는게 맞을까? diff는 요청한 대로 한거니 상관없는데.. AF는 일단 전체 영역에 대해, 모든 이미지 저장하구,, 렉트그리면 업데이트하는 방식?

    [해야할 것]
    - PIVlab 연동


'''


import sys
from PyQt5.QtWidgets import *
from PyQt5.QtGui import *
from PyQt5.QtCore import Qt
import ctypes
ctypes.windll.user32.SetProcessDPIAware()  # OpenGL 관련 문제 방지
import warnings
warnings.filterwarnings('ignore')
import subprocess


from p1_ImageProcessing_macro import ImageJBatchGUI
from p2_drift_correction_v3IB import main as drift_correction_main
from p3_density_tracking import *


class MainWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.imageproc_window = None
        self.density_window = None      
        self.pivlab_exe_path = None
        self.init_ui()

    def init_ui(self):
        self.setWindowTitle("[CSB-MGH] Main Window v1.3 ")
        self.setGeometry(50, 50, 800, 500)

        self.UI_components()
        self.UI_layout()

        # Signal connections
        self.imageProc_btn.clicked.connect(self.imageProc_clicked)
        self.drift_btn.clicked.connect(self.driftProc_clicked)
        self.areaFraction_btn.clicked.connect(self.density_clicked)
        self.pivlab_btn.clicked.connect(self.pivlab_clicked)


    def UI_components(self):
        # ---- 0. Left components :  logo image (QLabel + QPixmap) , Desciription title (Qlabel), text box
        # ---- ---- 0-1. Left components : logo image (QLabel + QPixmap)
        logo_pixmap = QPixmap("./resources/0_CSB_logo_v1.png")
        self.logo_label = QLabel(self)

        logo_scale = 0.7
        smaller_pixmap = logo_pixmap.scaled(int(logo_pixmap.width() * logo_scale), int(logo_pixmap.height() * logo_scale), Qt.KeepAspectRatio, Qt.FastTransformation)
        self.logo_label.setPixmap(smaller_pixmap)

        # ---- ---- 0-2. Left components :  Desciription title (Qlabel)
        self.description_label = QLabel(" [Description] ", self)
        self.description_label.setFont( QFont('Arial', 18))

        # ---- ---- 0-3. Left components :  text box (Qlabel)
        self.description_content = QLabel(self)
        imgTitle_txt ="\t 1. Image Processing \n"
        imgContent_text =("  • Background subtraction : rolling ball method \n"
                          "  • Threshold mask : binarization\n\n\n")

        driftTitle_txt ="\t 2. Image Alignment \n"
        driftContent_text ="  • Drift correction : Image alignment using FFT\n\n\n"

        AFTitle_txt ="\t 3. Density Analyzer \n"
        AFContent_text =("  • Density estimation \n"
                         "        • Calculate the area fraction heatmap for each input\n"
                         "  • Density difference \n"
                         "        • Calculate the density difference for two density heatmaps\n\n\n")

        pivLabTitle_txt ="\t 4. Force Analyzer \n"
        pivLabContent_text =("  • Calculate the Optical flow \n"
                         "  • Force and Shear stress estimation \n"
                         "      • Converting to force and shear stress by reflecting the \n"
                             "        physical properties of the fiber on optical flow results (ⅆ𝑦/ⅆ𝑥)\n\n\n")

        description_txt = imgTitle_txt + imgContent_text + driftTitle_txt + driftContent_text + AFTitle_txt + AFContent_text + pivLabTitle_txt + pivLabContent_text
        self.description_content.setText(description_txt)
        self.description_content.setFont(QFont('Arial'))
        self.description_content.setStyleSheet("font-size:12pt; color:black; background-color:white; outline:2px black;")
        self.description_content.setAlignment(Qt.AlignLeft)

        # ---- 1. Right components : QLabel (" Flow chart ") , FLow chart : Qbox (QLabel + (buttons) )
        # # ---- 1-1. Right components : QLabel (" Flow chart ")
        self.chartTitle_label = QLabel(" [ Flow Chart ] ", self)
        self.chartTitle_label.setFont(QFont('Arial', 18))
        self.chartTitle_label.setAlignment(Qt.AlignCenter)

        # ---- ---- 1-2. Right components : QPushButton (Each proc. btn) + QLabel (arrow)
        self.imageProc_btn = QPushButton(" 1. Image Processing ")
        self.imageProc_btn.setFixedSize(400,80)
        self.imageProc_btn.setStyleSheet("color: black;"
                                           "font-size:16pt;"
                                           "border-style: solid;"
                                           "border-width: 2px;"
                                           "border-color: #FA8072;"
                                           "border-radius: 5px")

        self.drift_btn = QPushButton(" 2. Drift Correction ")
        self.drift_btn.setFixedSize(400,80)
        self.drift_btn.setStyleSheet("color: black;"
                                           "font-size:16pt;"
                                           "border-style: solid;"
                                           "border-width: 2px;"
                                           "border-color: #FA8072;"
                                           "border-radius: 5px")

        self.areaFraction_btn = QPushButton(" 3. Density Analysis ")
        self.areaFraction_btn.setFixedSize(400,80)
        self.areaFraction_btn.setStyleSheet("color: black;"
                                           "font-size:16pt;"
                                           "border-style: solid;"
                                           "border-width: 2px;"
                                           "border-color: #FA8072;"
                                           "border-radius: 5px")

        self.pivlab_btn = QPushButton(" 4. PIVLab Analysis ")
        self.pivlab_btn.setFixedSize(400,80)
        self.pivlab_btn.setStyleSheet("color: black;"
                                       "font-size:16pt;"
                                       "border-style: solid;"
                                       "border-width: 2px;"
                                       "border-color: #FA8072;"
                                       "border-radius: 5px")

        arrow_pixmap = QPixmap("./resources/1_down_arrow.png")
        smaller_pixmap = arrow_pixmap.scaled(int(arrow_pixmap.width() * 0.1),
                                            int(arrow_pixmap.height() * 0.1),
                                            Qt.KeepAspectRatio,
                                            Qt.FastTransformation)

        self.arrow_label_12 = QLabel()
        self.arrow_label_12.setAlignment(Qt.AlignCenter)
        self.arrow_label_12.setPixmap(smaller_pixmap)

        self.arrow_label_23 = QLabel()
        self.arrow_label_23.setAlignment(Qt.AlignCenter)
        self.arrow_label_23.setPixmap(smaller_pixmap)

        self.arrow_label_34 = QLabel()
        self.arrow_label_34.setAlignment(Qt.AlignCenter)
        self.arrow_label_34.setPixmap(smaller_pixmap)


    def UI_layout(self):
        # ---- Left Layouts
        left_layout = QVBoxLayout()  # Left part of the top layout
        left_layout.addWidget(self.logo_label, stretch=2)
        left_layout.addWidget(self.description_label, stretch=1)
        left_layout.addWidget(self.description_content, stretch=6)


        # ---- Right Layouts
        chart_layout =  QVBoxLayout()
        chart_layout.addSpacing(50)
        chart_layout.addWidget(self.imageProc_btn)
        chart_layout.addWidget(self.arrow_label_12)
        chart_layout.addWidget(self.drift_btn)
        chart_layout.addWidget(self.arrow_label_23)
        chart_layout.addWidget(self.areaFraction_btn)
        chart_layout.addWidget(self.arrow_label_34)
        chart_layout.addWidget(self.pivlab_btn)

        right_layout = QVBoxLayout()  # Right part of the top layout for radio buttons
        right_layout.addSpacing(50)
        right_layout.addWidget(self.chartTitle_label, stretch = 1)
        right_layout.addLayout(chart_layout, stretch =5)
        right_layout.addSpacing(20)


        # ---- main layout
        main_layout = QHBoxLayout()
        main_layout.addLayout(left_layout)
        main_layout.addLayout(right_layout)
        self.setLayout(main_layout)

    def imageProc_clicked(self):
        print("Image Processing Clicked")
        if self.imageproc_window is not None and self.imageproc_window.isVisible():
            self.imageproc_window.raise_()
            self.imageproc_window.activateWindow()
            return
        self.imageproc_window = ImageJBatchGUI()
        self.imageproc_window.show()

    def driftProc_clicked(self):
        print("driftProc clicked")
        if self.density_window is not None:
            self.density_window.close()
            self.density_window = None

        try:
            drift_correction_main()
            QMessageBox.information(self, "Drift Correction", "Drift correction completed.")
        except Exception as e:
            QMessageBox.critical(self, "Drift Correction Error", f"Failed:\n{e}")

    def density_clicked(self):
        print("areaFraction clicked")
        self.density_window = MainDensityWindow()
        self.density_window.show()

    def pivlab_clicked(self):
        print("pivlab clicked")
        if self.density_window is not None:
            self.density_window.close()
            self.density_window = None

if __name__ == "__main__":
    app = QApplication(sys.argv)
    main_window = MainWindow()
    main_window.show()
    sys.exit(app.exec_())