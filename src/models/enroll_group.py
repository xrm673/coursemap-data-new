"""
EnrollGroup 数据模型
表示课程的注册组（每学期独立，不跨学期合并）
"""
from sqlalchemy import Column, String, Integer, Float, ForeignKey, DateTime, Index
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
    
    # 学期（每个 EnrollGroup 只属于一个学期）
    semester = Column(String(10), nullable=False, index=True)
    
    # Topic（从第一个有 topicDescription 的 classSection 提取）
    # 业务用途：专业要求匹配、防止重复选同 topic、combined course 关联
    topic = Column(String(255), nullable=True, index=True)
    
    # 注册组信息
    credits_minimum = Column(Float)
    credits_maximum = Column(Float)
    grading_basis = Column(String(50))
    session_code = Column(String(10))
    
    # 时间戳
    created_at = Column(DateTime, default=datetime.now, nullable=False)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now, nullable=False)
    
    # 关系：反向引用到 Course
    course = relationship("Course", back_populates="enroll_groups")
    
    # 关系：一对多 → ClassSection
    class_sections = relationship(
        "ClassSection",
        back_populates="enroll_group",
        cascade="all, delete-orphan"
    )
    
    # 复合索引：加速 (course_id, semester) 查询
    __table_args__ = (
        Index('ix_enroll_group_course_semester', 'course_id', 'semester'),
    )
    
    def __init__(self, data, semester, topic=None):
        """
        从 API 数据初始化 EnrollGroup 对象
        
        Args:
            data: 从 Cornell API 获取的 enrollGroup 数据字典
            semester: 学期代码，如 "SP26"
            topic: topic 描述（从 classSection 提取），可为 None
        """
        self.semester = semester
        self.topic = topic
        self.credits_minimum = data.get("unitsMinimum")
        self.credits_maximum = data.get("unitsMaximum")
        self.grading_basis = data.get("gradingBasis")
        self.session_code = data.get("sessionCode")
        
        # class_sections 在外部创建和关联
        self.class_sections = []
    
    def __repr__(self):
        topic_str = f" topic={self.topic[:20]}" if self.topic else ""
        return f"<EnrollGroup {self.id}: {self.course_id} {self.semester}{topic_str}>"
    
    def __str__(self):
        topic_str = f" [{self.topic[:30]}]" if self.topic else ""
        return f"{self.session_code} ({self.credits_minimum}-{self.credits_maximum} credits){topic_str}"
