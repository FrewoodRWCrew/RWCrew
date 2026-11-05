# Converters: each turns one kind of old list into sheets of the standard
# load workbook (load_workbook.py). Register a new one in CONVERTERS.

from masstest.convert.atelier_desk import convert_atelier_desk

CONVERTERS = {
    "atelier-desk": convert_atelier_desk,
}
