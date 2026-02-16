"""
Course 数据模型
使用 SQLAlchemy ORM 定义
"""
from sqlalchemy import Column, String, Integer, Text
from sqlalchemy.orm import relationship
from . import Base


class Course(Base):
    """课程表"""
    __tablename__ = 'courses'
    
    # 主键：subject + catalogNbr
    id = Column(String(20), primary_key=True)
    
    # 基本信息
    subject = Column(String(10), nullable=False)
    number = Column(String(10), nullable=False)
    level = Column(Integer, nullable=False)
    title_short = Column(String(255))
    title_long = Column(Text)
    description = Column(Text)
    enrollment_priority = Column(Text)
    forbidden_overlaps = Column(Text)
    prereq = Column(Text)
    coreq = Column(Text)
    fee = Column(Text)
    acad_career = Column(String(255))
    acad_group = Column(String(255))
    
    # 关系：一对多 → CourseAttribute
    attributes = relationship(
        "CourseAttribute",
        back_populates="course",
        cascade="all, delete-orphan"  # 删除课程时自动删除所有 attributes
    )
    
    # 关系：一对多 → EnrollGroup
    enroll_groups = relationship(
        "EnrollGroup",
        back_populates="course",
        cascade="all, delete-orphan"  # EnrollGroup 只属于一个 Course，可以级联删除
    )
    
    def __init__(self, data, semester):
        """
        从 API 数据初始化 Course 对象
        
        Args:
            data: 从 Cornell API 获取的课程数据字典
            semester: 学期代码，如 "SP26"
        """
        self.id = data["subject"] + data["catalogNbr"]
        self.subject = data["subject"]
        self.number = data["catalogNbr"]
        self.title_short = data["titleShort"]
        self.title_long = data["titleLong"]
        self.description = data.get("description", "")  # 有些课程可能没有描述
        self.enrollment_priority = data.get("catalogEnrollmentPriority", "")
        self.forbidden_overlaps = data.get("catalogForbiddenOverlaps", "")
        self.prereq = data.get("catalogPrereq", "")
        self.coreq = data.get("catalogCoreq", "")
        self.fee = data.get("catalogFee", "")
        self.acad_career = data.get("acadCareer", "")
        self.acad_group = data.get("acadGroup", "")
        
        # 计算课程级别（从 catalogNbr 第一位提取）
        try:
            self.level = int(data["catalogNbr"][0])
        except (ValueError, IndexError):
            self.level = 0
        
        # 处理课程属性（一对多关系）
        self.attributes = []
        crse_attrs = data.get("crseAttrs", [])
        if crse_attrs:
            from .course_attribute import CourseAttribute
            for attr in crse_attrs:
                # 跳过没有 crseAttrValue 的记录（复合主键必需）
                attr_value = attr.get("crseAttrValue", "").strip()
                if not attr_value:
                    continue
                
                # attrDescrShort 可以为空
                attr_type = attr.get("attrDescrShort", "")
                
                course_attr = CourseAttribute(
                    attribute_value=attr_value,
                    attribute_type=attr_type if attr_type else None
                )
                self.attributes.append(course_attr)
        
        # 注意：enroll_groups 不在此处创建
        # 现在由 CourseService 负责创建和匹配 EnrollGroups
        self.enroll_groups = []
    
    def __repr__(self):
        return f"<Course {self.id}: {self.title_short}>"
    
    def __str__(self):
        return f"{self.id} - {self.title_short}"
