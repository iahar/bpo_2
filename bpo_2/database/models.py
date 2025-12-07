import sqlite3
import threading
from contextlib import contextmanager
from datetime import datetime
import bcrypt
import os
import hashlib
from config import Config

class DatabaseManager:
    def __init__(self, db_path=None):
        self.db_path = db_path or "file_manager.db"
        self._lock = threading.Lock()
    
        # Проверяем, существует ли БД, если нет - инициализируем
        if not os.path.exists(self.db_path):
            print(f"Создание новой базы данных: {self.db_path}")
            self.init_database()
        else:
            print(f"Использование существующей БД: {self.db_path}")
            # Проверяем структуру БД
            self.check_database_structure()
    
    def init_database(self):
        """Инициализация базы данных и создание таблиц"""
        conn = sqlite3.connect(self.db_path, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        try:
            # Таблица пользователей
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    username VARCHAR(50) NOT NULL UNIQUE,
                    password_hash TEXT NOT NULL,
                    user_group VARCHAR(20) DEFAULT 'users',
                    full_name TEXT,
                    home_dir TEXT DEFAULT '/',  
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
        
            # Таблица файлов
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS files (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    filename VARCHAR(255) NOT NULL,
                    file_path TEXT NOT NULL,
                    file_size INTEGER DEFAULT 0,
                    file_type VARCHAR(10) DEFAULT 'file',
                    owner_id INTEGER NOT NULL,
                    permissions VARCHAR(10) DEFAULT 'rw-r--r--',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    modified_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (owner_id) REFERENCES users (id)
                )
            ''')
        
            # Таблица операций (логи)
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS operations (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    operation_type VARCHAR(20) NOT NULL,
                    user_id INTEGER NOT NULL,
                    file_id INTEGER,
                    file_path TEXT,
                    details TEXT,
                    ip_address VARCHAR(45) DEFAULT '127.0.0.1',
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users (id),
                    FOREIGN KEY (file_id) REFERENCES files (id)
                )
            ''')

            cursor.execute('''
                CREATE TABLE IF NOT EXISTS login_attempts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    username VARCHAR(50) NOT NULL,
                    attempt_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    success BOOLEAN DEFAULT 0,
                    user_agent TEXT
                )
            ''')
        
            # Создаем представления (аналог хранимых процедур в SQLite)
            cursor.execute('''
                CREATE VIEW IF NOT EXISTS user_files AS
                SELECT f.*, u.username as owner_name 
                FROM files f 
                JOIN users u ON f.owner_id = u.id
            ''')
        
            cursor.execute('''
                CREATE VIEW IF NOT EXISTS operation_details AS
                SELECT o.*, u.username, u.user_group, f.filename
                FROM operations o
                LEFT JOIN users u ON o.user_id = u.id
                LEFT JOIN files f ON o.file_id = f.id
            ''')

            # Таблица для отслеживания попыток входа
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS login_attempts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    username VARCHAR(50) NOT NULL,
                    attempt_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    success BOOLEAN DEFAULT 0,
                    user_agent TEXT
                )
            ''')

            # Индекс для быстрого поиска
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_login_username_time ON login_attempts(username, attempt_time)')

            # Создаем начальных пользователей
            self.create_initial_users(cursor)
        
            conn.commit()
            print(f"База данных инициализирована: {self.db_path}")
        
        except Exception as e:
            conn.rollback()
            print(f"Ошибка инициализации БД: {e}")
            raise
        finally:
            conn.close()
    
    def check_database_structure(self):
        """Проверка структуры БД"""
        try:
            with self.transaction() as cursor:
                # Просто проверяем существование таблиц
                cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
                tables = cursor.fetchall()
                print(f"Найдено таблиц в БД: {len(tables)}")
        except Exception as e:
            print(f"Ошибка проверки структуры БД: {e}")
            # Если ошибка, пересоздаем БД
            os.remove(self.db_path)
            self.init_database()

    def create_stored_procedures(self, cursor):
        """Создание представлений (аналог хранимых процедур в SQLite)"""
        # Представление для получения файлов пользователя
        cursor.execute('''
            CREATE VIEW IF NOT EXISTS user_files AS
            SELECT f.*, u.username as owner_name 
            FROM files f 
            JOIN users u ON f.owner_id = u.id
        ''')
        
        # Представление для операций с деталями
        cursor.execute('''
            CREATE VIEW IF NOT EXISTS operation_details AS
            SELECT o.*, u.username, f.filename
            FROM operations o
            LEFT JOIN users u ON o.user_id = u.id
            LEFT JOIN files f ON o.file_id = f.id
        ''')
    
    def create_initial_users(self, cursor):
        """Создание начальных пользователей"""
        initial_users = [
            ('root', 'root123', 'root', 'Root Administrator', '/root'),
            ('admin', 'admin123', 'admin', 'System Administrator', '/home/admin'),
            ('user1', 'password1', 'users', 'User One', '/home/user1'),
            ('user2', 'password2', 'users', 'User Two', '/home/user2')
        ]
        
        for username, password, user_group, full_name, home_dir in initial_users:
            # Проверяем, существует ли пользователь
            cursor.execute("SELECT id FROM users WHERE username = ?", (username,))
            if not cursor.fetchone():
                password_hash = hashlib.sha256(password.encode()).hexdigest()
                cursor.execute(
                    "INSERT INTO users (username, password_hash, user_group, full_name, home_dir) VALUES (?, ?, ?, ?, ?)",
                    (username, password_hash, user_group, full_name, home_dir)
                )
    
    @contextmanager
    def transaction(self):
        """Контекстный менеджер для транзакций"""
        conn = sqlite3.connect(self.db_path, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
    
        try:
            yield cursor
            conn.commit()
        except Exception as e:
            conn.rollback()
            raise e
        finally:
            conn.close()
    
    def execute_query(self, query, params=()):
        """Безопасное выполнение запроса с параметрами"""
        conn = sqlite3.connect(self.db_path, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
    
        try:
            cursor.execute(query, params)
            result = cursor.fetchall()
            conn.commit()
            return result
        except Exception as e:
            conn.rollback()
            raise e
        finally:
            conn.close()
    
    def get_user_by_username(self, username):
        """Получить пользователя по имени"""
        query = "SELECT * FROM users WHERE username = ?"
        result = self.execute_query(query, (username,))
        return dict(result[0]) if result else None
    
    def create_user(self, username, password, full_name):
        """Создать пользователя с домашней директорией"""
        try:
            hashed_password = hashlib.sha256(password.encode()).hexdigest()
            
            # Определяем домашнюю директорию
            home_dir = f"/home/{username}"
            
            query = """
                INSERT INTO users (username, password_hash, full_name, user_group, home_dir)
                VALUES (?, ?, ?, ?, ?)
                RETURNING id, username, full_name, user_group, home_dir
            """
            
            # Используем стандартную группу для новых пользователей
            result = self.execute_query(query, (username, hashed_password, full_name, 'users', home_dir))
            
            if result:
                user = dict(result[0])
                return user
        except Exception as e:
            print(f"Ошибка при создании пользователя: {e}")
            raise

    def authenticate_user(self, username, password):
        """Аутентификация пользователя"""
        query = "SELECT * FROM users WHERE username = ?"
        result = self.execute_query(query, (username,))
        
        if result:
            user_data = dict(result[0])
            # Проверяем пароль
            hashed_password = hashlib.sha256(password.encode()).hexdigest()
            if user_data['password_hash'] == hashed_password:
                return user_data
        return None
    
    # === ПОДГОТОВЛЕННЫЕ ЗАПРОСЫ ДЛЯ ФАЙЛОВ ===
    
    def create_file_record(self, filename, file_path, file_size, file_type, owner_id, permissions='rw-r--r--'):
        """Создать запись о файле (подготовленный запрос)"""
        query = """
            INSERT INTO files (filename, file_path, file_size, file_type, owner_id, permissions) 
            VALUES (?, ?, ?, ?, ?, ?)
        """
        self.execute_query(query, (filename, file_path, file_size, file_type, owner_id, permissions))
        
        # Возвращаем созданную запись
        query = "SELECT * FROM files WHERE file_path = ?"
        result = self.execute_query(query, (file_path,))
        return dict(result[0]) if result else None
    
    def get_user_files(self, user_id):
        """Получить файлы пользователя (подготовленный запрос)"""
        query = """
            SELECT * FROM files 
            WHERE owner_id = ? 
            ORDER BY modified_at DESC
        """
        return [dict(row) for row in self.execute_query(query, (user_id,))]
    
    def update_file_size(self, file_path, new_size):
        """Обновить размер файла (подготовленный запрос)"""
        query = """
            UPDATE files 
            SET file_size = ?, modified_at = CURRENT_TIMESTAMP 
            WHERE file_path = ?
        """
        self.execute_query(query, (new_size, file_path))
    
    def delete_file_record(self, file_path, user_id):
        """Удалить запись о файле (подготовленный запрос)"""
        query = "DELETE FROM files WHERE file_path = ? AND owner_id = ?"
        self.execute_query(query, (file_path, user_id))
    
    # === ПОДГОТОВЛЕННЫЕ ЗАПРОСЫ ДЛЯ ЛОГИРОВАНИЯ ===
    
    def log_operation(self, operation_type, user_id, file_id=None, file_path=None, details=None):
        """Логирование операции (подготовленный запрос)"""
        query = """
            INSERT INTO operations (operation_type, user_id, file_id, file_path, details) 
            VALUES (?, ?, ?, ?, ?)
        """
        self.execute_query(query, (operation_type, user_id, file_id, file_path, details))

    def get_operation_logs(self, user_id=None, limit=100):
        """Получить логи операций (подготовленный запрос)"""
        if user_id:
            query = """
                SELECT * FROM operation_details 
                WHERE user_id = ? 
                ORDER BY timestamp DESC 
                LIMIT ?
            """
            return [dict(row) for row in self.execute_query(query, (user_id, limit))]
        else:
            query = "SELECT * FROM operation_details ORDER BY timestamp DESC LIMIT ?"
            return [dict(row) for row in self.execute_query(query, (limit,))]
    
    def get_disk_usage_stats(self):
        """Статистика использования дискового пространства"""
        query = """
            SELECT 
                u.username,
                COUNT(f.id) as file_count,
                SUM(f.file_size) as total_size,
                MAX(f.modified_at) as last_modified
            FROM users u
            LEFT JOIN files f ON u.id = f.owner_id
            GROUP BY u.id, u.username
        """
        return [dict(row) for row in self.execute_query(query)]