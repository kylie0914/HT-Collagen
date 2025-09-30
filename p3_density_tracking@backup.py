'''
    24.12.12 main_v2
    [끝난 부분]
    - Area fraction mode
    - Diff mode layout 짜기
    - raw, heatmap, overlay 각각 계산/display 부분
    - Diff iamge 계산/저장
        - clim (0,3) 된  heatmap image 2 - 1 수행 함

    [수정해야 할 부분]
    - 읽어온 file list 전체를 한번에 processing 후 heatmap 저장하는 부분 있으면 좋을 듯
    - heatmap 범위가 항상 고정적으로 0~3이 될 수 없는 듯 (background signal increased)
        - 그런데,, 저 밀도값 자체가 필요하다고 함. area fraction.. area 자체에 밀도가 올라가는 것. 그 정보를 뺄 순 없다.
        - 그럼 어떻게...?
    - Diff 결과가... 약간... 음....................................................
    - interpolatino을 빼고 original heatmap끼리 빼면 뭔가 그림이 안이쁨
    - interpolation 적용된 hetamp 차이 구했더니 결과가 예상하고 다른 느낌(?) value 있어야 할 곳이  x<=0 처럼 보임. (보라색)


    [추가할 내용]
    - 현호 ImageJ 부분
    - isabel drift code (matlab -> python )  변환 후 적용
    - PIVlab code 불러와서 병합? <- 일단 이게 뭔지부터... 얘도 UI가 있을 건데, 기능부분만 쏘옥 빼와야 함... 가능하까
'''


import sys, os
import numpy as np
import cv2
import matplotlib.pyplot as plt
from PyQt5.QtWidgets import *

from PyQt5.QtGui import QFont
from matplotlib.figure import Figure
from matplotlib.backends.backend_qt5agg import FigureCanvas
from matplotlib.backends.backend_qt5agg import NavigationToolbar2QT as NavigationToolbar
from mpl_toolkits.axes_grid1 import make_axes_locatable
import ctypes
ctypes.windll.user32.SetProcessDPIAware()  # OpenGL 관련 문제 방지
import warnings
warnings.filterwarnings('ignore')

