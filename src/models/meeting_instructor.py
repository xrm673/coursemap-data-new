"""
MeetingInstructor 数据模型
表示 Meeting 和 Instructor 的多对多关系
"""
from sqlalchemy import Column, String, Integer, ForeignKey, PrimaryKeyConstraint
from sqlalchemy.orm import relationship
from . import Base


class MeetingInstructor(Base):
    """Meeting-Instructor 关系表"""
    __tablename__ = 'meeting_instructors'
    
    # 复合主键
    meeting_id = Column(Integer, ForeignKey('meetings.id', ondelete='CASCADE'), nullable=False)
    instructor_netid = Column(String(15), ForeignKey('instructors.netid'), nullable=False)
    
    # 教师顺序（用于判断"第一个教师"）
    assign_seq = Column(Integer, nullable=False)
    
    # 关系：反向引用
    meeting = relationship("Meeting", back_populates="meeting_instructors")
    instructor = relationship("Instructor", back_populates="meeting_instructors")
    
    # 表级约束
    __table_args__ = (
        PrimaryKeyConstraint('meeting_id', 'instructor_netid', name='pk_meeting_instructor'),
    )
    
    def __init__(self, instructor_netid, assign_seq):
        """
        初始化 MeetingInstructor 对象
        
        Args:
            instructor_netid: 教师的 netid
            assign_seq: 教师顺序
        """
        self.instructor_netid = instructor_netid
        self.assign_seq = assign_seq
    
    def __repr__(self):
        return f"<MeetingInstructor meeting={self.meeting_id} instructor={self.instructor_netid}>"
    
    def __str__(self):
        return f"Meeting {self.meeting_id} - {self.instructor_netid} (seq: {self.assign_seq})"
