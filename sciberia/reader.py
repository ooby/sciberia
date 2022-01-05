from itertools import groupby
import os
import nrrd
from pathlib import Path
from pydicom import dcmread
from pydicom.fileset import FileSet
from pydicom.dicomdir import DicomDir
from typing import List, Tuple


def commonprefix(args):
    return os.path.commonpath(args)


def series_projection(val):
    return val.SeriesInstanceUID


def study_projection(val):
    return val.StudyInstanceUID


def load_nrrd(files_path, nrrd_filename):
    fname = os.path.join(files_path, nrrd_filename)
    nrrd_data, nrrd_header = nrrd.read(fname)
    return nrrd_data, nrrd_header


def walk(path):
    for p in Path(path).iterdir():
        if p.is_dir():
            yield from walk(p)
            continue
        yield p.resolve()


class Reader():
    def __init__(self, path) -> None:
        self.__path = path
        __dicomdirs = []
        __filedatasets_datas = []
        for p in walk(Path(self.__path)):
            if self.is_dicom(p):
                __ds = dcmread(p, stop_before_pixels=True)
                if isinstance(__ds, DicomDir):
                    __dicomdirs.append({
                        "path": FileSet(__ds).path,
                        "dicomdir": True
                    })
                else:
                    if hasattr(__ds, "StudyInstanceUID"):
                        __filedatasets_datas.append({
                            "data": __ds,
                            "path": p
                        })
        __groupped_filedatasets = [
            [
                list(i) for _, i in groupby(k, lambda m: m["data"].SeriesInstanceUID)
            ]
            for k in [list(j) for _, j in groupby(__filedatasets_datas, lambda m: m["data"].StudyInstanceUID)]
        ]
        __dcm_studies = []
        for studies in __groupped_filedatasets:
            paths = []
            for series in studies:
                for item in series:
                    paths.append(item["path"])
            __path = commonprefix(paths)
            __continue = False
            for pp in [p["path"] for p in __dicomdirs]:
                if pp in __path:
                    __continue = True
            if __continue:
                continue
            else:
                __struct = {
                    "path": __path,
                    "dicomdir": False
                }
                __nrrds = [str(nc.name) for nc in Path(__path).glob("*.nrrd")]
                if len(__nrrds) > 0:
                    __struct["nrrd"] = __nrrds
                __dcm_studies.append(__struct)
        self.__filenames = __dicomdirs + __dcm_studies

    @property
    def filenames(self) -> List:
        return self.__filenames

    def read_datasets_generator(self, stop_before_pixels: bool = False) -> List:
        for study_struct in self.__filenames:
            datasets = []
            path = study_struct["path"]
            if study_struct["dicomdir"]:
                dicomdir = dcmread(os.path.join(path, "DICOMDIR"))
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
                                dcmread(os.path.join(path, image_path),
                                        stop_before_pixels=stop_before_pixels)
                                for image_path in paths
                            ]
                            datasets += _datasets
            else:
                p = Path(path)
                dicoms = [x for x in p.glob("**/*") if self.is_dicom(x)]
                datasets = [
                    dcmread(
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
            nrrd_set = []
            if "nrrd" in study_struct and len(study_struct["nrrd"]) > 0:
                for item in study_struct["nrrd"]:
                    nrrd_data, nrrd_header = load_nrrd(
                        study_struct["path"], item)
                    nrrd_set.append({
                        str(item): {
                            "header": nrrd_header,
                            "data": nrrd_data
                        }
                    })
            yield {
                "dataset": groupped_studies[0],
                "nrrd": nrrd_set
            }

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
