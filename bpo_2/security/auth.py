import getpass
from database.models import DatabaseManager

class AuthenticationManager:
    def __init__(self, db_manager):
        self.db_manager = db_manager
        self.current_user = None
    
    def login(self):
        """Аутентификация пользователя"""
        print("=== Аутентификация ===")
        username = input("Логин: ").strip()
        password = getpass.getpass("Пароль: ")
        
        user = self.db_manager.authenticate_user(username, password)
        if user:
            self.current_user = user
            print(f"Добро пожаловать, {user['username']}!")
            return True
        else:
            print("Неверный логин или пароль!")
            return False
    
    def register(self):
        """Регистрация нового пользователя"""
        print("=== Регистрация ===")
        username = input("Логин: ").strip()
        
        if len(username) < 3:
            print("Логин должен содержать минимум 3 символа!")
            return False
        
        password = getpass.getpass("Пароль: ")
        if len(password) < 6:
            print("Пароль должен содержать минимум 6 символов!")
            return False
        
        confirm_password = getpass.getpass("Подтвердите пароль: ")
        
        if password != confirm_password:
            print("Пароли не совпадают!")
            return False
        
        try:
            user_id = self.db_manager.create_user(username, password)
            self.current_user = {'id': user_id, 'username': username}
            print(f"Пользователь {username} успешно создан!")
            return True
        except Exception as e:
            print(f"Ошибка при создании пользователя: {e}")
            return False
    
    def get_current_user(self):
        return self.current_user