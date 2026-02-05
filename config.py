# config.py

MIN_BEDS = 4
MAX_PRICE = 1800
LOCATION_CODE = "bt7"
DB_FILE = "seen_properties.db"
CHECK_INTERVAL_MINUTES = 15

# 1. STRICT PROPBOX SITES (These worked in your log)
PROPBOX_AGENTS = {
    "Premier_Student": f"https://www.premierstudentproperty.com/property-to-rent/{LOCATION_CODE}/bedrooms-{MIN_BEDS}-plus/price-{MAX_PRICE}",
    "Key_Lets": f"https://www.keyletsni.com/search?bedroom_min={MIN_BEDS}&price_max={MAX_PRICE}&listing_type=let",
    "Finlay_Graham": f"https://www.finlaygrahamproperty.com/search?sta=toLet&st=rent&max={MAX_PRICE}&minbeds={MIN_BEDS}&term={LOCATION_CODE}&pt=residential"
}

# 2. CUSTOM / FLEXIBLE SITES (Moved back here so they work!)
CUSTOM_AGENTS = {
    "Property_People": "https://www.propertypeopleni.com/search/143265/",
    "Uni_Area_Properties": f"https://www.university-area-properties.com/grid/property-for-rent/{LOCATION_CODE}/bedrooms-{MIN_BEDS}-plus/price-{MAX_PRICE}",
    "M_and_M_Property": f"https://www.mandmpropertyservices.com/grid/property-for-rent/{LOCATION_CODE}/bedrooms-{MIN_BEDS}-plus/price-{MAX_PRICE}",
    "Goldsmith_Estates": f"https://www.goldsmithestates.com/search?sta=toLet&st=rent&max={MAX_PRICE}&minbeds={MIN_BEDS}&term={LOCATION_CODE}&pt=residential",
    "Boyle_Properties": "http://www.boyleproperties.co.uk/properties?q=&sort=+Price+%28Lowest%29+&show=Available+properties",
    "Giant_Property": "https://giantproperty.co.uk/search/181939/"
}