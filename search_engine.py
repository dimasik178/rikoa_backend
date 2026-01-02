import re
import math
from difflib import SequenceMatcher
from typing import List, Tuple, Dict, Set
from models import Product
from config import SearchConfig


class TrigramIndex:
    """Индекс триграмм для быстрого поиска"""
    
    def __init__(self):
        self.index: Dict[str, Set[int]] = {}
        self.documents: List[str] = []
    
    def add_document(self, text: str, doc_id: int):
        """Добавляет документ в индекс"""
        if doc_id >= len(self.documents):
            self.documents.extend([''] * (doc_id - len(self.documents) + 1))
        self.documents[doc_id] = text.lower()
        
        # Извлекаем триграммы
        trigrams = self._extract_trigrams(text)
        for trigram in trigrams:
            if trigram not in self.index:
                self.index[trigram] = set()
            self.index[trigram].add(doc_id)
    
    def _extract_trigrams(self, text: str) -> List[str]:
        """Извлекает триграммы из текста"""
        text = text.lower().replace(' ', '_')
        trigrams = []
        for i in range(len(text) - 2):
            trigram = text[i:i+3]
            if len(trigram) == 3:
                trigrams.append(trigram)
        return trigrams
    
    def search(self, query: str, threshold: float = 0.3) -> List[Tuple[int, float]]:
        """Ищет документы по запросу с использованием триграмм"""
        query_trigrams = set(self._extract_trigrams(query))
        
        if not query_trigrams:
            return []
        
        # Находим кандидатов по триграммам
        candidates: Dict[int, int] = {}
        for trigram in query_trigrams:
            if trigram in self.index:
                for doc_id in self.index[trigram]:
                    candidates[doc_id] = candidates.get(doc_id, 0) + 1
        
        # Вычисляем схожесть по Jaccard для триграмм
        results = []
        for doc_id, common_trigrams in candidates.items():
            doc_text = self.documents[doc_id]
            doc_trigrams = set(self._extract_trigrams(doc_text))
            
            # Коэффициент Жаккара для триграмм
            similarity = common_trigrams / len(query_trigrams.union(doc_trigrams))
            
            if similarity >= threshold:
                results.append((doc_id, similarity))
        
        return sorted(results, key=lambda x: x[1], reverse=True)


