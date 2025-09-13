import os
import re
import json
import uuid
import shutil

class KnowledgeBase:
    def __init__(self, texts_path, images_path, files_path, materials_file):
        self.texts_path = texts_path
        self.images_path = images_path
        self.files_path = files_path
        self.materials_file = materials_file
        self.topics = self.load_topics()
        
        # Создаем необходимые директории
        os.makedirs(texts_path, exist_ok=True)
        os.makedirs(images_path, exist_ok=True)
        os.makedirs(files_path, exist_ok=True)
        
        # Инициализируем файл материалов
        self.load_materials()
    
    def load_topics(self):
        """Загружает темы и подтемы из структуры папок"""
        topics = {}
        if os.path.exists(self.texts_path):
            for root, dirs, files in os.walk(self.texts_path):
                # Определяем уровень вложенности
                rel_path = os.path.relpath(root, self.texts_path)
                
                if rel_path == '.':
                    # Корневой уровень - здесь будут только подразделы
                    for dir_name in dirs:
                        topics[dir_name] = {
                            'path': os.path.join(root, dir_name),
                            'subtopics': self.load_subtopics(os.path.join(root, dir_name))
                        }
        return topics
    
    def load_subtopics(self, topic_path):
        """Загружает подразделы для указанного раздела"""
        subtopics = {}
        if os.path.exists(topic_path):
            for file_name in os.listdir(topic_path):
                if file_name.endswith('.txt'):
                    subtopic_name = file_name.replace('.txt', '')
                    subtopics[subtopic_name] = {
                        'path': os.path.join(topic_path, file_name)
                    }
        return subtopics
    
    def load_materials(self):
        """Загружает материалы из JSON файла"""
        if os.path.exists(self.materials_file):
            try:
                with open(self.materials_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except:
                return {}
        return {}
    
    def save_materials(self, materials):
        """Сохраняет материалы в JSON файл"""
        with open(self.materials_file, 'w', encoding='utf-8') as f:
            json.dump(materials, f, ensure_ascii=False, indent=2)
    
    def get_topics(self):
        """Возвращает список основных разделов"""
        return list(self.topics.keys())
    
    def get_subtopics(self, topic):
        """Возвращает подразделы для указанного раздела"""
        if topic in self.topics:
            return list(self.topics[topic]['subtopics'].keys())
        return []
    
    def get_subtopic_path(self, topic, subtopic):
        """Возвращает путь к файлу подраздела"""
        if topic in self.topics and subtopic in self.topics[topic]['subtopics']:
            return self.topics[topic]['subtopics'][subtopic]['path']
        return None
    
    def add_topic(self, topic_name):
        """Добавляет новый раздел"""
        # Создаем папку для раздела
        topic_path = os.path.join(self.texts_path, topic_name)
        os.makedirs(topic_path, exist_ok=True)
        
        # Создаем описание раздела
        description_path = os.path.join(topic_path, "_description.txt")
        with open(description_path, 'w', encoding='utf-8') as f:
            f.write(f"# {topic_name}\n\nОписание раздела {topic_name}.")
        
        # Обновляем структуру тем
        self.topics[topic_name] = {
            'path': topic_path,
            'subtopics': {}
        }
        
        return True
    
    def add_subtopic(self, topic, subtopic_name):
        """Добавляет новый подраздел"""
        if topic not in self.topics:
            return False
        
        # Создаем файл для подраздела
        filename = f"{subtopic_name.lower().replace(' ', '_')}.txt"
        filepath = os.path.join(self.topics[topic]['path'], filename)
        
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(f"# {subtopic_name}\n\nОписание подраздела {subtopic_name}.")
        
        # Обновляем структуру тем
        self.topics[topic]['subtopics'][subtopic_name] = {
            'path': filepath
        }
        
        return True
    
    def get_topic_description(self, topic):
        """Получает описание раздела"""
        if topic in self.topics:
            description_path = os.path.join(self.topics[topic]['path'], "_description.txt")
            if os.path.exists(description_path):
                with open(description_path, 'r', encoding='utf-8') as f:
                    return f.read()
        return "Описание раздела отсутствует."
    
    def get_content(self, topic, subtopic):
        """Получает содержимое подраздела"""
        filepath = self.get_subtopic_path(topic, subtopic)
        
        if not filepath or not os.path.exists(filepath):
            return {"text": "Подраздел не найден", "images": [], "files": []}
        
        try:
            # Читаем текст
            with open(filepath, 'r', encoding='utf-8') as file:
                text_content = file.read()
            
            # Формируем ключ для материалов
            material_key = f"{topic}/{subtopic}"
            
            # Получаем связанные изображения и файлы
            images = self.get_images_for_topic(material_key)
            files = self.get_files_for_topic(material_key)
            
            return {"text": text_content, "images": images, "files": files}
        except FileNotFoundError:
            return {"text": "Файл с знаниями не найден", "images": [], "files": []}
    
    def get_images_for_topic(self, topic_key):
        """Возвращает изображения для указанного раздела"""
        materials = self.load_materials()
        return materials.get(topic_key, {}).get("images", [])
    
    def get_files_for_topic(self, topic_key):
        """Возвращает файлы для указанного раздела"""
        materials = self.load_materials()
        return materials.get(topic_key, {}).get("files", [])
    
    def add_material(self, topic_key, file_path, caption, material_type="image"):
        """Добавляет новый материал"""
        materials = self.load_materials()
        
        if topic_key not in materials:
            materials[topic_key] = {"images": [], "files": []}
        
        material_id = str(uuid.uuid4())
        
        if material_type == "image":
            materials[topic_key]["images"].append({
                "id": material_id,
                "path": file_path,
                "caption": caption
            })
        else:
            materials[topic_key]["files"].append({
                "id": material_id,
                "path": file_path,
                "caption": caption,
                "type": material_type
            })
        
        self.save_materials(materials)
        return material_id
    
    def update_material(self, topic_key, material_id, new_caption=None, new_file_path=None, material_type="image"):
        """Обновляет существующий материал"""
        materials = self.load_materials()
        
        if topic_key not in materials:
            return False
        
        material_list = materials[topic_key]["images"] if material_type == "image" else materials[topic_key]["files"]
        
        for material in material_list:
            if material["id"] == material_id:
                if new_caption:
                    material["caption"] = new_caption
                if new_file_path:
                    # Удаляем старый файл
                    if os.path.exists(material["path"]):
                        os.remove(material["path"])
                    material["path"] = new_file_path
                
                self.save_materials(materials)
                return True
        
        return False
    
    def delete_material(self, topic_key, material_id, material_type="image"):
        """Удаляет материал"""
        materials = self.load_materials()
        
        if topic_key not in materials:
            return False
        
        material_list = materials[topic_key]["images"] if material_type == "image" else materials[topic_key]["files"]
        
        for i, material in enumerate(material_list):
            if material["id"] == material_id:
                # Удаляем файл
                if os.path.exists(material["path"]):
                    os.remove(material["path"])
                # Удаляем запись
                del material_list[i]
                
                # Если раздел пуст, удаляем его
                if not materials[topic_key]["images"] and not materials[topic_key]["files"]:
                    del materials[topic_key]
                
                self.save_materials(materials)
                return True
        
        return False
    
    def get_material(self, topic_key, material_id, material_type="image"):
        """Возвращает материал по ID"""
        materials = self.load_materials()
        
        if topic_key not in materials:
            return None
        
        material_list = materials[topic_key]["images"] if material_type == "image" else materials[topic_key]["files"]
        
        for material in material_list:
            if material["id"] == material_id:
                return material
        
        return None
    
    def create_text_file(self, text, filename):
        """Создает текстовый файл"""
        file_path = os.path.join(self.files_path, filename)
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(text)
        return file_path
    
    def save_uploaded_file(self, file_data, filename, file_type="image"):
        """Сохраняет загруженный файл"""
        if file_type == "image":
            save_path = self.images_path
        else:
            save_path = self.files_path
        
        file_path = os.path.join(save_path, filename)
        with open(file_path, 'wb') as f:
            f.write(file_data)
        return file_path
    
    def search(self, query):
        """Поиск по всем файлам базы знаний"""
        results = []
        for topic in self.topics:
            for subtopic in self.topics[topic]['subtopics']:
                filepath = self.get_subtopic_path(topic, subtopic)
                if filepath and os.path.exists(filepath):
                    with open(filepath, 'r', encoding='utf-8') as file:
                        content = file.read()
                        if re.search(query, content, re.IGNORECASE):
                            results.append(f"Найдено в {topic}/{subtopic}:")
                            lines = content.split('\n')
                            for line in lines:
                                if re.search(query, line, re.IGNORECASE):
                                    results.append(f"• {line}")
                            results.append("")
        
        return "\n".join(results) if results else "Ничего не найдено"

# Инициализация базы знаний
kb = KnowledgeBase(
    "knowledge_base/texts", 
    "knowledge_base/images", 
    "knowledge_base/files", 
    "knowledge_base/materials.json"
)