class densityEstimation(QWidget):
    def __init__(self):
        super().__init__()
        self.area_window = None
        self.diff_window = None

        self.grid_scale = 25
        self.save_directory = "./"  # current directory
        self.selected_file = None
        self.init_ui()

    def init_ui(self):
        self.setWindowTitle("[CSB-MGH] Main Widnow for Area Fraction ")
        self.setGeometry(550, 150, 900,1000)

        self.UI_components()
        self.UI_layout()

        # Signal connections
        self.select_dir_button.clicked.connect(self.select_directory)
        self.file_list.itemClicked.connect(self.display_image)
        self.save_button.clicked.connect(self.save_results)

        self.radio_area_mode.clicked.connect(self.area_mode_selected)
        self.radio_diff_mode.clicked.connect(self.diff_mode_selected)

    # ---- UI control
    def UI_components(self):
        # Top Frame (Directory Selection)
        self.current_dir_label = QLabel("Current Directory: Not selected", self)
        self.save_dir_label = QLabel("Save Directory: Not selected", self)

        self.radio_area_mode = QRadioButton("Area Fraction")
        self.radio_diff_mode = QRadioButton("Diff. Result")
        self.radio_area_mode.setChecked(True)

        self.radio_group = QButtonGroup(self)
        self.radio_group.addButton(self.radio_area_mode)
        self.radio_group.addButton(self.radio_diff_mode)

        # Middle Frame (Image Display)
        # --- Matplot Canvas
        self.raw_fig = Figure(figsize=(5, 5))
        self.raw_image_canvas = FigureCanvas(self.raw_fig)
        self.raw_toolbar = NavigationToolbar(self.raw_image_canvas, self)
        self.raw_ax = None

        self.raw_image_label = QLabel(self)
        self.raw_image_label.setText(" Raw Image (Origin) ")
        self.raw_image_label.setFont(QFont('Arial', 12))

        # --- Matplot Canvas
        self.heatmap_fig = Figure(figsize=(5, 5))
        self.heatmap_canvas = FigureCanvas(self.heatmap_fig)
        self.heatmap_toolbar = NavigationToolbar(self.heatmap_canvas, self)
        self.heatmap_ax = None

        self.heatmap_image_label = QLabel(self)
        self.heatmap_image_label.setText(" Heatmap Image ")
        self.heatmap_image_label.setFont(QFont('Arial', 12))

        self.overlay_fig = Figure(figsize=(5, 5))
        self.overlay_canvas = FigureCanvas(self.overlay_fig)
        self.overlay_toolbar = NavigationToolbar(self.overlay_canvas, self)
        self.overlay_ax = None

        self.overlay_image_label = QLabel(self)
        self.overlay_image_label.setText(" Overlay Image (Origin) ")
        self.overlay_image_label.setFont(QFont('Arial', 12))

        self.density_text = QLabel(self)
        self.density_text.setText(" [Measurement]  ")
        self.density_text.setFont(QFont('Arial', 18))

        self.density_min_text = QLabel(self)
        self.density_min_text.setText(" [min] ")
        self.density_min_text.setFont(QFont('Arial', 12))

        self.density_max_text = QLabel(self)
        self.density_max_text.setText(" [max] ")
        self.density_max_text.setFont(QFont('Arial', 12))

        self.density_mean_text = QLabel(self)
        self.density_mean_text.setText(" [mean] ")
        self.density_mean_text.setFont(QFont('Arial', 12))

        self.density_std_text = QLabel(self)
        self.density_std_text.setText(" [std]] ")
        self.density_std_text.setFont(QFont('Arial', 12))

        # Directory and Save buttons
        self.select_dir_button = QPushButton("Select File Directory", self)
        self.save_button = QPushButton("Save Results", self)
        self.file_list = QListWidget(self)
    def UI_layout(self):
        # --------- Top Layouts
        top_left_layout = QVBoxLayout()  # Left part of the top layout
        top_left_layout.addWidget(self.current_dir_label)
        top_left_layout.addWidget(self.save_dir_label)

        top_right_layout = QVBoxLayout()  # Right part of the top layout for radio buttons
        top_right_layout.addWidget(self.radio_area_mode)
        top_right_layout.addWidget(self.radio_diff_mode)

        top_layout = QHBoxLayout()  # Combine left and right layouts in the top layout
        top_layout.addLayout(top_left_layout)
        top_layout.addLayout(top_right_layout)

        # --------- Middle  Layouts
        raw_img_layout = QVBoxLayout()
        raw_img_layout.addWidget(self.raw_image_label)
        raw_img_layout.addWidget(self.raw_image_canvas, stretch=2)
        raw_img_layout.addWidget(self.raw_toolbar)

        heatmap_layout = QVBoxLayout()
        heatmap_layout.addWidget(self.heatmap_image_label)
        heatmap_layout.addWidget(self.heatmap_canvas, stretch=2)
        heatmap_layout.addWidget(self.heatmap_toolbar)

        middle_layout1 = QHBoxLayout()
        middle_layout1.setSpacing(20)
        middle_layout1.addLayout(raw_img_layout)
        middle_layout1.addLayout(heatmap_layout)

        # --------- Bottom  Layouts
        overlay_layout = QVBoxLayout()
        overlay_layout.addWidget(self.overlay_image_label)
        overlay_layout.addWidget(self.overlay_canvas)
        overlay_layout.addWidget(self.overlay_toolbar)

        control_layout = QVBoxLayout()
        control_layout.setSpacing(20)
        control_layout.addWidget(self.density_text)
        control_layout.addWidget(self.density_min_text)
        control_layout.addWidget(self.density_max_text)
        control_layout.addWidget(self.density_mean_text)
        control_layout.addWidget(self.density_std_text)
        control_layout.addStretch()  # 아래에 빈 공간 추가
        control_layout.addWidget(self.save_button)

        filelist_layout = QVBoxLayout()
        filelist_layout.setContentsMargins(0, 30, 0, 0)  # 좌, 상, 우, 하
        filelist_layout.addWidget(self.file_list)
        filelist_layout.addWidget(self.select_dir_button)

        bottom_layout = QHBoxLayout()
        bottom_layout.setSpacing(20)
        bottom_layout.addLayout(overlay_layout, stretch=4)
        bottom_layout.addLayout(control_layout, stretch=3)
        bottom_layout.addLayout(filelist_layout, stretch=2)

        # # -- main layout
        main_layout = QVBoxLayout()
        main_layout.addLayout(top_layout)
        main_layout.addLayout(middle_layout1)
        main_layout.addLayout(bottom_layout)
        self.setLayout(main_layout)

    def area_mode_selected(self):
        print("area mode")
        if self.diff_window is not None:
            self.diff_window.close()
            self.diff_window = None

    def diff_mode_selected(self):
        print("diff mode")
        if self.radio_diff_mode.isChecked():
            if self.diff_window is None:  # 창이 없으면 새로운 창을 만듦
                self.diff_window = densityTracking()
                self.diff_window.show()

    # --- UI functions
    def select_directory(self):
        directory = QFileDialog.getExistingDirectory(self, "Select Directory")
        print(directory)
        if directory:
            self.current_dir_label.setText(f"Current Directory: {directory}")
            selected_folder = directory.split("/")[-1]
            self.save_directory = os.path.join("prev_saveResult/AFmode/", selected_folder)
            print(self.save_directory)
            if not os.path.exists(self.save_directory):
                os.makedirs(self.save_directory)
            self.save_dir_label.setText(f"Save Directory: {self.save_directory}")
            self.list_png_files(directory)

    def list_png_files(self, directory):
        self.file_list.clear()

        files = [file for file in os.listdir(directory) if file.endswith(".png") or file.endswith(".jpg") or file.endswith(".tif")]
        # files.sort(key=lambda x: float(x.strip('im_').strip('.png').strip('.jpg')))
        files.sort(key=lambda x: float(x.strip('im_').strip('.png').strip('.jpg').strip('.tif')))

        for file in files:
            self.file_list.addItem(file)

    # -------------- Calc Area fraciton
    def trim_heatmapData(self, heatmap_density, bi_img_resize, heatmap_size,):
        # -- density 0 ~ 3사이로 범위 정리
        density_range = [0, 5] #  [min value, max value]
        heatmap_density_trim = [0 if x <= density_range[0] else density_range[1] if x >= density_range[1] else x for x in heatmap_density]  # 1D
        heatmap_density_mat = np.array(heatmap_density_trim).reshape(heatmap_size, heatmap_size)  # 2D

        # --- 3. density 범위  정리
        perc_interp = [np.interp(perc, (0, (self.grid_scale ** 2) / 100), (0, 255)) for perc in heatmap_density_trim]
        # perc_interp = [np.interp(perc, (0, 3), (0, 255)) for perc in heatmap_density_trim]  #  0 <= 0, 3> = 3 / 0~3
        interp_matrix = np.array(perc_interp).reshape(heatmap_size, heatmap_size)  # 1d to 2D
        interp_matrix_resized = cv2.resize(interp_matrix,
                                           (bi_img_resize.shape[1], bi_img_resize.shape[0]))  # has float variables
        interp_matrix_resized_rgb = cv2.cvtColor(interp_matrix_resized.astype(np.uint8), cv2.COLOR_GRAY2RGB)
        interp_matrix_resized_int = interp_matrix_resized.astype(np.uint8)

        return heatmap_density_mat, interp_matrix_resized_int, interp_matrix_resized_rgb

    def calc_heatmap(self, binary_image, bi_img_resize):
        # --- 2.calc heatmap :  격자별 1의 비율 계산 후 density 계산 (1이 기준임)
        grid_size = (int(binary_image.shape[0] / self.grid_scale), int(binary_image.shape[1] / self.grid_scale))

        hematmap_ratio = []
        heatmap_density = []
        for y in range(0, bi_img_resize.shape[0], self.grid_scale):
            for x in range(0, bi_img_resize.shape[1], self.grid_scale):
                grid = binary_image[y:y + self.grid_scale, x:x + self.grid_scale]

                # 히트맵 ratio 계산
                one_ratio = np.count_nonzero(grid) / (self.grid_scale ** 2)
                zero_ratio = 1 - one_ratio

                # 히트맵 밀도 계산
                # one_density = float((one_ratio - 0.040156 )/0.074642)
                one_density = float((one_ratio - 0.1142) / 0.069721)

                # 1의 비율이 높을수록 높은 수치
                hematmap_ratio.append(one_ratio)
                heatmap_density.append(one_density)

        return grid_size, hematmap_ratio, heatmap_density

    # -------------- Plot
    def matplotFig_init(self):
        self.raw_fig.clf()
        self.heatmap_fig.clf()
        self.overlay_fig.clf()

        self.raw_ax = self.raw_fig.subplots()
        self.raw_ax.set_axis_off()
        self.heatmap_ax = self.heatmap_fig.subplots()
        self.heatmap_ax.set_axis_off()
        self.overlay_ax = self.overlay_fig.subplots()
        self.overlay_ax.set_axis_off()

    def draw_rawImg(self, bi_img_resize):
        self.raw_ax.cla()
        img = self.raw_ax.imshow(bi_img_resize, cmap="gray")  # matplot -> 행, 열, 채널 순

        self.raw_ax.set_axis_off()
        self.raw_fig.colorbar(img, ax=self.raw_ax, orientation='vertical')

        self.raw_fig.tight_layout()
        self.raw_image_canvas.draw()

    def draw_heatmap(self,heatmap_density_mat_resized):
        self.heatmap_ax.cla()
        img = self.heatmap_ax.imshow(heatmap_density_mat_resized,  interpolation='bilinear', clim=(0,5))

        self.heatmap_ax.set_axis_off()
        self.heatmap_fig.colorbar(img, ax=self.heatmap_ax, orientation='vertical')

        self.heatmap_fig.tight_layout()
        self.heatmap_canvas.draw()

        # heatmap_np = np.array(self.heatmap_fig.canvas.renderer._renderer) # matplot -> numpy
        # return heatmap_np

    def draw_overlay(self,bi_img_resize,heatmap_density_mat_resized):
        self.overlay_ax.cla()
        self.overlay_ax.imshow(bi_img_resize, cmap='gray', alpha=1.0)
        self.overlay_ax.imshow(heatmap_density_mat_resized, interpolation='bilinear', alpha=0.6)

        self.overlay_ax.set_axis_off()
        self.overlay_fig.tight_layout()
        self.overlay_canvas.draw()

    def display_image(self):
        if self.radio_area_mode.isChecked():
            # -- figure init
            self.matplotFig_init()

            #-- file list
            self.selected_file = self.file_list.currentItem().text()
            print(self.selected_file)
            directory = self.current_dir_label.text().replace("Current Directory: ", "")
            img_path = os.path.join(directory, self.selected_file)

            # # ----- Load raw image
            binary_image = cv2.imread(img_path, cv2.IMREAD_GRAYSCALE)
            binary_image = 255 - binary_image
            bi_img_resize = cv2.resize(binary_image, (1000, 1000))  # 1000, 1000 for analysis
            bi_img_display = cv2.resize(bi_img_resize, (400, 400))
            heatmap_size = int(bi_img_resize.shape[0] / self.grid_scale)

            self.draw_rawImg(bi_img_display)

            # ---- Get Heatmap array and image
            grid_size, hematmap_ratio, heatmap_density = self.calc_heatmap(binary_image, bi_img_resize)

            self.heatmap_density_data = heatmap_density

            # self.density_text.setText(density_text)
            self.density_min_text.setText(" [min] :  {0}".format(np.round(np.min(heatmap_density), 5) ))
            self.density_max_text.setText(" [max] :  {0}".format(np.round(np.max(heatmap_density), 5)))
            self.density_mean_text.setText(" [mean] :  {0}".format(np.round(np.mean(heatmap_density), 5)))
            self.density_std_text.setText(" [std] :  {0}".format(np.round(np.std(heatmap_density), 5)))

            heatmap_density_mat = np.array(heatmap_density).reshape(heatmap_size, heatmap_size)  # 2D (40,40)
            heatmap_density_mat_resized = cv2.resize(heatmap_density_mat, (bi_img_resize.shape[1], bi_img_resize.shape[0])) # (1000,1000)
            self.draw_heatmap(heatmap_density_mat_resized)  # (1000, 1000)

            # ---- Draw overlay image
            self.draw_overlay(bi_img_resize, heatmap_density_mat_resized)
        else:
            pass

    def save_results(self):
        # --- save image , data
        # ---- Heatmap image/ data
        heatmap_density_mat = np.array(self.heatmap_density_data).reshape(40, 40)  # 2D (40,40)
        cm = 1/2.54
        fig, ax = plt.subplots(figsize=(40*cm, 30*cm))
        ax.imshow(heatmap_density_mat)

        for i in range(heatmap_density_mat.shape[0]):
            for j in range(heatmap_density_mat.shape[1]):
                plt.annotate(str(round(heatmap_density_mat[i][j],1) ), ha = 'center', va='center', color='white', xy =(j, i))

        if not os.path.exists(os.path.join(self.save_directory, "heatmap_" + self.selected_file)):
            plt.savefig(os.path.join(self.save_directory,"heatmap_" + self.selected_file))
        else:
            pass

        plt.show()
        plt.pause(3)
        plt.close()


        # ---- Overlay image 저장
        overlay_np = np.array(self.overlay_fig.canvas.renderer._renderer)  # matplot -> numpy

        fig = plt.figure(frameon=False)
        plt.tight_layout()
        plt.imshow(overlay_np)

        if not os.path.exists(os.path.join(self.save_directory, "Overlay_" + self.selected_file)):
            plt.savefig(os.path.join(self.save_directory,"Overlay_" + self.selected_file))
        else:
            pass

        plt.show()
        plt.pause(3)
        plt.close()



