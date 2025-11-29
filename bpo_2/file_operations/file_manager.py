import os
import shutil
import threading
from pathlib import Path
from security.path_validator import PathValidator, PathTraversalError
from config import Config
from database.models import OperationType

class FileManager:
    def __init__(self, db_operations, path_validator: PathValidator):
        self.db_operations = db_operations
        self.validator = path_validator
        self.locks = {}  # Для предотвращения race conditions
        self.lock = threading.Lock()  # Блокировка для управления доступом к locks
    
    def _get_file_lock(self, file_path: Path) -> threading.Lock:
        """Получение блокировки для файла (предотвращение race conditions)"""
        with self.lock:
            if file_path not in self.locks:
                self.locks[file_path] = threading.Lock()
            return self.locks[file_path]
    
    def list_directory(self, user_path: str = "") -> list:
        """Безопасное получение списка файлов в директории"""
        try:
            safe_path = self.validator.validate_path(user_path)
            
            if not safe_path.exists():
                raise FileNotFoundError(f"Директория {user_path} не существует")
            
            if not safe_path.is_dir():
                raise NotADirectoryError(f"{user_path} не является директорией")
            
            items = []
            for item in safe_path.iterdir():
                item_info = {
                    'name': item.name,
                    'is_dir': item.is_dir(),
                    'size': item.stat().st_size if item.is_file() else 0,
                    'modified': item.stat().st_mtime
                }
                items.append(item_info)
            
            # Логирование операции
            if self.db_operations:
                user = self.db_operations.get_current_user()
                self.db_operations.log_operation(
                    OperationType.READ, 
                    user.id, 
                    details=f"Просмотр директории: {user_path}"
                )
            
            return sorted(items, key=lambda x: (not x['is_dir'], x['name']))
        
        except (PathTraversalError, FileNotFoundError, NotADirectoryError) as e:
            raise e
    
    def read_file(self, user_path: str) -> str:
        """Безопасное чтение файла"""
        try:
            safe_path = self.validator.validate_path(user_path)
            file_lock = self._get_file_lock(safe_path)
            
            with file_lock:  # Защита от race conditions
                if not safe_path.exists():
                    raise FileNotFoundError(f"Файл {user_path} не существует")
                
                if not safe_path.is_file():
                    raise IsADirectoryError(f"{user_path} является директорией")
                
                if safe_path.stat().st_size > Config.MAX_FILE_SIZE:
                    raise ValueError("Файл слишком большой")
                
                with open(safe_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                # Логирование
                if self.db_operations:
                    user = self.db_operations.get_current_user()
                    self.db_operations.log_operation(
                        OperationType.READ, 
                        user.id, 
                        details=f"Чтение файла: {user_path}"
                    )
                
                return content
        
        except Exception as e:
            raise e
    
    def write_file(self, user_path: str, content: str) -> bool:
        """Безопасная запись в файл"""
        try:
            safe_path = self.validator.validate_path(user_path)
            file_lock = self._get_file_lock(safe_path)
            
            with file_lock:
                # Проверка размера контента
                if len(content.encode('utf-8')) > Config.MAX_FILE_SIZE:
                    raise ValueError("Содержимое файла превышает максимальный размер")
                
                # Создание родительских директорий
                safe_path.parent.mkdir(parents=True, exist_ok=True)
                
                # Атомарная запись во временный файл с последующим перемещением
                temp_path = safe_path.with_suffix('.tmp')
                
                with open(temp_path, 'w', encoding='utf-8') as f:
                    f.write(content)
                
                # Атомарная замена файла
                if safe_path.exists():
                    backup_path = safe_path.with_suffix('.bak')
                    safe_path.replace(backup_path)
                
                temp_path.replace(safe_path)
                
                # Логирование
                if self.db_operations:
                    user = self.db_operations.get_current_user()
                    op_type = OperationType.MODIFY if safe_path.exists() else OperationType.CREATE
                    self.db_operations.log_operation(
                        op_type, 
                        user.id, 
                        details=f"Запись в файл: {user_path}"
                    )
                
                return True
        
        except Exception as e:
            raise e
    
    def delete_file(self, user_path: str) -> bool:
        """Безопасное удаление файла"""
        try:
            safe_path = self.validator.validate_path(user_path)
            file_lock = self._get_file_lock(safe_path)
            
            with file_lock:
                if not safe_path.exists():
                    raise FileNotFoundError(f"Файл {user_path} не существует")
                
                if safe_path.is_file():
                    safe_path.unlink()
                else:
                    shutil.rmtree(safe_path)
                
                # Логирование
                if self.db_operations:
                    user = self.db_operations.get_current_user()
                    self.db_operations.log_operation(
                        OperationType.DELETE, 
                        user.id, 
                        details=f"Удаление: {user_path}"
                    )
                
                return True
        
        except Exception as e:
            raise e
    
    def get_disk_info(self):
        """Получение информации о дисках"""
        try:
            disk_info = []
            for partition in os.popen('df -h').read().splitlines()[1:]:
                parts = partition.split()
                if len(parts) >= 6:
                    disk_info.append({
                        'filesystem': parts[0],
                        'size': parts[1],
                        'used': parts[2],
                        'available': parts[3],
                        'use_percent': parts[4],
                        'mounted_on': parts[5]
                    })
            return disk_info
        except:
            # Альтернативная реализация для Windows
            import shutil
            base_dir = Config.BASE_DIR
            usage = shutil.disk_usage(base_dir)
            return [{
                'filesystem': 'Local',
                'size': f"{usage.total // (1024**3)}G",
                'used': f"{usage.used // (1024**3)}G", 
                'available': f"{usage.free // (1024**3)}G",
                'use_percent': f"{(usage.used / usage.total * 100):.1f}%",
                'mounted_on': str(base_dir)
            }]

    def get_current_directory(self) -> Path:
        """Получение текущей рабочей директории"""
        return self.validator.base_dir

    def change_directory(self, new_path: str) -> bool:
        """Смена текущей директории"""
        try:
            # Обработка специальных путей
            if new_path == "..":
                # Переход на уровень вверх
                parent_dir = self.validator.base_dir.parent
                # Проверяем, что не вышли за пределы базового каталога
                if parent_dir.resolve().is_relative_to(Config.BASE_DIR.resolve()):
                    safe_path = parent_dir
                else:
                    safe_path = self.validator.base_dir  # Остаемся в текущей
            elif new_path == "" or new_path == "/":
                # Переход в корневую директорию
                safe_path = Config.BASE_DIR
            else:
                # Обычный путь
                safe_path = self.validator.validate_path(new_path)
        
            if not safe_path.exists():
                raise FileNotFoundError(f"Директория {new_path} не существует")
        
            if not safe_path.is_dir():
                raise NotADirectoryError(f"{new_path} не является директорией")
        
            # Обновляем базовый каталог валидатора
            self.validator.base_dir = safe_path
        
            # Логирование
            if self.db_operations and hasattr(self.db_operations, 'log_operation'):
                user = self.db_operations.get_current_user()
                if user:
                    self.db_operations.log_operation(
                        OperationType.READ, 
                        user['id'], 
                        details=f"Смена директории на: {new_path}"
                    )
        
            return True
    
        except Exception as e:
            raise e

    def get_parent_directory(self) -> Path:
        """Получение родительской директории"""
        current_dir = self.validator.base_dir
        parent_dir = current_dir.parent
    
        # Проверяем, что не вышли за пределы базового каталога
        if parent_dir.resolve().is_relative_to(self.validator.base_dir.resolve()):
            return parent_dir
        else:
            return current_dir  # Остаемся в текущей директории