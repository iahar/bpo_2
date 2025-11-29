import json
import defusedxml.ElementTree as ET
from defusedxml.common import DefusedXmlException
from file_operations.file_manager import FileManager

class JSONXMLHandler:
    def __init__(self, file_manager: FileManager):
        self.file_manager = file_manager
    
    def read_json(self, file_path: str):
        """Безопасное чтение JSON файла"""
        content = self.file_manager.read_file(file_path)
        
        try:
            # Безопасная десериализация JSON
            return json.loads(content)
        except json.JSONDecodeError as e:
            raise ValueError(f"Некорректный JSON формат: {e}")
    
    def write_json(self, file_path: str, data: dict) -> bool:
        """Безопасная запись JSON файла"""
        try:
            # Валидация данных перед записью
            if not isinstance(data, (dict, list)):
                raise ValueError("JSON данные должны быть словарем или списком")
            
            content = json.dumps(data, ensure_ascii=False, indent=2)
            return self.file_manager.write_file(file_path, content)
        
        except Exception as e:
            raise e
    
    def read_xml(self, file_path: str):
        """Безопасное чтение XML файла с использованием defusedxml"""
        content = self.file_manager.read_file(file_path)
        
        try:
            # Безопасный парсинг XML (защита от XXE и других атак)
            root = ET.fromstring(content)
            return self._xml_to_dict(root)
        
        except DefusedXmlException as e:
            raise ValueError(f"Обнаружена потенциально опасная XML конструкция: {e}")
        except ET.ParseError as e:
            raise ValueError(f"Некорректный XML формат: {e}")
    
    def write_xml(self, file_path: str, data: dict, root_tag: str = "root") -> bool:
        """Безопасная запись XML файла"""
        try:
            root = ET.Element(root_tag)
            self._dict_to_xml(root, data)
            
            # Безопасная сериализация XML
            xml_content = ET.tostring(root, encoding='unicode', method='xml')
            return self.file_manager.write_file(file_path, xml_content)
        
        except Exception as e:
            raise e
    
    def _xml_to_dict(self, element):
        """Рекурсивное преобразование XML в словарь"""
        result = {}
        
        for child in element:
            if len(child) == 0:
                result[child.tag] = child.text
            else:
                result[child.tag] = self._xml_to_dict(child)
        
        return result
    
    def _dict_to_xml(self, parent, data):
        """Рекурсивное преобразование словаря в XML"""
        for key, value in data.items():
            if isinstance(value, dict):
                child = ET.SubElement(parent, key)
                self._dict_to_xml(child, value)
            else:
                child = ET.SubElement(parent, key)
                child.text = str(value)