class densityTracking(QWidget):
    def __init__(self):
        super().__init__()
        self.selected_file_1 = None
        self.selected_file_2 = None
        self.grid_scale = 25
        self.heatmap_density_data1 = None
        self.heatmap_density_data2 = None

        self.directory = None
        self.init_ui()


    def init_ui(self):
        # --
        self.setWindowTitle("[CSB-MGH] hyunho")
        self.setGeometry(550, 350, 1200, 900)

        self.UI_components()
        self.UI_layout()

        # --- signal
        self.select_dir_file.clicked.connect(self.select_directory)
        self.file_list_1.itemClicked.connect(self.get_selectedFile_1)
        self.file_list_2.itemClicked.connect(self.get_selectedFile_2)
        self.calc_save_button.clicked.connect(self.calc_saveResult)


    def UI_components(self):
        # ---- UI components
        # ---- # Top frame : current/save directory
        self.current_dir_label = QLabel("Current Directory: Not selected", self)
        self.save_dir_label = QLabel("Save Directory: Not selected", self)

        # ---- # Middle frame : Matplot canvas + label for raw/heatmap img
        self.raw_fig_1 = Figure(figsize=(4, 4))
        self.raw_canvas_1 = FigureCanvas(self.raw_fig_1)
        self.raw_toolbar_1 = NavigationToolbar(self.raw_canvas_1, self)
        # self.raw_ax_1 = None
        self.raw_ax_1 = None

        self.raw_fig_2 = Figure(figsize=(4, 4))
        self.raw_canvas_2 = FigureCanvas(self.raw_fig_2)
        self.raw_toolbar_2 = NavigationToolbar(self.raw_canvas_2, self)
        self.raw_ax_2 = None

        self.heatmap_fig_1 = Figure(figsize=(4, 4))
        self.heatmap_canvas_1 = FigureCanvas(self.heatmap_fig_1)
        self.heatmap_toolbar_1 = NavigationToolbar(self.heatmap_canvas_1, self)
        self.heatmap_ax_1 = None

        self.heatmap_fig_2 = Figure(figsize=(4, 4))
        self.heatmap_canvas_2 = FigureCanvas(self.heatmap_fig_2)
        self.heatmap_toolbar_2 = NavigationToolbar(self.heatmap_canvas_2, self)
        self.heatmap_ax_2 = None

        # --- Label
        self.raw_image_label_1 = QLabel(self)
        self.raw_image_label_1.setText(" Raw Image (Origin) 1")
        self.raw_image_label_1.setFont(QFont('Arial', 12))

        self.raw_image_label_2 = QLabel(self)
        self.raw_image_label_2.setText(" Raw Image (Origin) 2")
        self.raw_image_label_2.setFont(QFont('Arial', 12))

        self.heatmap_image_label_1 = QLabel(self)
        self.heatmap_image_label_1.setText(" Heatmap Image 1")
        self.heatmap_image_label_1.setFont(QFont('Arial', 12))

        self.heatmap_image_label_2 = QLabel(self)
        self.heatmap_image_label_2.setText(" Heatmap Image 2")
        self.heatmap_image_label_2.setFont(QFont('Arial', 12))

        # ---- # Bottom frame :
        self.diff_fig = Figure(figsize=(4, 4))
        self.diff_canvas = FigureCanvas(self.diff_fig)
        self.diff_toolbar = NavigationToolbar(self.diff_canvas, self)
        self.diff_ax = None

        self.diff_image_label = QLabel(self)
        self.diff_image_label.setText(" Diff Image: 2-1 ")
        self.diff_image_label.setFont(QFont('Arial', 12))

        self.file_list_1 = QListWidget(self)
        self.file_list_2 = QListWidget(self)
        self.select_dir_file = QPushButton("Select File 1,2", self)


        self.calc_save_button = QPushButton("Calc. and Save ", self)

    def UI_layout(self):
        # --------- Top Layouts
        top_layout = QVBoxLayout()  # Left part of the top layout
        top_layout.addWidget(self.current_dir_label)
        top_layout.addWidget(self.save_dir_label)

        # --------- Middle Layouts
        raw_img1_layout = QVBoxLayout()
        raw_img1_layout.addWidget(self.raw_image_label_1)
        raw_img1_layout.addWidget(self.raw_canvas_1)
        raw_img1_layout.addWidget(self.raw_toolbar_1 )

        raw_img2_layout = QVBoxLayout()
        raw_img2_layout.addWidget(self.raw_image_label_2)
        raw_img2_layout.addWidget(self.raw_canvas_2)
        raw_img2_layout.addWidget(self.raw_toolbar_2)

        diff_layout = QVBoxLayout()
        diff_layout.addWidget(self.diff_image_label)
        diff_layout.addWidget(self.diff_canvas)
        diff_layout.addWidget(self.diff_toolbar)

        middle_layout = QHBoxLayout()
        middle_layout.addLayout(raw_img1_layout)
        middle_layout.addLayout(raw_img2_layout)
        middle_layout.addLayout(diff_layout)

        # --------- Bottom  Layouts
        heatmap_img1_layout = QVBoxLayout()
        heatmap_img1_layout.addWidget(self.heatmap_image_label_1)
        heatmap_img1_layout.addWidget(self.heatmap_canvas_1)
        heatmap_img1_layout.addWidget(self.heatmap_toolbar_1)

        heatmap_img2_layout = QVBoxLayout()
        heatmap_img2_layout.addWidget(self.heatmap_image_label_2)
        heatmap_img2_layout.addWidget(self.heatmap_canvas_2)
        heatmap_img2_layout.addWidget(self.heatmap_toolbar_2)


        filelist_layout = QHBoxLayout()
        filelist_layout.addWidget(self.file_list_1)
        filelist_layout.addWidget(self.file_list_2)


        # --- filelist 1, filelist 2
        file_save_layout = QVBoxLayout()
        file_save_layout.setContentsMargins(0,30,0,0) # 좌, 상, 우, 하
        file_save_layout.addLayout(filelist_layout)
        file_save_layout.addWidget(self.select_dir_file)
        file_save_layout.addWidget(self.calc_save_button)

        bottom_layout = QHBoxLayout()
        bottom_layout.addLayout(heatmap_img1_layout,stretch=3)
        bottom_layout.addLayout(heatmap_img2_layout,stretch=3)
        bottom_layout.addLayout(file_save_layout,stretch=3)

        # --------- Main  Layouts
        main_layout = QVBoxLayout()
        main_layout.addLayout(top_layout)
        main_layout.addLayout(middle_layout)
        main_layout.addLayout(bottom_layout)
        self.setLayout(main_layout)


    def select_directory(self):
        self.directory = QFileDialog.getExistingDirectory(self, "Select Directory")
        print(self.directory)

        if self.directory:
            self.current_dir_label.setText(f"Current Directory: {self.directory}")
            selected_folder = self.directory.split("/")[-1]
            self.save_directory = os.path.join("prev_saveResult/DFmode/", selected_folder)
            print(self.save_directory)

            if not os.path.exists(self.save_directory):
                os.makedirs(self.save_directory)

            self.save_dir_label.setText(f"Save Directory: {self.save_directory}")
            self.list_png_files(self.directory)


    def list_png_files(self, directory):
        self.file_list_1.clear()
        self.file_list_2.clear()

        files = [file for file in os.listdir(directory) if file.endswith(".png") or file.endswith(".jpg")]
        files.sort(key=lambda x: float(x.strip('im_').strip('.png').strip('.jpg')))

        for file in files:
            self.file_list_1.addItem(file)
            self.file_list_2.addItem(file)


    def get_selectedFile_1(self):
        try:
            # self.matplotFig_init()
            self.selected_file_1 = self.file_list_1.currentItem().text()
            img_path = os.path.join(self.directory, self.selected_file_1)

            #  ------------- raw------------
            binary_image = cv2.imread(img_path, cv2.IMREAD_GRAYSCALE)
            bi_img_resize = cv2.resize(binary_image, (1000, 1000))  # 분석용 크기로 리사이즈
            bi_img_resize = 255 - bi_img_resize


            self.raw_fig_1.clf()
            self.raw_ax_1 = self.raw_fig_1.subplots()

            img = self.raw_ax_1.imshow(bi_img_resize, cmap="gray")  # matplot -> 행, 열, 채널 순
            divider = make_axes_locatable(self.raw_ax_1)
            cax = divider.append_axes("right", size="5%", pad=0.05)  # colorbar의 크기 및 간격 설정
            self.raw_fig_1.colorbar(img, ax=self.raw_ax_1, orientation='vertical', cax=cax)

            self.raw_ax_1.set_axis_off()
            self.raw_fig_1.tight_layout()
            self.raw_canvas_1.draw()

            # ------------ Heatmap -----------
            heatmap_size = int(bi_img_resize.shape[0] / self.grid_scale)  # (40,40) for heatmap size

            grid_size, hematmap_ratio, heatmap_density = self.calc_heatmap(binary_image, bi_img_resize)
            heatmap_density_mat = np.array(heatmap_density).reshape(heatmap_size, heatmap_size)  # 2D (40,40)
            heatmap_density_mat_resized = cv2.resize(heatmap_density_mat, (bi_img_resize.shape[1], bi_img_resize.shape[0])) # (1000,1000)

            heatmap_density_mat_clim, interp_matrix_resized_int, interp_matrix_resized_rgb = self.trim_heatmapData(heatmap_density, bi_img_resize, heatmap_size)

            self.heatmap_fig_1.clf()
            self.heatmap_ax_1 = self.heatmap_fig_1.subplots()

            self.heatmap_ax_1.imshow(bi_img_resize, cmap='gray', alpha=1.0)
            # img = self.heatmap_ax_1.imshow(heatmap_density_mat_resized, interpolation='bilinear', alpha=0.6, clim=(0,3))
            img = self.heatmap_ax_1.imshow(heatmap_density_mat_resized, interpolation='bilinear', alpha=0.6)

            divider = make_axes_locatable(self.heatmap_ax_1)
            cax = divider.append_axes("right", size="5%", pad=0.05)  # colorbar의 크기 및 간격 설정
            self.heatmap_fig_1.colorbar(img, ax=self.heatmap_ax_1, orientation='vertical', cax=cax)

            self.heatmap_ax_1.set_axis_off()
            self.heatmap_fig_1.tight_layout()
            self.heatmap_canvas_1.draw()

            # --- for Diff image
            # self.heatmap_density_data1= heatmap_density_mat_clim  # heatmap 0-3 clim (
            self.heatmap_density_data1 = heatmap_density_mat_resized

            # self.heatmap_density_data1= heatmap_density  #  heatmap original
            # self.heatmap_density_data1 = np.array(self.heatmap_fig_1.canvas.renderer._renderer)  # overlay image


        except Exception as e:
            print(f"오류 발생: {e}")


    def get_selectedFile_2(self):
        try:

            self.selected_file_2 = self.file_list_2.currentItem().text()
            img_path= os.path.join(self.directory, self.selected_file_2)

            #  ------------- raw------------
            binary_image = cv2.imread(img_path, cv2.IMREAD_GRAYSCALE)
            bi_img_resize = cv2.resize(binary_image, (1000, 1000))  # 분석용 크기로 리사이즈
            bi_img_resize = 255 - bi_img_resize

            self.raw_fig_2.clf()
            self.raw_ax_2 = self.raw_fig_2.subplots()

            img = self.raw_ax_2.imshow(bi_img_resize,  interpolation='bilinear', cmap="gray")  # matplot -> 행, 열, 채널 순
            divider = make_axes_locatable(self.raw_ax_2)
            cax = divider.append_axes("right", size="5%", pad=0.05)  # colorbar의 크기 및 간격 설정
            self.raw_fig_2.colorbar(img, ax=self.raw_ax_2, orientation='vertical', cax=cax)

            self.raw_ax_2.set_axis_off()
            self.raw_fig_2.tight_layout()
            self.raw_canvas_2.draw()

            # ------------ Heatmap Overlay -----------
            heatmap_size = int(bi_img_resize.shape[0] / self.grid_scale)  # (40,40) for heatmap size

            grid_size, hematmap_ratio, heatmap_density = self.calc_heatmap(binary_image, bi_img_resize)
            heatmap_density_mat = np.array(heatmap_density).reshape(heatmap_size, heatmap_size)  # 2D (40,40)
            heatmap_density_mat_resized = cv2.resize(heatmap_density_mat, (bi_img_resize.shape[1], bi_img_resize.shape[0])) # (1000,1000)

            heatmap_density_mat_clim, interp_matrix_resized_int, interp_matrix_resized_rgb = self.trim_heatmapData(heatmap_density, bi_img_resize, heatmap_size)


            self.heatmap_fig_2.clf()
            self.heatmap_ax_2 = self.heatmap_fig_2.subplots()

            self.heatmap_ax_2.imshow(bi_img_resize, cmap='gray', alpha=1.0)
            # img = self.heatmap_ax_2.imshow(heatmap_density_mat_resized, interpolation='bilinear', alpha=0.6, clim=(0,3))
            img = self.heatmap_ax_2.imshow(heatmap_density_mat_resized, interpolation='bilinear', alpha=0.6)

            divider = make_axes_locatable(self.heatmap_ax_2)
            cax = divider.append_axes("right", size="5%", pad=0.05)  # colorbar의 크기 및 간격 설정
            self.heatmap_fig_2.colorbar(img, ax=self.heatmap_ax_2, orientation='vertical', cax=cax)

            self.heatmap_ax_2.set_axis_off()
            self.heatmap_fig_2.tight_layout()
            self.heatmap_canvas_2.draw()

            # --- for Diff image
            # self.heatmap_density_data2= heatmap_density_mat_clim  # heatmap 0-3 clim (
            self.heatmap_density_data2 = heatmap_density_mat_resized

            # self.heatmap_density_data2= heatmap_density  #  heatmap original
            # self.heatmap_density_data2 = np.array(self.heatmap_fig_2.canvas.renderer._renderer)  # overlay image

        except Exception as e:
            print(f"오류 발생: {e}")



    def calc_saveResult(self):
        if self.heatmap_density_data1 is None and self.heatmap_density_data2 is None:
            print("Heatmap 1,2 is not calculated yet")
        else:
            try:
                # --- Diff 는 0~3 clim  된 heatmap image에 대해서 계산..? <--- 현호한테 물어봐야 함 (일단 이렇게 진행)
                '''
                    [수정해야 할 부분]
                    - Diff iamge 계산/저장
                        - clim (0,3) 된 이미지 ? or origianl heatmap image?
                        - image1 - image 2 or image2 - iamge 1 or abs(image1-image2)
    
                        - interpolation(Heatmap2 - heatmap1 ) 이거로 보여주는 것
                        -  Heatmap2 w.interp -  Heatmap1 w.interp 
                '''
                # self.heatmap_density_data1 = heatmap_density (1D array, (1600,)) //self.heatmap_density_data2
                # heatmap_density_mat_1 = np.array(self.heatmap_density_data1).reshape(40, 40)
                # heatmap_density_mat_2 = np.array(self.heatmap_density_data2).reshape(40, 40)
                heatmap_density_mat_1 = np.array(self.heatmap_density_data1).reshape(1000, 1000)
                heatmap_density_mat_2 = np.array(self.heatmap_density_data2).reshape(1000, 1000)
                # heatmap_density_mat, interp_matrix_resized_int, interp_matrix_resized_rgb = trim_heatmapData( heatmap_density, bi_img_resize, heatmap_size)
                heatmap_diff = [ai - bi for ai, bi in zip(heatmap_density_mat_2, heatmap_density_mat_1)]  # density diff. == image 2- image 1

                # ----------- diff --------------
                self.diff_fig.clf()
                self.diff_ax = self.diff_fig.subplots()

                img = self.diff_ax.imshow(heatmap_diff, cmap='viridis', alpha=1.0, clim=(0,3), interpolation='bilinear')
                divider = make_axes_locatable(self.diff_ax)
                cax = divider.append_axes("right", size="5%", pad=0.05)  # colorbar의 크기 및 간격 설정
                self.diff_fig.colorbar(img, ax=self.diff_ax, orientation='vertical', cax=cax)

                self.diff_ax.set_axis_off()
                self.diff_fig.tight_layout()
                self.diff_canvas.draw()


                file_name = "{0}-{1}.{2}".format(self.selected_file_2.split(".")[0], self.selected_file_1.split(".")[0], self.selected_file_2.split(".")[1])
                print(file_name)


                if not os.path.exists(os.path.join(self.save_directory, "Diff_" + file_name)):
                    self.diff_fig.savefig(os.path.join(self.save_directory, "Diff_" + file_name))
                else:
                    pass



            except Exception as e:
                print(f"오류 발생: {e}")

    def calc_heatmap(self, binary_image, bi_img_resize):
        # --- 2.calc heatmap :  격자별 1의 비율 계산 후 density 계산 (1이 기준임)
        grid_size = (int(binary_image.shape[0] / self.grid_scale), int(binary_image.shape[1] / self.grid_scale))

        hematmap_ratio = []
        heatmap_density = []
        for y in range(0, bi_img_resize.shape[0], self.grid_scale):
            for x in range(0, bi_img_resize.shape[1], self.grid_scale):
                grid = binary_image[y:y + self.grid_scale, x:x + self.grid_scale]

                # 히트맵 ratio 계산
                one_ratio = np.count_nonzero(grid) / (self.grid_scale ** 2)
                zero_ratio = 1 - one_ratio

                # 히트맵 밀도 계산
                # one_density = float((one_ratio - 0.040156 )/0.074642)
                one_density = float((one_ratio - 0.1142) / 0.069721)

                # 1의 비율이 높을수록 높은 수치
                hematmap_ratio.append(one_ratio)
                heatmap_density.append(one_density)

        return grid_size, hematmap_ratio, heatmap_density


    def trim_heatmapData(self, heatmap_density, bi_img_resize, heatmap_size):
      # -- density 0 ~ 3사이로 범위 정리
      heatmap_density_trim = [0 if x <= 0 else 3 if x >= 3 else x for x in heatmap_density] # 1D
      heatmap_density_mat = np.array(heatmap_density_trim).reshape(heatmap_size, heatmap_size) # 2D

      # --- 3. density 범위  정리
      perc_interp = [np.interp(perc, (0, ( self.grid_scale **2)/100), (0, 255)) for perc in heatmap_density_trim]
      # perc_interp = [np.interp(perc, (0, 3), (0, 255)) for perc in heatmap_density_trim]  #  0 <= 0, 3> = 3 / 0~3
      interp_matrix = np.array(perc_interp).reshape(heatmap_size,heatmap_size)  # 1d to 2D
      interp_matrix_resized = cv2.resize(interp_matrix, (bi_img_resize.shape[1], bi_img_resize.shape[0]))  # has float variables
      interp_matrix_resized_rgb = cv2.cvtColor(interp_matrix_resized.astype(np.uint8), cv2.COLOR_GRAY2RGB)
      interp_matrix_resized_int = interp_matrix_resized.astype(np.uint8)


      return heatmap_density_mat, interp_matrix_resized_int, interp_matrix_resized_rgb

if __name__ == "__main__":
    app = QApplication(sys.argv)
    main_window = densityEstimation()
    # main_window = densityTracking()
    main_window.show()
    sys.exit(app.exec_())