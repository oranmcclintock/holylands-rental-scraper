# config.py

# --- USER PREFERENCES ---
# The bot will IGNORE anything that doesn't match these rules.

MIN_BEDS = 3          # Minimum number of bedrooms
MAX_PRICE = 2000      # Maximum monthly rent in £
LOCATION_CODE = "bt7" # Postcode area (used for some search links)

# --- SYSTEM SETTINGS ---
DB_FILE = "seen_properties.db"
CHECK_INTERVAL_MINUTES = 15

# --- AGENT LINKS ---
# These are the search links.
# NOTE: Even though these links have filters, we DOUBLE CHECK in Python
# because agents often let "3 bed" houses slip into "4 bed" searches.

PROPBOX_AGENTS = {
    "Premier_Student": f"https://www.premierstudentproperty.com/property-to-rent/{LOCATION_CODE}/bedrooms-{MIN_BEDS}-plus/price-{MAX_PRICE}",
    "Key_Lets": f"https://www.keyletsni.com/search?bedroom_min={MIN_BEDS}&price_max={MAX_PRICE}&listing_type=let",
    "Finlay_Graham": f"https://www.finlaygrahamproperty.com/search?sta=toLet&st=rent&max={MAX_PRICE}&minbeds={MIN_BEDS}&term={LOCATION_CODE}&pt=residential"
}

CUSTOM_AGENTS = {
    "Property_People": "https://www.propertypeopleni.com/search/143265/", # Specific Student List
    "Uni_Area_Properties": f"https://www.university-area-properties.com/grid/property-for-rent/{LOCATION_CODE}/bedrooms-{MIN_BEDS}-plus/price-{MAX_PRICE}",
    "Boyle_Properties": "http://www.boyleproperties.co.uk/properties?q=&sort=+Price+%28Lowest%29+&show=Available+properties",
    "Giant_Property": "https://giantproperty.co.uk/search/181939/",
    "M_and_M_Property": f"https://www.mandmpropertyservices.com/grid/property-for-rent/{LOCATION_CODE}/bedrooms-{MIN_BEDS}-plus/price-{MAX_PRICE}",
    "Goldsmith_Estates": f"https://www.goldsmithestates.com/search?sta=toLet&st=rent&max={MAX_PRICE}&minbeds={MIN_BEDS}&term={LOCATION_CODE}&pt=residential"
}