import os
import json
import xml.etree.ElementTree as ET
import zipfile
import shutil
import getpass
import platform
from datetime import datetime
import hashlib

class UserManager:
    def __init__(self):
        self.users_file = "users.json"
        self.current_user = None
        self.load_users()

    def load_users(self):
        """Загрузка пользователей из файла"""
        if os.path.exists(self.users_file):
            with open(self.users_file, 'r', encoding='utf-8') as f:
                self.users = json.load(f)
        else:
            # Создаем начальных пользователей
            self.users = {
                'root': {  
                'password': self.hash_password('root'),
                'group': 'root',
                'home_dir': '/root',
                'full_name': 'Root'
                },
                'admin': {
                    'password': self.hash_password('admin123'),
                    'group': 'admin',
                    'home_dir': '/home/admin',
                    'full_name': 'System Administrator'
                },
                'user': {
                    'password': self.hash_password('password1'),
                    'group': 'users',
                    'home_dir': '/home/user1',
                    'full_name': 'User One'
                }
            }
            self.save_users()

    def save_users(self):
        """Сохранение пользователей в файл"""
        with open(self.users_file, 'w', encoding='utf-8') as f:
            json.dump(self.users, f, ensure_ascii=False, indent=2)

    def hash_password(self, password):
        """Хеширование пароля"""
        return hashlib.sha256(password.encode()).hexdigest()

    def authenticate(self, username, password):
        """Аутентификация пользователя"""
        if username in self.users:
            if self.users[username]['password'] == self.hash_password(password):
                self.current_user = username
                return True
        return False

    def register_user(self):
        print("\n=== РЕГИСТРАЦИЯ ===")
        username = input("Введите имя пользователя: ").strip()
        
        if username in self.users:
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
        
        self.users[username] = {
            'password': self.hash_password(password),
            'group': 'users',
            'home_dir': f'/home/{username}',
            'full_name': full_name
        }
        self.save_users()
        print(f"Пользователь {username} успешно зарегистрирован")
        return True

    def get_current_user_info(self):
        """Получить информацию о текущем пользователе"""
        if self.current_user:
            return self.users[self.current_user]
        return None

    def logout(self):
        """Выход из системы"""
        self.current_user = None

