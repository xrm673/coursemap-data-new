"""
Instructor 数据模型
表示课程教师（主键：netid）
"""
from sqlalchemy import Column, String, DateTime
from sqlalchemy.orm import relationship
from datetime import datetime
from . import Base


class Instructor(Base):
    """教师表"""
    __tablename__ = 'instructors'
    
    # 主键：netid
    netid = Column(String(15), primary_key=True)
    
    # 教师信息
    first_name = Column(String(50))
    middle_name = Column(String(50))
    last_name = Column(String(50))
    
    # 时间戳
    created_at = Column(DateTime, default=datetime.now, nullable=False)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now, nullable=False)
    
    # 关系：多对多 → Meeting (通过 MeetingInstructor)
    meeting_instructors = relationship(
        "MeetingInstructor",
        back_populates="instructor"
    )
    
    def __init__(self, data):
        """
        从 API 数据初始化 Instructor 对象
        
        Args:
            data: 从 Cornell API 获取的 instructor 数据字典
        """
        self.netid = data.get("netid")
        self.first_name = data.get("firstName")
        self.middle_name = data.get("middleName", "")
        self.last_name = data.get("lastName")
    
    def __repr__(self):
        return f"<Instructor {self.netid}: {self.first_name} {self.last_name}>"
    
    def __str__(self):
        full_name = f"{self.first_name} {self.last_name}"
        return full_name.strip()
