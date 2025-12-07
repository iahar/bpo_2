import zipfile
import os
from pathlib import Path
from file_operations.file_manager import FileManager
from security.path_validator import PathValidator, PathTraversalError
from config import Config

class ZipBombError(Exception):
    """Исключение для ZIP-бомб"""
    pass

class ZipHandler:
    def __init__(self, file_manager: FileManager, path_validator: PathValidator):
        self.file_manager = file_manager
        self.validator = path_validator
    
    def create_zip(self, source_paths: list, zip_path: str) -> bool:
        """Создание ZIP архива с проверками безопасности"""
        try:
            safe_zip_path = self.validator.validate_path(zip_path)           
            # Проверка расширения файла
            if safe_zip_path.suffix.lower() != '.zip':
                raise ValueError("Целевой файл должен иметь расширение .zip")
            
            total_size = 0
            files_to_zip = []
            
            # Сбор информации о файлах для архивации
            for source_path in source_paths:
                safe_source_path = self.validator.validate_path(source_path)
                
                if safe_source_path.is_file():
                    file_size = safe_source_path.stat().st_size
                    total_size += file_size
                    files_to_zip.append(safe_source_path)
                elif safe_source_path.is_dir():
                    for file in safe_source_path.rglob('*'):
                        if file.is_file():
                            file_size = file.stat().st_size
                            total_size += file_size
                            files_to_zip.append(file)
                
                # Проверка общего размера
                if total_size > Config.MAX_ZIP_SIZE:
                    raise ZipBombError("Общий размер файлов для архивации превышает лимит")
            
            # Создание ZIP архива
            with zipfile.ZipFile(safe_zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
                for file_path in files_to_zip:
                    # Сохранение относительных путей
                    arcname = file_path.relative_to(Config.BASE_DIR)
                    zipf.write(file_path, arcname)
            return True        
        except Exception as e:
            raise e
    
    def extract_zip(self, zip_path: str, extract_path: str = "") -> bool:
        """Извлечение ZIP архива с защитой от ZIP-бомб"""
        try:
            safe_zip_path = self.validator.validate_path(zip_path)
            safe_extract_path = self.validator.validate_path(extract_path) if extract_path else Config.BASE_DIR
            
            if not safe_zip_path.exists():
                raise FileNotFoundError(f"ZIP архив {zip_path} не существует")
            
            total_extracted_size = 0
            extracted_files = []
            
            with zipfile.ZipFile(safe_zip_path, 'r') as zipf:
                # Проверка каждого файла в архиве
                for file_info in zipf.infolist():
                    # Проверка на Path Traversal в именах файлов
                    try:
                        target_path = (safe_extract_path / file_info.filename).resolve()
                        if not target_path.is_relative_to(safe_extract_path):
                            raise PathTraversalError(f"Опасное имя файла в архиве: {file_info.filename}")
                    except:
                        raise PathTraversalError(f"Опасное имя файла в архиве: {file_info.filename}")
                    
                    # Проверка размера распакованного файла
                    file_size = file_info.file_size
                    total_extracted_size += file_size
                    
                    # Защита от ZIP-бомбы
                    if total_extracted_size > Config.MAX_ZIP_SIZE:
                        # Удаление уже распакованных файлов
                        for extracted_file in extracted_files:
                            if extracted_file.exists():
                                extracted_file.unlink()
                        raise ZipBombError("Превышен максимальный размер распакованных данных")
                    
                    # Извлечение файла
                    zipf.extract(file_info, safe_extract_path)
                    extracted_file_path = safe_extract_path / file_info.filename
                    extracted_files.append(extracted_file_path)
            
            return True
        
        except Exception as e:
            # Очистка в случае ошибки
            try:
                for extracted_file in extracted_files:
                    if extracted_file.exists():
                        extracted_file.unlink()
            except:
                pass
            raise e
    
    def get_zip_info(self, zip_path: str) -> dict:
        """Получение информации о ZIP архиве"""
        try:
            safe_zip_path = self.validator.validate_path(zip_path)
            
            if not safe_zip_path.exists():
                raise FileNotFoundError(f"ZIP архив {zip_path} не существует")
            
            with zipfile.ZipFile(safe_zip_path, 'r') as zipf:
                total_size = 0
                file_count = 0
                
                for file_info in zipf.infolist():
                    total_size += file_info.file_size
                    file_count += 1
                
                return {
                    'filename': safe_zip_path.name,
                    'file_count': file_count,
                    'total_size': total_size,
                    'compressed_size': safe_zip_path.stat().st_size,
                    'compression_ratio': (1 - safe_zip_path.stat().st_size / total_size) * 100 if total_size > 0 else 0
                }
        
        except Exception as e:
            raise e