import os
from pathlib import Path
from urllib.parse import unquote
from config import Config

class PathTraversalError(Exception):
    """Исключение для обхода путей"""
    pass

class PathValidator:
    def __init__(self, base_dir: Path):
        self.base_dir = base_dir.resolve()  # Абсолютный путь
    
    def validate_path(self, user_path: str) -> Path:
        """Валидация пути для предотвращения Path Traversal"""
        if not user_path or user_path.strip() == "":
            raise PathTraversalError("Путь не может быть пустым")
        
        # Декодирование URL-encoded путей
        decoded_path = unquote(user_path)
        
        # Очистка пути от потенциально опасных последовательностей
        clean_path = self.sanitize_path(decoded_path)
        
        # Создание полного пути
        full_path = (self.base_dir / clean_path).resolve()
        
        # Проверка, что путь находится внутри базового каталога
        if not full_path.is_relative_to(self.base_dir):
            raise PathTraversalError(f"Доступ к пути вне {self.base_dir} запрещен")
        
        return full_path
    
    def sanitize_path(self, path: str) -> str:
        """Очистка пути от потенциально опасных последовательностей"""
        # Удаление ../, ./, ~ и других опасных конструкций
        dangerous_sequences = ['../', './', '~', '//', '\\\\']
        clean_path = path
        
        for seq in dangerous_sequences:
            clean_path = clean_path.replace(seq, '')
        
        # Удаление ведущих и завершающих точек и слэшей
        clean_path = clean_path.strip('./\\')
        
        return clean_path
    
    def is_safe_filename(self, filename: str) -> bool:
        """Проверка безопасности имени файла"""
        dangerous_chars = ['/', '\\', ':', '*', '?', '"', '<', '>', '|']
        return not any(char in filename for char in dangerous_chars)

    def set_base_dir(self, new_base_dir: Path):
        """Установка нового базового каталога"""
        self.base_dir = new_base_dir.resolve()

    def validate_path(self, user_path: str) -> Path:
        """Валидация пути для предотвращения Path Traversal"""
        if not user_path or user_path.strip() == "":
            return self.base_dir
    
        # Декодирование URL-encoded путей
        decoded_path = unquote(user_path)
    
        # Очистка пути от потенциально опасных последовательностей
        clean_path = self.sanitize_path(decoded_path)
    
        # Обработка специальных случаев
        if clean_path == "..":
            parent = self.base_dir.parent
            # Проверяем, что не выходим за пределы базового каталога
            if parent.resolve().is_relative_to(Config.BASE_DIR.resolve()):
                return parent
            else:
                return self.base_dir
    
        # Создание полного пути
        full_path = (self.base_dir / clean_path).resolve()
    
        # Проверка, что путь находится внутри базового каталога
        if not full_path.is_relative_to(Config.BASE_DIR):
            raise PathTraversalError(f"Доступ к пути вне {Config.BASE_DIR} запрещен")
    
        return full_path