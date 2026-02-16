"""
Meeting 数据模型
表示课程的具体上课时间和地点
"""
from sqlalchemy import Column, String, Integer, ForeignKey, Date, DateTime, ForeignKeyConstraint
from sqlalchemy.orm import relationship
from datetime import datetime
from . import Base


class Meeting(Base):
    """上课时间表"""
    __tablename__ = 'meetings'
    
    # 主键：自增ID
    id = Column(Integer, primary_key=True, autoincrement=True)
    
    # 外键：指向 class_sections 表（复合外键）
    class_section_class_nbr = Column(Integer, nullable=False)
    class_section_roster = Column(String(10), nullable=False)
    
    # Meeting 信息
    time_start = Column(String(10))  # "09:05AM"
    time_end = Column(String(10))    # "09:55AM"
    pattern = Column(String(10))     # "TR" (Tuesday, Thursday)
    start_date = Column(Date)        # 开始日期
    end_date = Column(Date)          # 结束日期
    
    # 时间戳
    created_at = Column(DateTime, default=datetime.now, nullable=False)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now, nullable=False)
    
    # 关系：反向引用到 ClassSection
    class_section = relationship("ClassSection", back_populates="meetings")
    
    # 关系：多对多 → Instructor (通过 MeetingInstructor)
    meeting_instructors = relationship(
        "MeetingInstructor",
        back_populates="meeting",
        cascade="all, delete-orphan"
    )
    
    # 表级约束：复合外键（添加级联删除）
    __table_args__ = (
        ForeignKeyConstraint(
            ['class_section_class_nbr', 'class_section_roster'],
            ['class_sections.class_nbr', 'class_sections.roster'],
            name='fk_meeting_class_section',
            ondelete='CASCADE'  # 当 ClassSection 被删除时，自动删除相关的 Meetings
        ),
    )
    
    def __init__(self, data):
        """
        从 API 数据初始化 Meeting 对象
        
        Args:
            data: 从 Cornell API 获取的 meeting 数据字典
        """
        self.time_start = data.get("timeStart")
        self.time_end = data.get("timeEnd")
        self.pattern = data.get("pattern")
        
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
        return f"<Meeting {self.id}: {self.pattern} {self.time_start}-{self.time_end}>"
    
    def __str__(self):
        return f"{self.pattern} {self.time_start}-{self.time_end}"
