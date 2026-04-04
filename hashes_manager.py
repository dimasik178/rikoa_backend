import threading
from models import db, Product

class HashesManager:
    def __init__(self):
        self.original_owners = {}     # {hash_original: owner_id}
        self.watermarked_set = set()  # {hash_watermarked}
        self._lock = threading.Lock()
        self._loaded = False
    
    def load_from_db(self, app):
        """Загружает ВСЕ товары из БД"""
        with app.app_context():
            results = db.session.query(
                Product.original_hash,
                Product.watermarked_hash,
                Product.owner_id
            ).all()
            
            self.original_owners = {}
            self.watermarked_set = set()
            
            for original_hash, watermarked_hash, owner_id in results:
                if original_hash:
                    self.original_owners[original_hash] = owner_id
                if watermarked_hash:
                    self.watermarked_set.add(watermarked_hash)
            
            self._loaded = True
            print(f"✅ Загружено {len(self.original_owners)} оригиналов и {len(self.watermarked_set)} водяных хешей")
    
    def check_and_get_owner(self, file_hash: str, user_id: str) -> tuple[bool, str, str | None]:
        """
        Проверяет, может ли пользователь выставить фото.
        Возвращает: (можно_ли, сообщение, owner_id_из_памяти)
        """
        if not self._loaded:
            raise RuntimeError("Хеши ещё не загружены")
        
        with self._lock:
            if file_hash in self.watermarked_set:
                return False, "Нельзя выставлять изображение с водяным знаком", None
            
            if file_hash not in self.original_owners:
                return True, "new", None
            
            stored_owner_id = self.original_owners[file_hash]
            if stored_owner_id != user_id:
                return False, "Вы не являетесь владельцем этого изображения", stored_owner_id
            
            return True, "relist", stored_owner_id
    
    def add_new_product(self, original_hash: str, watermarked_hash: str, owner_id: str):
        with self._lock:
            self.original_owners[original_hash] = owner_id
            self.watermarked_set.add(watermarked_hash)
    
    def update_owner(self, original_hash: str, new_owner_id: str):
        with self._lock:
            if original_hash in self.original_owners:
                self.original_owners[original_hash] = new_owner_id
    
    def remove_original(self, original_hash: str):
        with self._lock:
            if original_hash in self.original_owners:
                del self.original_owners[original_hash]
    
    def is_watermarked(self, file_hash: str) -> bool:
        with self._lock:
            return file_hash in self.watermarked_set

hashes_manager = HashesManager()