class LinuxLikeFileSystem:
    def __init__(self, user_manager):
        self.user_manager = user_manager
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
        for username in self.user_manager.users:
            home_dir[username] = {
                'type': 'directory',
                'permissions': 'drwxr-xr-x',
                'owner': username,
                'group': 'users',
                'created': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'children': {
                    'Documents': {
                        'type': 'directory', 
                        'permissions': 'drwxr-xr-x', 
                        'owner': username, 
                        'group': 'users', 
                        'created': datetime.now().strftime('%Y-%m-%d %H:%M:%S'), 
                        'children': {
                            'project1': {
                                'type': 'directory',
                                'permissions': 'drwxr-xr-x',
                                'owner': username,
                                'group': 'users',
                                'created': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                                'children': {}
                            }
                        }
                    },
                    'Downloads': {
                        'type': 'directory', 
                        'permissions': 'drwxr-xr-x', 
                        'owner': username, 
                        'group': 'users', 
                        'created': datetime.now().strftime('%Y-%m-%d %H:%M:%S'), 
                        'children': {}
                    },
                    'Pictures': {
                        'type': 'directory', 
                        'permissions': 'drwxr-xr-x', 
                        'owner': username, 
                        'group': 'users', 
                        'created': datetime.now().strftime('%Y-%m-%d %H:%M:%S'), 
                        'children': {}
                    },
                    'readme.txt': {
                        'type': 'file', 
                        'permissions': '-rw-r--r--', 
                        'owner': username, 
                        'group': 'users', 
                        'size': 1024, 
                        'content': f'Добро пожаловать, {username}!\nЭто ваша домашняя директория.\n\nСодержимое:\n- Documents: для документов\n- Downloads: для загрузок\n- Pictures: для изображений', 
                        'created': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                    }
                }
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
        if not self.user_manager.current_user:
            return False
        
        if self.user_manager.current_user == 'root':
            return True

        if self.user_manager.current_user == 'admin':
            return True
            
        if node['owner'] == self.user_manager.current_user:
            return True
            
        # Проверка прав для группы
        user_info = self.user_manager.get_current_user_info()
        if user_info and user_info['group'] == node['group']:
            return True
            
        return False

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
        new_path = self.current_path
        
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
            user_info = self.user_manager.get_current_user_info()
            if user_info:
                new_path = user_info['home_dir']
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
            new_path = self.current_path + ('/' if self.current_path != '/' else '') + path
        
        target_node = self.get_node(new_path)
        if target_node and target_node['type'] == 'directory':
            if self.check_permission(target_node, 'r'):
                # Сохраняем в историю
                if self.current_path != new_path:
                    self.navigation_history.append(self.current_path)
                    if len(self.navigation_history) > 10:  # Ограничиваем историю
                        self.navigation_history.pop(0)
                
                self.current_path = new_path
                print(f"Переход в: {new_path}")
            else:
                print(f"Ошибка: Нет прав доступа к {new_path}")
        else:
            print(f"Ошибка: Директория {new_path} не существует")

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
        
        current_node.setdefault('children', {})[name] = {
            'type': 'directory',
            'permissions': 'drwxr-xr-x',
            'owner': self.user_manager.current_user,
            'group': 'users',
            'created': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'children': {}
        }
        print(f"Директория '{name}' создана в {self.current_path}")

    def touch(self, name):
        current_node = self.get_node(self.current_path)
        if not self.check_permission(current_node, 'w'):
            print(f"Ошибка: Нет прав на запись в текущую директорию")
            return
        
        if name in current_node.get('children', {}):
            print(f"Файл '{name}' уже существует")
            return
    
        # Предлагаем ввести начальное содержимое
        initial_content = input("Введите начальное содержимое файла (или Enter для пустого): ").strip()
    
        current_node.setdefault('children', {})[name] = {
            'type': 'file',
            'permissions': '-rw-r--r--',
            'owner': self.user_manager.current_user,
            'group': 'users',
            'size': len(initial_content.encode('utf-8')),
            'content': initial_content,
            'created': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'modified': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }
    
        # Обновляем использование дисков
        self.update_disk_usage()
    
        print(f"Файл '{name}' создан в {self.current_path}")
        print(f"Размер: {len(initial_content.encode('utf-8'))} bytes")


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
        file_path = self.current_path + ('/' if self.current_path != '/' else '') + name
        node = self.get_node(file_path)
    
        if not node:
            print(f"Ошибка: Файл '{name}' не существует")
            return
    
        if node['type'] != 'file':
            print(f"Ошибка: '{name}' не является файлом")
            return
    
        if not self.check_permission(node, 'w'):
            print(f"Ошибка: Нет прав на запись в файл '{name}'")
            return
    
        print(f"\nРедактирование файла '{name}':")
        print("Текущее содержимое:")
        print("-" * 40)
        current_content = node.get('content', '')
        print(current_content)
        print("-" * 40)
    
        print("\nВведите новое содержимое (Ctrl+D или пустая строка для завершения):")
    
        try:
            lines = []
            while True:
                try:
                    line = input()
                    lines.append(line)
                except EOFError:
                    break
                except KeyboardInterrupt:
                    print("\nОтмена редактирования")
                    return
        
            new_content = '\n'.join(lines)
        
            # Проверяем, не превысит ли новый размер лимиты диска
            new_size = len(new_content.encode('utf-8'))
            old_size = node.get('size', 0)
            size_diff = new_size - old_size
        
            # Проверяем доступное место на диске
            if not self.check_disk_space(size_diff):
                print("Ошибка: Недостаточно места на диске")
                return
        
            # Обновляем файл
            node['content'] = new_content
            node['size'] = new_size
            node['modified'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
            # Обновляем использование дисков
            self.update_disk_usage()
        
            print(f"Файл '{name}' успешно обновлен")
            print(f"Новый размер: {new_size} bytes")
        
        except Exception as e:
            print(f"Ошибка при редактировании файла: {e}")


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
            if node['type'] == 'file':
                size += node.get('size', 0)
            elif node['type'] == 'directory':
                for child in node.get('children', {}).values():
                    size += calculate_fs_size(child)
            return size
        
        total_used = calculate_fs_size(self.fs['/'])
        
        # Обновляем информацию о дисках
        for disk_name, disk_info in self.disks.items():
            if disk_info['mount_point'] == '/':
                # Для корневого диска используем общий размер
                used_bytes = total_used
                used_gb = used_bytes // (1024**3)
                size_gb = int(disk_info['size'].replace('GB', ''))
                free_gb = max(0, size_gb - used_gb)
                
                disk_info['used'] = f"{used_gb}GB"
                disk_info['free'] = f"{free_gb}GB"
                disk_info['used_bytes'] = used_bytes
                disk_info['usage_percent'] = (used_gb / size_gb * 100) if size_gb > 0 else 0
            
            elif disk_info['mount_point'] == '/home':
                # Для домашнего диска вычисляем размер домашних директорий
                home_node = self.get_node('/home')
                home_size = calculate_fs_size(home_node) if home_node else 0
                used_bytes = home_size
                used_gb = used_bytes // (1024**3)
                size_gb = int(disk_info['size'].replace('GB', ''))
                free_gb = max(0, size_gb - used_gb)
                
                disk_info['used'] = f"{used_gb}GB"
                disk_info['free'] = f"{free_gb}GB"
                disk_info['used_bytes'] = home_size
                disk_info['usage_percent'] = (used_gb / size_gb * 100) if size_gb > 0 else 0

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
            print(' '*50, f"НАВИГАЦИЯ ПО ФАЙЛОВОЙ СИСТЕМЕ")
            print(' '*50, f"Пользователь: {self.user_manager.current_user}")
            print(' '*50, "1. Показать содержимое текущей директории (ls)")
            print(' '*50, "2. Перейти в поддиректорию (cd <name>)")
            print(' '*50, "3. Перейти на уровень вверх (cd ..)")
            print(' '*50, "4. Перейти в домашнюю директорию (cd ~)")
            print(' '*50, "5. Перейти в корневую директорию (cd /)")
            print(' '*50, "6. Показать текущий путь (pwd)")
            print(' '*50, "7. История навигации")
            print(' '*50, "8. Операции с файлами и директориями")
            print(' '*50, "0. Назад в главное меню")
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
            print(' '*50, f"\n=== ОПЕРАЦИИ С ФАЙЛАМИ И ДИРЕКТОРИЯМИ ===")
            print(' '*50, f"Текущий путь: {self.current_path}")
            print(' '*50, "1. Создать файл (touch)")
            print(' '*50, "2. Показать содержимое файла (cat)")
            print(' '*50, "3. Удалить файл (rm)")
            print(' '*50, "4. Создать директорию (mkdir)")
            print(' '*50, "5. Удалить директорию (rmdir)")
            print(' '*50, "6. Редактировать файл (edit)")
            print(' '*50, "7. Переименовать файл/директорию")
            print(' '*50, "8. Информация о файле/директории")
            print(' '*50, "0. Назад к навигации")
            
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
        print(f"  Тип: {'Директория' if node['type'] == 'directory' else 'Файл'}")
        print(f"  Права доступа: {node['permissions']}")
        print(f"  Владелец: {node['owner']}")
        print(f"  Группа: {node['group']}")
        print(f"  Создан: {node['created']}")
        
        if node['type'] == 'file':
            print(f"  Размер: {node.get('size', 0)} bytes")
            content = node.get('content', '')
            print(f"  Строк: {len(content.splitlines())}")
        else:
            children_count = len(node.get('children', {}))
            print(f"  Элементов: {children_count}")



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
    """Экран авторизации"""
    while True:
        print("\n" + "="*50)
        print("          СИСТЕМА УПРАВЛЕНИЯ ФАЙЛАМИ")
        print("="*50)
        print("1. Вход в систему")
        print("2. Регистрация")
        print("0. Выход")
        
        choice = input("Выберите действие: ").strip()
        
        if choice == '1':
            print("\n=== АВТОРИЗАЦИЯ ===")
            username = input("Имя пользователя: ").strip()
            password = getpass.getpass("Пароль: ").strip()
            
            if user_manager.authenticate(username, password):
                print(f"\nДобро пожаловать, {username}!")
                return True
            else:
                print("Ошибка: Неверное имя пользователя или пароль")
                
        elif choice == '2':
            user_manager.register_user()
            
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
                print(f"Группа: {user_info['group']}")
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

def main():
    user_manager = UserManager()
    
    while True:
        if not login_screen(user_manager):
            break
            
        file_system = LinuxLikeFileSystem(user_manager)
        
        while user_manager.current_user:
            print(f"\n=== ГЛАВНОЕ МЕНЮ (пользователь: {user_manager.current_user}) ===")
            print("1. Файловая система")
            print("2. Работа с JSON/XML")
            print("3. Операции с ZIP архивами")
            print("4. Информация о дисках")
            print("5. Операции пользователя")
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
            elif choice == '0':
                user_manager.logout()
                print("Выход из учетной записи...")
                break
            else:
                print("Неверный выбор. Попробуйте снова.")

if __name__ == "__main__":
    main()