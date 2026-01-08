"""
JWT Manager for authentication
"""
import jwt
import datetime
from datetime import timezone
from typing import Optional, Dict
from flask import current_app


class JWTManager:
    """JWT токен менеджер"""
    
    def __init__(self, app=None):
        if app:
            self.init_app(app)
    
    def init_app(self, app):
        """Инициализация JWT с приложением"""
        self.secret_key = app.config.get('JWT_SECRET_KEY')
        self.algorithm = app.config.get('JWT_ALGORITHM')
        self.access_token_expires = int(app.config.get('JWT_ACCESS_TOKEN_EXPIRES'))  # 1 час
        self.refresh_token_expires = int(app.config.get('JWT_REFRESH_TOKEN_EXPIRES'))  # 30 дней
    
    def create_access_token(self, user_id: str, additional_data: Optional[Dict] = None) -> str:
        """Создает access токен"""
        payload = {
            'sub': user_id,
            'type': 'access',
            'exp': datetime.datetime.now(timezone.utc) + datetime.timedelta(seconds=self.access_token_expires),
            'iat': datetime.datetime.now(timezone.utc)
        }
        
        if additional_data:
            payload.update(additional_data)
        
        return jwt.encode(payload, self.secret_key, algorithm=self.algorithm)
    
    def create_refresh_token(self, user_id: str) -> str:
        """Создает refresh токен"""
        payload = {
            'sub': user_id,
            'type': 'refresh',
            'exp': datetime.datetime.now(timezone.utc) + datetime.timedelta(seconds=self.refresh_token_expires),
            'iat': datetime.datetime.now(timezone.utc)
        }
        
        return jwt.encode(payload, self.secret_key, algorithm=self.algorithm)
    
    def decode_token(self, token: str) -> Optional[Dict]:
        """Декодирует и проверяет токен"""
        try:
            payload = jwt.decode(token, self.secret_key, algorithms=[self.algorithm])
            return payload
        except jwt.ExpiredSignatureError:
            raise ValueError("Token expired")
        except jwt.InvalidTokenError:
            raise ValueError("Invalid token")
    
    def refresh_access_token(self, refresh_token: str) -> Optional[str]:
        """Обновляет access токен с помощью refresh токена"""
        try:
            payload = self.decode_token(refresh_token)
            if payload.get('type') != 'refresh':
                raise ValueError("Not a refresh token")
            
            user_id = payload.get('sub')
            if not user_id:
                raise ValueError("Invalid token payload")
            
            return self.create_access_token(user_id)
        except Exception:
            return None
    
    def get_user_id_from_token(self, token: str) -> Optional[str]:
        """Получает user_id из токена"""
        try:
            payload = self.decode_token(token)
            return payload.get('sub')
        except Exception:
            return None

# Глобальный экземпляр
jwt_manager = JWTManager()
