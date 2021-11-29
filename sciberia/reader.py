import errno
import os
import pydicom
from typing import Dict, List, Tuple


class Reader():
    def __init__(self) -> None:
        pass

    def checkpath(self, path: str) -> None:
        """Check path for existing"""
        if not os.path.exists(path):
            try:
                os.makedirs(path, exist_ok=True)
            except OSError as exc:
                if exc.errno != errno.EEXIST:
                    raise

    def get_uids(self, path: str) -> Tuple[str, str]:
        """Get StudyInstanceUID and SeriesInstanceUID, no pixel data"""
        study_data = pydicom.read_file(path, stop_before_pixels=True)
        return study_data.StudyInstanceUID, study_data.SeriesInstanceUID

    def is_dicom(self, path: str) -> bool:
        """Check file whether dicom-file or not"""
        if not os.path.isfile(path):
            return False
        try:
            with open(path, "rb") as file_name:
                return file_name.read(132).decode("ASCII")[-4:] == "DICM"
        except UnicodeDecodeError:
            return False

    def dicoms_list_in_dir(self, path: str = ".") -> List[str]:
        """Forms list of dicom-files in directory"""
        path = os.path.expanduser(path)
        candidates = [os.path.join(path, f) for f in sorted(os.listdir(path))]
        return [f for f in candidates if self.is_dicom(f)]

    def is_dicomdir(self, path: str = ".") -> Tuple[bool, str]:
        """Find first DICOMDIR in subdirectories"""
        dicomdir = False
        for root, _, files in os.walk(path):
            if "DICOMDIR" in files:
                return True, root
        if not dicomdir:
            return False, path

    def batch_reader(self, scanpath: str) -> List[Dict]:
        """Recursively read files and subdirectories to find dicom-file collections"""
        scans = []
        for root, _, files in os.walk(scanpath):
            dicoms_list_candidates = self.dicoms_list_in_dir(root)
            scan = {}
            if len(dicoms_list_candidates) > 0:
                scan["nrrd"] = [file for file in files if ".nrrd" in file]
                scan["path"] = root
                scans.append(scan)
        return scans

    def dicomdir_reader(self, path: str) -> List:
        """Read dicomdir"""
        dicomdir = self.read_dicomdir(os.path.join(path, "DICOMDIR"))
        datasets = []
        for patient_record in dicomdir.patient_records:
            studies = patient_record.children
            for study in studies:
                all_series = study.children
                for series in all_series:
                    if "SeriesDescription" not in series:
                        series.SeriesDescription = "default"
                    image_records = [child for child in series.children]
                    image_filenames = [os.path.join(
                        path, *image_rec.ReferencedFileID) for image_rec in image_records]
                    dataset = [pydicom.dcmread(image_filename)
                               for image_filename in image_filenames]
                    datasets.append(dataset)
        datasets = datasets[0]
        return datasets
