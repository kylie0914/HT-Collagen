import os,sys
import cv2
import numpy as np
from tkinter import filedialog
from tkinter import Tk
from scipy.fft import fft2, ifft2, fftshift
import matplotlib.pyplot as plt
import pickle


# Helper function to get input from user using tkinter
def get_directory():
    root = Tk()
    root.withdraw()  # Hide the root window
    folder_selected = filedialog.askdirectory(title="Choose a folder containing the image sequence")
    return folder_selected


def tiff16bit_to_np8bit(tiff_image_16bit):
    if tiff_image_16bit.dtype == np.uint16:
        min_val = np.min(tiff_image_16bit)
        max_val = np.max(tiff_image_16bit)
        np_image_8bit = ((tiff_image_16bit - min_val) / (max_val - min_val) * 255).astype(np.uint8)
        return np_image_8bit
    else:
        min_val = np.min(tiff_image_16bit)
        max_val = np.max(tiff_image_16bit)
        np_image_8bit = ((tiff_image_16bit - min_val) / (max_val - min_val) * 255).astype(np.uint8)
        return np_image_8bit


input_format = ".png"
# input_format = ".tiff"
inputpath = get_directory()

if inputpath:
    files = sorted([f for f in os.listdir(inputpath) if f.endswith(input_format)])
    files.sort(key=lambda x: float(x.strip('im_0 (').strip(').png').strip('.jpg')))
    nFrames = len(files)

    if nFrames == 0:
        print("No image files found in the directory.")
        exit()

    drift_y = np.zeros(nFrames)
    drift_x = np.zeros(nFrames)

    # Get reference frame (first one in the sequence)
    imageref = cv2.imread(os.path.join(inputpath, files[0]), cv2.IMREAD_UNCHANGED)

    if imageref.dtype == np.uint16: # tif format
        min_val = np.min(imageref)
        max_val = np.max(imageref)
        np_image_8bit = ((imageref - min_val) / (max_val - min_val) * 255).astype(np.uint8)
    else:   # 8-bit format
        min_val = np.min(imageref)
        max_val = np.max(imageref)
        np_image_8bit = ((imageref - min_val) / (max_val - min_val) * 255).astype(np.uint8)


    imageref_crop, rect = plt.imshow(np_image_8bit, cmap='gray'), plt.ginput(2)

    # Fix: Unpack and create rect correctly with proper ordering
    (x1, y1), (x2, y2) = plt.ginput(2)
    rect = (min(int(x1), int(x2)), min(int(y1), int(y2)), abs(int(x2 - x1)), abs(int(y2 - y1)))

    # Check if the crop size is valid
    if rect[2] <= 0 or rect[3] <= 0:
        raise ValueError(f"Invalid crop area: width = {rect[2]}, height = {rect[3]}")

    imageref_crop = imageref[rect[1]:rect[1] + rect[3], rect[0]:rect[0] + rect[2]]

    fft_ref = fft2(imageref_crop)
    vidHeight, vidWidth = imageref_crop.shape
    centery, centerx = (vidHeight // 2, vidWidth // 2)

    for i, filename in enumerate(files):
        imagei = cv2.imread(os.path.join(inputpath, filename), cv2.IMREAD_UNCHANGED)
        if imagei.dtype == np.uint16:  # for tif
            min_val = np.min(imagei)
            max_val = np.max(imagei)
            imagei_8bit = ((imagei - min_val) / (max_val - min_val) * 255).astype(np.uint8)
        else:                           #  8-bit (png)
            min_val = np.min(imagei)
            max_val = np.max(imagei)
            imagei_8bit = ((imagei - min_val) / (max_val - min_val) * 255).astype(np.uint8)

        imagei_crop = imagei_8bit[rect[1]:rect[1] + rect[3], rect[0]:rect[0] + rect[2]]
        fft_frame = fft2(imagei_crop)

        prod = fft_ref * np.conj(fft_frame)
        cc = ifft2(prod)
        cc_shifted = fftshift(cc)

        maxy, maxx = np.unravel_index(np.argmax(cc_shifted), cc_shifted.shape)

        drift_y[i] = maxy - centery
        drift_x[i] = maxx - centerx

        if i > 0:
            if abs(drift_y[i] - drift_y[i - 1]) > vidHeight / 2:
                drift_y[i] -= np.sign(drift_y[i] - drift_y[i - 1]) * vidHeight
            if abs(drift_x[i] - drift_x[i - 1]) > vidWidth / 2:
                drift_x[i] -= np.sign(drift_x[i] - drift_x[i - 1]) * vidWidth

    # --- save
    savepath = os.path.join(inputpath, "drift_corr" )
    if not os.path.exists(savepath):
        os.makedirs(savepath)


    shiftdatafilename = os.path.join(savepath, f"{files[0].split('.')[0]}_driftdata.pkl")
    with open(shiftdatafilename, 'wb') as f:
        pickle.dump({'nFrames': nFrames, 'drift_y': drift_y, 'drift_x': drift_x}, f)
    print(f"I finished calculating the drift data. It was saved to: {shiftdatafilename}")

    # Apply drift correction and save shifted images
    for i, filename in enumerate(files):
        imagei = cv2.imread(os.path.join(inputpath, filename), cv2.IMREAD_UNCHANGED)

        if imagei.dtype == np.uint16:
            min_val = np.min(imagei)
            max_val = np.max(imagei)
            imagei_8bit = ((imagei - min_val) / (max_val - min_val) * 255).astype(np.uint8)

        else:                           #  8-bit (png)
            min_val = np.min(imagei)
            max_val = np.max(imagei)
            imagei_8bit = ((imagei - min_val) / (max_val - min_val) * 255).astype(np.uint8)


        shifted_image = np.roll(imagei_8bit, int(drift_y[i]), axis=0)
        shifted_image = np.roll(shifted_image, int(drift_x[i]), axis=1)
        cv2.imwrite(os.path.join(savepath, f"im_{i}.png"), shifted_image)

    print("Drift correction completed and images saved.")
