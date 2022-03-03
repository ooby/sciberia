from sqlalchemy import Column, create_engine, ForeignKey, Integer, String
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship, backref
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy.orm import sessionmaker

engine = create_engine('sqlite:///database.db')
Base = declarative_base()


class Patient(Base):
    __tablename__ = "patients"

    id = Column(Integer, primary_key=True)
    patient_id = Column("PatientID", String)
    patient_name = Column("PatientName", String)
    patient_birth_data = Column("PatientBirthDate", String)
    patient_sex = Column("PatientSex", String)
    patient_age = Column("PatientAge", String)
    studies = relationship("Study", backref=backref(
        "patients", cascade="all, delete"))


class Study(Base):
    __tablename__ = "studies"

    id = Column(Integer, primary_key=True)
    study_instance_uid = Column("StudyInstanceUID", String)
    path_prefix = Column("PathPrefix", String)
    series = relationship("Series", backref=backref(
        "studies", cascade="all, delete"))
    patient_id = Column(String, ForeignKey("patients.id"))


class Series(Base):
    __tablename__ = "series"

    id = Column(Integer, primary_key=True)
    series_instance_uid = Column("SeriesInstanceUID", String)
    path_prefix = Column("PathPrefix", String)
    sop_instances = relationship("SOPInstance", backref=backref(
        "series", cascade="all, delete"))
    study_id = Column(String, ForeignKey("studies.id"))


class SOPInstance(Base):
    __tablename__ = "sop_instances"

    id = Column(Integer, primary_key=True)
    sop_instance_uid = Column("SOPInstanceUID", String)
    path_prefix = Column("PathPrefix", String)
    data_elements = relationship("DataElement", backref=backref(
        "sop_instances", cascade="all, delete"))
    series_id = Column(String, ForeignKey("series.id"))


class DataElement(Base):
    __tablename__ = "data_elements"

    id = Column(Integer, primary_key=True)
    name = Column("Name", String)
    tag = Column("Tag", String)
    value = Column("Value", String)
    sop_instance_id = Column(String, ForeignKey("sop_instances.id"))


class Send(Base):
    __tablename__ = "sended_data"

    id = Column(Integer, primary_key=True)
    series_instance_uid = Column(String)
    api_uid = Column(String)

class DB():
    def db_create_all(self):
        Base.metadata.create_all(engine)


    def db_drop_all(self):
        Base.metadata.drop_all(engine)


    def db_session(self):
        engine = create_engine("sqlite:///database.db")
        Base.metadata.bind = engine
        return sessionmaker(bind=engine)


    def async_session(self):
        engine = create_async_engine("sqlite+aiosqlite:///database.db")
        return sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)


    def fetch_db_data(self, db_study_collection):
        sess = db_session()
        session = sess()
        db_studies = session.query(Study).all()
        if len(db_studies) == 0:
            return db_study_collection
        for db_study in db_studies:
            db_study_filenames = unified_read_filenames(db_study.path_prefix)
            db_study_data = read_study(db_study_filenames)
            db_study_collection.append(db_study_data)
        return db_study_collection


    def db_write(self, session, study, filenames):
        # TODO: add path prefixes to Series, SOPInstance models and filenames to SOPInstance model
        print(study)
        _study = Study(
            study_instance_uid=str(study[0][0].StudyInstanceUID),
            path_prefix=filenames["path"]
        )
        for series in study:
            _series = Series(
                series_instance_uid=str(series[0].SeriesInstanceUID)
            )
            for sop_instance in series:
                _sop_instance = SOPInstance(
                    sop_instance_uid=str(sop_instance.SOPInstanceUID),
                )
                for data_element in sop_instance:
                    if isinstance(data_element.private_creator, list):
                        _elem_name = "Private tag data"
                    else:
                        _elem_name = data_element.name
                    _data_element = DataElement(
                        name=str(_elem_name),
                        tag=str(data_element.tag),
                        value=str(data_element.repval)
                    )
                    _sop_instance.data_elements.append(_data_element)
                _series.sop_instances.append(_sop_instance)
            _study.series.append(_series)
        # TODO: check _patient unique condition
        with session as asess:
            q = select(Patient)
            result = asess.execute(q)
            curr = result.scalars()
            _patient = None
            for item in curr:
                if item.patient_id == str(study[0][0].PatientID) and item.patient_name == str(study[0][0].PatientName) and item.patient_birth_data == str(study[0][0].PatientBirthDate):
                    _patient = item
        if _patient is None:
            if hasattr(study[0][0], "PatientSex"):
                patsex = str(study[0][0].PatientSex)
            else:
                patsex = "Unknown"
            if hasattr(study[0][0], "PatientAge"):
                patage = str(study[0][0].PatientAge)
            else:
                patage = "Unknown"
            _patient = Patient(
                patient_name=str(study[0][0].PatientName),
                patient_birth_data=str(study[0][0].PatientBirthDate),
                patient_sex=patsex,
                patient_age=patage
            )
        _patient.studies.append(_study)
        session.add(_patient)
        session.commit()
