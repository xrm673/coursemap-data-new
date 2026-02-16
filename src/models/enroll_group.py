"""
EnrollGroup 数据模型
表示课程的注册组（跨学期合并）
"""
from sqlalchemy import Column, String, Integer, ForeignKey, DateTime, Text
from sqlalchemy.orm import relationship
from datetime import datetime
from . import Base


class EnrollGroup(Base):
    """课程注册组表"""
    __tablename__ = 'enroll_groups'
    
    # 主键：自增ID
    id = Column(Integer, primary_key=True, autoincrement=True)
    
    # 外键：指向 courses 表
    course_id = Column(String(20), ForeignKey('courses.id'), nullable=False, index=True)
    
    # 匹配信息（用于判断不同学期的 EnrollGroup 是否相同）
    matching_type = Column(String(20), nullable=False, index=True)  # "topic", "instructor", "section_name"
    matching_key = Column(Text, nullable=False)  # 具体的匹配值
    
    # 注册组信息
    credits_minimum = Column(Integer)
    credits_maximum = Column(Integer)
    grading_basis = Column(String(50))
    session_code = Column(String(10))
    
    # 追踪字段：记录该 EnrollGroup 最后开设的学期
    last_offered_semester = Column(String(10), nullable=True, index=True)
    last_offered_year = Column(Integer, nullable=True, index=True)
    
    # 时间戳
    created_at = Column(DateTime, default=datetime.now, nullable=False)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now, nullable=False)
    
    # 关系：反向引用到 Course
    course = relationship("Course", back_populates="enroll_groups")
    
    # 关系：一对多 → EnrollGroupSemester
    semesters = relationship(
        "EnrollGroupSemester",
        back_populates="enroll_group",
        cascade="all, delete-orphan"
    )
    
    # 关系：一对多 → ClassSection
    class_sections = relationship(
        "ClassSection",
        back_populates="enroll_group",
        cascade="all, delete-orphan"
    )
    
    def __init__(self, data, matching_type, matching_key):
        """
        从 API 数据初始化 EnrollGroup 对象
        
        Args:
            data: 从 Cornell API 获取的 enrollGroup 数据字典
            matching_type: 匹配类型 ("topic", "instructor", "section_name")
            matching_key: 匹配值
        """
        self.matching_type = matching_type
        self.matching_key = matching_key
        self.credits_minimum = data.get("unitsMinimum")
        self.credits_maximum = data.get("unitsMaximum")
        self.grading_basis = data.get("gradingBasis")
        self.session_code = data.get("sessionCode")
        
        # 注意：class_sections 和 semesters 在外部创建和关联
        self.class_sections = []
        self.semesters = []
    
    def update_from_data(self, data):
        """
        从 API 数据更新 EnrollGroup 字段（覆盖）
        
        Args:
            data: 从 Cornell API 获取的 enrollGroup 数据字典
        """
        self.credits_minimum = data.get("unitsMinimum")
        self.credits_maximum = data.get("unitsMaximum")
        self.grading_basis = data.get("gradingBasis")
        self.session_code = data.get("sessionCode")
    
    def __repr__(self):
        return f"<EnrollGroup {self.id}: {self.course_id} [{self.matching_type}]>"
    
    def __str__(self):
        return f"{self.session_code} ({self.credits_minimum}-{self.credits_maximum} credits) [{self.matching_type}={self.matching_key[:30]}...]"
