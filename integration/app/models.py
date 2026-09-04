from sqlalchemy import Column, Integer, String
from .db import Base


class PrintJob(Base):
    __tablename__ = "print_jobs"

    id = Column(Integer, primary_key=True, index=True)
    printer_id = Column(Integer)
    job_id = Column(String, unique=True)
    status = Column(String)