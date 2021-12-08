from typing import Tuple
import numpy as np
import scipy.ndimage
from pydicom.dataset import Dataset, FileMetaDataset
from pydicom.pixel_data_handlers import gdcm_handler, pillow_handler
from pydicom.uid import ImplicitVRLittleEndian, generate_uid
from pydicom._storage_sopclass_uids import SecondaryCaptureImageStorage


class Process():
    def __init__(self, data) -> None:
        self.__data = data
        self.__rgb = None
        self.__w1_min = self.__w1_max = None
        self.__w2_min = self.__w2_max = None
        self.__w3_min = self.__w3_max = None

    @property
    def rgb_windows(self) -> Tuple:
        return (
            self.__w1_min, self.__w1_max,
            self.__w2_min, self.__w2_max,
            self.__w3_min, self.__w3_max
        )

    @rgb_windows.setter
    def rgb_windows(self, *args: Tuple):
        self.__w1_min = args[0][0]
        self.__w1_max = args[0][1]
        self.__w2_min = args[0][2]
        self.__w2_max = args[0][3]
        self.__w3_min = args[0][4]
        self.__w3_max = args[0][5]

    @property
    def rgb(self):
        return self.__rgb

    def rgb_conversion(self):
        data_B = np.where(self.__data <= self.__w1_min,
                          self.__w1_min, self.__data)
        data_B = np.where(data_B >= self.__w1_max, self.__w1_min, data_B)
        data_B = (abs(data_B - self.__w1_min) /
                  abs(self.__w1_max - self.__w1_min)) * 255

        data_G = np.where(self.__data <= self.__w2_min,
                          self.__w2_min, self.__data)
        data_G = np.where(data_G >= self.__w2_max, self.__w2_min, data_G)
        data_G = (abs(data_G - self.__w2_min) /
                  abs(self.__w2_max - self.__w2_min)) * 255

        data_R = np.where(self.__data <= self.__w3_min,
                          self.__w3_min, self.__data)
        data_R = np.where(data_R >= self.__w3_max, self.__w3_min, data_R)
        data_R = (abs(data_R - self.__w3_min) /
                  abs(self.__w3_max - self.__w3_min)) * 255

        self.__rgb = np.zeros((*self.__data.shape, 3), dtype=np.uint8)
        self.__rgb[..., 0] = data_R.astype(np.uint8)
        self.__rgb[..., 1] = data_G.astype(np.uint8)
        self.__rgb[..., 2] = data_B.astype(np.uint8)

    def windowed_data(self, *args: int):
        result = np.where(self.__data <= args[0], args[0], self.__data)
        result = np.where(result >= args[1], args[1], result)
        return result

    def ct_get_pixels_hu(self, slices: np.ndarray) -> np.ndarray:
        """Get pixel data from dicom-file Dataset"""
        try:
            image = np.stack([s.pixel_array for s in slices])
        except RuntimeError:
            for slice_item in slices:
                slice_item.pixel_data_handlers = [gdcm_handler, pillow_handler]
            image = np.stack([s.pixel_array for s in slices])
        image = image.astype(np.int16)
        image[image == -2000] = 0
        for slice_number, _ in enumerate(slices):
            intercept = slices[slice_number].RescaleIntercept
            slope = slices[slice_number].RescaleSlope
            if slope != 1:
                image[slice_number] = slope * \
                    image[slice_number].astype(np.float64)
                image[slice_number] = image[slice_number].astype(np.int16)
            image[slice_number] += np.int16(intercept)
        return np.array(image, dtype=np.int16)

    def erosion(self, binary_image: np.ndarray) -> np.ndarray:
        """Morphological erosion"""
        return scipy.ndimage.binary_erosion(binary_image).astype(binary_image.dtype)

    def dilation(self, binary_image: np.ndarray) -> np.ndarray:
        """Morphological dilation"""
        return scipy.ndimage.binary_dilation(binary_image).astype(binary_image.dtype)

    def generate_sc_dataset(self, image, source_dataset, SeriesInstanceUID, number):
        meta = FileMetaDataset()
        meta.TransferSyntaxUID = ImplicitVRLittleEndian

        ds = Dataset()
        ds.file_meta = meta

        if hasattr(source_dataset, "PatientName"):
            ds.PatientName = source_dataset.PatientName
        else:
            ds.PatientName = "Unknown"

        if hasattr(source_dataset, "PatientID"):
            ds.PatientID = source_dataset.PatientID
        else:
            ds.PatientID = "Unknown"

        if hasattr(source_dataset, "PatientBirthDate"):
            ds.PatientBirthDate = source_dataset.PatientBirthDate
        else:
            ds.PatientBirthDate = "Unknown"

        if hasattr(source_dataset, "PatientSex"):
            ds.PatientSex = source_dataset.PatientSex
        else:
            ds.PatientSex = "O"

        if hasattr(source_dataset, "StudyDescription"):
            ds.StudyDescription = source_dataset.StudyDescription
        else:
            ds.StudyDescription = "default"

        ds.SeriesDescription = "SC Sciberia"
        ds.StudyInstanceUID = source_dataset.StudyInstanceUID

        if hasattr(source_dataset, "StudyDate"):
            ds.StudyDate = source_dataset.StudyDate
        else:
            ds.StudyDate = "19700101"

        if hasattr(source_dataset, "StudyTime"):
            ds.StudyTime = source_dataset.StudyTime
        else:
            ds.StudyTime = "000000"

        if hasattr(source_dataset, "ReferringPhysicianName"):
            ds.ReferringPhysicianName = source_dataset.ReferringPhysicianName
        else:
            ds.ReferringPhysicianName = None

        if hasattr(source_dataset, "StudyID"):
            ds.StudyID = source_dataset.StudyID
        else:
            ds.StudyID = None

        if hasattr(source_dataset, "AccessionNumber"):
            ds.AccessionNumber = source_dataset.AccessionNumber
        else:
            ds.AccessionNumber = None

        ds.Modality = "SC"
        ds.SeriesInstanceUID = SeriesInstanceUID
        ds.SeriesNumber = 100
        ds.ConversionType = "DF"

        ds.InstanceNumber = number

        arr = np.stack([image])
        ds.NumberOfFrames, ds.Rows, ds.Columns, ds.SamplesPerPixel = arr.shape
        ds.PhotometricInterpretation = "RGB"
        ds.BitsAllocated = 8
        ds.BitsStored = 8
        ds.HighBit = 7
        ds.PixelRepresentation = 0
        ds.PlanarConfiguration = 0
        ds.PixelData = arr.tobytes()

        ds.SOPClassUID = SecondaryCaptureImageStorage
        ds.SOPInstanceUID = generate_uid()

        return ds
