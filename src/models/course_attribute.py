"""
CourseAttribute 数据模型
表示课程的属性（一对多关系）
"""
from sqlalchemy import Column, String, Integer, ForeignKey, PrimaryKeyConstraint, Index
from . import Base
from sqlalchemy.orm import relationship


class CourseAttribute(Base):
    """课程属性表"""
    __tablename__ = 'course_attributes'
    
    # 外键：指向 courses 表
    course_id = Column(String(20), ForeignKey('courses.id'), nullable=False)
    
    # 属性值（如 "MQR", "CA-AS"）
    attribute_value = Column(String(50), nullable=False)
    
    # 属性类型描述（如 "Quantitative Literacy"）
    attribute_type = Column(String(255))
    
    # 关系：反向引用到 Course
    course = relationship("Course", back_populates="attributes")
    
    # 表级约束
    __table_args__ = (
        # 复合主键：course_id + attribute_value
        PrimaryKeyConstraint('course_id', 'attribute_value', name='pk_course_attribute'),
        # 索引：加速"查找有某 attribute 的所有课程"
        Index('idx_attribute_value', 'attribute_value'),
    )
    
    def __repr__(self):
        return f"<CourseAttribute {self.course_id}: {self.attribute_value}>"
    
    def __str__(self):
        return f"{self.attribute_value} - {self.attribute_type}"
