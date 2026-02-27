"""
ClassSection 数据模型
表示具体的课程 section（主键：自增 id）
"""
from sqlalchemy import Column, String, Integer, ForeignKey, Date, Boolean, Text, Index, UniqueConstraint, DateTime
from sqlalchemy.orm import relationship
from datetime import datetime
from . import Base


class ClassSection(Base):
    """课程 Section 表"""
    __tablename__ = 'class_sections'
    
    # 主键：自增 ID
    id = Column(Integer, primary_key=True, autoincrement=True)
    
    # 外键：指向 enroll_groups 表
    enroll_group_id = Column(Integer, ForeignKey('enroll_groups.id'), nullable=False, index=True)
    
    # 匹配标识：section_number（在同一个 EnrollGroup 下唯一）
    section_number = Column(String(10), nullable=False)
    
    # API 数据字段
    class_nbr = Column(Integer, nullable=False)
    semester = Column(String(10), nullable=False)
    
    # Section 基本信息
    section_type = Column(String(10))  # "LEC", "DIS", "LAB"
    campus = Column(String(10))  # "MAIN", "NYT"
    location = Column(String(20))  # "ITH", "NYCTECH"
    start_date = Column(Date)  # 课程开始日期
    end_date = Column(Date)  # 课程结束日期
    add_consent = Column(String(5))  # "N", "D", "I"
    is_component_graded = Column(Boolean)  # true/false
    instruction_mode = Column(String(10))  # "P", "IS", "HY"
    section_topic = Column(Text)  # 主题描述
    
    # 频繁更新的字段
    open_status = Column(String(5))  # "O", "C", "W"
    
    # 时间戳
    created_at = Column(DateTime, default=datetime.now, nullable=False)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now, nullable=False)
    
    # 关系：反向引用到 EnrollGroup
    enroll_group = relationship("EnrollGroup", back_populates="class_sections")
    
    # 关系：一对多 → Meeting
    meetings = relationship(
        "Meeting",
        back_populates="class_section",
        cascade="all, delete-orphan"
    )

    # 关系：一对多 → UserCourseSection
    user_course_sections = relationship(
        "UserCourseSection",
        back_populates="class_section"
    )
    
    # 表级约束
    __table_args__ = (
        # 唯一约束：在同一个 EnrollGroup 下，section_number 唯一
        UniqueConstraint('enroll_group_id', 'section_number', name='uq_eg_section'),
        # 索引：方便通过 class_nbr + semester 查询
        Index('ix_class_nbr_semester', 'class_nbr', 'semester'),
    )
    
    def __init__(self, data, semester):
        """
        从 API 数据初始化 ClassSection 对象
        
        Args:
            data: 从 Cornell API 获取的 classSection 数据字典
            semester: 学期代码，如 "SP26"
        """
        self.semester = semester
        self.class_nbr = data.get("classNbr")
        self.section_type = data.get("ssrComponent")
        self.section_number = data.get("section")
        self.campus = data.get("campus")
        self.location = data.get("location")
        self.add_consent = data.get("addConsent")
        self.is_component_graded = data.get("isComponentGraded")
        self.instruction_mode = data.get("instructionMode")
        self.section_topic = data.get("topicDescription") or None
        self.open_status = data.get("openStatus")
        
        # 解析日期字段
        self.start_date = self._parse_date(data.get("startDt"))
        self.end_date = self._parse_date(data.get("endDt"))
    
    def _parse_date(self, date_str):
        """
        解析日期字符串 "01/20/2026" 为 Date 对象
        
        Args:
            date_str: 日期字符串
            
        Returns:
            datetime.date 对象或 None
        """
        if not date_str:
            return None
        try:
            # API 返回格式：MM/DD/YYYY
            return datetime.strptime(date_str, "%m/%d/%Y").date()
        except (ValueError, AttributeError):
            return None
    
    def __repr__(self):
        return f"<ClassSection {self.id}: {self.section_type} {self.section_number} ({self.semester})>"
    
    def __str__(self):
        return f"{self.section_type} {self.section_number} - {self.open_status}"
