from .models import DatabaseManager

class SecureDBOperations:
    """Безопасные операции с базой данных с защитой от SQL-инъекций"""
    
    def __init__(self, db_manager=None):
        self.db = db_manager or DatabaseManager()
    
    # === БЕЗОПАСНЫЕ ОПЕРАЦИИ С ФАЙЛАМИ ===
    
    def safe_file_creation(self, filename, file_path, file_size, file_type, owner_id, permissions='rw-r--r--'):
        """Безопасное создание записи о файле в БД с правами доступа"""
        try:
            query = """
                INSERT INTO files (filename, file_path, file_size, file_type, owner_id, permissions) 
                VALUES (?, ?, ?, ?, ?, ?)
            """
            self.db.execute_query(query, (filename, file_path, file_size, file_type, owner_id, permissions))
            return True
        except Exception as e:
            print(f"Ошибка создания записи о файле: {e}")
            return False

    def safe_file_deletion(self, file_path, user_id):
        """Безопасное удаление записи о файле"""
        return self.db.delete_file_record(file_path, user_id)
    
    def safe_file_update(self, file_path, new_size):
        """Безопасное обновление информации о файле"""
        return self.db.update_file_size(file_path, new_size)
    
    def safe_get_user_files(self, user_id):
        """Безопасное получение файлов пользователя"""
        return self.db.get_user_files(user_id)
    
    # === БЕЗОПАСНЫЕ ОПЕРАЦИИ АУДИТА ===
    
    def safe_log_operation(self, operation_type, user_id, file_id=None, file_path=None, details=None):
        """Безопасное логирование операции"""  
        return self.db.log_operation(operation_type, user_id, file_id, file_path, details)

    def safe_get_audit_logs(self, user_id=None, limit=100):
        """Безопасное получение логов аудита"""
        return self.db.get_operation_logs(user_id, limit)
    
    # === СТАТИСТИКА И ОТЧЕТЫ ===
    
    def get_security_report(self):
        """Отчет о безопасности"""
        stats = self.db.get_disk_usage_stats()
        recent_logs = self.db.get_operation_logs(limit=50)
        
        return {
            'disk_usage': stats,
            'recent_operations': recent_logs,
            'suspicious_activities': self.detect_suspicious_activities(recent_logs)
        }
    
    def detect_suspicious_activities(self, logs):
        """Обнаружение подозрительной активности"""
        suspicious = []
        for log in logs:
            # Пример: много операций удаления за короткое время
            if log['operation_type'] == 'DELETE':
                suspicious.append(f"Множественное удаление: {log['username']}")
            
            # Пример: попытки доступа к системным файлам
            if 'etc/passwd' in str(log.get('file_path', '')) and log['user_group'] != 'root':
                suspicious.append(f"Попытка доступа к системным файлам: {log['username']}")
        
        return suspicious