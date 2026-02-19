"""
Subject 数据模型
表示学科（如 INFO, CS, MATH）
"""
from sqlalchemy import Column, String, DateTime
from sqlalchemy.orm import relationship
from datetime import datetime
from . import Base


class Subject(Base):
    """学科表"""
    __tablename__ = 'subjects'
    
    # 主键：subject code
    value = Column(String(10), primary_key=True)  # "INFO"
    
    # 描述
    description = Column(String(100), nullable=False)  # "Information Science"
    description_formal = Column(String(100), nullable=False)  # "Information Science"
    
    # 时间戳
    created_at = Column(DateTime, default=datetime.now, nullable=False)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now, nullable=False)
    
    # 关系：一对多 → Course
    courses = relationship("Course", back_populates="subject_info")
    
    def __repr__(self):
        return f"<Subject {self.value}: {self.description}>"
    
    def __str__(self):
        return f"{self.value} - {self.description}"
