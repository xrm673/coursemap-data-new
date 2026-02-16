"""
EnrollGroupSemester 数据模型
表示 EnrollGroup 在哪些学期出现（一对多关系）
"""
from sqlalchemy import Column, String, Integer, ForeignKey, DateTime, PrimaryKeyConstraint
from sqlalchemy.orm import relationship
from datetime import datetime
from . import Base


class EnrollGroupSemester(Base):
    """EnrollGroup-Semester 关系表"""
    __tablename__ = 'enroll_group_semesters'
    
    # 复合主键
    enroll_group_id = Column(Integer, ForeignKey('enroll_groups.id'), nullable=False)
    semester = Column(String(10), nullable=False)  # "SP26", "FA26"
    
    # 时间戳
    created_at = Column(DateTime, default=datetime.now, nullable=False)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now, nullable=False)
    
    # 关系：反向引用到 EnrollGroup
    enroll_group = relationship("EnrollGroup", back_populates="semesters")
    
    # 表级约束
    __table_args__ = (
        PrimaryKeyConstraint('enroll_group_id', 'semester', name='pk_enroll_group_semester'),
    )
    
    def __init__(self, semester):
        """
        初始化 EnrollGroupSemester 对象
        
        Args:
            semester: 学期代码，如 "SP26"
        """
        self.semester = semester
    
    def __repr__(self):
        return f"<EnrollGroupSemester group={self.enroll_group_id} semester={self.semester}>"
    
    def __str__(self):
        return f"Group {self.enroll_group_id} - {self.semester}"
