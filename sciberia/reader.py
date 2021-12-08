import errno
from itertools import groupby
import os
from pathlib import Path
import pydicom
from typing import Dict, List, Tuple


def commonprefix(args):
    return os.path.commonpath(args)


def series_projection(val):
    return val.SeriesInstanceUID


def study_projection(val):
    return val.StudyInstanceUID


class Reader():
    def __init__(self, path) -> None:
        self.__path = path
        self.__filenames = None
    
    @property
    def filenames(self) -> List:
        return self.__filenames

    def read_filenames(self) -> None:
        studies_candidates = []
        for root, _, files in os.walk(self.__path):
            scan = None
            if "DICOMDIR" in files:
                scan = {
                    "path": root,
                    "dicomdir": True
                }
            else:
                dicoms_list_candidates = self.dicoms_list_in_dir(root)
                if len(studies_candidates) > 0:
                    _sc = [item["path"] for item in studies_candidates]
                    if _sc[-1] in root:
                        continue
                if len(dicoms_list_candidates) > 0:
                    scan = {
                        "path": root,
                        "dicomdir": False
                    }
            if not scan is None:
                studies_candidates.append(scan)
        datasets = [
            {
                "data": pydicom.dcmread(os.path.join(study_candidate["path"], file), specific_tags=["StudyInstanceUID", "SeriesInstanceUID"]),
                "path": study_candidate["path"]
            }
            for study_candidate in studies_candidates if not study_candidate["dicomdir"]
            for file in os.listdir(study_candidate["path"]) if self.is_dicom(os.path.join(study_candidate["path"], file))
        ]
        groupped_studies = [
            [list(i)
             for _, i in groupby(k, lambda m: m["data"].SeriesInstanceUID)]
            for k in [list(j) for _, j in groupby(datasets, lambda m: m["data"].StudyInstanceUID)]
        ]
        dicomdir_studies_candidates = [
            i for i in studies_candidates if i["dicomdir"]]
        dcm_studies_candidates = []
        for studies in groupped_studies:
            paths = []
            for series in studies:
                for item in series:
                    paths.append(item["path"])
            dcm_studies_candidates.append({
                "path": commonprefix(paths),
                "dicomdir": False
            })
        self.__filenames = dicomdir_studies_candidates + dcm_studies_candidates

    def read_studies_generator(self, stop_before_pixels: bool = False) -> List:
        for study_struct in self.__filenames:
            datasets = []
            path = study_struct["path"]
            if study_struct["dicomdir"]:
                dicomdir = pydicom.dcmread(os.path.join(path, "DICOMDIR"))
                for patient_record in dicomdir.patient_records:
                    studies = [
                        ii for ii in patient_record.children if ii.DirectoryRecordType == "STUDY"
                    ]
                    for study in studies:
                        all_series = [
                            ii for ii in study.children if ii.DirectoryRecordType == "SERIES"
                        ]
                        for series in all_series:
                            images = [
                                ii for ii in series.children
                                if ii.DirectoryRecordType == "IMAGE"
                            ]
                            elems = [ii["ReferencedFileID"] for ii in images]
                            paths = [[ee.value] if ee.VM ==
                                    1 else ee.value for ee in elems]
                            paths = [Path(*p) for p in paths]
                            _datasets = [
                                pydicom.dcmread(os.path.join(path, image_path),
                                                stop_before_pixels=stop_before_pixels)
                                for image_path in paths
                            ]
                            datasets += _datasets
            else:
                p = Path(path)
                dicoms = [x for x in p.glob("**/*") if self.is_dicom(x)]
                datasets = [
                    pydicom.dcmread(
                        str(dicom), stop_before_pixels=stop_before_pixels)
                    for dicom in dicoms
                ]
            for data in datasets:
                if not hasattr(data, "StudyDescription"):
                    data.StudyDescription = "default"
                if not hasattr(data, "SeriesDescription"):
                    data.SeriesDescription = "default"
            groupped_studies = []
            for item in [
                list(it) for k, it in groupby(datasets, study_projection)
            ]:
                groupped_by_series = [
                    list(it) for k, it in groupby(item, series_projection)
                ]
                groupped_studies.append(groupped_by_series)
            for series in groupped_studies[0]:
                if len(series) > 1:
                    if hasattr(series[0], "ImagePositionPatient"):
                        series.sort(key=lambda x: float(
                            x.ImagePositionPatient[2]), reverse=True)
            yield groupped_studies[0]

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
