import os
import json
import xml.etree.ElementTree as ET
import zipfile
import shutil
import getpass
import platform
import hashlib
import time
import sqlite3
from datetime import datetime
from database.models import DatabaseManager
from database.operations import SecureDBOperations

class UserManager:
    def __init__(self):
        self.db = DatabaseManager()
        self.current_user = None
        self.max_attempts = 6
        self.lockout_time = 300
        self.delay_time = 2
    
        # Проверяем и создаем таблицу login_attempts если её нет
        self.ensure_login_attempts_table()

    def ensure_login_attempts_table(self):
        """Убедиться, что таблица login_attempts существует"""
        try:
            # Просто пытаемся выполнить запрос к таблице
            test_query = "SELECT COUNT(*) FROM login_attempts"
            self.db.execute_query(test_query)
            print("✓ Таблица login_attempts существует")
        except sqlite3.OperationalError:
            print("✗ Таблица login_attempts не найдена, создаем...")
            self.create_login_attempts_table()
        except Exception as e:
            print(f"Ошибка проверки таблицы login_attempts: {e}")

           
    def get_user_home_dir(self, username):
        """Получить домашнюю директорию пользователя"""
        if not username:
            return '/'
        return f"/home/{username}"
    
    def create_home_directory(self, username, user_group='users'):
        """Создать домашнюю директорию для нового пользователя"""
        if not username:
            return False
        
        home_path = f"/home/{username}"
        return True

    def create_login_attempts_table(self):
        """Создать таблицу login_attempts"""
        try:
            # Вместо прямого подключения к SQLite, используем существующий DatabaseManager
            conn = sqlite3.connect(self.db.db_path, check_same_thread=False)
            cursor = conn.cursor()
        
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS login_attempts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    username VARCHAR(50) NOT NULL,
                    attempt_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    success BOOLEAN DEFAULT 0,
                    user_agent TEXT
                )
            ''')
        
            cursor.execute('''
                CREATE INDEX IF NOT EXISTS idx_login_username_time 
                ON login_attempts(username, attempt_time)
            ''')
        
            conn.commit()
            conn.close()
            print("✓ Таблица login_attempts создана")
        except Exception as e:
            print(f"Ошибка создания таблицы login_attempts: {e}")

    def get_all_users(self):
        """Получить всех пользователей из БД"""
        try:
            query = "SELECT * FROM users ORDER BY username"
            result = self.db.execute_query(query)
            return [dict(row) for row in result]
        except Exception as e:
            print(f"Ошибка получения пользователей: {e}")
            return []

    def hash_password(self, password):
        """Хеширование пароля"""
        return hashlib.sha256(password.encode()).hexdigest()

    def authenticate(self, username, password):
        """Аутентификация пользователя с защитой от brute-force"""
        print(f"Попытка входа для пользователя: {username}")

        # 1. Проверяем, существует ли пользователь
        existing_user = self.db.get_user_by_username(username)
        if not existing_user:
            print(f"Ошибка: Пользователь '{username}' не существует")
            return False     
    
        # 5. Пробуем аутентифицировать
        user = self.db.authenticate_user(username, password)
    
        if user:
            # УСПЕШНЫЙ ВХОД
            self.current_user = user
            # Убедимся, что у пользователя есть home_dir
            if 'home_dir' not in self.current_user or not self.current_user['home_dir']:
                self.current_user['home_dir'] = f"/home/{username}"
            self.log_login_attempt(username, True, "Login successful")
            print(f"Аутентификация успешна для {username}")
            return True
        else:
            # НЕУДАЧНЫЙ ВХОД
            # Получаем обновленное количество попыток
            failed_attempts = self.get_failed_attempts_count(username)
            remaining = max(0, self.max_attempts - failed_attempts)

            # Проверяем количество неудачных попыток
            failed_attempts = self.get_failed_attempts_count(username) 
            print(f"Неудачных попыток за 15 минут: {failed_attempts}")

            # Если превышен лимит - блокируем
            if failed_attempts >= self.max_attempts:
                print(f" Учетная запись '{username}' заблокирована!")
                print(f" Превышено {self.max_attempts} неудачных попыток.")
                self.log_login_attempt(username, False, "Аккаунт заблокирован.")
                return False 

            self.log_login_attempt(username, False, "Invalid credentials")
            
            print(f"Неверный пароль для пользователя {username}")
            print(f"Осталось попыток: {remaining}")
        
            if remaining <= 0:
                print(f"Учетная запись заблокирована!")
        
            # Добавляем задержку если есть неудачные попытки
            if failed_attempts > 0:
                delay = self.delay_time * failed_attempts
                print(f"Задержка {delay} секунд...")
                time.sleep(delay)

            return False

    def register_user(self):
        """Регистрация нового пользователя в БД"""
        print("\n=== РЕГИСТРАЦИЯ ===")
        username = input("Введите имя пользователя: ").strip()
        
        # Проверяем существует ли пользователь в БД
        existing = self.db.get_user_by_username(username)  # ← ИЗМЕНИТЬ
        if existing:
            print("Ошибка: Пользователь уже существует")
            return False
        
        password = getpass.getpass("Введите пароль: ").strip()
        confirm_password = getpass.getpass("Подтвердите пароль: ").strip()
        full_name = input("Введите полное имя: ").strip()
        
        if not username or not password:
            print("Ошибка: Имя пользователя и пароль не могут быть пустыми")
            return False
        
        if password != confirm_password:
            print("Ошибка: Пароли не совпадают")
            return False
        
        try:
            user = self.db.create_user(username, password, full_name) 
            if user:
                self.current_user = user
                print(f"Пользователь {username} успешно зарегистрирован")
                return True
        except Exception as e:
            print(f"Ошибка при создании пользователя: {e}")
        return False

    def get_username(self):
        """Получить имя текущего пользователя как строку"""
        if not self.current_user:
            return None
        
        if isinstance(self.current_user, dict):
            return self.current_user.get('username')
        else:
            return str(self.current_user)
    
    def get_user_group(self):
        """Получить группу текущего пользователя"""
        if not self.current_user:
            return 'users'
        
        user_info = self.get_current_user_info()
        if user_info:
            return user_info.get('user_group', 'users')
        
        return 'users'
    
    def get_user_id(self):
        """Получить ID текущего пользователя"""
        if not self.current_user:
            return None
        
        if isinstance(self.current_user, dict):
            return self.current_user.get('id')
        
        # Если current_user не словарь, пытаемся получить ID из БД
        try:
            username = self.get_username()
            if username:
                query = "SELECT id FROM users WHERE username = ?"
                result = self.db.execute_query(query, (username,))
                if result:
                    return result[0]['id']
        except Exception as e:
            print(f"Ошибка получения ID пользователя: {e}")
        
        return None

    def get_current_user_info(self):
        """Получить информацию о текущем пользователе из БД"""
        if self.current_user:
            return self.current_user
        return None

    def cleanup_old_logs(self, days=30):
        """Очистка старых логов попыток входа"""
        try:
            if self.current_user and self.current_user.get('user_group') in ['admin', 'root']:
                query = """
                    DELETE FROM login_attempts 
                    WHERE datetime(attempt_time) < datetime('now', ?)
                """
                # В SQLite execute_query не возвращает количество удаленных строк
                # Просто выполняем запрос
                self.db.execute_query(query, (f'-{days} days',))
                print(f"✓ Очищены логи попыток входа старше {days} дней")
            else:
                print("Ошибка: Требуются права администратора")
        except Exception as e:
            print(f"Ошибка очистки логов: {e}")

    def get_failed_attempts_count(self, username, minutes=1):
        """Получить количество неудачных попыток за последние N минут"""
        try:
            query = """
                SELECT COUNT(*) as attempts 
                FROM login_attempts 
                WHERE username = ? 
                AND success = 0 
                AND datetime(attempt_time) > datetime('now', ?)
            """
            # Используем правильный формат параметра времени
            result = self.db.execute_query(query, (username, f'-{minutes} minutes'))
            return result[0]['attempts'] if result else 0
        except Exception as e:
            print(f"Ошибка получения попыток входа: {e}")
            return 0

    def log_login_attempt(self, username, success, details=None):
        """Логирование попытки входа"""
        try:
            query = """
                INSERT INTO login_attempts (username, success, user_agent) 
                VALUES (?, ?, ?)
            """
            agent = details or f"Login {'success' if success else 'failed'}"
            self.db.execute_query(query, (username, 1 if success else 0, agent))
        except Exception as e:
            print(f"Ошибка логирования попытки входа: {e}")

    def logout(self):
        """Выход из системы"""
        self.current_user = None

class LinuxLikeFileSystem:
    def __init__(self, user_manager):
        self.user_manager = user_manager
        self.db_operations = SecureDBOperations()  # ← ДОБАВИТЬ
        self.navigation_history = []
        self.init_file_system()

    def init_file_system(self):
        # Создаем виртуальную файловую систему в памяти
        self.fs = {
            '/': {
                'type': 'directory',
                'permissions': 'drwxr-xr-x',
                'owner': 'root',
                'group': 'root',
                'created': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'children': {
                    'home': {
                        'type': 'directory',
                        'permissions': 'drwxr-xr-x',
                        'owner': 'root',
                        'group': 'root',
                        'created': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                        'children': {}
                    },
                    'etc': {
                        'type': 'directory',
                        'permissions': 'drwxr-xr-x',
                        'owner': 'root',
                        'group': 'root',
                        'created': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                        'children': {
                            'passwd': {
                                'type': 'file', 
                                'permissions': '-rw-r--r--', 
                                'owner': 'root', 
                                'group': 'root', 
                                'size': 2048, 
                                'content': 'root:x:0:0:root:/root:/bin/bash\nadmin:x:1000:1000:System Administrator:/home/admin:/bin/bash', 
                                'created': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                            }
                        }
                    },
                    'var': {
                        'type': 'directory',
                        'permissions': 'drwxr-xr-x',
                        'owner': 'root',
                        'group': 'root',
                        'created': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                        'children': {
                            'log': {
                                'type': 'directory', 
                                'permissions': 'drwxr-xr-x', 
                                'owner': 'root', 
                                'group': 'root', 
                                'created': datetime.now().strftime('%Y-%m-%d %H:%M:%S'), 
                                'children': {}
                            }
                        }
                    },
                    'tmp': {
                        'type': 'directory',
                        'permissions': 'drwxrwxrwt',
                        'owner': 'root',
                        'group': 'root',
                        'created': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                        'children': {}
                    },
                    'bin': {
                        'type': 'directory',
                        'permissions': 'drwxr-xr-x',
                        'owner': 'root',
                        'group': 'root',
                        'created': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                        'children': {
                            'bash': {
                                'type': 'file',
                                'permissions': '-rwxr-xr-x',
                                'owner': 'root',
                                'group': 'root',
                                'size': 1200000,
                                'content': '',
                                'created': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                            }
                        }
                    },
                    'root': {
                        'type': 'directory',
                        'permissions': 'drwx------',
                        'owner': 'root',
                        'group': 'root',
                        'created': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                        'children': {}
                    }
                }
            }
        }
        
        # Создаем домашние директории для существующих пользователей
        home_dir = self.fs['/']['children']['home']['children']

        # Получаем список пользователей из базы данных
        try:
            # Добавляем метод в UserManager для получения всех пользователей
            users = self.user_manager.get_all_users()  # ← нужно добавить этот метод
            for user in users:
                username = user['username']
                home_dir[username] = {
                    'type': 'directory',
                    'permissions': 'drwxr-xr-x',
                    'owner': username,
                    'group': user.get('user_group', 'users'),
                    'created': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                    'children': {
                        'Documents': {
                            'type': 'directory', 
                            'permissions': 'drwxr-xr-x', 
                            'owner': username, 
                            'group': user.get('user_group', 'users'), 
                            'created': datetime.now().strftime('%Y-%m-%d %H:%M:%S'), 
                            'children': {
                                'project1': {
                                    'type': 'directory',
                                    'permissions': 'drwxr-xr-x',
                                    'owner': username,
                                    'group': user.get('user_group', 'users'),
                                    'created': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                                    'children': {}
                                }
                            }
                        },
                        'Downloads': {
                            'type': 'directory', 
                            'permissions': 'drwxr-xr-x', 
                            'owner': username, 
                            'group': user.get('user_group', 'users'), 
                            'created': datetime.now().strftime('%Y-%m-%d %H:%M:%S'), 
                            'children': {}
                        },
                        'Pictures': {
                            'type': 'directory', 
                            'permissions': 'drwxr-xr-x', 
                            'owner': username, 
                            'group': user.get('user_group', 'users'), 
                            'created': datetime.now().strftime('%Y-%m-%d %H:%M:%S'), 
                            'children': {}
                        },
                        'readme.txt': {
                            'type': 'file', 
                            'permissions': '-rw-r--r--', 
                            'owner': username, 
                            'group': user.get('user_group', 'users'), 
                            'size': 1024, 
                            'content': f'Добро пожаловать, {username}!\nЭто ваша домашняя директория.\n\nСодержимое:\n- Documents: для документов\n- Downloads: для загрузок\n- Pictures: для изображений', 
                            'created': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                        }
                    }
                }
        except Exception as e:
            print(f"Ошибка при создании домашних директорий: {e}")
            # Создаем хотя бы домашнюю директорию для текущего пользователя
            if self.user_manager.current_user:
                username = self.user_manager.current_user['username']
                home_dir[username] = {
                    'type': 'directory',
                    'permissions': 'drwxr-xr-x',
                    'owner': username,
                    'group': 'users',
                    'created': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                    'children': {}
                }
                        
        # Диски (разделы) - УМЕНЬШЕННЫЕ РАЗМЕРЫ
        self.disks = {
            'sda1': {
                'mount_point': '/', 
                'size': '10GB',
                'used': '2GB',
                'free': '8GB',
                'used_bytes': 0,
                'usage_percent': 20.0
            },
            'sda2': {
                'mount_point': '/home', 
                'size': '20GB',
                'used': '5GB',
                'free': '15GB',
                'used_bytes': 0,
                'usage_percent': 25.0
            }
        }
        
        self.current_path = '/'
        self.update_disk_usage()

    def get_node(self, path):
        """Получить узел по пути"""
        if path == '/':
            return self.fs['/']
        
        parts = [p for p in path.split('/') if p]
        node = self.fs['/']
        
        for part in parts:
            if part in node.get('children', {}):
                node = node['children'][part]
            else:
                return None
        return node

    def check_permission(self, node, permission='r'):
        """Проверка прав доступа к файлу/директории"""
        if not self.user_manager.current_user:
            print("Ошибка: Пользователь не авторизован")
            return False
        
        # Получаем имя текущего пользователя
        current_username = self.user_manager.get_username()
        if not current_username:
            print("Ошибка: Не удалось получить имя пользователя")
            return False
        
        # Получаем owner узла как строку
        node_owner = str(node.get('owner', ''))
        
        # Пользователь root имеет все права
        if current_username == 'root':
            return True
        
        # Пользователь admin также имеет все права (если нужно)
        if current_username == 'admin':
            return True
        
        # Владелец файла имеет права
        if node_owner == current_username:
            return True
            
        # Получаем группу пользователя
        user_group = self.user_manager.get_user_group()
        node_group = str(node.get('group', ''))
        
        # Проверка прав для группы
        if user_group == node_group:
            # Проверяем конкретные права доступа
            return self.check_permission_bits(node.get('permissions', ''), 'group', permission)
            
        # Для остальных пользователей
        return self.check_permission_bits(node.get('permissions', ''), 'other', permission)

    def log_to_db(self, operation_type, file_path=None, details=None):
        """Логирование операции в базу данных"""
        if not self.user_manager.current_user:
            return
    
        file_id = None
        # Получаем ID файла если он существует в БД
        if file_path:
            try:
                # Пытаемся найти файл в БД по пути
                query = "SELECT id FROM files WHERE file_path = ?"
                result = self.db_operations.db.execute_query(query, (file_path,))
                if result:
                    file_id = result[0]['id']
            except Exception as e:
                # Если не нашли файл в БД, оставляем file_id = None
                pass
    
        try:
            self.db_operations.safe_log_operation(
                operation_type=operation_type,
                user_id=self.user_manager.current_user['id'],
                file_id=file_id,
                file_path=file_path,
                details=details
            )
        except Exception as e:
            print(f"Предупреждение: Не удалось записать лог в БД: {e}")

    def ls(self, path=None):
        if path is None:
            path = self.current_path
        
        node = self.get_node(path)
        if not node or node['type'] != 'directory':
            print(f"Ошибка: {path} не является директорией")
            return
        
        if not self.check_permission(node, 'r'):
            print(f"Ошибка: Нет прав доступа к {path}")
            return
        
        print(f"\nСодержимое {path}:")
        print(f"{'Permissions':12} {'Owner':8} {'Group':8} {'Size':8} {'Created':19} {'Name':20}")
        print("-" * 80)
        
        # Показываем родительскую директорию
        if path != '/':
            parent_path = '/'.join(path.split('/')[:-1]) or '/'
            parent_node = self.get_node(parent_path)
            if parent_node:
                print(f"{parent_node['permissions']:12} {parent_node['owner']:8} {parent_node['group']:8} {'-':8} {parent_node['created']:19} {'..'}")
        
        for name, item in node.get('children', {}).items():
            size = str(item.get('size', '')) if item['type'] == 'file' else '-'
            print(f"{item['permissions']:12} {item['owner']:8} {item['group']:8} {size:8} {item['created']:19} {name}")

    def cd(self, path):
        """Сменить директорию с интеграцией логирования в БД"""
        new_path = self.current_path
    
        # Обработка специальных команд
        if path == '..':
            # Переход на уровень выше
            if self.current_path == '/':
                print("Вы уже в корневой директории!")
                return
            parts = [p for p in self.current_path.split('/') if p]
            parts.pop()
            new_path = '/' + '/'.join(parts) if parts else '/'
        elif path == '~' or path == '':
            # Переход в домашнюю директорию
            if self.user_manager.current_user:
                user_info = self.user_manager.get_current_user_info()
                new_path = user_info.get('home_dir', f"/home/{user_info['username']}")
            else:
                print("Ошибка: Пользователь не авторизован")
                return
        elif path == '/':
            # Переход в корневую директорию
            new_path = '/'
        elif path.startswith('/'):
            # Абсолютный путь
            new_path = path
        else:
            # Относительный путь
            if self.current_path.endswith('/'):
                new_path = self.current_path + path
            else:
                new_path = self.current_path + '/' + path
    
        # Валидация пути
        target_node = self.get_node(new_path)
        if not target_node:
            print(f"Ошибка: Директория '{new_path}' не существует")
            return
    
        if target_node['type'] != 'directory':
            print(f"Ошибка: '{new_path}' не является директорией")
            return
    
        # Проверка прав доступа
        if not self.check_permission(target_node, 'r'):
            print(f"Ошибка: Нет прав доступа к директории '{new_path}'")
            return
    
        # Сохраняем в историю навигации
        if self.current_path != new_path:
            self.navigation_history.append(self.current_path)
            if len(self.navigation_history) > 10:
                self.navigation_history.pop(0)
    
        # Логируем операцию в БД
        if self.user_manager.current_user:
            self.log_to_db(
                operation_type="NAVIGATION",
                file_path=new_path,
                details=f"Смена директории: {self.current_path} -> {new_path}"
            )
    
        # Обновляем текущий путь
        self.current_path = new_path
        print(f"Переход в: {new_path}")

    def pwd(self):
        print(f"Текущая директория: {self.current_path}")

    def mkdir(self, name):
        current_node = self.get_node(self.current_path)
        if not self.check_permission(current_node, 'w'):
            print(f"Ошибка: Нет прав на запись в текущую директорию")
            return
            
        if name in current_node.get('children', {}):
            print(f"Ошибка: Директория {name} уже существует")
            return
        
        # Получаем имя пользователя и группу
        owner_name = self.user_manager.get_username() or 'unknown'
        group_name = self.user_manager.get_user_group()
        
        current_node.setdefault('children', {})[name] = {
            'type': 'directory',
            'permissions': 'drwxr-xr-x',
            'owner': owner_name,
            'group': group_name,
            'created': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'children': {}
        }
        
        # Логирование
        if self.user_manager.current_user:
            dir_path = f"{self.current_path}/{name}" if self.current_path != '/' else f"/{name}"
            self.log_to_db(
                operation_type="DIR_CREATE",
                file_path=dir_path,
                details=f"Создана директория '{name}'"
            )
        
        print(f"Директория '{name}' создана в {self.current_path}")


    def touch(self, name):
        """Создать файл с записью в БД"""
        # Проверка прав на запись в текущую директорию
        current_node = self.get_node(self.current_path)
        if not current_node:
            print(f"Ошибка: Текущая директория '{self.current_path}' не существует")
            return
    
        if not self.check_permission(current_node, 'w'):
            print(f"Ошибка: Нет прав на запись в текущую директорию")
            return
    
        # Проверка существования файла
        if name in current_node.get('children', {}):
            print(f"Ошибка: Файл '{name}' уже существует")
            return
    
        # Ввод начального содержимого
        print(f"\nСоздание файла '{name}' в {self.current_path}")
        initial_content = input("Введите начальное содержимое файла (или Enter для пустого): ").strip()
    
        # Расчет размера
        file_size = len(initial_content.encode('utf-8'))
    
        # Проверка доступного места на диске
        if not self.check_disk_space(file_size):
            print("Ошибка: Недостаточно места на диске для создания файла")
            return
    
        # Проверка максимального размера файла
        if file_size > 100 * 1024 * 1024:  # 100MB
            print("Ошибка: Размер файла превышает максимально допустимый (100MB)")
            return
    
        # Получаем имя пользователя и группу
        owner_name = self.user_manager.get_username() or 'unknown'
        group_name = self.user_manager.get_user_group()
    
        # Создание файла в виртуальной файловой системе
        current_node.setdefault('children', {})[name] = {
            'type': 'file',
            'permissions': '-rw-r--r--',
            'owner': owner_name, 
            'group': group_name, 
            'size': file_size,
            'content': initial_content,
            'created': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'modified': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }
    
        # Обновление использования дисков
        self.update_disk_usage()
    
        # Логирование и сохранение в БД
        if self.user_manager.current_user:
            file_path = f"{self.current_path}/{name}" if self.current_path != '/' else f"/{name}"
            
            # Получаем ID пользователя
            user_id = self.user_manager.get_user_id()
            
            if user_id:
                # Логируем операцию
                self.log_to_db(
                    operation_type="FILE_CREATE",
                    file_path=file_path,
                    details=f"Создан файл '{name}', размер: {file_size} байт"
                )
            
                # Сохраняем информацию о файле в БД
                try:
                    self.db_operations.safe_file_creation(
                        filename=name,
                        file_path=file_path,
                        file_size=file_size,
                        file_type='file',
                        owner_id=user_id,
                        permissions='rw-r--r--'
                    )
                except Exception as e:
                    print(f"Предупреждение: Не удалось сохранить информацию о файле в БД: {e}")
            else:
                print("Предупреждение: Не удалось получить ID пользователя для записи в БД")
    
        print(f"\n Файл '{name}' успешно создан")
        print(f"  Путь: {self.current_path}/{name}")
        print(f"  Размер: {file_size} байт")
        print(f"  Владелец: {owner_name}")
        print(f"  Группа: {group_name}")


    def cat(self, name):
        file_path = self.current_path + ('/' if self.current_path != '/' else '') + name
        node = self.get_node(file_path)
        
        if not node:
            print(f"Ошибка: Файл '{name}' не существует")
        elif node['type'] != 'file':
            print(f"Ошибка: '{name}' не является файлом")
        elif not self.check_permission(node, 'r'):
            print(f"Ошибка: Нет прав на чтение файла '{name}'")
        else:
            print(f"\nСодержимое файла '{name}':")
            print("-" * 40)
            print(node.get('content', ''))
            print("-" * 40)

    def rm(self, name):
        target_path = self.current_path + ('/' if self.current_path != '/' else '') + name
        node = self.get_node(target_path)
        
        if not node:
            print(f"Ошибка: '{name}' не существует")
            return
        
        if not self.check_permission(node, 'w'):
            print(f"Ошибка: Нет прав на удаление '{name}'")
            return
        
        # Получаем родительский узел
        parent_path = '/'.join(target_path.split('/')[:-1]) or '/'
        parent_node = self.get_node(parent_path)
        
        if node['type'] == 'directory' and node.get('children'):
            confirm = input(f"Директория '{name}' не пуста. Удалить рекурсивно? (y/N): ").strip().lower()
            if confirm != 'y':
                print("Отмена удаления")
                return
        
        del parent_node['children'][name]
        print(f"{'Директория' if node['type'] == 'directory' else 'Файл'} '{name}' удален")

    def rename(self, old_name, new_name):
        old_path = self.current_path + ('/' if self.current_path != '/' else '') + old_name
        new_path = self.current_path + ('/' if self.current_path != '/' else '') + new_name
        
        old_node = self.get_node(old_path)
        new_node = self.get_node(new_path)
        
        if not old_node:
            print(f"Ошибка: '{old_name}' не существует")
            return
        
        if not self.check_permission(old_node, 'w'):
            print(f"Ошибка: Нет прав на переименование '{old_name}'")
            return
        
        if new_node:
            print(f"Ошибка: '{new_name}' уже существует")
            return
        
        # Получаем родительский узел
        parent_path = '/'.join(old_path.split('/')[:-1]) or '/'
        parent_node = self.get_node(parent_path)
        
        parent_node['children'][new_name] = parent_node['children'].pop(old_name)
        print(f"Успешно переименовано из '{old_name}' в '{new_name}'")

    def edit_file(self, name):
        """Редактировать содержимое файла с сохранением в БД"""
        # Полный путь к файлу
        file_path = self.current_path + ('/' if self.current_path != '/' else '') + name
    
        # Получение узла файла
        node = self.get_node(file_path)
        if not node:
            print(f"Ошибка: Файл '{name}' не существует")
            return 
    
        if node['type'] != 'file':
            print(f"Ошибка: '{name}' не является файлом")
            return  # ДОБАВЛЕН return
    
        # Проверка прав доступа
        if not self.check_permission(node, 'w'):
            print(f"Ошибка: Нет прав на запись в файл '{name}'")
            return
    
        print(f"\n{'='*60}")
        print(f"РЕДАКТИРОВАНИЕ ФАЙЛА: {name}")
        print(f"{'='*60}")
        print(f"Путь: {file_path}")
        print(f"Текущий размер: {node.get('size', 0)} байт")
        print(f"Владелец: {node['owner']}")
        print(f"Последнее изменение: {node.get('modified', node.get('created', 'N/A'))}")
        print(f"{'-'*60}")
    
        # Показываем текущее содержимое
        current_content = node.get('content', '')
        if current_content:
            print("Текущее содержимое:")
            print("-" * 40)
            print(current_content)
            print("-" * 40)
        else:
            print("Файл пуст")
    
        # Ввод нового содержимого
        print("Введите все строки, затем нажмите Enter на пустой строке для завершения:")
        print("-" * 40)
    
        lines = []
        print("Начинайте ввод (пустая строка для завершения):")
    
        while True:
            try:
                line = input()
                if line == "":  # Пустая строка завершает ввод
                    break
                lines.append(line)
            except (EOFError, KeyboardInterrupt):
                print("\nЗавершение ввода...")
                break
    
        # Если ничего не ввели, спрашиваем
        if not lines:
            keep_old = input("Файл будет пустым. Продолжить? (Y/n): ").strip().lower()
            if keep_old not in ['', 'y', 'yes']:
                print("Редактирование отменено.")
                return
    
        new_content = '\n'.join(lines)
        new_size = len(new_content.encode('utf-8'))
        old_size = node.get('size', 0)
        size_diff = new_size - old_size
        
        # Проверка доступного места на диске
        if size_diff > 0 and not self.check_disk_space(size_diff):
            print(f"Ошибка: Недостаточно места на диске. Требуется дополнительно: {size_diff} байт")
            return
        
        # Проверка максимального размера файла
        if new_size > 100 * 1024 * 1024:  # 100MB
            print("Ошибка: Новый размер файла превышает максимально допустимый (100MB)")
            return
        
        # Обновляем файл в виртуальной файловой системе
        node['content'] = new_content
        node['size'] = new_size
        node['modified'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        # Обновляем использование дисков
        self.update_disk_usage()
        
        # Логирование и обновление в БД
        if self.user_manager.current_user:
            # Логируем операцию
            self.log_to_db(
                operation_type="FILE_EDIT",
                file_path=file_path,
                details=f"Файл отредактирован. Старый размер: {old_size} байт, новый: {new_size} байт"
            )
            
        # Обновляем информацию о файле в БД
        try:
            self.db_operations.safe_file_update(file_path, new_size)
        except Exception as e:
            print(f"Предупреждение: Не удалось обновить информацию о файле в БД: {e}")
        
            print(f"\n{'='*60}")
            print(f"✓ Файл '{name}' успешно обновлен")
            print(f"  Новый размер: {new_size} байт")
            if size_diff != 0:
                change = f"+{size_diff}" if size_diff > 0 else f"{size_diff}"
                print(f"  Изменение размера: {change} байт")
            print(f"  Линий в файле: {len(lines)}")
            print(f"{'='*60}")
        except Exception as e:
            print(f"\nОшибка при редактировании файла: {e}")
            print("Изменения не сохранены.")


    def check_disk_space(self, required_bytes):
        required_gb = required_bytes / (1024**3)    
        for disk_name, disk_info in self.disks.items():
            if disk_info['mount_point'] == '/':
                free_gb = int(disk_info['free'].replace('GB', ''))
                if free_gb * (1024**3) < required_bytes:
                    print(f"Недостаточно места на диске {disk_name}. Требуется: {required_gb:.2f}GB, доступно: {free_gb}GB")
                    return False
        return True

    def update_disk_usage(self):
        """Обновить использование дисков на основе реальных данных"""
        def calculate_fs_size(node):
            size = 0
            node_type = node.get('type')
            if node_type == 'file':
                size += node.get('size', 0)
            elif node_type == 'directory':
                children = node.get('children', {})
                for child in children.values():
                    size += calculate_fs_size(child)
            return size
        
        try:
            total_used = calculate_fs_size(self.fs['/'])
        except Exception as e:
            print(f"Ошибка при расчете размера файловой системы: {e}")
            total_used = 0
        
        # Обновляем информацию о дисках
        for disk_name, disk_info in self.disks.items():
            try:
                if disk_info['mount_point'] == '/':
                    # Для корневого диска используем общий размер
                    used_bytes = total_used
                    used_gb = used_bytes // (1024**3)
                    size_gb_str = disk_info.get('size', '0GB').replace('GB', '')
                    size_gb = int(size_gb_str) if size_gb_str.isdigit() else 0
                    free_gb = max(0, size_gb - used_gb)
                    
                    disk_info['used'] = f"{used_gb}GB"
                    disk_info['free'] = f"{free_gb}GB"
                    disk_info['used_bytes'] = used_bytes
                    disk_info['usage_percent'] = (used_gb / size_gb * 100) if size_gb > 0 else 0
                
                elif disk_info['mount_point'] == '/home':
                    # Для домашнего диска вычисляем размер домашних директорий
                    home_node = self.get_node('/home')
                    if home_node:
                        home_size = calculate_fs_size(home_node)
                    else:
                        home_size = 0
                    
                    used_bytes = home_size
                    used_gb = used_bytes // (1024**3)
                    size_gb_str = disk_info.get('size', '0GB').replace('GB', '')
                    size_gb = int(size_gb_str) if size_gb_str.isdigit() else 0
                    free_gb = max(0, size_gb - used_gb)
                    
                    disk_info['used'] = f"{used_gb}GB"
                    disk_info['free'] = f"{free_gb}GB"
                    disk_info['used_bytes'] = home_size
                    disk_info['usage_percent'] = (used_gb / size_gb * 100) if size_gb > 0 else 0
            except Exception as e:
                print(f"Ошибка обновления информации о диске {disk_name}: {e}")

    def get_disk_space_info(self):
        """Получить информацию о свободном месте на дисках"""
        self.update_disk_usage()
        info = []
        for disk_name, disk_info in self.disks.items():
            info.append({
                'name': disk_name,
                'mount_point': disk_info['mount_point'],
                'total': disk_info['size'],
                'used': disk_info['used'],
                'free': disk_info['free'],
                'usage_percent': disk_info.get('usage_percent', 0)
            })
        return info

    def navigation_menu(self):
        """Меню навигации по файловой системе"""
        # Автоматический переход в домашнюю директорию при первом входе
        if self.current_path == '/':
            user_info = self.user_manager.get_current_user_info()
            if user_info:
                self.current_path = user_info['home_dir']
    
        while True:
            current_relative_path = self.current_path if self.current_path != '/' else '/'
            print()
            print(' '*30, f"НАВИГАЦИЯ ПО ФАЙЛОВОЙ СИСТЕМЕ")
            print(' '*30, f"Пользователь: {self.user_manager.current_user['username']}")
            print(' '*30, "1. Показать содержимое текущей директории (ls)")
            print(' '*30, "2. Перейти в поддиректорию (cd <name>)")
            print(' '*30, "3. Перейти на уровень вверх (cd ..)")
            print(' '*30, "4. Перейти в домашнюю директорию (cd ~)")
            print(' '*30, "5. Перейти в корневую директорию (cd /)")
            print(' '*30, "6. Показать текущий путь (pwd)")
            print(' '*30, "7. История навигации")
            print(' '*30, "8. Операции с файлами и директориями")
            print(' '*30, "0. Назад в главное меню")
            print()
            print(f"Текущий путь: {current_relative_path}")
        
            choice = input("Выберите действие или введите команду: ").strip()
        
            if choice == '1' or choice.lower() == 'ls':
                self.ls()
            elif choice == '2' or choice.lower().startswith('cd '):
                if choice == '2':
                    self.enter_subdirectory()
                else:
                    # Обработка команды cd
                    path = choice[3:].strip()
                    self.cd(path)
            elif choice == '3' or choice.lower() == 'cd ..':
                self.cd('..')
            elif choice == '4' or choice.lower() == 'cd ~':
                self.cd('~')
            elif choice == '5' or choice.lower() == 'cd /':
                self.cd('/')
            elif choice == '6' or choice.lower() == 'pwd':
                self.pwd()
            elif choice == '7':
                self.show_navigation_history()
            elif choice == '8':
                self.file_operations_menu()
            elif choice == '0' or choice.lower() == 'exit':
                break


    def enter_subdirectory(self):
        """Переход в поддиректорию с выбором из списка"""
        current_node = self.get_node(self.current_path)
        if not current_node or current_node['type'] != 'directory':
            print("Ошибка: Текущий путь не является директорией")
            return
        
        directories = []
        for name, item in current_node.get('children', {}).items():
            if item['type'] == 'directory':
                directories.append(name)
        
        if not directories:
            print("В текущей директории нет поддиректорий")
            return
        
        print("\nДоступные поддиректории:")
        for i, dir_name in enumerate(directories, 1):
            print(f"  {i}. {dir_name}/")
        
        try:
            choice = input("\nВведите номер директории или имя: ").strip()
            if choice.isdigit():
                index = int(choice) - 1
                if 0 <= index < len(directories):
                    self.cd(directories[index])
                else:
                    print("Неверный номер директории")
            else:
                self.cd(choice)
        except ValueError:
            print("Неверный ввод")

    def show_navigation_history(self):
        if not self.navigation_history:
            print("История навигации пуста")
            return
        
        print("\nИстория навигации (последние 10 переходов):")
        for i, path in enumerate(reversed(self.navigation_history), 1):
            print(f"  {i}. {path}")
        
        choice = input("\nПерейти к пути из истории? (номер или 0 для отмены): ").strip()
        if choice.isdigit():
            index = int(choice)
            if 1 <= index <= len(self.navigation_history):
                target_path = self.navigation_history[-index]
                self.cd(target_path)
            elif index != 0:
                print("Неверный номер")

    def file_operations_menu(self):
        while True:
            print(' '*30, f"=== ОПЕРАЦИИ С ФАЙЛАМИ И ДИРЕКТОРИЯМИ ===")
            print(' '*30, f"Текущий путь: {self.current_path}")
            print(' '*30, "1. Создать файл (touch)")
            print(' '*30, "2. Показать содержимое файла (cat)")
            print(' '*30, "3. Удалить файл (rm)")
            print(' '*30, "4. Создать директорию (mkdir)")
            print(' '*30, "5. Удалить директорию (rmdir)")
            print(' '*30, "6. Редактировать файл (edit)")
            print(' '*30, "7. Переименовать файл/директорию")
            print(' '*30, "8. Информация о файле/директории")
            print(' '*30, "0. Назад к навигации")
            
            choice = input("Выберите действие: ").strip()
            
            if choice == '1' or choice == 'touch':
                name = input("Введите имя файла: ").strip()
                if name:
                    self.touch(name)
                else:
                    print("Имя файла не может быть пустым")
            elif choice == '2' or choice == 'cat':
                name = input("Введите имя файла: ").strip()
                if name:
                    self.cat(name)
                else:
                    print("Имя файла не может быть пустым")
            elif choice == '3' or choice == 'rm':
                name = input("Введите имя файла/директории: ").strip()
                if name:
                    self.rm(name)
                else:
                    print("Имя не может быть пустым")
            elif choice == '4' or choice == 'mkdir':
                name = input("Введите имя директории: ").strip()
                if name:
                    self.mkdir(name)
                else:
                    print("Имя директории не может быть пустым")
            elif choice == '5' or choice == 'rmdir':
                name = input("Введите имя директории: ").strip()
                if name:
                    self.rm(name)
                else:
                    print("Имя директории не может быть пустым")
            elif choice == '3' or choice == 'edit': 
                name = input("Введите имя файла для редактирования: ").strip()
                if name:
                    self.edit_file(name)
                else:
                    print("Имя файла не может быть пустым")
            elif choice == '7':
                old_name = input("Введите текущее имя: ").strip()
                new_name = input("Введите новое имя: ").strip()
                if old_name and new_name:
                    self.rename(old_name, new_name)
                else:
                    print("Имена не могут быть пустыми")
            elif choice == '8':
                name = input("Введите имя файла/директории: ").strip()
                if name:
                    self.file_info(name)
                else:
                    print("Имя не может быть пустым")
            elif choice == '0':
                break
            else:
                print("Неверный выбор")

    def file_info(self, name):
        target_path = self.current_path + ('/' if self.current_path != '/' else '') + name
        node = self.get_node(target_path)
        
        if not node:
            print(f"Ошибка: '{name}' не существует")
            return
        
        print(f"\nИнформация о '{name}':")
        print(f"  Тип: {'Директория' if node.get('type') == 'directory' else 'Файл'}")
        print(f"  Права доступа: {node.get('permissions', '??????????')}")
        print(f"  Владелец: {node.get('owner', 'unknown')}")
        print(f"  Группа: {node.get('group', 'unknown')}")
        print(f"  Создан: {node.get('created', 'N/A')}")
        
        if node.get('type') == 'file':
            print(f"  Размер: {node.get('size', 0)} байт")
            content = node.get('content', '')
            print(f"  Строк: {len(content.splitlines())}")
            if node.get('modified'):
                print(f"  Изменен: {node.get('modified')}")
        else:
            children = node.get('children', {})
            children_count = len(children)
            print(f"  Элементов: {children_count}")
            if children_count > 0:
                print(f"  Поддиректории: {sum(1 for item in children.values() if item.get('type') == 'directory')}")
                print(f"  Файлы: {sum(1 for item in children.values() if item.get('type') == 'file')}")



def show_disk_info(file_system):
        print("\n=== ИНФОРМАЦИЯ О ДИСКАХ ===")
        print(f"{'Устройство':<10} {'Точка монтир.':<15} {'Размер':<12} {'Использовано':<12} {'Свободно':<12} {'Использование':<12}")
        print("-" * 80)
    
        for disk_name, disk_info in file_system.disks.items():
            size_gb = disk_info['size']
            used_gb = disk_info['used']
            free_gb = disk_info['free']
            mount_point = disk_info['mount_point']
        
            # Вычисляем процент использования
            size_num = int(size_gb.replace('GB', ''))
            used_num = int(used_gb.replace('GB', ''))
            usage_percent = (used_num / size_num) * 100 if size_num > 0 else 0
        
            print(f"{disk_name:<10} {mount_point:<15} {size_gb:<12} {used_gb:<12} {free_gb:<12} {usage_percent:.1f}%")

def login_screen(user_manager):
    """Экран авторизации с защитой от brute-force"""
    while True:
        print("\n" + "="*50)
        print("          СИСТЕМА УПРАВЛЕНИЯ ФАЙЛАМИ")
        print("="*50)
        print("1. Вход в систему")
        print("2. Регистрация")
        print("3. Сбросить блокировку (только для администраторов)")  # ← НОВЫЙ ПУНКТ
        print("0. Выход")
        
        choice = input("Выберите действие: ").strip()
        
        if choice == '1':
            print("\n=== АВТОРИЗАЦИЯ ===")
            username = input("Имя пользователя: ").strip()
            password = getpass.getpass("Пароль: ").strip()
            
            # Получаем IP-адрес (для реального приложения)
            ip_address = '127.0.0.1'  # В демо-версии используем localhost
            
            if user_manager.authenticate(username, password):
                print(f"\nДобро пожаловать, {username}!")
                return True
            else:
                print("Ошибка: Неверное имя пользователя или пароль")
                
        elif choice == '2':
            user_manager.register_user()
            
        elif choice == '3':
            # Сброс блокировки (только для админов)
            admin_username = input("Введите имя администратора: ").strip()
            admin_password = getpass.getpass("Пароль администратора: ").strip()
            
            if user_manager.db.authenticate_user(admin_username, admin_password):
                username_to_unlock = input("Введите имя пользователя для разблокировки: ").strip()
                user_manager.unlock_account(username_to_unlock)
            else:
                print("Ошибка: Неверные учетные данные администратора")
            
        elif choice == '0':
            print("Выход из программы...")
            return False
        else:
            print("Неверный выбор")

def json_xml_menu():
    """Меню работы с JSON/XML"""
    while True:
        print("\n=== РАБОТА С JSON/XML ===")
        print("1. Создать JSON файл")
        print("2. Чтение JSON файла")
        print("3. Создать XML файл")
        print("4. Чтение XML файла")
        print("0. Назад")
        
        choice = input("Выберите действие: ").strip()
        
        if choice == '1':
            create_json_file()
        elif choice == '2':
            read_json_file()
        elif choice == '3':
            create_xml_file()
        elif choice == '4':
            read_xml_file()
        elif choice == '0':
            break
        else:
            print("Неверный выбор")

def zip_operations_menu():
    """Меню операций с ZIP архивами"""
    while True:
        print("\n=== ОПЕРАЦИИ С ZIP АРХИВАМИ ===")
        print("1. Создать ZIP архив")
        print("2. Распаковать ZIP архив")
        print("3. Просмотреть содержимое ZIP архива")
        print("0. Назад")
        
        choice = input("Выберите действие: ").strip()
        
        if choice == '1':
            create_zip_archive()
        elif choice == '2':
            extract_zip_archive()
        elif choice == '3':
            view_zip_contents()
        elif choice == '0':
            break
        else:
            print("Неверный выбор")

def user_operations_menu(user_manager):
    """Меню операций пользователя"""
    while True:
        print("\n=== ОПЕРАЦИИ ПОЛЬЗОВАТЕЛЯ ===")
        print("1. Показать текущего пользователя")
        print("2. Показать информацию о системе")
        print("3. Сменить пользователя")
        print("0. Назад")
        
        choice = input("Выберите действие: ").strip()
        
        if choice == '1':
            user_info = user_manager.get_current_user_info()
            if user_info:
                print(f"Текущий пользователь: {user_manager.current_user}")
                print(f"Полное имя: {user_info['full_name']}")
                print(f"Группа: {user_info['user_group']}")
                print(f"Домашняя директория: {user_info['home_dir']}")
        elif choice == '2':
            print(f"Система: {platform.system()}")
            print(f"Версия: {platform.version()}")
            print(f"Процессор: {platform.processor()}")
        elif choice == '3':
            user_manager.logout()
            print("Выход из учетной записи...")
            return True
        elif choice == '0':
            break
        else:
            print("Неверный выбор")
    return False

def create_json_file():
    filename = input("Введите имя JSON файла: ")
    data = {}
    while True:
        key = input("Введите ключ (или пусто для завершения): ")
        if not key:
            break
        value = input(f"Введите значение для '{key}': ")
        data[key] = value
    
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print(f"JSON файл {filename} создан")

def read_json_file():
    filename = input("Введите имя JSON файла: ")
    try:
        with open(filename, 'r', encoding='utf-8') as f:
            data = json.load(f)
        print("Содержимое JSON файла:")
        print(json.dumps(data, ensure_ascii=False, indent=2))
    except FileNotFoundError:
        print(f"Файл {filename} не найден")

def create_xml_file():
    filename = input("Введите имя XML файла: ")
    root_name = input("Введите имя корневого элемента: ")
    
    root = ET.Element(root_name)
    
    while True:
        element_name = input("Введите имя элемента (или пусто для завершения): ")
        if not element_name:
            break
        element_value = input(f"Введите значение для элемента '{element_name}': ")
        child = ET.SubElement(root, element_name)
        child.text = element_value
    
    tree = ET.ElementTree(root)
    tree.write(filename, encoding='utf-8', xml_declaration=True)
    print(f"XML файл {filename} создан")

def read_xml_file():
    filename = input("Введите имя XML файла: ")
    try:
        tree = ET.parse(filename)
        root = tree.getroot()
        
        print("Содержимое XML файла:")
        def print_element(element, indent=0):
            print(' ' * indent + f"<{element.tag}>: {element.text or ''}")
            for child in element:
                print_element(child, indent + 2)
        
        print_element(root)
    except FileNotFoundError:
        print(f"Файл {filename} не найден")

def create_zip_archive():
    zip_name = input("Введите имя ZIP архива: ")
    files = input("Введите имена файлов для архивации (через пробел): ").split()
    
    with zipfile.ZipFile(zip_name, 'w') as zipf:
        for file in files:
            if os.path.exists(file):
                zipf.write(file)
                print(f"Файл {file} добавлен в архив")
            else:
                print(f"Файл {file} не найден")
    
    print(f"ZIP архив {zip_name} создан")

def extract_zip_archive():
    zip_name = input("Введите имя ZIP архива: ")
    extract_dir = input("Введите директорию для распаковки (пусто - текущая): ") or '.'
    
    try:
        with zipfile.ZipFile(zip_name, 'r') as zipf:
            zipf.extractall(extract_dir)
        print(f"ZIP архив {zip_name} распакован в {extract_dir}")
    except FileNotFoundError:
        print(f"ZIP архив {zip_name} не найден")

def view_zip_contents():
    zip_name = input("Введите имя ZIP архива: ")
    
    try:
        with zipfile.ZipFile(zip_name, 'r') as zipf:
            print(f"Содержимое архива {zip_name}:")
            for file_info in zipf.infolist():
                print(f"  {file_info.filename} ({file_info.file_size} bytes)")
    except FileNotFoundError:
        print(f"ZIP архив {zip_name} не найден")


def view_db_logs_menu(file_system):
    """Меню просмотра логов из базы данных"""
    while True:
        print("\n=== ЛОГИ ОПЕРАЦИЙ ИЗ БАЗЫ ДАННЫХ ===")
        print("1. Показать все логи")
        print("2. Показать мои логи")
        print("3. Статистика использования")
        print("4. Отчет о безопасности")
        print("0. Назад")
        
        choice = input("Выберите действие: ").strip()
        
        if choice == '1':
            logs = file_system.db_operations.safe_get_audit_logs(limit=50)
            print("\nПоследние 50 операций:")
            print("-" * 100)
            for log in logs:
                print(f"{log['timestamp']} | {log.get('username', 'N/A')} | {log['operation_type']} | {log.get('file_path', '')} | {log.get('details', '')}")
        
        elif choice == '2':
            if file_system.user_manager.current_user:
                logs = file_system.db_operations.safe_get_audit_logs(
                    user_id=file_system.user_manager.current_user['id'], 
                    limit=30
                )
                print(f"\nМои последние 30 операций:")
                print("-" * 100)
                for log in logs:
                    print(f"{log['timestamp']} | {log['operation_type']} | {log.get('file_path', '')} | {log.get('details', '')}")
        
        elif choice == '3':
            stats = file_system.db_operations.get_security_report()['disk_usage']
            print("\nСтатистика использования:")
            print("-" * 60)
            for stat in stats:
                size_mb = stat['total_size'] / (1024*1024) if stat['total_size'] else 0
                print(f"{stat['username']}: {stat['file_count']} файлов, {size_mb:.2f} MB")
        
        elif choice == '4':
            report = file_system.db_operations.get_security_report()
            print("\nОтчет о безопасности:")
            print("-" * 60)
            if report['suspicious_activities']:
                print("Обнаружены подозрительные активности:")
                for activity in report['suspicious_activities']:
                    print(f"{activity}")
            else:
                print("Подозрительных активностей не обнаружено ✓")
        
        elif choice == '0':
            break
        else:
            print("Неверный выбор")


def main():
    user_manager = UserManager()
    
    while True:
        if not login_screen(user_manager):
            break
            
        file_system = LinuxLikeFileSystem(user_manager)
        
        while user_manager.current_user:
            print(f"\n=== ГЛАВНОЕ МЕНЮ ===")
            print("1. Файловая система")
            print("2. Работа с JSON/XML")
            print("3. Операции с ZIP архивами")
            print("4. Информация о дисках")
            print("5. Операции пользователя")
            print("6. Логи операций (БД)")
            print("0. Выход")
            
            choice = input("Выберите пункт меню: ").strip()
            
            if choice == '1':
                file_system.navigation_menu()
            elif choice == '2':
                json_xml_menu()
            elif choice == '3':
                zip_operations_menu()
            elif choice == '4':
                show_disk_info(file_system)
            elif choice == '5':
                if user_operations_menu(user_manager):
                    break
            elif choice == '6':  
                view_db_logs_menu(file_system)
            elif choice == '0':
                user_manager.logout()
                print("Выход из учетной записи...")
                break
            else:
                print("Неверный выбор. Попробуйте снова.")

if __name__ == "__main__":
    main()