class ProductSearchEngine:
    """
    Улучшенный поисковый движок с триграммами и исправлением кодировки
    """
    
    def __init__(self):
        self.config = SearchConfig
        self.weights = self.config.WEIGHTS
        self.penalties = self.config.PENALTIES
        self.common_words = set().union(
            self.config.COMMON_WORDS['english'],
            self.config.COMMON_WORDS['russian']
        )
        
        # Триграммный индекс
        self.trigram_index = TrigramIndex()
        self.products_indexed = False
    
    def build_index(self, products: List[Product]):
        """Строит поисковый индекс для товаров"""
        for idx, product in enumerate(products):
            search_text = self._prepare_search_text(product)
            self.trigram_index.add_document(search_text, idx)
        self.products_indexed = True
        self.products_list = products
    
    def _prepare_search_text(self, product: Product) -> str:
        """Подготавливает поисковый текст из товара"""
        fields = [
            product.title,
            product.description or '',
            product.creator.nickname if product.creator else '',
        ]
        return " ".join(filter(None, fields))
    
    def search(self, products: List[Product], search_term: str, 
               max_results: int = 20) -> List[Tuple[Product, float]]:
        """
        Выполняет интеллектуальный поиск с триграммами
        
        Args:
            products: Список товаров для поиска
            search_term: Поисковый запрос (уже декодированный)
            max_results: Максимальное количество результатов
            
        Returns:
            Список кортежей (товар, рейтинг релевантности)
        """
        if not search_term or not products:
            return []
        
        search_term = search_term.strip()
        if not search_term:
            return []
        
        # Если индекс еще не построен - строим
        if not self.products_indexed or len(products) != len(self.products_list):
            self.build_index(products)
        
        search_lower = search_term.lower()
        search_words = [word for word in search_lower.split() if word]
        
        # Динамический порог
        threshold = self._calculate_threshold(search_lower, search_words)
        
        # Этап 1: Быстрый поиск по триграммам
        trigram_results = self._trigram_search(search_lower, threshold)
        
        # Этап 2: Точный поиск по найденным кандидатам
        detailed_results = []
        
        for doc_id, trigram_score in trigram_results[:max_results * 2]:  # Берем больше для фильтрации
            product = products[doc_id]
            search_text = self._prepare_search_text(product).lower()
            
            # Комбинированный рейтинг
            score = self._calculate_relevance_score(
                search_lower, search_words, search_text, product
            )
            
            # Учитываем триграммный рейтинг
            combined_score = (score * 0.7) + (trigram_score * 0.3 * 100)  # Приводим к одной шкале
            
            # Коррекции
            combined_score = self._apply_corrections(search_lower, search_text, combined_score)
            
            if combined_score >= threshold:
                detailed_results.append((product, combined_score))
        
        # Если триграммы не дали результатов, ищем обычным способом
        if not detailed_results:
            detailed_results = self._fallback_search(
                products, search_lower, search_words, threshold, max_results
            )
        
        # Сортируем и ограничиваем
        detailed_results.sort(key=lambda x: x[1], reverse=True)
        return detailed_results[:min(max_results, self.config.MAX_VALUES['results_limit'])]
    
    def _trigram_search(self, search_term: str, threshold: float) -> List[Tuple[int, float]]:
        """Поиск по триграммному индексу"""
        return self.trigram_index.search(search_term, threshold / 100)  # threshold для триграмм ниже
    
    def _fallback_search(self, products: List[Product], search_lower: str, 
                        search_words: List[str], threshold: float, 
                        max_results: int) -> List[Tuple[Product, float]]:
        """Резервный поиск (старый алгоритм)"""
        results = []
        
        for product in products:
            search_text = self._prepare_search_text(product).lower()
            if not search_text:
                continue
            
            score = self._calculate_relevance_score(
                search_lower, search_words, search_text, product
            )
            
            score = self._apply_corrections(search_lower, search_text, score)
            
            if score >= threshold:
                results.append((product, score))
        
        return results
    
    def _calculate_threshold(self, search_lower: str, search_words: List[str]) -> float:
        """Рассчитывает динамический порог релевантности"""
        if not search_lower:
            return 0.0
        
        # Для цифр
        if search_lower.isdigit():
            if len(search_lower) == 1:
                return self.config.MIN_SCORES['single_digit']
            elif len(search_lower) <= 3:
                return self.config.MIN_SCORES['short_number']
        
        # Для коротких запросов
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
        
        # 1. ТОЧНЫЕ СОВПАДЕНИЯ
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
        
        # 3. СОВПАДЕНИЯ ОТДЕЛЬНЫХ СЛОВ
        score += self._score_individual_words(search_words, search_text)
        
        # 4. НЕЧЕТКИЕ СОВПАДЕНИЯ (триграммы уже учтены)
        if len(search_lower) >= self.config.FUZZY_SEARCH['min_word_length']:
            score += self._score_fuzzy_matches(search_lower, search_words, search_text)
        
        # 5. БОНУС ЗА ЧАСТИЧНЫЕ СОВПАДЕНИЯ ТРИГРАММ (дополнительно)
        trigram_bonus = self._calculate_trigram_bonus(search_lower, search_text)
        score += trigram_bonus
        
        return score
    
    def _calculate_trigram_bonus(self, query: str, text: str) -> float:
        """Вычисляет бонус за совпадение триграмм"""
        query_trigrams = set(self._extract_trigrams_from_text(query))
        text_trigrams = set(self._extract_trigrams_from_text(text))
        
        if not query_trigrams:
            return 0.0
        
        common = len(query_trigrams.intersection(text_trigrams))
        jaccard = common / len(query_trigrams.union(text_trigrams))
        
        # Бонус по шкале 0-5
        return jaccard * 5.0
    
    def _extract_trigrams_from_text(self, text: str) -> List[str]:
        """Извлекает триграммы из текста"""
        text = text.lower().replace(' ', '_')
        trigrams = []
        for i in range(len(text) - 2):
            trigram = text[i:i+3]
            if len(trigram) == 3:
                trigrams.append(trigram)
        return trigrams
    
    def _score_individual_words(self, search_words: List[str], search_text: str) -> float:
        """Оценивает совпадения отдельных слов"""
        score = 0.0
        
        for word in search_words:
            if word.isdigit():
                if re.search(r'\b' + re.escape(word) + r'\b', search_text):
                    score += self.weights['number_exact']
                elif re.search(r'\d*' + re.escape(word) + r'\d*', search_text):
                    score += self.weights['number_partial']
            else:
                if len(word) <= 2:
                    if re.search(r'\b' + re.escape(word) + r'\b', search_text):
                        score += 8.0
                else:
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
        """Оценивает нечеткие совпадения"""
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
        
        if search_lower.isdigit():
            if len(search_lower) <= 3:
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
        
        return max(0.0, score)


# Создаем глобальный экземпляр поискового движка
search_engine = ProductSearchEngine()