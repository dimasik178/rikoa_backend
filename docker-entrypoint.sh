#!/bin/bash
set -e

echo "🚀 Market Investment Platform - Запуск"

# === 1. Проверка .env файла ===
if [ ! -f .env ]; then
    echo "⚠️  Файл .env не найден!"
    echo "📝 Создаю .env из .env.example..."
    
    if [ -f .env.example ]; then
        cp .env.example .env
        echo "✅ Файл .env создан!"
        echo ""
        echo "⚠️  ВНИМАНИЕ: Используются значения по умолчанию!"
        echo "   Для продакшена рекомендуется изменить секретные ключи в .env"
        echo "   JWT_SECRET_KEY и SECRET_KEY должны быть уникальными!"
        echo ""
    else
        echo "❌ Файл .env.example не найден!"
        exit 1
    fi
fi

# === 2. Проверка photo_examples ===
if [ ! -d "photo_examples" ] || [ -z "$(ls -A photo_examples 2>/dev/null)" ]; then
    echo "⚠️  Папка photo_examples пуста или отсутствует!"
    mkdir -p photo_examples
    # Создаем простой placeholder
    cat > photo_examples/placeholder.txt << EOF
Для работы seed.py поместите изображения (.jpg, .png) в эту папку.
Примеры можно скачать или создать самостоятельно.
EOF
    echo "✅ Папка photo_examples создана"
fi

# === 3. Seed логика (с проверкой переменной окружения) ===
if [ "$RUN_SEED" = "true" ]; then
    if [ ! -f ".seed_done" ]; then
        echo "🌱 Заполняю базу данных..."
        python seed.py
        touch .seed_done
        echo "✅ Seed завершён"
    else
        echo "⏭️  Seed уже выполнялся ранее, пропускаю"
    fi
else
    echo "⏭️  Seed пропущен (RUN_SEED != true)"
fi

echo ""
echo "========================================"
echo "✅ Все проверки пройдены, запускаю сервер"
echo "========================================"
echo ""

# === 4. Запуск приложения ===
# exec заменяет текущий процесс на приложение
# Это позволяет корректно обрабатывать сигналы (Ctrl+C, SIGTERM)
exec "$@"