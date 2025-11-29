from sqlalchemy import text
from .models import get_session, User, File, Operation, OperationType
import bcrypt
from datetime import datetime

class DatabaseOperations:
    def __init__(self, session):
        self.session = session
    
    # === БЕЗОПАСНЫЕ ОПЕРАЦИИ С ИСПОЛЬЗОВАНИЕМ ПОДГОТОВЛЕННЫХ ЗАПРОСОВ ===
    
    def create_user(self, username: str, password: str) -> User:
        """Создание пользователя с хешированием пароля"""
        password_hash = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
        
        # Используем подготовленный запрос для предотвращения SQL-инъекций
        stmt = text("""
            INSERT INTO users (username, password_hash) 
            VALUES (:username, :password_hash)
            RETURNING id
        """)
        
        result = self.session.execute(stmt, {
            'username': username,
            'password_hash': password_hash
        })
        user_id = result.scalar()
        
        self.session.commit()
        return self.get_user_by_id(user_id)
    
    def authenticate_user(self, username: str, password: str) -> User:
        """Аутентификация пользователя"""
        stmt = text("SELECT id, username, password_hash FROM users WHERE username = :username")
        result = self.session.execute(stmt, {'username': username})
        user_data = result.fetchone()
        
        if user_data and bcrypt.checkpw(password.encode('utf-8'), user_data[2].encode('utf-8')):
            return self.get_user_by_id(user_data[0])
        return None
    
    def get_user_by_id(self, user_id: int) -> User:
        """Получение пользователя по ID"""
        return self.session.get(User, user_id)
    
    def log_operation(self, operation_type: OperationType, user_id: int, 
                     file_id: int = None, details: str = None):
        """Логирование операции пользователя"""
        stmt = text("""
            INSERT INTO operations (operation_type, user_id, file_id, details)
            VALUES (:operation_type, :user_id, :file_id, :details)
        """)
        
        self.session.execute(stmt, {
            'operation_type': operation_type.value,
            'user_id': user_id,
            'file_id': file_id,
            'details': details
        })
        self.session.commit()
    
    def create_file_record(self, filename: str, size: int, location: str, owner_id: int) -> File:
        """Создание записи о файле в базе данных"""
        stmt = text("""
            INSERT INTO files (filename, size, location, owner_id)
            VALUES (:filename, :size, :location, :owner_id)
            RETURNING id
        """)
        
        result = self.session.execute(stmt, {
            'filename': filename,
            'size': size,
            'location': location,
            'owner_id': owner_id
        })
        file_id = result.scalar()
        self.session.commit()
        
        return self.session.get(File, file_id)
    
    def get_user_files(self, user_id: int):
        """Получение файлов пользователя"""
        stmt = text("""
            SELECT id, filename, created_at, size, location 
            FROM files 
            WHERE owner_id = :user_id
            ORDER BY created_at DESC
        """)
        
        return self.session.execute(stmt, {'user_id': user_id}).fetchall()
    
    def delete_file_record(self, file_id: int, user_id: int):
        """Удаление записи о файле"""
        stmt = text("DELETE FROM files WHERE id = :file_id AND owner_id = :user_id")
        self.session.execute(stmt, {'file_id': file_id, 'user_id': user_id})
        self.session.commit()
