#!/bin/bash
# Скрипт для запуска тестов

echo "🚀 Запуск тестов Telegram Daily Bot"
echo "====================================="
echo

# Цвета для вывода
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Проверка наличия pytest
if ! command -v pytest &> /dev/null; then
    echo "❌ pytest не установлен!"
    echo "Установите: pip install -r requirements-dev.txt"
    exit 1
fi

# Функция для запуска категории тестов
run_test_category() {
    local category=$1
    local description=$2
    
    echo -e "${YELLOW}📋 $description${NC}"
    if [ "$category" == "all" ]; then
        pytest -v
    else
        pytest -m $category -v
    fi
    
    if [ $? -eq 0 ]; then
        echo -e "${GREEN}✅ $description - PASSED${NC}"
    else
        echo "❌ $description - FAILED"
        return 1
    fi
    echo
}

# Парсим аргументы
case "$1" in
    unit)
        run_test_category "unit" "Unit тесты"
        ;;
    integration)
        run_test_category "integration" "Integration тесты"
        ;;
    e2e)
        run_test_category "e2e" "End-to-end тесты"
        ;;
    fast)
        pytest -v -m "not slow"
        ;;
    coverage)
        echo -e "${YELLOW}📊 Запуск тестов с покрытием${NC}"
        pytest --cov --cov-report=html --cov-report=term-missing
        echo
        echo "📄 HTML отчет: htmlcov/index.html"
        ;;
    specific)
        if [ -z "$2" ]; then
            echo "❌ Укажите файл теста: ./run_tests.sh specific tests/test_utils.py"
            exit 1
        fi
        pytest "$2" -v
        ;;
    *)
        echo "Доступные опции:"
        echo "  ./run_tests.sh unit           - Только unit тесты"
        echo "  ./run_tests.sh integration    - Только integration тесты"
        echo "  ./run_tests.sh e2e            - Только e2e тесты"
        echo "  ./run_tests.sh fast           - Быстрые тесты (без медленных)"
        echo "  ./run_tests.sh coverage       - С отчетом о покрытии"
        echo "  ./run_tests.sh specific FILE  - Конкретный файл"
        echo "  ./run_tests.sh                - Все тесты (по умолчанию)"
        echo
        
        # Запуск всех тестов по умолчанию
        run_test_category "all" "Все тесты"
        ;;
esac

exit $?

