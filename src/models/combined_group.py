"""
CombinedGroup 数据模型
表示组合在一起的课程组（Combined Courses）
"""
from sqlalchemy import Column, Integer, String, DateTime
from sqlalchemy.orm import relationship
from datetime import datetime
from . import Base


class CombinedGroup(Base):
    """Combined Course Group 表"""
    __tablename__ = 'combined_groups'
    
    # 主键
    id = Column(Integer, primary_key=True, autoincrement=True)
    
    # 学期（方便按学期查询和管理）
    semester = Column(String(10), nullable=False, index=True)
    
    # 时间戳
    created_at = Column(DateTime, default=datetime.now, nullable=False)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now, nullable=False)
    
    # 关系：一对多 → EnrollGroup
    enroll_groups = relationship(
        "EnrollGroup",
        back_populates="combined_group",
        lazy='select'
    )
    
    def __repr__(self):
        return f"<CombinedGroup {self.id} ({self.semester})>"
    
    def __str__(self):
        if self.enroll_groups:
            course_ids = [eg.course_id for eg in self.enroll_groups]
            return f"Combined: {', '.join(course_ids)}"
        return f"CombinedGroup {self.id}"
