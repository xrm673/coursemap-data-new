"""
数据模型包
"""
from sqlalchemy.orm import declarative_base

# 创建 ORM 基类
Base = declarative_base()

# 导出所有模型
from .subject import Subject
from .course import Course
from .course_attribute import CourseAttribute
from .enroll_group import EnrollGroup
from .class_section import ClassSection
from .meeting import Meeting
from .instructor import Instructor
from .meeting_instructor import MeetingInstructor
from .combined_group import CombinedGroup

__all__ = [
    'Base',
    'Subject',
    'Course', 
    'CourseAttribute', 
    'EnrollGroup', 
    'ClassSection',
    'Meeting',
    'Instructor',
    'MeetingInstructor',
    'CombinedGroup'
]
