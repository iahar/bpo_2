# -*- coding: utf-8 -*-
import os
from pathlib import Path

class Config:
    # Базовые настройки
    BASE_DIR = Path("/safe_directory")  # Базовый каталог для работы
    MAX_FILE_SIZE = 100 * 1024 * 1024  # 100MB максимальный размер файла
    MAX_ZIP_SIZE = 500 * 1024 * 1024  # 500MB максимальный размер распакованного ZIP
    
    # Настройки базы данных
    DB_TYPE = "sqlite"  # "postgresql", "mysql", или "sqlite"
    DB_HOST = "localhost"
    DB_PORT = 5432
    DB_NAME = "file_manager"
    DB_USER = "file_manager_user"
    DB_PASSWORD = "secure_password"
    
    # Настройки безопасности
    SESSION_TIMEOUT = 3600  # 1 час
    
    @classmethod
    def init_directories(cls):
        """Инициализация необходимых директорий"""
        # Для тестирования используем текущую директорию
        if cls.BASE_DIR == Path("/safe_directory"):
            cls.BASE_DIR = Path.cwd() / "safe_directory"
        
        cls.BASE_DIR.mkdir(exist_ok=True, parents=True)
        print(f"Базовый каталог: {cls.BASE_DIR}")