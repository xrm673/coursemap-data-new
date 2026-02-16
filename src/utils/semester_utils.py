"""
学期代码解析和比较工具函数

学期格式：两位季节代码 + 两位年份
- WI26: Winter 2026
- SP26: Spring 2026
- SU26: Summer 2026
- FA25: Fall 2025

学期顺序：... < FA25 < WI26 < SP26 < SU26 < FA26 < WI27 < ...
"""


def parse_semester(semester_code: str) -> tuple:
    """
    解析学期代码为可比较的元组
    
    Args:
        semester_code: 学期代码，如 "WI26", "SP26", "SU26", "FA25"
    
    Returns:
        tuple: (year, season_order)
            - year: 完整年份 (2026)
            - season_order: 季节顺序 (0=WI, 1=SP, 2=SU, 3=FA)
    
    Raises:
        ValueError: 如果学期代码格式不正确
    
    Examples:
        >>> parse_semester("WI26")
        (2026, 0)
        >>> parse_semester("SP26")
        (2026, 1)
        >>> parse_semester("FA25")
        (2025, 3)
    """
    if not isinstance(semester_code, str) or len(semester_code) != 4:
        raise ValueError(f"Invalid semester format: {semester_code}. Expected format: XX##")
    
    season = semester_code[:2].upper()
    year_suffix = semester_code[2:]
    
    # 验证年份部分是数字
    if not year_suffix.isdigit():
        raise ValueError(f"Invalid year in semester: {semester_code}")
    
    # 转换为完整年份（假设 00-99 对应 2000-2099）
    year = 2000 + int(year_suffix)
    
    # 季节顺序映射
    season_order = {
        "WI": 0,  # Winter - 年初
        "SP": 1,  # Spring
        "SU": 2,  # Summer
        "FA": 3,  # Fall - 年末
    }
    
    if season not in season_order:
        raise ValueError(
            f"Invalid season: {season}. Must be one of: WI, SP, SU, FA"
        )
    
    return (year, season_order[season])


def extract_year(semester_code: str) -> int:
    """
    从学期代码提取年份
    
    Args:
        semester_code: 学期代码，如 "SP26"
    
    Returns:
        int: 完整年份
    
    Examples:
        >>> extract_year("SP26")
        2026
        >>> extract_year("FA25")
        2025
    """
    year, _ = parse_semester(semester_code)
    return year


def compare_semesters(sem1: str, sem2: str) -> int:
    """
    比较两个学期的先后顺序
    
    Args:
        sem1: 第一个学期代码
        sem2: 第二个学期代码
    
    Returns:
        int: 
            -1 如果 sem1 < sem2 (sem1 更早)
             0 如果 sem1 == sem2 (相同)
             1 如果 sem1 > sem2 (sem1 更晚)
    
    Examples:
        >>> compare_semesters("FA25", "SP26")
        -1
        >>> compare_semesters("SP26", "SP26")
        0
        >>> compare_semesters("FA26", "SP26")
        1
    """
    parsed1 = parse_semester(sem1)
    parsed2 = parse_semester(sem2)
    
    if parsed1 < parsed2:
        return -1
    elif parsed1 > parsed2:
        return 1
    else:
        return 0


def is_earlier(sem1: str, sem2: str) -> bool:
    """
    判断 sem1 是否早于 sem2
    
    Args:
        sem1: 第一个学期代码
        sem2: 第二个学期代码
    
    Returns:
        bool: True 如果 sem1 < sem2
    
    Examples:
        >>> is_earlier("FA25", "SP26")
        True
        >>> is_earlier("SP26", "FA25")
        False
    """
    return compare_semesters(sem1, sem2) < 0


def is_later(sem1: str, sem2: str) -> bool:
    """
    判断 sem1 是否晚于 sem2
    
    Args:
        sem1: 第一个学期代码
        sem2: 第二个学期代码
    
    Returns:
        bool: True 如果 sem1 > sem2
    
    Examples:
        >>> is_later("SP26", "FA25")
        True
        >>> is_later("FA25", "SP26")
        False
    """
    return compare_semesters(sem1, sem2) > 0


def is_earlier_or_equal(sem1: str, sem2: str) -> bool:
    """
    判断 sem1 是否早于或等于 sem2
    
    Args:
        sem1: 第一个学期代码
        sem2: 第二个学期代码
    
    Returns:
        bool: True 如果 sem1 <= sem2
    """
    return compare_semesters(sem1, sem2) <= 0


def is_later_or_equal(sem1: str, sem2: str) -> bool:
    """
    判断 sem1 是否晚于或等于 sem2
    
    Args:
        sem1: 第一个学期代码
        sem2: 第二个学期代码
    
    Returns:
        bool: True 如果 sem1 >= sem2
    
    Examples:
        >>> is_later_or_equal("SP26", "SP26")
        True
        >>> is_later_or_equal("FA26", "SP26")
        True
    """
    return compare_semesters(sem1, sem2) >= 0


def validate_semester(semester_code: str) -> bool:
    """
    验证学期代码格式是否正确
    
    Args:
        semester_code: 学期代码
    
    Returns:
        bool: True 如果格式正确，False 否则
    
    Examples:
        >>> validate_semester("SP26")
        True
        >>> validate_semester("XX99")
        False
    """
    try:
        parse_semester(semester_code)
        return True
    except ValueError:
        return False
