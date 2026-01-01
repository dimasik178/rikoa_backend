import re
from difflib import SequenceMatcher
from typing import List, Tuple
from models import Product
from config import SearchConfig

class ProductSearchEngine:
    """
    Интеллектуальный поисковый движок для товаров
    """
    
    def __init__(self):
        self.config = SearchConfig
        self.weights = self.config.WEIGHTS
        self.penalties = self.config.PENALTIES
        self.common_words = set().union(
            self.config.COMMON_WORDS['english'],
            self.config.COMMON_WORDS['russian']
        )
    
    def search(self, products: List[Product], search_term: str, 
               max_results: int = 20) -> List[Tuple[Product, float]]:
        """
        Выполняет интеллектуальный поиск среди товаров
        
        Args:
            products: Список товаров для поиска
            search_term: Поисковый запрос
            max_results: Максимальное количество результатов
            
        Returns:
            Список кортежей (товар, рейтинг релевантности)
        """
        if not search_term or not products:
            return []
        
        search_term = search_term.strip()
        if not search_term:
            return []
        
        search_lower = search_term.lower()
        search_words = [word for word in search_lower.split() if word]
        
        # Динамический порог в зависимости от длины запроса
        threshold = self._calculate_threshold(search_lower, search_words)
        
        results = []
        
        for product in products:
            search_text = self._prepare_search_text(product)
            if not search_text:
                continue
            
            score = self._calculate_relevance_score(
                search_lower, search_words, search_text, product
            )
            
            # Применяем коррекции и фильтрацию
            score = self._apply_corrections(search_lower, search_text, score)
            
            if score >= threshold:
                results.append((product, score))
        
        # Сортируем по релевантности
        results.sort(key=lambda x: x[1], reverse=True)
        
        return results[:min(max_results, self.config.MAX_VALUES['results_limit'])]
    
    def _prepare_search_text(self, product: Product) -> str:
        """Подготавливает поисковый текст из товара"""
        fields = [
            product.title,
            product.description or '',
            product.creator.nickname if product.creator else '',
        ]
        return " ".join(filter(None, fields)).lower()
    
    def _calculate_threshold(self, search_lower: str, search_words: List[str]) -> float:
        """Рассчитывает динамический порог релевантности"""
        if not search_lower:
            return 0.0
        
        # Проверяем, является ли запрос числом
        if search_lower.isdigit():
            if len(search_lower) == 1:
                return self.config.MIN_SCORES['single_digit']
            elif len(search_lower) <= 3:
                return self.config.MIN_SCORES['short_number']
        
        # Проверяем длину запроса
        if len(search_lower) == 1:
            return self.config.MIN_SCORES['single_char']
        elif len(search_lower) == 2:
            return self.config.MIN_SCORES['two_chars']
        elif len(search_lower) == 3:
            return self.config.MIN_SCORES['three_chars']
        
        # Многословные запросы
        if len(search_words) > 1:
            return self.config.MIN_SCORES['multi_word']
        
        return self.config.MIN_SCORES['default']
    
    def _calculate_relevance_score(self, search_lower: str, search_words: List[str],
                                  search_text: str, product: Product) -> float:
        """Рассчитывает рейтинг релевантности"""
        score = 0.0
        
        # 0. ОСОБЫЙ СЛУЧАЙ: поиск цифр
        if search_lower.isdigit():
            score += self._score_number_search(search_lower, search_text, product)
        
        # 1. ТОЧНЫЕ СОВПАДЕНИЯ (высший приоритет)
        if product.title.lower() == search_lower:
            score += self.weights['exact_title']
        
        if product.creator and product.creator.nickname.lower() == search_lower:
            score += self.weights['exact_artist']
        
        # 2. ТОЧНЫЕ СОВПАДЕНИЯ ФРАЗ
        exact_phrase = re.search(r'\b' + re.escape(search_lower) + r'\b', search_text)
        if exact_phrase:
            position = exact_phrase.start()
            position_bonus = self.config.POSITION_BONUSES['phrase_exact'] / (position + 1)
            score += self.weights['phrase_exact'] + position_bonus
        elif search_lower in search_text:
            position = search_text.find(search_lower)
            position_bonus = self.config.POSITION_BONUSES['phrase_partial'] / (position + 1)
            score += self.weights['phrase_partial'] + position_bonus
        
        # 3. СОВПАДЕНИЯ ОТДЕЛЬНЫХ СЛОВ (включая цифры)
        score += self._score_individual_words(search_words, search_text)
        
        # 4. НЕЧЕТКИЕ СОВПАДЕНИЯ (исправление опечаток)
        if len(search_lower) >= self.config.FUZZY_SEARCH['min_word_length']:
            score += self._score_fuzzy_matches(search_lower, search_words, search_text)
        
        return score
    
    def _score_number_search(self, search_lower: str, search_text: str, product: Product) -> float:
        """Оценивает поиск цифр"""
        score = 0.0
        
        # Ищем цифры в тексте
        numbers_in_text = re.findall(r'\b\d+\b', search_text)
        
        # Проверяем точное совпадение числа
        if search_lower in numbers_in_text:
            score += self.weights['number_exact']
            
            # Дополнительный бонус если число в названии
            title_numbers = re.findall(r'\b\d+\b', product.title.lower())
            if search_lower in title_numbers:
                score += self.config.NUMBER_SEARCH['title_bonus']
        
        # Проверяем частичные совпадения (цифра внутри другого числа)
        for number in numbers_in_text:
            if search_lower in number:
                score += self.weights['number_partial']
        
        return score
    
    def _score_individual_words(self, search_words: List[str], search_text: str) -> float:
        """Оценивает совпадения отдельных слов"""
        score = 0.0
        
        for word in search_words:
            # Для цифр - специальная обработка
            if word.isdigit():
                # Ищем точное совпадение цифры
                if re.search(r'\b' + re.escape(word) + r'\b', search_text):
                    score += self.weights['number_exact']
                # Ищем частичное вхождение цифры (например, "1" в "13")
                elif re.search(r'\d*' + re.escape(word) + r'\d*', search_text):
                    score += self.weights['number_partial']
            else:
                # Для обычных слов
                if len(word) <= 2:
                    # Для коротких слов - только точные совпадения
                    if re.search(r'\b' + re.escape(word) + r'\b', search_text):
                        score += 8.0  # Фиксированный вес для коротких слов
                else:
                    # Для обычных слов
                    exact_match = re.search(r'\b' + re.escape(word) + r'\b', search_text)
                    if exact_match:
                        score += self.weights['word_exact']
                    elif word in search_text:
                        score += self.weights['word_partial']
        
        # Бонус за все слова в запросе
        if len(search_words) > 1:
            all_words_found = all(
                re.search(r'\b' + re.escape(word) + r'\b', search_text)
                for word in search_words if len(word) > 2 and not word.isdigit()
            )
            if all_words_found:
                score += self.weights['all_words']
        
        return score
    
    def _score_fuzzy_matches(self, search_lower: str, search_words: List[str],
                            search_text: str) -> float:
        """Оценивает нечеткие совпадения (для опечаток)"""
        score = 0.0
        
        # Общая схожесть текста
        max_length = self.config.MAX_VALUES['similarity_text_length']
        similarity = SequenceMatcher(None, search_lower, search_text[:max_length]).ratio()
        
        if similarity > self.config.FUZZY_SEARCH['similarity_threshold_high']:
            score += similarity * self.weights['similarity_high']
        elif similarity > self.config.FUZZY_SEARCH['similarity_threshold_medium']:
            score += similarity * self.weights['similarity_medium']
        
        # Схожесть отдельных слов
        min_word_length = self.config.FUZZY_SEARCH['min_word_length']
        word_similarity_threshold = self.config.FUZZY_SEARCH['word_similarity_threshold']
        
        for word in search_words:
            if len(word) >= min_word_length:
                for text_word in re.findall(r'\b\w+\b', search_text):
                    if len(text_word) >= min_word_length:
                        word_similarity = SequenceMatcher(None, word, text_word).ratio()
                        if word_similarity > word_similarity_threshold:
                            score += word_similarity * self.weights['word_similarity']
        
        return score
    
    def _apply_corrections(self, search_lower: str, search_text: str, score: float) -> float:
        """Применяет коррекции к рейтингу"""
        
        # Для цифр - меньше штрафов
        if search_lower.isdigit():
            if len(search_lower) <= 3:
                # Только небольшой штраф за слишком длинный текст
                if len(search_text) > len(search_lower) * self.penalties['long_number_text_ratio']:
                    score *= self.penalties['long_number_penalty']
            return max(0.0, score)
        
        # Штраф за слишком длинный текст
        if len(search_text) > len(search_lower) * self.penalties['long_text_ratio']:
            score *= self.penalties['long_text_penalty']
        
        # Строгие штрафы для общих слов
        if search_lower in self.common_words:
            score *= self.penalties['common_word_penalty']
        
        # Дополнительная фильтрация для коротких слов
        if len(search_lower) <= 3:
            has_exact_match = any(
                re.search(r'\b' + re.escape(search_lower) + r'\b', text_word)
                for text_word in re.findall(r'\b\w+\b', search_text)
            )
            if not has_exact_match:
                score *= self.penalties['short_word_no_match']
        
        # Гарантируем неотрицательный рейтинг
        return max(0.0, score)

# Создаем глобальный экземпляр поискового движка
search_engine = ProductSearchEngine()
