-- Seed categorization rules. NL-focused merchants.
-- Lower priority = checked first.

INSERT INTO rules (name, priority, description_re, category_id)
SELECT 'Albert Heijn', 10, 'AH (TO GO|XPRESS)?|ALBERT HEIJN', id FROM categories WHERE name = 'Groceries';

INSERT INTO rules (name, priority, description_re, category_id)
SELECT 'Other supermarkets', 10, 'JUMBO|LIDL|ALDI\b|PLUS SUPERMARKT|DIRK|VOMAR|EKOPLAZA|MARQT', id FROM categories WHERE name = 'Groceries';

INSERT INTO rules (name, priority, description_re, category_id)
SELECT 'Petrol stations', 10, '\b(SHELL|BP\b|ESSO|TOTAL ENERGIES|TOTAL TANK|TINQ|TANGO|TEXACO|GULF|TAMOIL|AVIA|FIRE|FASTNED|ALLEGO|IONITY)\b', id FROM categories WHERE name = 'Car: Fuel';

INSERT INTO rules (name, priority, description_re, category_id)
SELECT 'Telecoms', 10, 'KPN|T-MOBILE|VODAFONE|ZIGGO|ODIDO|TELE2|YOUFONE|SIMYO|HOLLANDSNIEUWE', id FROM categories WHERE name = 'Internet & Phone';

INSERT INTO rules (name, priority, description_re, category_id)
SELECT 'Energy', 10, 'VATTENFALL|ENECO|ESSENT|GREENCHOICE|BUDGET ENERGIE|NUON|OXXIO|PURE ENERGIE', id FROM categories WHERE name = 'Utilities';

INSERT INTO rules (name, priority, description_re, category_id)
SELECT 'Water', 10, 'VITENS|BRABANT WATER|EVIDES|WATERNET|PWN\b|WATERSCHAP', id FROM categories WHERE name = 'Utilities';

INSERT INTO rules (name, priority, description_re, category_id)
SELECT 'Streaming', 10, 'NETFLIX|SPOTIFY|DISNEY ?PLUS|YOUTUBE ?PREMIUM|HBO ?MAX|VIAPLAY|VIDEOLAND|PRIME VIDEO|APPLE\.COM/BILL', id FROM categories WHERE name = 'Subscriptions';

INSERT INTO rules (name, priority, description_re, category_id)
SELECT 'Health insurance', 10, 'ZILVEREN KRUIS|CZ\b|VGZ|MENZIS|ANDERZORG|ONVZ|DSW|ZIEKTEKOSTEN|ZORGVERZEKERING', id FROM categories WHERE name = 'Healthcare';

INSERT INTO rules (name, priority, description_re, category_id)
SELECT 'Pharmacy', 20, 'APOTHEEK|APOTHEKER|ETOS|KRUIDVAT', id FROM categories WHERE name = 'Healthcare';

INSERT INTO rules (name, priority, description_re, category_id)
SELECT 'Toeslagen incoming', 10, 'BELASTINGDIENST.*TOESLAG|HUURTOESLAG|ZORGTOESLAG|KINDEROPVANG', id FROM categories WHERE name = 'Toeslagen';

INSERT INTO rules (name, priority, description_re, category_id)
SELECT 'Car insurance', 10, 'ANWB|UNIVE|CENTRAAL BEHEER|FBTO|INSHARED|INTERPOLIS|REAAL|NATIONALE-NEDERLANDEN|AEGON|OHRA', id FROM categories WHERE name = 'Car: Insurance';

INSERT INTO rules (name, priority, description_re, category_id)
SELECT 'Road tax (MRB)', 10, 'BELASTINGDIENST.*MOTOR|MOTORRIJTUIGENBELASTING|MRB\b', id FROM categories WHERE name = 'Car: Road Tax';

INSERT INTO rules (name, priority, description_re, category_id)
SELECT 'Car maintenance / parts', 20, 'GARAGE|AUTOBEDRIJF|HALFORDS|KWIK-FIT|PROFILE|AUTOSERVICE|BANDEN', id FROM categories WHERE name = 'Car: Maintenance';

INSERT INTO rules (name, priority, description_re, category_id)
SELECT 'Parking', 10, 'PARKEREN|P\+R|Q-PARK|PARKMOBILE|YELLOWBRICK|BPP|EASYPARK', id FROM categories WHERE name = 'Car: Parking';

INSERT INTO rules (name, priority, description_re, category_id)
SELECT 'Public transport', 10, '\bNS REIZIGERS\b|GVB|RET\b|HTM\b|CONNEXXION|OV-CHIPKAART|9292|NS-GROEP|ARRIVA', id FROM categories WHERE name = 'Travel';

INSERT INTO rules (name, priority, description_re, category_id)
SELECT 'Restaurants / delivery', 50, 'RESTAURANT|CAFE|BAR\b|BRASSERIE|EETCAFE|THUISBEZORGD|UBEREATS|DELIVEROO|FLINK|GORILLAS|PIZZERIA', id FROM categories WHERE name = 'Eating Out';

INSERT INTO rules (name, priority, description_re, category_id)
SELECT 'Transfer to Trade Republic', 5, 'TRADE REPUBLIC', id FROM categories WHERE name = 'Internal Transfer';

INSERT INTO rules (name, priority, description_re, category_id)
SELECT 'Transfer to GBI Sparen', 5, 'GARANTI BBVA|GBI SPAREN', id FROM categories WHERE name = 'Internal Transfer';

INSERT INTO rules (name, priority, description_re, category_id)
SELECT 'Salary placeholder (tighten with your employer name)', 5, NULL, id FROM categories WHERE name = 'Salary';
UPDATE rules SET enabled = FALSE WHERE name LIKE 'Salary placeholder%';
