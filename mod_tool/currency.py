"""Item price presentation; serialized values always stay in gold pieces."""
from decimal import Decimal,InvalidOperation

def item_unit(gold):return 'bars' if gold>10000 else 'gold'

def item_amount(gold):
    if gold<=10000:return str(gold)
    text=format(Decimal(gold)/10000,'f')
    return text.rstrip('0').rstrip('.')if '.'in text else text

def item_price(gold):
    return f'{item_amount(gold)} gold bars' if gold>10000 else f'{gold:,} gold'

def parse_item_amount(text,unit):
    try:
        value=Decimal(text)*(10000 if unit=='bars' else 1)
        if not value.is_finite()or value!=value.to_integral_value():raise ValueError()
        return int(value)
    except (ValueError,InvalidOperation,OverflowError):
        raise ValueError('Enter a valid item price (1 gold bar = 10,000 gold).')
