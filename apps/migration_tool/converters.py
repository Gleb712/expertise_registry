import re
from datetime import date

# Даты раньше этого года считаются за None
MIN_VALID_YEAR = 1800

# Границы годов ввода объектов в эксплуатацию
MIN_COMMISSIONING_YEAR = 1900
MAX_COMMISSIONING_YEAR = 2100


def parse_legacy_date(text):
    # 2020-01-30 -> date(2020, 1, 30)
    if not text:
        return None
    
    text = str(text).strip()

    if text.endswith(' BC'):
        return None
    
    try:
        value = date.fromisoformat(text)
    except ValueError:
        return None
    
    if value.year < MIN_VALID_YEAR:
        return None
    
    return value


def parse_year(raw):
    """
    Год ввода в эксплуатацию
    В старой базе встречается в форматах '2020' и '30.01.2020'
    """

    if raw is None:
        return None
    
    text = str(raw).strip()
    if not text:
        return None
    
    if text.isdigit():
        year = int(text)
        return year if MIN_COMMISSIONING_YEAR <= year <= MAX_COMMISSIONING_YEAR else None
    
    # Дата в формате 30.01.2020 - год в конце
    match = re.fullmatch(r'\d{1,2}[.\-/]\d{1,2}[./\-/](\d{4})', text)
    if match:
        year = int(match.group(1))
        return year if MIN_COMMISSIONING_YEAR <= year <= MAX_COMMISSIONING_YEAR else None
    
    return None

def parse_int(raw):
    # Срок службы в годах
    if raw is None:
        return None
    
    text = str(raw).strip()
    if not text:
        return None
    
    try:
        return int(text)
    except ValueError:
        return None
    

def parse_opo_numbers(raw):
    # Собирает перечисление номеров в список номеров
    if not raw:
        return []
    
    parts = [p.strip() for p in str(raw).split(',')]
    return [p for p in parts if p]


def parse_conclusion(raw):
    # Текст решения комиссии, ключ TextChoices, возвращает None, если значение не указано
    if not raw:
        return None
    
    text = str(raw).strip().lower()

    # Порядок важен
    if 'не в полной мере' in text:
        return 'partially'
    elif 'не соответствует' in text:
        return 'non_compliant'
    elif 'соответствует' in text:
        return 'compliant'
    
    return None
