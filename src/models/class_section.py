"""
ClassSection 数据模型
表示具体的课程 section（复合主键：classNbr + roster）
"""
from sqlalchemy import Column, String, Integer, ForeignKey, Date, Boolean, Text, PrimaryKeyConstraint
from sqlalchemy.orm import relationship
from datetime import datetime
from . import Base


class ClassSection(Base):
    """课程 Section 表"""
    __tablename__ = 'class_sections'
    
    # 复合主键：classNbr + roster
    class_nbr = Column(Integer, nullable=False)
    roster = Column(String(10), nullable=False)
    
    # 外键：指向 enroll_groups 表
    enroll_group_id = Column(Integer, ForeignKey('enroll_groups.id'), nullable=False, index=True)
    
    # Section 基本信息
    section_name = Column(String(6))  # "LEC001", "DIS202"
    section_type = Column(String(3))  # "LEC", "DIS", "LAB"
    section_number = Column(String(3))  # "001", "202"
    campus = Column(String(10))  # "MAIN", "NYT"
    location = Column(String(20))  # "ITH", "NYCTECH"
    start_date = Column(Date)  # 课程开始日期
    end_date = Column(Date)  # 课程结束日期
    add_consent = Column(String(5))  # "N", "D", "I"
    is_component_graded = Column(Boolean)  # true/false
    instruction_mode = Column(String(10))  # "P", "IS", "HY"
    section_topic = Column(Text)  # 主题描述
    open_status = Column(String(5))  # "O", "C", "W"
    
    # 关系：反向引用到 EnrollGroup
    enroll_group = relationship("EnrollGroup", back_populates="class_sections")
    
    # 关系：一对多 → Meeting
    meetings = relationship(
        "Meeting",
        back_populates="class_section",
        cascade="all, delete-orphan"
    )
    
    # 表级约束
    __table_args__ = (
        PrimaryKeyConstraint('class_nbr', 'roster', name='pk_class_section'),
    )
    
    def __init__(self, data, roster):
        """
        从 API 数据初始化 ClassSection 对象
        
        Args:
            data: 从 Cornell API 获取的 classSection 数据字典
            roster: 学期代码，如 "SP26"
        """
        self.roster = roster
        self.class_nbr = data.get("classNbr")
        self.section_type = data.get("ssrComponent")
        self.section_number = data.get("section")
        self.section_name = self.section_type + self.section_number
        self.campus = data.get("campus")
        self.location = data.get("location")
        self.add_consent = data.get("addConsent")
        self.is_component_graded = data.get("isComponentGraded")
        self.instruction_mode = data.get("instructionMode")
        self.section_topic = data.get("topicDescription")
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
        return f"<ClassSection {self.class_nbr} ({self.roster}): {self.section_type} {self.section_number}>"
    
    def __str__(self):
        return f"{self.section_type} {self.section_number} - {self.open_status}"
