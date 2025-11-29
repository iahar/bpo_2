import sqlite3
import bcrypt
from datetime import datetime
from config import Config
import enum

class OperationType(enum.Enum):
    CREATE = "create"
    MODIFY = "modify" 
    DELETE = "delete"
    READ = "read"

class DatabaseManager:
    def __init__(self):
        self.connection = None
        self.connect()
        self.create_tables()
    
    def connect(self):
        """Установка соединения с базой данных"""
        if Config.DB_TYPE == "sqlite":
            self.connection = sqlite3.connect('file_manager.db', check_same_thread=False)
        else:
            # Для других БД можно добавить позже
            raise NotImplementedError("Поддерживается только SQLite для демонстрации")
    
    def create_tables(self):
        """Создание таблиц"""
        cursor = self.connection.cursor()
        
        # Таблица пользователей
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username VARCHAR(50) NOT NULL UNIQUE,
                password_hash TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Таблица файлов
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS files (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                filename VARCHAR(255) NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                size INTEGER,
                location VARCHAR(255),
                owner_id INTEGER REFERENCES users(id)
            )
        ''')
        
        # Таблица операций
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS operations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                operation_type TEXT NOT NULL,
                file_id INTEGER REFERENCES files(id),
                user_id INTEGER REFERENCES users(id),
                details TEXT
            )
        ''')
        
        self.connection.commit()
    
    def execute_query(self, query, params=()):
        """Безопасное выполнение запроса с параметрами"""
        cursor = self.connection.cursor()
        cursor.execute(query, params)
        return cursor
    
    def create_user(self, username, password):
        """Создание пользователя с хешированием пароля"""
        password_hash = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
        
        cursor = self.execute_query(
            "INSERT INTO users (username, password_hash) VALUES (?, ?)",
            (username, password_hash)
        )
        self.connection.commit()
        return cursor.lastrowid
    
    def authenticate_user(self, username, password):
        """Аутентификация пользователя"""
        cursor = self.execute_query(
            "SELECT id, username, password_hash FROM users WHERE username = ?",
            (username,)
        )
        user_data = cursor.fetchone()
        
        if user_data and bcrypt.checkpw(password.encode('utf-8'), user_data[2].encode('utf-8')):
            return {'id': user_data[0], 'username': user_data[1]}
        return None
    
    def get_user_by_id(self, user_id):
        """Получение пользователя по ID"""
        cursor = self.execute_query(
            "SELECT id, username FROM users WHERE id = ?",
            (user_id,)
        )
        user_data = cursor.fetchone()
        if user_data:
            return {'id': user_data[0], 'username': user_data[1]}
        return None
    
    def log_operation(self, operation_type, user_id, file_id=None, details=None):
        """Логирование операции"""
        self.execute_query(
            "INSERT INTO operations (operation_type, user_id, file_id, details) VALUES (?, ?, ?, ?)",
            (operation_type.value, user_id, file_id, details)
        )
        self.connection.commit()
    
    def create_file_record(self, filename, size, location, owner_id):
        """Создание записи о файле"""
        cursor = self.execute_query(
            "INSERT INTO files (filename, size, location, owner_id) VALUES (?, ?, ?, ?)",
            (filename, size, location, owner_id)
        )
        self.connection.commit()
        return cursor.lastrowid
    
    def get_user_files(self, user_id):
        """Получение файлов пользователя"""
        cursor = self.execute_query(
            "SELECT id, filename, created_at, size, location FROM files WHERE owner_id = ? ORDER BY created_at DESC",
            (user_id,)
        )
        return cursor.fetchall()
    
    def delete_file_record(self, file_id, user_id):
        """Удаление записи о файле"""
        self.execute_query(
            "DELETE FROM files WHERE id = ? AND owner_id = ?",
            (file_id, user_id)
        )
        self.connection.commit()