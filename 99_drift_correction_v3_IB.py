import os
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


# Ask for input file format
def get_input_format():
    print("What is your input file format? (PNG, TIF, Movie)")
    input_format = input().strip().lower()
    if input_format == "png":
        return "png"
    elif input_format == "tif":
        return "tiff"
    else:
        print("Invalid format, assuming 'png'.")
        return "png"


# Step 1: Calculate shift x,y pairs for each frame
input_format = get_input_format()
inputpath = get_directory()

if inputpath:
    files = [f for f in os.listdir(inputpath) if f.endswith(input_format)]
    nFrames = len(files)

    if nFrames == 0:
        print("No image files found in the directory.")
        exit()

    drift_y = np.zeros(nFrames)
    drift_x = np.zeros(nFrames)

    # Get reference frame (first one in the sequence)
    imageref = cv2.imread(os.path.join(inputpath, files[0]), cv2.IMREAD_UNCHANGED)
    print(imageref.dtype)
    if imageref.dtype == np.uint16:
        # Normalize the 16-bit image to 8-bit range
        # converted_image = cv2.convertScaleAbs(tiff_image, alpha=(255.0/65535.0))
        min_val = np.min(imageref)
        max_val = np.max(imageref)
        np_image_8bit = ((imageref - min_val) / (max_val - min_val) * 255).astype(np.uint8)

    # imageref_adjusted = cv2.normalize(imageref, None, 0, 255, cv2.NORM_MINMAX)
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
        if imagei.dtype == np.uint16:
            # Normalize the 16-bit image to 8-bit range
            # converted_image = cv2.convertScaleAbs(tiff_image, alpha=(255.0/65535.0))
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
                print("haha")
                drift_y[i] -= np.sign(drift_y[i] - drift_y[i - 1]) * vidHeight
            if abs(drift_x[i] - drift_x[i - 1]) > vidWidth / 2:
                print("huhu")
                drift_x[i] -= np.sign(drift_x[i] - drift_x[i - 1]) * vidWidth

            print(int(drift_y[i]))
            print(int(drift_x[i]))

    # Save results to file
    # shiftdatafilename = os.path.join(inputpath, f"{files[0].split('.')[0]}_driftdata.pkl")
    shiftdatafilename = os.path.join(inputpath, f"{files[0].split('.')[0]}_driftdata.pkl")
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

        shifted_image = np.roll(imagei_8bit, int(drift_y[i]), axis=0)
        shifted_image = np.roll(shifted_image, int(drift_x[i]), axis=1)
        cv2.imwrite(os.path.join(inputpath, f"im_{i}.tiff"), shifted_image)

    print("Drift correction completed and images saved.")
