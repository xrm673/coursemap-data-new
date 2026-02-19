"""
Cornell API 调用服务
"""
import requests


class APIService:
    """Cornell 课程 API 调用类"""
    
    BASE_URL = "https://classes.cornell.edu/api/2.0"
    
    def __init__(self):
        self.session = requests.Session()
    
    def fetch_subjects(self, roster):
        """
        从 Cornell API 获取所有 subject
        
        Args:
            roster: 学期代码，如 "SP26"
        
        Returns:
            list: subject 数据列表，如果失败返回空列表
        """
        url = f"{self.BASE_URL}/config/subjects.json"
        params = {'roster': roster}
        
        try:
            print(f"正在获取 {roster} 的所有 Subject...")
            response = self.session.get(url, params=params, timeout=30)
            response.raise_for_status()
            
            data = response.json()
            
            if data.get('status') == 'success':
                subjects = data.get('data', {}).get('subjects', [])
                print(f"✓ 成功获取 {len(subjects)} 个 Subject")
                return subjects
            else:
                print(f"✗ API 返回错误: {data.get('message', '未知错误')}")
                return []
                
        except requests.exceptions.RequestException as e:
            print(f"✗ 网络请求失败: {e}")
            return []
        except ValueError as e:
            print(f"✗ JSON 解析失败: {e}")
            return []
    
    def fetch_courses(self, semester, subject):
        """
        从 Cornell API 获取课程数据
        
        Args:
            semester: 学期代码，如 "SP26"
            subject: 学科代码，如 "MATH"
        
        Returns:
            list: 课程数据列表，如果失败返回空列表
        """
        url = f"{self.BASE_URL}/search/classes.json"
        params = {
            'roster': semester,
            'subject': subject
        }
        
        try:
            print(f"正在获取 {semester} {subject} 的课程数据...")
            response = self.session.get(url, params=params, timeout=30)
            response.raise_for_status()
            
            data = response.json()
            
            if data.get('status') == 'success':
                classes = data.get('data', {}).get('classes', [])
                print(f"✓ 成功获取 {len(classes)} 门课程")
                return classes
            else:
                print(f"✗ API 返回错误: {data.get('message', '未知错误')}")
                return []
                
        except requests.exceptions.RequestException as e:
            print(f"✗ 网络请求失败: {e}")
            return []
        except ValueError as e:
            print(f"✗ JSON 解析失败: {e}")
            return []
