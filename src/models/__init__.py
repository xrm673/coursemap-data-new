"""
数据模型包
"""
from sqlalchemy.orm import declarative_base

# 创建 ORM 基类
Base = declarative_base()

# 导出所有模型
from .course import Course
from .course_attribute import CourseAttribute

__all__ = ['Base', 'Course', 'CourseAttribute']
