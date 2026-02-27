"""
业务逻辑层（Service）包
"""
from .api_service import APIService
from .course_service import CourseService
from .program_service import ProgramService
from .college_service import CollegeService

__all__ = ['APIService', 'CourseService', 'ProgramService', 'CollegeService']
