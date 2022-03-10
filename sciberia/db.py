from sqlalchemy import Column, create_engine, ForeignKey, Integer, String
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship, backref
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.future import select

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
    sop_instances = relationship("SOPInstance", backref=backref(
        "studyes", cascade="all, delete"))
    data_elements = relationship("DataElement", backref=backref(
        "sop_instances", cascade="all, delete"))
    patient_id = Column(String, ForeignKey("patients.id"))


class SOPInstance(Base):
    __tablename__ = "sop_instances"

    id = Column(Integer, primary_key=True)
    sop_instance_uid = Column("SOPInstanceUID", String)
    series_instance_uid = Column("SeriesInstanceUID", String)
    path_prefix = Column("PathPrefix", String)
    study_id = Column(String, ForeignKey("studies.id"))



class DataElement(Base):
    __tablename__ = "data_elements"

    id = Column(Integer, primary_key=True)
    series_instance_uid = Column("SeriesInstanceUID", String)
    name = Column("Name", String)
    tag = Column("Tag", String)
    value = Column("Value", String)
    study_id = Column(String, ForeignKey("studies.id"))


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
        _study = Study(
            study_instance_uid=str(study[0][0]['data'].StudyInstanceUID),
            path_prefix=filenames["path"]
        )
        for series in study:
            for sop_instance in series:
                _sop_instance = SOPInstance(
                    sop_instance_uid=str(sop_instance['data'].SOPInstanceUID),
                    series_instance_uid=str(sop_instance['data'].SeriesInstanceUID)
                )
                _study.sop_instances.append(_sop_instance)
            for data_element in series[0]['data']:
                if isinstance(data_element.private_creator, list):
                    _elem_name = "Private tag data"
                else:
                    _elem_name = data_element.name
                _data_element = DataElement(
                    series_instance_uid=str(series[0]['data'].SeriesInstanceUID),
                    name=str(_elem_name),
                    tag=str(data_element.tag),
                    value=str(data_element.repval)
                )
                _study.data_elements.append(_data_element)
        # TODO: check _patient unique condition
        #with session as asess:
        sess = session()
        q = select(Patient)
        result = sess.execute(q)
        curr = result.scalars()
        _patient = None
        for item in curr:
            if item.patient_id == str(study[0][0]['data'].PatientID) and item.patient_name == str(study[0][0]['data'].PatientName) and item.patient_birth_data == str(study[0][0]['data'].PatientBirthDate):
                _patient = item
        if _patient is None:
            if hasattr(study[0][0]['data'], "PatientSex"):
                patsex = str(study[0][0]['data'].PatientSex)
            else:
                patsex = "Unknown"
            if hasattr(study[0][0]['data'], "PatientAge"):
                patage = str(study[0][0]['data'].PatientAge)
            else:
                patage = "Unknown"
            _patient = Patient(
                patient_name=str(study[0][0]['data'].PatientName),
                patient_birth_data=str(study[0][0]['data'].PatientBirthDate),
                patient_sex=patsex,
                patient_age=patage
            )
        _patient.studies.append(_study)
        sess.add(_patient)
        sess.commit()