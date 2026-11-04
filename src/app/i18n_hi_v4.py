"""Hindi text added in v4 phase 8 (317 districts, 25 trades, five-year forecasts, Demand Index, capacity gap).  Same layout as i18n_hi.py.
Reviewed by the project team only: have a Hindi speaker read it before launch (district names are transliterations)."""
PAGE = {
    "Find a district": "ज़िला खोजें",
    "14 of 14": "14 में से 14",
    "2000 to 2009": "2000 से 2009",
    "2015 to 2025": "2015 से 2025",
    "23 of 23": "23 में से 23",
    "24,72,600 rows and 17 columns, January 2000 to December 2025. Forecasts use all of it.": "24,72,600 पंक्तियाँ और 17 स्तंभ, जनवरी 2000 से दिसंबर 2025। पूर्वानुमान इन सभी का उपयोग करते हैं।",
    "31 of 31": "31 में से 31",
    "317 districts in ten states.": "दस राज्यों के 317 ज़िले।",
    "33 of 33": "33 में से 33",
    "38 of 38": "38 में से 38",
    "4,75,500 forecast rows (7,925 series, 60 months) with two ranges and a confidence label each, and the Demand Index, capacity gap and flags built on them. Rerunning gives identical files, and every file carries a checksum.": "4,75,500 पूर्वानुमान पंक्तियाँ (7,925 श्रृंखलाएँ, 60 महीने), हर एक के साथ दो दायरे और एक विश्वसनीयता लेबल, और उन पर बने माँग सूचकांक, क्षमता अंतर और चेतावनी निशान। दोबारा चलाने पर वही फ़ाइलें मिलती हैं, और हर फ़ाइल के साथ चेकसम है।",
    "4,75,500 forecast rows (7,925 series, 60 months), from data up to December 2025.": "4,75,500 पूर्वानुमान पंक्तियाँ (7,925 श्रृंखलाएँ, 60 महीने), दिसंबर 2025 तक के डेटा से।",
    "4,94,520 rows and 8 columns.": "4,94,520 पंक्तियाँ और 8 स्तंभ।",
    "75 of 75": "75 में से 75",
    "82 inputs, chosen from 119 candidates by testing on the validation years. Dropping the inputs that identify a single district or sector cut the validation error for employed workers from 10.9% to 4.5%, because they let the trees memorise the period instead of the series.": "119 उम्मीदवारों में से 82 इनपुट, वैलिडेशन वर्षों के परीक्षण से चुने गए। जो इनपुट किसी एक ज़िले या सेक्टर की पहचान कराते थे, उन्हें हटाने से नियोजित कामगारों की वैलिडेशन त्रुटि 10.9% से घटकर 4.5% रह गई, क्योंकि वे पेड़ों को श्रृंखला के बजाय उस दौर को याद कर लेने देते थे।",
    "A Demand Index from 0 to 100, a capacity gap against training seats, and early warnings for the tightest and loosest tenth of districts.": "0 से 100 तक का माँग सूचकांक, प्रशिक्षण सीटों के सामने क्षमता अंतर, और सबसे तंग तथा सबसे ढीले दसवें हिस्से के ज़िलों के लिए पूर्व चेतावनी।",
    "A TPE search (Optuna), 20 trials per measure, over learning rate, tree size, penalties and sampling, scored on the validation years only. The number of trees for each twelve-month band of horizons is chosen there too.": "TPE खोज (Optuna), हर माप के लिए 20 प्रयास, लर्निंग रेट, पेड़ के आकार, दंड और नमूने पर, केवल वैलिडेशन वर्षों पर जाँची गई। बारह महीनों के हर अवधि-खंड के लिए पेड़ों की संख्या भी वहीं चुनी गई।",
    "A district is judged against its peers in the same trade, not against a fixed line.": "ज़िले को उसी ट्रेड के अपने जैसे ज़िलों से परखा जाता है, किसी तय रेखा से नहीं।",
    "A monthly panel of 7,925 series: employed workers, vacancies and registered job seekers, with wages, unemployment, training seats, demographics and four demand channels.": "7,925 श्रृंखलाओं का मासिक पैनल: नियोजित कामगार, रिक्तियाँ और पंजीकृत नौकरी चाहने वाले, साथ में मज़दूरी, बेरोज़गारी, प्रशिक्षण सीटें, जनसांख्यिकी और माँग के चार स्रोत।",
    "A number from 0 to 100 for a district and trade in a month. It compares openings per worker, from vacancies, job-portal postings and the National Career Service, with the other districts of the same trade, and adds a national level term so that it moves over the years. 50 is the median district at the 2018 to 2019 level; forecast months use the forecast vacancies only.": "एक ज़िले और ट्रेड के लिए किसी महीने का 0 से 100 तक का अंक। यह रिक्तियों, जॉब-पोर्टल पोस्टिंग और राष्ट्रीय कॅरियर सेवा से प्रति कामगार रिक्तियों की तुलना उसी ट्रेड के अन्य ज़िलों से करता है, और एक राष्ट्रीय स्तर का घटक जोड़ता है ताकि यह वर्षों में बदले। 50 का अर्थ है 2018-2019 के स्तर पर मध्य ज़िला; पूर्वानुमान के महीनों में केवल पूर्वानुमानित रिक्तियाँ ली जाती हैं।",
    "A pandemic or a new registration drive would break the pattern the models learned. The wide range allows for some of it, not all.": "कोई महामारी या नया पंजीकरण अभियान उस पैटर्न को तोड़ देगा जो मॉडलों ने सीखा है। विस्तृत दायरा उसका कुछ हिस्सा ही समेटता है, पूरा नहीं।",
    "A usual and a wider 90% range, a simple baseline to compare with and a confidence label beside every forecast.": "हर पूर्वानुमान के साथ एक सामान्य और एक विस्तृत 90% दायरा, तुलना के लिए एक सरल आधार रेखा और एक विश्वसनीयता लेबल।",
    "All 11, from New Delhi to Shahdara.": "सभी 11, नई दिल्ली से शाहदरा तक।",
    "All 14, from Thiruvananthapuram to Ernakulam.": "सभी 14, तिरुवनंतपुरम से एर्नाकुलम तक।",
    "All 23, from Amritsar to Ludhiana.": "सभी 23, अमृतसर से लुधियाना तक।",
    "All 23, from Kolkata to Darjeeling.": "सभी 23, कोलकाता से दार्जिलिंग तक।",
    "All 31, from Bengaluru Urban to Mysuru.": "सभी 31, बेंगलुरु शहरी से मैसूरु तक।",
    "All 317 districts of ten states, each forecast for five sectors. Choose a sector and a measure, hover a district for its numbers, and select a state to zoom in.": "दस राज्यों के सभी 317 ज़िले, हर एक का पाँच सेक्टरों के लिए पूर्वानुमान। सेक्टर और माप चुनें, किसी ज़िले पर जाकर उसके आँकड़े देखें, और ज़ूम करने के लिए राज्य चुनें।",
    "All 33, from Ahmedabad to Surat.": "सभी 33, अहमदाबाद से सूरत तक।",
    "All 33, from Hyderabad to Warangal.": "सभी 33, हैदराबाद से वारंगल तक।",
    "All 36, from Mumbai City and Pune to Nagpur.": "सभी 36, मुंबई शहर और पुणे से नागपुर तक।",
    "All 38, from Chennai to Coimbatore.": "सभी 38, चेन्नई से कोयंबटूर तक।",
    "All 75, from Lucknow and Agra to Varanasi.": "सभी 75, लखनऊ और आगरा से वाराणसी तक।",
    "Average bias": "औसत झुकाव",
    "Average miss (WAPE, lower is better) on the test years 2015 to 2019, one to sixty months ahead. Bias is the average over- or under-forecast. Job vacancies add little over the baseline and are slightly worse than it in the fifth year, so they carry the lowest labels. The test years are calm by design; the shock years are reported separately and the models do not beat the baseline there for job seekers.": "परीक्षण वर्षों 2015-2019 पर औसत चूक (WAPE, जितना कम उतना अच्छा), एक से साठ महीने आगे। झुकाव औसत अधिक या कम पूर्वानुमान है। रिक्तियाँ आधार रेखा पर कम ही जोड़ती हैं और पाँचवें वर्ष में उससे थोड़ी खराब हैं, इसलिए उन्हें सबसे निचले लेबल मिलते हैं। परीक्षण वर्ष जानबूझकर शांत हैं; झटके वाले वर्ष अलग बताए गए हैं और नौकरी चाहने वालों के लिए मॉडल वहाँ आधार रेखा से बेहतर नहीं हैं।",
    "Capacity gap": "क्षमता अंतर",
    "Codes from the Local Government Directory. Populations from the Census 2011 district tables, reduced where a district was split after 2011, and checked against the state totals. Growth rates and tiers are project assumptions.": "कोड स्थानीय सरकार निर्देशिका से। जनसंख्या जनगणना 2011 की ज़िला तालिकाओं से, जहाँ 2011 के बाद ज़िला बँटा वहाँ घटाई गई, और राज्यों के कुल योग से मिलाई गई। वृद्धि दर और श्रेणियाँ परियोजना की मान्यताएँ हैं।",
    "Colour all 317 districts by sector, measure and months ahead, and zoom into a state.": "सेक्टर, माप और कितने महीने आगे, के अनुसार सभी 317 ज़िलों को रंगें, और किसी राज्य में ज़ूम करें।",
    "Colours sort the 317 districts into five equal groups, so they show who is higher or lower, not by how much. Read the exact figure in the hover. The Demand Index is a position among peers from 0 to 100. Employed-worker forecasts are the most reliable and job-seeker forecasts the least, and the further ahead, the less certain. Boundaries are the Local Government Directory layer, distributed by bharatlas under CC0 or CC BY, simplified for orientation only.": "रंग 317 ज़िलों को पाँच बराबर समूहों में बाँटते हैं, इसलिए वे बताते हैं कि कौन ऊपर या नीचे है, कितना, यह नहीं। सटीक आँकड़ा ज़िले पर जाकर पढ़ें। माँग सूचकांक अपने जैसे ज़िलों के बीच 0 से 100 तक की स्थिति है। नियोजित कामगारों के पूर्वानुमान सबसे भरोसेमंद और नौकरी चाहने वालों के सबसे कम हैं, और जितना आगे देखें, अनिश्चितता उतनी बढ़ती है। सीमाएँ स्थानीय सरकार निर्देशिका की परत हैं, जिसे bharatlas CC0 या CC BY के तहत वितरित करता है, और केवल दिशा-बोध के लिए सरल की गई हैं।",
    "Counts are audited for gaps and errors, and the five trades of a sector are made to add up to the sector. Shock periods such as COVID and the e-Shram launch are marked so they cannot mislead the model.": "गिनतियों में कमियों और गलतियों की जाँच की जाती है, और किसी सेक्टर के पाँच ट्रेड उस सेक्टर के बराबर जुड़ने वाले बनाए जाते हैं। कोविड और ई-श्रम की शुरुआत जैसे झटके वाले दौर चिह्नित किए जाते हैं ताकि वे मॉडल को भटका न सकें।",
    "Dec 2025": "दिस 2025",
    "Demand Index": "माँग सूचकांक",
    "Demand Index, capacity gap and early warnings": "माँग सूचकांक, क्षमता अंतर और पूर्व चेतावनी",
    "Demand and capacity": "माँग और क्षमता",
    "Demand channels": "माँग के स्रोत",
    "Derived from the trade panel; the trades add up to the sector exactly.": "ट्रेड पैनल से निकाला गया; ट्रेड जुड़कर सेक्टर के ठीक बराबर होते हैं।",
    "District shapes for the map: the 317 districts of the ten states and an outline of the rest of India.": "मानचित्र के लिए ज़िलों के आकार: दस राज्यों के 317 ज़िले और शेष भारत की रूपरेखा।",
    "Districts are ranked within their trade, and the tightest and loosest tenth are flagged.": "ज़िलों को उनके ट्रेड के भीतर क्रमबद्ध किया जाता है, और सबसे तंग तथा सबसे ढीले दसवें हिस्से को चिह्नित किया जाता है।",
    "Districts of one trade, ranked": "एक ट्रेड के ज़िले, क्रमबद्ध",
    "Each series is forecast one to sixty months ahead, with two 90% ranges and a confidence label.": "हर श्रृंखला का एक से साठ महीने आगे पूर्वानुमान, दो 90% दायरों और एक विश्वसनीयता लेबल के साथ।",
    "Employed workers 4.61% and 4.60%, against 5.61% and 5.55% for the baseline, with no refit or tuning.": "नियोजित कामगार 4.61% और 4.60%, जबकि आधार रेखा 5.61% और 5.55%, बिना दोबारा फ़िट या ट्यूनिंग के।",
    "Employed workers, job vacancies, registered job seekers, wages, unemployment rate, training seats, certified trainees, worker shares and four demand channels, for each of 25 trades.": "नियोजित कामगार, रिक्तियाँ, पंजीकृत नौकरी चाहने वाले, मज़दूरी, बेरोज़गारी दर, प्रशिक्षण सीटें, प्रमाणित प्रशिक्षु, कामगारों के अनुपात और माँग के चार स्रोत, 25 ट्रेडों में से हर एक के लिए।",
    "Error of 16.15% against 17.63%. Slightly worse than the baseline in the first two years, 15 to 23% better in years four and five.": "त्रुटि 16.15%, आधार रेखा 17.63%। पहले दो वर्षों में आधार रेखा से थोड़ी खराब, चौथे और पाँचवें वर्ष में 15 से 23% बेहतर।",
    "Error of 4.64% against 5.65%, and better at every horizon, by 4% in the first year and 30% in the fifth.": "त्रुटि 4.64%, आधार रेखा 5.65%, और हर अवधि पर बेहतर: पहले वर्ष में 4% और पाँचवें में 30%।",
    "Errors of neighbouring series move together, so the usual range for a state or for India held only about six times in ten in calm years and almost never in the shock years. Totals show the wider range as well.": "पास की श्रृंखलाओं की त्रुटियाँ साथ-साथ चलती हैं, इसलिए किसी राज्य या भारत के लिए सामान्य दायरा शांत वर्षों में दस में केवल छह बार सही रहा और झटके वाले वर्षों में लगभग कभी नहीं। कुल योगों के साथ विस्तृत दायरा भी दिखाया जाता है।",
    "Every dashboard table downloads as CSV or JSON, and every export file carries a checksum.": "डैशबोर्ड की हर तालिका CSV या JSON में डाउनलोड होती है, और हर निर्यात फ़ाइल के साथ चेकसम होता है।",
    "Every forecast carries a usual and a wider 90% range and a confidence label, high, medium or low, earned in testing.": "हर पूर्वानुमान के साथ एक सामान्य और एक विस्तृत 90% दायरा और परीक्षण में अर्जित विश्वसनीयता लेबल, उच्च, मध्यम या निम्न, होता है।",
    "Every forecast gets two 90% ranges, set from past errors for the same horizon: a usual one from 2010 to 2019 and a wider one that also uses the shock years.": "हर पूर्वानुमान को दो 90% दायरे मिलते हैं, उसी अवधि की पिछली त्रुटियों से तय: एक सामान्य, 2010 से 2019 से, और एक विस्तृत, जो झटके वाले वर्षों को भी लेता है।",
    "Every forecast shows a usual and a wider 90% range around it, in a chart you can read month by month.": "हर पूर्वानुमान के चारों ओर एक सामान्य और एक विस्तृत 90% दायरा दिखता है, ऐसे चार्ट में जिसे आप महीने-दर-महीने पढ़ सकते हैं।",
    "Everything the forecasts are built from is listed on this page: the monthly district and trade panel, the district catalogue, the occupation list, the crosswalk that links them and the district boundaries used by the map. For each one you can see what it contains, how large it is, where it came from, and whether it is real, simulated or produced by the model.": "पूर्वानुमान जिन चीज़ों से बने हैं, वे सब इस पृष्ठ पर सूचीबद्ध हैं: मासिक ज़िला और ट्रेड पैनल, ज़िला सूची, व्यवसाय सूची, उन्हें जोड़ने वाला क्रॉसवॉक, और मानचित्र में प्रयुक्त ज़िला सीमाएँ। हर एक के बारे में आप देख सकते हैं कि उसमें क्या है, वह कितना बड़ा है, कहाँ से आया, और वह वास्तविक है, सिम्युलेटेड है या मॉडल का परिणाम।",
    "Final fit": "अंतिम फ़िट",
    "Five trades in each of five sectors, 25 in all, forecast separately in every district.": "पाँच सेक्टरों में से हर एक के पाँच ट्रेड, कुल 25, हर ज़िले में अलग-अलग पूर्वानुमानित।",
    "Five-year forecasts of employment, job vacancies and job seekers for all 317 districts of ten states, five sectors and 25 trades. Every forecast comes with a range that shows how sure we are.": "दस राज्यों के सभी 317 ज़िलों, पाँच सेक्टरों और 25 ट्रेडों के लिए रोज़गार, रिक्तियों और नौकरी चाहने वालों के पाँच वर्ष के पूर्वानुमान। हर पूर्वानुमान के साथ एक दायरा आता है जो बताता है कि हम कितने आश्वस्त हैं।",
    "Flags and the Demand Index compare a district with the other districts of the same trade in the same month.": "चेतावनी निशान और माँग सूचकांक एक ज़िले की तुलना उसी महीने उसी ट्रेड के अन्य ज़िलों से करते हैं।",
    "For combinations such as one trade across a state, no checked range exists, so only the forecast itself is drawn and the dashboard says so.": "किसी राज्य में एक ट्रेड जैसे संयोजनों के लिए कोई जाँचा हुआ दायरा नहीं है, इसलिए केवल पूर्वानुमान ही खींचा जाता है और डैशबोर्ड यह बताता है।",
    "For each of the 317 districts: official LGD code, 2011 population, annual growth rate, economic tier and state.": "317 ज़िलों में से हर एक के लिए: आधिकारिक LGD कोड, 2011 की जनसंख्या, वार्षिक वृद्धि दर, आर्थिक श्रेणी और राज्य।",
    "For every forecast month": "हर पूर्वानुमान माह के लिए",
    "For every series and month ahead: the forecast, two 90% ranges, a confidence label and an early-warning flag; the Demand Index; the capacity gap by year; the rankings.": "हर श्रृंखला और आगे के हर महीने के लिए: पूर्वानुमान, दो 90% दायरे, विश्वसनीयता लेबल और पूर्व-चेतावनी निशान; माँग सूचकांक; वर्ष के अनुसार क्षमता अंतर; रैंकिंग।",
    "Forecast for <span data-fill=\"meta.first_target\">January 2026</span> to <span data-fill=\"meta.last_target\">December 2030</span>, made from data up to <span data-fill=\"meta.origin_label\">December 2025</span>.": "पूर्वानुमान <span data-fill=\"meta.first_target\">January 2026</span> से <span data-fill=\"meta.last_target\">December 2030</span> तक, <span data-fill=\"meta.origin_label\">December 2025</span> तक के डेटा से बनाया गया।",
    "Forecast openings for each year against the training seats sanctioned in 2025 to 2026, held flat, and the trainees expected to be certified, which is the seats times the 2023 to 2025 certification rate. Seats fall short where a district's share of seats is under 0.6 times its share of openings in the trade, and exceed demand above 1.65 times.": "हर वर्ष की पूर्वानुमानित रिक्तियाँ 2025-26 में स्वीकृत प्रशिक्षण सीटों के सामने, जिन्हें स्थिर रखा गया है, और प्रमाणित होने की अपेक्षा वाले प्रशिक्षु, यानी सीटें × 2023 से 2025 की प्रमाणन दर। जहाँ ट्रेड में ज़िले की सीटों का हिस्सा रिक्तियों के हिस्से के 0.6 गुना से कम हो वहाँ सीटें कम पड़ती हैं, और 1.65 गुना से अधिक हो तो माँग से अधिक हैं।",
    "Forecast openings set against training seats and expected certified trainees, by trade, state and district.": "पूर्वानुमानित रिक्तियाँ प्रशिक्षण सीटों और अपेक्षित प्रमाणित प्रशिक्षुओं के सामने, ट्रेड, राज्य और ज़िले के अनुसार।",
    "Forecasts beyond two years rest on how districts behaved before 2020, and seeker forecasts are the least reliable. Treat the fifth year as a direction, not a figure.": "दो वर्ष से आगे के पूर्वानुमान 2020 से पहले ज़िलों के व्यवहार पर टिके हैं, और नौकरी चाहने वालों के पूर्वानुमान सबसे कम भरोसेमंद हैं। पाँचवें वर्ष को आँकड़ा नहीं, दिशा समझें।",
    "Forecasts, ranges, indexes and flags": "पूर्वानुमान, दायरे, सूचकांक और निशान",
    "Formal training capacity for the year and the number of people certified each month.": "वर्ष की औपचारिक प्रशिक्षण क्षमता और हर महीने प्रमाणित लोगों की संख्या।",
    "Four further views of hiring demand: job-portal postings, a quarterly hiring survey, National Career Service vacancies and a labour-force survey estimate. The last two start in 2015 and 2017.": "भर्ती की माँग के चार और स्रोत: जॉब-पोर्टल पोस्टिंग, तिमाही भर्ती सर्वेक्षण, राष्ट्रीय कॅरियर सेवा की रिक्तियाँ और श्रम-बल सर्वेक्षण का अनुमान। अंतिम दो 2015 और 2017 में शुरू होते हैं।",
    "From January 2000": "जनवरी 2000 से",
    "From monthly counts to a five-year view.": "मासिक गिनतियों से पाँच वर्ष की तस्वीर तक।",
    "From raw counts to published forecasts.": "कच्ची गिनतियों से प्रकाशित पूर्वानुमानों तक।",
    "Generalist medical practitioners (2211); specialist medical practitioners (2212); nursing professionals (2221); laboratory technicians (3212); nursing associate professionals (3221).": "सामान्य चिकित्सक (2211); विशेषज्ञ चिकित्सक (2212); नर्सिंग पेशेवर (2221); प्रयोगशाला तकनीशियन (3212); नर्सिंग सहायक पेशेवर (3221)।",
    "Generated by the project's simulator (fixed random seed) so that it behaves like official statistics. No public source reports these counts by district and trade.": "परियोजना के सिम्युलेटर (तय रैंडम सीड) से बनाया गया ताकि यह आधिकारिक आँकड़ों जैसा व्यवहार करे। कोई सार्वजनिक स्रोत ज़िले और ट्रेड के अनुसार ये गिनतियाँ नहीं देता।",
    "Gujarat": "गुजरात",
    "House builders (7111); bricklayers (7112); carpenters and joiners (7115); plumbers and pipe fitters (7126); building construction labourers (9313).": "घर बनाने वाले (7111); राजमिस्त्री (7112); बढ़ई और जोड़ने वाले (7115); प्लंबर और पाइप फ़िटर (7126); भवन निर्माण मज़दूर (9313)।",
    "How the forecasts did on years they had not seen.": "पूर्वानुमान उन वर्षों में कैसे रहे जो उसने नहीं देखे थे।",
    "In 2020 to 2025 employed workers were still 14% closer than the baseline, but the models under-forecast the jump in registered job seekers by 41%.": "2020 से 2025 में नियोजित कामगारों के लिए मॉडल आधार रेखा से फिर भी 14% करीब थे, पर पंजीकृत नौकरी चाहने वालों की उछाल का पूर्वानुमान 41% कम रहा।",
    "In each trade and month, districts are ranked by forecast vacancies per registered seeker. The top tenth is a shortage alert and the bottom tenth an oversupply alert; the next fifteen per cent either side is a watch. The flag is relative: it says which districts stand out, not that openings exceed seekers.": "हर ट्रेड और महीने में ज़िलों को प्रति पंजीकृत नौकरी चाहने वाले पूर्वानुमानित रिक्तियों के अनुसार क्रमबद्ध किया जाता है। शीर्ष दसवाँ हिस्सा कमी की चेतावनी और निचला दसवाँ हिस्सा अधिशेष की चेतावनी है; दोनों ओर के अगले पंद्रह प्रतिशत निगरानी हैं। निशान सापेक्ष है: यह बताता है कि कौन-से ज़िले अलग दिखते हैं, यह नहीं कि रिक्तियाँ नौकरी चाहने वालों से अधिक हैं।",
    "Index, flag and compare": "सूचकांक, निशान और तुलना",
    "Index, flags and files": "सूचकांक, निशान और फ़ाइलें",
    "India trains lakhs of candidates every year, but training capacity is often out of step with what employers need in a district and trade. Planners usually find out only after placement results arrive. This project forecasts employment, job vacancies and registered job seekers for every district and trade, five years ahead, with a range and a confidence label on every number, and sets the forecast openings against the training seats on offer, so that seats, camps and attention can go where they are needed.": "भारत हर साल लाखों उम्मीदवारों को प्रशिक्षित करता है, पर प्रशिक्षण क्षमता अक्सर उस माँग से मेल नहीं खाती जो किसी ज़िले और ट्रेड में नियोक्ताओं को चाहिए। योजनाकारों को आमतौर पर प्लेसमेंट के नतीजे आने के बाद ही पता चलता है। यह परियोजना हर ज़िले और ट्रेड के लिए रोज़गार, रिक्तियों और पंजीकृत नौकरी चाहने वालों का पाँच वर्ष आगे का पूर्वानुमान देती है, हर संख्या पर दायरे और विश्वसनीयता लेबल के साथ, और पूर्वानुमानित रिक्तियों को उपलब्ध प्रशिक्षण सीटों के सामने रखती है, ताकि सीटें, शिविर और ध्यान वहाँ जाएँ जहाँ उनकी ज़रूरत है।",
    "Inputs": "इनपुट",
    "It behaves like official statistics but describes no real district, so no figure is an official statistic.": "यह आधिकारिक आँकड़ों जैसा व्यवहार करता है पर किसी वास्तविक ज़िले का वर्णन नहीं करता, इसलिए कोई भी संख्या आधिकारिक आँकड़ा नहीं है।",
    "It is scored once on 2015 to 2019, then once on the shock years 2020 to 2025, against simple forecasts that need no model.": "इसे एक बार 2015 से 2019 पर, फिर एक बार झटके वाले वर्षों 2020 से 2025 पर, ऐसे सरल पूर्वानुमानों के सामने जाँचा जाता है जिन्हें मॉडल नहीं चाहिए।",
    "Jan 2000": "जन 2000",
    "Job vacancies 85% and job seekers 64%: the range for seekers is too narrow, which is why the wider range is shown too.": "रिक्तियाँ 85% और नौकरी चाहने वाले 64%: चाहने वालों का दायरा बहुत संकरा है, इसीलिए विस्तृत दायरा भी दिखाया जाता है।",
    "Job-seeker forecasts, vacancies in the fifth year, and anything in a shock year are weaker, and the site says so beside the numbers.": "नौकरी चाहने वालों के पूर्वानुमान, पाँचवें वर्ष की रिक्तियाँ और झटके वाले वर्ष की हर चीज़ कमज़ोर हैं, और साइट यह संख्याओं के पास ही बताती है।",
    "Judge on unseen years": "अनदेखे वर्षों पर परखें",
    "Karnataka": "कर्नाटक",
    "Keep the assumptions visible": "मान्यताएँ दिखती रहें",
    "Kerala": "केरल",
    "Limits stated plainly, so that the numbers are read as they deserve.": "सीमाएँ सीधे शब्दों में, ताकि संख्याएँ उतनी ही गंभीरता से पढ़ी जाएँ जितनी वे हक़दार हैं।",
    "Links each of the five sectors to its NIC divisions and its five NCO-2015 trades.": "पाँचों सेक्टरों में से हर एक को उसके NIC प्रभागों और पाँच NCO-2015 ट्रेडों से जोड़ता है।",
    "Long horizons are looser": "लंबी अवधि ढीली है",
    "Medium or low": "मध्यम या निम्न",
    "Miss of 16.15% against 17.63%. The 2020 to 2025 shock was not foreseen, and seekers are the least reliable measure.": "चूक 16.15%, आधार रेखा 17.63%। 2020 से 2025 का झटका पूर्वानुमानित नहीं था, और नौकरी चाहने वाले सबसे कम भरोसेमंद माप हैं।",
    "Miss of 4.64% against 5.65%. Test period 2015 to 2019, opened once.": "चूक 4.64%, आधार रेखा 5.65%। परीक्षण अवधि 2015 से 2019, एक बार खोली गई।",
    "Monthly counts of employed workers, job vacancies and registered job seekers, back to January 2000.": "नियोजित कामगारों, रिक्तियों और पंजीकृत नौकरी चाहने वालों की मासिक गिनतियाँ, जनवरी 2000 तक पीछे।",
    "Monthly counts of employed workers, vacancies and registered job seekers, for 7,925 district and trade series.": "नियोजित कामगारों, रिक्तियों और पंजीकृत नौकरी चाहने वालों की मासिक गिनतियाँ, 7,925 ज़िला और ट्रेड श्रृंखलाओं के लिए।",
    "Monthly district and sector table": "मासिक ज़िला और सेक्टर तालिका",
    "Monthly district and trade panel": "मासिक ज़िला और ट्रेड पैनल",
    "Mostly high": "अधिकतर उच्च",
    "Mostly medium": "अधिकतर मध्यम",
    "Next 60 months": "अगले 60 महीने",
    "No public source reports these counts by district and trade, so every count on this site is simulated to behave like official statistics. The codes, populations and boundaries are real. The forecasts are real model output on that simulated history.": "कोई सार्वजनिक स्रोत ये गिनतियाँ ज़िले और ट्रेड के अनुसार नहीं देता, इसलिए इस साइट की हर गिनती आधिकारिक आँकड़ों जैसा व्यवहार करने के लिए सिम्युलेट की गई है। कोड, जनसंख्या और सीमाएँ वास्तविक हैं। पूर्वानुमान उस सिम्युलेटेड इतिहास पर मॉडल के वास्तविक परिणाम हैं।",
    "Not luck": "संयोग नहीं",
    "One monthly panel with a row for every district, trade and month. It is simulated to behave like official statistics; where each part came from is listed on the <a class=\"ulink\" href=\"resources.html#datasets\">Resources</a> page.": "हर ज़िले, ट्रेड और महीने की एक पंक्ति वाला एक मासिक पैनल। इसे आधिकारिक सांख्यिकी की तरह व्यवहार करने के लिए सिम्युलेट किया गया है; हर हिस्सा कहाँ से आया, यह <a class=\"ulink\" href=\"resources.html#datasets\">संसाधन</a> पृष्ठ पर दिया है।",
    "One number from 0 to 100 for how strong hiring demand is in a district and trade, now and for every month to 2030.": "किसी ज़िले और ट्रेड में भर्ती की माँग कितनी मज़बूत है, इसका 0 से 100 तक का एक अंक, अभी और 2030 तक हर महीने के लिए।",
    "One to sixty months ahead, each with a 90% range and a simple baseline to compare against.": "एक से साठ महीने आगे, हर एक के साथ 90% दायरा और तुलना के लिए एक सरल आधार रेखा।",
    "One to sixty months ahead. The range widens the further we look.": "एक से साठ महीने आगे। जितना आगे देखें, दायरा उतना चौड़ा होता है।",
    "Oversupply alerts 71%. One to twelve months ahead, on the test years.": "अधिशेष चेतावनियाँ 71%। एक से बारह महीने आगे, परीक्षण वर्षों पर।",
    "Produced by the model from the simulated panel. Rerunning gives identical files, and every file carries a checksum.": "सिम्युलेटेड पैनल से मॉडल द्वारा बनाया गया। दोबारा चलाने पर वही फ़ाइलें मिलती हैं, और हर फ़ाइल के साथ चेकसम है।",
    "Punjab": "पंजाब",
    "Ranges for some views are missing": "कुछ दृश्यों के लिए दायरे नहीं हैं",
    "Recent movement, level against the recent average, volatility, vacancy and seeker rates, training and wage ratios and the demand channels, all built only from data up to the forecast month: 82 inputs.": "हाल की चाल, हालिया औसत के मुकाबले स्तर, उतार-चढ़ाव, रिक्ति और नौकरी चाहने वालों की दरें, प्रशिक्षण और मज़दूरी के अनुपात और माँग के स्रोत, सब केवल पूर्वानुमान माह तक के डेटा से बने: 82 इनपुट।",
    "Reconcile": "मिलान",
    "Seats are held flat": "सीटें स्थिर मानी गई हैं",
    "Sector to trade crosswalk": "सेक्टर से ट्रेड क्रॉसवॉक",
    "Sectors and trades": "सेक्टर और ट्रेड",
    "See every district of a trade in order, and which are heading into the tightest or loosest tenth.": "किसी ट्रेड के हर ज़िले को क्रम में देखें, और कौन-से सबसे तंग या सबसे ढीले दसवें हिस्से की ओर जा रहे हैं।",
    "Series and time": "श्रृंखला और समय",
    "Shock years": "झटके वाले वर्ष",
    "Shocks cannot be forecast": "झटकों का पूर्वानुमान नहीं हो सकता",
    "Sixty months ahead for 7,925 district and trade series, from January 2026 to December 2030.": "7,925 ज़िला और ट्रेड श्रृंखलाओं के लिए साठ महीने आगे, जनवरी 2026 से दिसंबर 2030 तक।",
    "State averages hide the districts where openings and job seekers are drifting apart. Each of the 317 districts is forecast on its own, trade by trade, and compared with its peers.": "राज्य के औसत उन ज़िलों को छिपा देते हैं जहाँ रिक्तियाँ और नौकरी चाहने वाले अलग दिशाओं में जा रहे हैं। 317 ज़िलों में से हर एक का पूर्वानुमान अलग से, ट्रेड-दर-ट्रेड, किया जाता है और अपने जैसे ज़िलों से तुलना की जाती है।",
    "System analysts (2511); software developers (2512); web and multimedia developers (2513); applications programmers (2514); ICT user support technicians (3512).": "सिस्टम विश्लेषक (2511); सॉफ़्टवेयर डेवलपर (2512); वेब और मल्टीमीडिया डेवलपर (2513); एप्लिकेशन प्रोग्रामर (2514); ICT उपयोगकर्ता सहायता तकनीशियन (3512)।",
    "Tailors and dressmakers (7531); sewing and embroidery workers (7533); spinning and winding machine operators (8151); weaving and knitting machine operators (8152); sewing machine operators (8153).": "दर्ज़ी और पोशाक बनाने वाले (7531); सिलाई और कढ़ाई कामगार (7533); कताई और लपेटने की मशीन चालक (8151); बुनाई और निटिंग मशीन चालक (8152); सिलाई मशीन चालक (8153)।",
    "Telangana": "तेलंगाना",
    "The Demand Index and the capacity gap are computed, districts are ranked and flagged, and the files are published with checksums.": "माँग सूचकांक और क्षमता अंतर निकाले जाते हैं, ज़िलों को क्रमबद्ध और चिह्नित किया जाता है, और फ़ाइलें चेकसम के साथ प्रकाशित होती हैं।",
    "The Demand Index, the capacity gap, the early-warning flags and the confidence labels are computed for every series, and the files are written with checksums.": "माँग सूचकांक, क्षमता अंतर, पूर्व-चेतावनी निशान और विश्वसनीयता लेबल हर श्रृंखला के लिए निकाले जाते हैं, और फ़ाइलें चेकसम के साथ लिखी जाती हैं।",
    "The capacity gap assumes today's seats for every year to 2030, and reads best as a ranking of where capacity is stretched rather than a count of unfilled places.": "क्षमता अंतर 2030 तक हर वर्ष के लिए आज की सीटें मानता है, और इसे खाली स्थानों की गिनती के बजाय इस क्रम के रूप में पढ़ना बेहतर है कि क्षमता कहाँ तनी हुई है।",
    "The data is simulated": "डेटा सिम्युलेटेड है",
    "The declared settings are refitted on all data to December 2025, with nothing re-tuned. The training pairs that reach into the 2020 to 2023 shock and recovery are left out, so the forecasts do not repeat that jump as if it were a normal month.": "घोषित सेटिंग्स को दिसंबर 2025 तक के सारे डेटा पर दोबारा फ़िट किया जाता है, कुछ भी दोबारा ट्यून नहीं होता। 2020 से 2023 के झटके और सुधार तक पहुँचने वाले प्रशिक्षण जोड़े छोड़ दिए जाते हैं, ताकि पूर्वानुमान उस उछाल को सामान्य महीने की तरह न दोहराएँ।",
    "The district and trade of each row (district LGD code plus trade code) and its month, from January 2000 to December 2025.": "हर पंक्ति का ज़िला और ट्रेड (ज़िले का LGD कोड और ट्रेड कोड) और उसका महीना, जनवरी 2000 से दिसंबर 2025 तक।",
    "The engine is built to be believed only as far as it has earned. It forecasts three measures for every district and trade, and it is judged against simple baselines on years it has never seen. These principles shape every choice.": "इंजन को इतना ही माने जाने के लिए बनाया गया है जितना उसने कमाया है। यह हर ज़िले और ट्रेड के लिए तीन माप का पूर्वानुमान देता है, और उन वर्षों पर सरल आधार रेखाओं के सामने परखा जाता है जो उसने कभी नहीं देखे। ये सिद्धांत हर चुनाव को आकार देते हैं।",
    "The female share, the graduate share and the share aged 15 to 24 among a trade's workers.": "किसी ट्रेड के कामगारों में महिलाओं का हिस्सा, स्नातकों का हिस्सा और 15 से 24 वर्ष के लोगों का हिस्सा।",
    "The five trades of a district and sector are made to add up exactly to the sector forecast, so totals at every level agree.": "किसी ज़िले और सेक्टर के पाँच ट्रेड ठीक सेक्टर के पूर्वानुमान के बराबर जुड़ने वाले बनाए जाते हैं, ताकि हर स्तर के कुल योग मेल खाएँ।",
    "The five trades of each sector added up, for each district.": "हर ज़िले के लिए हर सेक्टर के पाँच ट्रेड जोड़कर।",
    "The model learns recent movement, trends and seasonal patterns, using only what was known at each forecast date. Settings are tuned on 2010 to 2014.": "मॉडल हाल की चाल, रुझान और मौसमी पैटर्न सीखता है, केवल वही उपयोग करते हुए जो हर पूर्वानुमान तिथि पर ज्ञात था। सेटिंग्स 2010 से 2014 पर ट्यून की जाती हैं।",
    "The same four steps run for every one of the 7,925 series. Pick a step to see it.": "यही चार चरण 7,925 श्रृंखलाओं में से हर एक के लिए चलते हैं। देखने के लिए कोई चरण चुनें।",
    "The same three counts, every month, for 317 districts and 25 trades.": "वही तीन गिनतियाँ, हर महीने, 317 ज़िलों और 25 ट्रेडों के लिए।",
    "The test years 2015 to 2019 and the shock years 2020 to 2025 were each opened once, after the settings were fixed, and scored against the best of three simple forecasts. Errors are averaged over one to sixty months ahead.": "परीक्षण वर्ष 2015 से 2019 और झटके वाले वर्ष 2020 से 2025 हर एक को सेटिंग्स तय होने के बाद एक बार खोला गया और तीन सरल पूर्वानुमानों में सबसे अच्छे के सामने जाँचा गया। त्रुटियाँ एक से साठ महीने आगे पर औसत की गई हैं।",
    "Three readings built on the forecasts, each defined in a few lines so that it can be checked.": "पूर्वानुमानों पर बने तीन पाठ, हर एक को कुछ पंक्तियों में परिभाषित किया गया है ताकि उसकी जाँच हो सके।",
    "Three simple forecasts sit beside the model, and the best of them in each case is the comparison, so anyone can see how much the model adds, and where it adds little.": "मॉडल के साथ तीन सरल पूर्वानुमान रखे जाते हैं, और हर मामले में उनमें सबसे अच्छा तुलना का आधार है, ताकि कोई भी देख सके कि मॉडल कितना जोड़ता है और कहाँ कम जोड़ता है।",
    "Totals need the wider range": "कुल योगों के लिए विस्तृत दायरा चाहिए",
    "Trade by trade": "ट्रेड-दर-ट्रेड",
    "Trades (NCO-2015 occupation codes)": "ट्रेड (NCO-2015 व्यवसाय कोड)",
    "Trained on 2000 to 2009, tuned on 2010 to 2014, tested once on 2015 to 2019 and once on 2020 to 2025. The split is by calendar time, never random.": "2000 से 2009 पर प्रशिक्षित, 2010 से 2014 पर ट्यून, 2015 से 2019 पर एक बार और 2020 से 2025 पर एक बार परीक्षित। विभाजन कैलेंडर समय से होता है, कभी रैंडम नहीं।",
    "Training seats are held at today's level because no seat plans are forecast, and the page where seats are compared with openings says so.": "प्रशिक्षण सीटें आज के स्तर पर रखी गई हैं क्योंकि सीट योजनाओं का पूर्वानुमान नहीं होता, और जिस पृष्ठ पर सीटों की रिक्तियों से तुलना होती है वह यह बताता है।",
    "Uttar Pradesh": "उत्तर प्रदेश",
    "Vacancies 85%, job seekers 64%; a wider range is shown too, because calm-year ranges are too narrow for shocks.": "रिक्तियाँ 85%, नौकरी चाहने वाले 64%; विस्तृत दायरा भी दिखाया जाता है, क्योंकि शांत वर्षों के दायरे झटकों के लिए बहुत संकरे हैं।",
    "Validation and testing are split by calendar time. The test years 2015 to 2019 and the shock years 2020 to 2025 were each opened once, and nothing was changed afterwards.": "वैलिडेशन और परीक्षण कैलेंडर समय से बाँटे जाते हैं। परीक्षण वर्ष 2015 से 2019 और झटके वाले वर्ष 2020 से 2025 हर एक को एक बार खोला गया, और उसके बाद कुछ नहीं बदला गया।",
    "Websites: <a class=\"ulink\" href=\"https://lgdirectory.gov.in/\">lgdirectory.gov.in</a>, <a class=\"ulink\" href=\"https://censusindia.gov.in/\">censusindia.gov.in</a>": "वेबसाइटें: <a class=\"ulink\" href=\"https://lgdirectory.gov.in/\">lgdirectory.gov.in</a>, <a class=\"ulink\" href=\"https://censusindia.gov.in/\">censusindia.gov.in</a>",
    "Welders and flame cutters (7212); metal working machine tool setters and operators (7223); machinery mechanics and repairers (7233); chemical products plant and machine operators (8131); electrical and electronic equipment assemblers (8212).": "वेल्डर और ज्वाला काटने वाले (7212); धातु कार्य मशीन टूल सेटर और ऑपरेटर (7223); मशीनरी मिस्त्री और मरम्मत करने वाले (7233); रासायनिक उत्पाद संयंत्र और मशीन ऑपरेटर (8131); बिजली और इलेक्ट्रॉनिक उपकरण असेंबलर (8212)।",
    "What to keep in mind": "ध्यान में रखने योग्य बातें",
    "XGBoost histogram trees. Three measures, three random starts each: nine models in the final fit.": "XGBoost हिस्टोग्राम ट्री। तीन माप, हर एक के तीन रैंडम आरंभ: अंतिम फ़िट में नौ मॉडल।",
    "XGBoost, a gradient-boosted tree method. One model per measure forecasts the change in the log of the level, with the number of months ahead as an input, for every horizon from 1 to 60, averaged over three random starts.": "XGBoost, ग्रेडिएंट-बूस्टेड ट्री विधि। हर माप का एक मॉडल स्तर के लघुगणक में बदलाव का पूर्वानुमान देता है, कितने महीने आगे यह एक इनपुट के रूप में रहता है, 1 से 60 तक हर अवधि के लिए, तीन रैंडम आरंभों के औसत से।",
    "columns, from identity to demand channels": "स्तंभ, पहचान से लेकर माँग के स्रोतों तक",
    "district and trade series, every one forecast": "ज़िला और ट्रेड श्रृंखलाएँ, हर एक का पूर्वानुमान",
    "five years early.": "पाँच साल पहले।",
    "months ahead, January 2026 to December 2030": "महीने आगे, जनवरी 2026 से दिसंबर 2030",
    "months, January 2000 to December 2025": "महीने, जनवरी 2000 से दिसंबर 2025",
    "of employed-worker outcomes fell inside the usual 90% range.": "नियोजित कामगारों के नतीजे सामान्य 90% दायरे के भीतर रहे।",
    "of shortage alerts really were in the top tenth, 7 times better than chance.": "कमी की चेतावनियाँ वास्तव में शीर्ष दसवें हिस्से में थीं, संयोग से 7 गुना बेहतर।",
    "rows, one per district, trade and month": "पंक्तियाँ, हर ज़िले, ट्रेड और महीने की एक",
    "sectors and 25 trades, from manufacturing to healthcare": "सेक्टर और 25 ट्रेड, विनिर्माण से स्वास्थ्य सेवा तक",
    "series: 317 districts and 25 trades": "श्रृंखलाएँ: 317 ज़िले और 25 ट्रेड",
    "states, every district included": "राज्य, हर ज़िला शामिल",
    "were not foreseen, and the site says so.": "का पूर्वानुमान नहीं था, और साइट यह कहती है।",
}
ATTR = {}
JS = {
    "Choose a district": "ज़िला चुनें",
    "Demand Index": "माँग सूचकांक",
    "All ten states": "सभी दस राज्य",
    "{n} districts in ten states": "दस राज्यों के {n} ज़िले",
    "Map of the {c} districts, coloured by {m} for {s}, {n} ahead": "{c} ज़िलों का मानचित्र, {s} के लिए {m} से रंगा हुआ, {n} आगे",
    "varies by trade": "ट्रेड के अनुसार बदलता है",
    "varies by sector": "सेक्टर के अनुसार बदलता है",
    "the larger district-trade series with a medium-confidence 12-month vacancy forecast whose 60-month vacancy forecast grows fastest relative to its seeker forecast": "बड़ी ज़िला-ट्रेड श्रृंखला, जिसका 12 महीने का रिक्ति पूर्वानुमान मध्यम विश्वसनीयता का है और जिसका 60 महीने का रिक्ति पूर्वानुमान नौकरी चाहने वालों के पूर्वानुमान की तुलना में सबसे तेज़ बढ़ता है",
}
NAMES = {
    "Gujarat": "गुजरात",
    "Karnataka": "कर्नाटक",
    "Kerala": "केरल",
    "Punjab": "पंजाब",
    "Telangana": "तेलंगाना",
    "Uttar Pradesh": "उत्तर प्रदेश",
    "Agra": "आगरा",
    "Aligarh": "अलीगढ़",
    "Prayagraj": "प्रयागराज",
    "Ambedkar Nagar": "आंबेडकर नगर",
    "Auraiya": "औरैया",
    "Azamgarh": "आज़मगढ़",
    "Baghpat": "बागपत",
    "Bahraich": "बहराइच",
    "Ballia": "बलिया",
    "Balrampur": "बलरामपुर",
    "Banda": "बांदा",
    "Barabanki": "बाराबंकी",
    "Bareilly": "बरेली",
    "Basti": "बस्ती",
    "Bijnor": "बिजनौर",
    "Budaun": "बदायूँ",
    "Bulandshahr": "बुलंदशहर",
    "Chandauli": "चंदौली",
    "Chitrakoot": "चित्रकूट",
    "Deoria": "देवरिया",
    "Etah": "एटा",
    "Etawah": "इटावा",
    "Ayodhya": "अयोध्या",
    "Farrukhabad": "फ़र्रुख़ाबाद",
    "Fatehpur": "फ़तेहपुर",
    "Firozabad": "फ़िरोज़ाबाद",
    "Gautam Buddha Nagar": "गौतम बुद्ध नगर",
    "Ghaziabad": "ग़ाज़ियाबाद",
    "Ghazipur": "ग़ाज़ीपुर",
    "Gonda": "गोंडा",
    "Gorakhpur": "गोरखपुर",
    "Hamirpur": "हमीरपुर",
    "Hardoi": "हरदोई",
    "Jalaun": "जालौन",
    "Jaunpur": "जौनपुर",
    "Jhansi": "झाँसी",
    "Amroha": "अमरोहा",
    "Kannauj": "कन्नौज",
    "Kanpur Dehat": "कानपुर देहात",
    "Kanpur Nagar": "कानपुर नगर",
    "Kaushambi": "कौशांबी",
    "Lakhimpur Kheri": "लखीमपुर खीरी",
    "Kushinagar": "कुशीनगर",
    "Lalitpur": "ललितपुर",
    "Lucknow": "लखनऊ",
    "Hathras": "हाथरस",
    "Maharajganj": "महराजगंज",
    "Mahoba": "महोबा",
    "Mainpuri": "मैनपुरी",
    "Mathura": "मथुरा",
    "Mau": "मऊ",
    "Meerut": "मेरठ",
    "Mirzapur": "मिर्ज़ापुर",
    "Moradabad": "मुरादाबाद",
    "Muzaffarnagar": "मुज़फ़्फ़रनगर",
    "Pilibhit": "पीलीभीत",
    "Pratapgarh": "प्रतापगढ़",
    "Raebareli": "रायबरेली",
    "Rampur": "रामपुर",
    "Saharanpur": "सहारनपुर",
    "Sant Kabir Nagar": "संत कबीर नगर",
    "Bhadohi": "भदोही",
    "Shahjahanpur": "शाहजहाँपुर",
    "Shrawasti": "श्रावस्ती",
    "Siddharthnagar": "सिद्धार्थनगर",
    "Sitapur": "सीतापुर",
    "Sonbhadra": "सोनभद्र",
    "Sultanpur": "सुल्तानपुर",
    "Unnao": "उन्नाव",
    "Varanasi": "वाराणसी",
    "Kasganj": "कासगंज",
    "Amethi": "अमेठी",
    "Sambhal": "संभल",
    "Shamli": "शामली",
    "Hapur": "हापुड़",
    "Amritsar": "अमृतसर",
    "Bathinda": "बठिंडा",
    "Faridkot": "फ़रीदकोट",
    "Fatehgarh Sahib": "फ़तेहगढ़ साहिब",
    "Firozpur": "फ़िरोज़पुर",
    "Gurdaspur": "गुरदासपुर",
    "Hoshiarpur": "होशियारपुर",
    "Jalandhar": "जालंधर",
    "Kapurthala": "कपूरथला",
    "Ludhiana": "लुधियाना",
    "Mansa": "मानसा",
    "Moga": "मोगा",
    "Sri Muktsar Sahib": "श्री मुक्तसर साहिब",
    "Shaheed Bhagat Singh Nagar": "शहीद भगत सिंह नगर",
    "Patiala": "पटियाला",
    "Rupnagar": "रूपनगर",
    "Sangrur": "संगरूर",
    "Barnala": "बरनाला",
    "SAS Nagar (Mohali)": "एसएएस नगर (मोहाली)",
    "Tarn Taran": "तरन तारन",
    "Fazilka": "फ़ाज़िल्का",
    "Pathankot": "पठानकोट",
    "Malerkotla": "मलेरकोटला",
    "Cooch Behar": "कूच बिहार",
    "Dakshin Dinajpur": "दक्षिण दिनाजपुर",
    "Uttar Dinajpur": "उत्तर दिनाजपुर",
    "Malda": "मालदा",
    "Purba Medinipur": "पूर्व मेदिनीपुर",
    "Paschim Medinipur": "पश्चिम मेदिनीपुर",
    "Ahmedabad": "अहमदाबाद",
    "Amreli": "अमरेली",
    "Anand": "आणंद",
    "Banaskantha": "बनासकांठा",
    "Bharuch": "भरूच",
    "Bhavnagar": "भावनगर",
    "The Dangs": "डांग",
    "Dahod": "दाहोद",
    "Gandhinagar": "गांधीनगर",
    "Jamnagar": "जामनगर",
    "Junagadh": "जूनागढ़",
    "Kutch": "कच्छ",
    "Kheda": "खेड़ा",
    "Mehsana": "मेहसाणा",
    "Narmada": "नर्मदा",
    "Navsari": "नवसारी",
    "Panchmahal": "पंचमहाल",
    "Patan": "पाटन",
    "Porbandar": "पोरबंदर",
    "Rajkot": "राजकोट",
    "Sabarkantha": "साबरकांठा",
    "Surat": "सूरत",
    "Surendranagar": "सुरेंद्रनगर",
    "Vadodara": "वडोदरा",
    "Valsad": "वलसाड",
    "Tapi": "तापी",
    "Chhota Udaipur": "छोटा उदयपुर",
    "Mahisagar": "महीसागर",
    "Aravalli": "अरावली",
    "Morbi": "मोरबी",
    "Devbhumi Dwarka": "देवभूमि द्वारका",
    "Gir Somnath": "गिर सोमनाथ",
    "Botad": "बोटाद",
    "Adilabad": "आदिलाबाद",
    "Hyderabad": "हैदराबाद",
    "Karimnagar": "करीमनगर",
    "Khammam": "खम्मम",
    "Mahbubnagar": "महबूबनगर",
    "Medak": "मेदक",
    "Nalgonda": "नलगोंडा",
    "Nizamabad": "निज़ामाबाद",
    "Rangareddy": "रंगारेड्डी",
    "Warangal": "वारंगल",
    "Nirmal": "निर्मल",
    "Jagitial": "जगित्याल",
    "Peddapalli": "पेद्दापल्ली",
    "Rajanna Sircilla": "राजन्ना सिरसिल्ला",
    "Mancherial": "मंचिरियल",
    "Kamareddy": "कामारेड्डी",
    "Hanumakonda": "हनुमकोंडा",
    "Jayashankar Bhupalapally": "जयशंकर भूपालपल्ली",
    "Mahabubabad": "महबूबाबाद",
    "Jangoan": "जनगाँव",
    "Bhadradri Kothagudem": "भद्राद्रि कोठागुडेम",
    "Sangareddy": "संगारेड्डी",
    "Siddipet": "सिद्दिपेट",
    "Wanaparthy": "वनपर्ती",
    "Nagarkurnool": "नागरकर्नूल",
    "Jogulamba Gadwal": "जोगुलांबा गडवाल",
    "Suryapet": "सूर्यापेट",
    "Yadadri Bhuvanagiri": "यादाद्रि भुवनगिरि",
    "Vikarabad": "विकाराबाद",
    "Komaram Bheem Asifabad": "कोमरम भीम आसिफाबाद",
    "Medchal-Malkajgiri": "मेडचल-मलकाजगिरि",
    "Mulugu": "मुलुगु",
    "Narayanpet": "नारायणपेट",
    "Bagalkot": "बागलकोट",
    "Bengaluru Urban": "बेंगलुरु शहरी",
    "Bengaluru Rural": "बेंगलुरु ग्रामीण",
    "Belagavi": "बेलगावी",
    "Ballari": "बल्लारी",
    "Bidar": "बीदर",
    "Vijayapura": "विजयपुरा",
    "Chamarajanagar": "चामराजनगर",
    "Chikkamagaluru": "चिक्कमगलूरु",
    "Chitradurga": "चित्रदुर्ग",
    "Dakshina Kannada": "दक्षिण कन्नड़",
    "Davangere": "दावणगेरे",
    "Dharwad": "धारवाड़",
    "Gadag": "गदग",
    "Kalaburagi": "कलबुर्गी",
    "Hassan": "हासन",
    "Haveri": "हावेरी",
    "Kodagu": "कोडगु",
    "Kolar": "कोलार",
    "Koppal": "कोप्पल",
    "Mandya": "मांड्या",
    "Mysuru": "मैसूरु",
    "Raichur": "रायचूर",
    "Shivamogga": "शिवमोग्गा",
    "Tumakuru": "तुमकूरु",
    "Udupi": "उडुपी",
    "Uttara Kannada": "उत्तर कन्नड़",
    "Chikkaballapur": "चिक्कबल्लापुर",
    "Ramanagara": "रामनगर",
    "Yadgir": "यादगीर",
    "Vijayanagar": "विजयनगर",
    "Alappuzha": "आलप्पुझा",
    "Ernakulam": "एर्नाकुलम",
    "Idukki": "इडुक्की",
    "Kannur": "कन्नूर",
    "Kasaragod": "कासरगोड",
    "Kollam": "कोल्लम",
    "Kottayam": "कोट्टयम",
    "Kozhikode": "कोझिकोड",
    "Malappuram": "मलप्पुरम",
    "Palakkad": "पलक्कड़",
    "Pathanamthitta": "पथनमथिट्टा",
    "Thiruvananthapuram": "तिरुवनंतपुरम",
    "Thrissur": "त्रिशूर",
    "Wayanad": "वायनाड",
    "Kanyakumari": "कन्याकुमारी",
    "Thoothukudi": "थूथुकुडी",
    "Viluppuram": "विल्लुपुरम",
    "Tirupattur": "तिरुपत्तूर",
    "House Builders": "घर बनाने वाले",
    "Bricklayers and Related Workers": "राजमिस्त्री और संबंधित कामगार",
    "Carpenters and Joiners": "बढ़ई और जोड़ने वाले",
    "Plumbers and Pipe Fitters": "प्लंबर और पाइप फ़िटर",
    "Building Construction Labourers": "भवन निर्माण मज़दूर",
    "Generalist Medical Practitioners": "सामान्य चिकित्सक",
    "Specialist Medical Practitioners": "विशेषज्ञ चिकित्सक",
    "Nursing Professionals": "नर्सिंग पेशेवर",
    "Medical and Pathology Laboratory Technicians": "चिकित्सा और पैथोलॉजी प्रयोगशाला तकनीशियन",
    "Nursing Associate Professionals": "नर्सिंग सहायक पेशेवर",
    "System Analysts": "सिस्टम विश्लेषक",
    "Software Developers": "सॉफ़्टवेयर डेवलपर",
    "Web and Multimedia Developers": "वेब और मल्टीमीडिया डेवलपर",
    "Applications Programmers": "एप्लिकेशन प्रोग्रामर",
    "Information and Communication Technology User Support Technicians": "सूचना और संचार प्रौद्योगिकी उपयोगकर्ता सहायता तकनीशियन",
    "Welders and Flame Cutters": "वेल्डर और ज्वाला काटने वाले",
    "Metal Working Machine Tool Setters and Operators": "धातु कार्य मशीन टूल सेटर और ऑपरेटर",
    "Agricultural and Industrial Machinery Mechanics and Repairers": "कृषि और औद्योगिक मशीनरी मिस्त्री और मरम्मत करने वाले",
    "Chemical Products Plant and Machine Operators": "रासायनिक उत्पाद संयंत्र और मशीन ऑपरेटर",
    "Electrical and Electronic Equipment Assemblers": "बिजली और इलेक्ट्रॉनिक उपकरण असेंबलर",
    "Tailors, Dressmakers, Furriers and Hatters": "दर्ज़ी, पोशाक बनाने वाले, फ़र और टोपी बनाने वाले",
    "Sewing, Embroiderers and Related Workers": "सिलाई, कढ़ाई और संबंधित कामगार",
    "Fibre Preparing, Spinning and Winding Machine Operators": "रेशा तैयार करने, कताई और लपेटने की मशीन चालक",
    "Weaving and Knitting Machine Operators": "बुनाई और निटिंग मशीन चालक",
    "Sewing Machine Operators": "सिलाई मशीन चालक",
}
TITLES = {
    "Forecast API | KaushalSetu": "पूर्वानुमान API | KaushalSetu",
    "Methodology | KaushalSetu": "कार्यप्रणाली | KaushalSetu",}


# phase 9: the API page (docs/api.html) and the footer link
PAGE.update({
    "<code>E</code> (employed workers), <code>V</code> (job vacancies), <code>S</code> (registered job seekers), several separated by commas, or <code>all</code> (the default).": "<code>E</code> (नियोजित कामगार), <code>V</code> (रिक्तियाँ), <code>S</code> (पंजीकृत नौकरी चाहने वाले), कई हों तो कॉमा से अलग, या <code>all</code> (डिफ़ॉल्ट)।",
    "<code>aggregate</code> (the default: one total for the filters) or <code>series</code> (every district and trade series, with <code>limit</code> up to 200 and <code>offset</code>).": "<code>aggregate</code> (डिफ़ॉल्ट: फ़िल्टर का एक कुल योग) या <code>series</code> (हर ज़िला और ट्रेड श्रृंखला, <code>limit</code> अधिकतम 200 और <code>offset</code> के साथ)।",
    "A parameter is unknown, repeated or has an invalid value; the message says which.": "कोई पैरामीटर अज्ञात है, दोहराया गया है या उसका मान अमान्य है; संदेश बताता है कि कौन-सा।",
    "A range exists for India, a sector, a trade, a state, a state with a sector, a district with a sector, and a district with a trade. For other combinations the field is null and a note says so.": "भारत, किसी सेक्टर, ट्रेड, राज्य, सेक्टर सहित राज्य, सेक्टर सहित ज़िले और ट्रेड सहित ज़िले के लिए दायरा मिलता है। अन्य संयोजनों में यह खाना null होता है और एक टिप्पणी यह बताती है।",
    "A trade code such as HLT-2221 (nursing professionals) or its full name. A trade fixes the sector.": "HLT-2221 (नर्सिंग पेशेवर) जैसा ट्रेड कोड या उसका पूरा नाम। ट्रेड से सेक्टर तय हो जाता है।",
    "Address": "पता",
    "All are GET requests on this site and return JSON. Add the filters to the address, for example <code translate=\"no\">/api/forecast?state=Kerala&amp;sector=Healthcare</code>.": "सभी GET अनुरोध हैं, इसी साइट पर, और JSON लौटाते हैं। पते में फ़िल्टर जोड़ें, जैसे <code translate=\"no\">/api/forecast?state=Kerala&amp;sector=Healthcare</code>।",
    "Early-warning alerts 12, 36 or 60 months ahead, or the flag of every month for one district and trade.": "12, 36 या 60 महीने आगे की पूर्व-चेतावनियाँ, या किसी एक ज़िले और ट्रेड के लिए हर महीने का निशान।",
    "Employed workers in Kerala's healthcare sector, 12 and 60 months ahead. A range shown as a pair of numbers is the lower and the upper end.": "केरल के स्वास्थ्य सेवा सेक्टर में नियोजित कामगार, 12 और 60 महीने आगे। संख्याओं की जोड़ी के रूप में दिखा दायरा निचला और ऊपरी सिरा है।",
    "Endpoints": "एंडपॉइंट",
    "Every response says that the data is <strong>simulated</strong>. It behaves like official statistics but describes no real district, and it is not an official statistic.": "हर उत्तर बताता है कि डेटा <strong>सिम्युलेटेड</strong> है। यह आधिकारिक आँकड़ों जैसा व्यवहार करता है पर किसी वास्तविक ज़िले का वर्णन नहीं करता, और यह आधिकारिक आँकड़ा नहीं है।",
    "Example": "उदाहरण",
    "For flags: <code>shortage</code>, <code>oversupply</code> or <code>all</code>.": "फ़्लैग के लिए: <code>shortage</code>, <code>oversupply</code> या <code>all</code>।",
    "For the Demand Index: months like 2026-12, and <code>annual</code> (December of each year, the default) or <code>monthly</code>.": "माँग सूचकांक के लिए: 2026-12 जैसे महीने, और <code>annual</code> (हर वर्ष का दिसंबर, डिफ़ॉल्ट) या <code>monthly</code>।",
    "Forecast API": "पूर्वानुमान API",
    "Forecast of employed workers, job vacancies and registered job seekers: a point forecast with a usual and a wide 90% range for each horizon.": "नियोजित कामगारों, रिक्तियों और पंजीकृत नौकरी चाहने वालों का पूर्वानुमान: हर अवधि के लिए बिंदु पूर्वानुमान, साथ में सामान्य और विस्तृत 90% दायरा।",
    "Forecast openings against training seats and expected certified trainees, by year.": "प्रशिक्षण सीटों और अपेक्षित प्रमाणित प्रशिक्षुओं के सामने पूर्वानुमानित रिक्तियाँ, वर्ष के अनुसार।",
    "Job-seeker forecasts and the fifth year are the weakest. Each series also carries a confidence label for each twelve-month band.": "नौकरी चाहने वालों के पूर्वानुमान और पाँचवाँ वर्ष सबसे कमज़ोर हैं। हर श्रृंखला के साथ हर बारह महीने के खंड का विश्वसनीयता लेबल भी होता है।",
    "Kerala, 12 months": "केरल, 12 महीने",
    "Kerala, Healthcare": "केरल, स्वास्थ्य सेवा",
    "Limits and errors": "सीमाएँ और त्रुटियाँ",
    "Lists and checksums": "सूचियाँ और चेकसम",
    "Months ahead from 1 to 60, several separated by commas, or <code>all</code>. The default is 12, 36 and 60. For flags: 12, 36 or 60.": "1 से 60 तक आगे के महीने, कई हों तो कॉमा से अलग, या <code>all</code>। डिफ़ॉल्ट 12, 36 और 60 है। फ़्लैग के लिए: 12, 36 या 60।",
    "More than 60 requests a minute from one address, or the daily limit of the whole site. Wait a minute and try again.": "एक पते से प्रति मिनट 60 से अधिक अनुरोध, या पूरी साइट की दैनिक सीमा। एक मिनट रुककर दोबारा कोशिश करें।",
    "None.": "कुछ नहीं।",
    "One of the five sectors, for example IT-ITeS.": "पाँच सेक्टरों में से एक, जैसे IT-ITeS।",
    "One of the ten state names, for example Kerala. Not case sensitive.": "दस राज्यों के नामों में से एक, जैसे Kerala। अक्षरों के आकार से फ़र्क़ नहीं पड़ता।",
    "Parameter": "पैरामीटर",
    "Parameters": "पैरामीटर",
    "Point forecasts of the trades add up exactly to their sector, and sectors to states and India. Ranges are calibrated for each level separately.": "ट्रेडों के बिंदु पूर्वानुमान ठीक उनके सेक्टर के बराबर जुड़ते हैं, और सेक्टर राज्यों और भारत के। दायरे हर स्तर के लिए अलग से जाँचे गए हैं।",
    "Points add up, ranges do not": "बिंदु जुड़ते हैं, दायरे नहीं",
    "Reading the numbers": "संख्याओं को कैसे पढ़ें",
    "Responses may be cached for up to an hour. The API sets no cookies, keeps no record of what you ask, and allows requests from any website, since the data is public and read-only.": "उत्तर एक घंटे तक कैश हो सकते हैं। API कोई कुकी नहीं लगाती, आप क्या पूछते हैं इसका कोई रिकॉर्ड नहीं रखती, और किसी भी वेबसाइट से अनुरोध की अनुमति देती है, क्योंकि डेटा सार्वजनिक और केवल-पढ़ने योग्य है।",
    "Same data as the dashboard": "डैशबोर्ड जैसा ही डेटा",
    "Seekers are the least reliable": "नौकरी चाहने वाले सबसे कम भरोसेमंद हैं",
    "The API accepts GET only.": "API केवल GET स्वीकार करती है।",
    "The API is read-only and open: no key and no login. It serves the 2026 to 2030 forecasts, the early-warning alerts, the Demand Index and the capacity gap, with the same filters as the dashboard: state, district, sector and trade.": "API केवल-पढ़ने योग्य और खुली है: न कुंजी, न लॉगिन। यह 2026 से 2030 के पूर्वानुमान, पूर्व-चेतावनियाँ, माँग सूचकांक और क्षमता अंतर देती है, डैशबोर्ड जैसे ही फ़िल्टर के साथ: राज्य, ज़िला, सेक्टर और ट्रेड।",
    "The API reads the files the dashboard loads, so a figure there and a figure here are the same figure, to the nearest person.": "API वही फ़ाइलें पढ़ती है जो डैशबोर्ड लोड करता है, इसलिए वहाँ की संख्या और यहाँ की संख्या एक ही है, निकटतम व्यक्ति तक।",
    "The Demand Index from 0 to 100, from 2016 to 2030 (December values, or every month).": "0 से 100 तक का माँग सूचकांक, 2016 से 2030 तक (दिसंबर के मान, या हर महीना)।",
    "The capacity gap uses the 2025 to 2026 sanctioned seats for every year to 2030, an assumption, because no seat plans are forecast.": "क्षमता अंतर हर वर्ष के लिए 2030 तक 2025-26 की स्वीकृत सीटें मानता है, यह एक मान्यता है, क्योंकि सीट योजनाओं का पूर्वानुमान नहीं होता।",
    "The filters are valid but match no series.": "फ़िल्टर मान्य हैं पर किसी श्रृंखला से मेल नहीं खाते।",
    "The official LGD code, for example 118 for Agra, or the district name. A district fixes the state.": "आधिकारिक LGD कोड, जैसे आगरा के लिए 118, या ज़िले का नाम। ज़िले से राज्य तय हो जाता है।",
    "The request was understood. The body has <code translate=\"no\">\"ok\": true</code>.": "अनुरोध समझ लिया गया। उत्तर में <code translate=\"no\">\"ok\": true</code> है।",
    "The same numbers as the dashboard, as plain JSON.": "डैशबोर्ड वाली ही संख्याएँ, सादे JSON में।",
    "The usual range was calibrated on 2010 to 2019; the wide range also uses the shock years 2020 to 2025. For totals of many series, such as a state, read the wide range: errors of neighbouring series move together.": "सामान्य दायरा 2010 से 2019 पर बना है; विस्तृत दायरा झटके वाले वर्ष 2020 से 2025 भी लेता है। कई श्रृंखलाओं के कुल योग के लिए, जैसे राज्य, विस्तृत दायरा पढ़ें: पास की श्रृंखलाओं की त्रुटियाँ साथ-साथ चलती हैं।",
    "The valid states, districts (with LGD codes), sectors and trades, the forecast origin and the checksums of the files behind the numbers.": "मान्य राज्य, ज़िले (LGD कोड सहित), सेक्टर और ट्रेड, पूर्वानुमान का आधार माह और संख्याओं के पीछे की फ़ाइलों के चेकसम।",
    "Try it": "आज़माएँ",
    "Two ranges": "दो दायरे",
    "Values": "मान",
    "Values are checked against the lists in <code translate=\"no\">/api/meta</code>; unknown or repeated parameters are refused with a clear message.": "मान <code translate=\"no\">/api/meta</code> की सूचियों से जाँचे जाते हैं; अज्ञात या दोहराए गए पैरामीटर साफ़ संदेश के साथ अस्वीकार होते हैं।",
    "What it returns": "यह क्या लौटाता है",
    "When": "कब",
    "Where there is no range": "जहाँ दायरा नहीं है",
    "endpoints": "एंडपॉइंट",
    "filters": "फ़िल्टर",
    "months ahead": "महीने आगे",
    "requests a minute": "अनुरोध प्रति मिनट",
})
PAGE["Trades and places ranked by how far trained supply is from the openings: a score, a band (severe, high, moderate, balanced) and the direction (undersupply or oversupply)."] = "ट्रेड और स्थान इस क्रम में कि प्रशिक्षित आपूर्ति रिक्तियों से कितनी दूर है: एक अंक, एक स्तर (गंभीर, उच्च, मध्यम, संतुलित) और दिशा (कम आपूर्ति या अधिक आपूर्ति)।"
PAGE["Most undersupplied trades"] = "सबसे कम आपूर्ति वाले ट्रेड"
PAGE["For severity: <code>level</code> is <code>trade</code> (the default), <code>state</code>, <code>state_trade</code>, <code>district</code>, <code>district_sector</code> or <code>series</code> (needs a state or a district); <code>order</code> is <code>under</code> (most undersupplied first, the default), <code>over</code> or <code>severity</code> (largest gap either way); <code>year</code> is one year from 2026 to 2030 (the default is 2030). For the capacity gap, <code>year</code> may be several years."] = "गंभीरता के लिए: <code>level</code> है <code>trade</code> (डिफ़ॉल्ट), <code>state</code>, <code>state_trade</code>, <code>district</code>, <code>district_sector</code> या <code>series</code> (राज्य या ज़िला चाहिए); <code>order</code> है <code>under</code> (सबसे कम आपूर्ति पहले, डिफ़ॉल्ट), <code>over</code> या <code>severity</code> (दोनों ओर सबसे बड़ा अंतर); <code>year</code> 2026 से 2030 में से एक वर्ष है (डिफ़ॉल्ट 2030)। क्षमता अंतर के लिए <code>year</code> कई वर्ष हो सकते हैं।"
PAGE["The API is read-only and open: no key and no login. It serves the 2026 to 2030 forecasts, the early-warning alerts, the Demand Index, the capacity gap and the severity ranking, with the same filters as the dashboard: state, district, sector and trade."] = "API केवल-पढ़ने योग्य और खुली है: न कुंजी, न लॉगिन। यह 2026 से 2030 के पूर्वानुमान, पूर्व-चेतावनियाँ, माँग सूचकांक, क्षमता अंतर और गंभीरता क्रम देती है, डैशबोर्ड जैसे ही फ़िल्टर के साथ: राज्य, ज़िला, सेक्टर और ट्रेड।"
PAGE["For flags: <code>entering</code> or <code>leaving</code> lists the series that enter or leave an alert tail between now (December 2025, actual) and the <code>horizon</code> of 12, 36 or 60 months, with the percentile now and then and the first month in the tail."] = "फ़्लैग के लिए: <code>entering</code> या <code>leaving</code> उन श्रृंखलाओं की सूची देता है जो अभी (दिसंबर 2025, वास्तविक) और 12, 36 या 60 महीने के <code>horizon</code> के बीच चेतावनी वाले छोर में प्रवेश करती हैं या उससे बाहर जाती हैं, साथ में अभी और तब का प्रतिशतक और छोर में पहला महीना।"
PAGE["A seat scenario: seats multiplied from a year on, with the ratio, the severity band and the seats needed to reach a target, row by row and in total."] = "सीट परिदृश्य: किसी वर्ष से सीटों को गुणा करना, अनुपात, गंभीरता स्तर और लक्ष्य तक पहुँचने के लिए चाहिए सीटों के साथ, पंक्ति-दर-पंक्ति और कुल।"
PAGE["Seats up 50% from 2027"] = "2027 से सीटें 50% अधिक"
PAGE["For the scenario: <code>seat_change</code> is a percentage from -90 to 500 applied to the seats from <code>from_year</code> on (default 0), and <code>target</code> is the certified per opening to plan for (0.2 to 5, default 1). The certification rate and the forecast openings are unchanged; <code>order</code> may also be <code>needed</code>."] = "परिदृश्य के लिए: <code>seat_change</code> -90 से 500 तक का प्रतिशत है जो <code>from_year</code> से सीटों पर लागू होता है (डिफ़ॉल्ट 0), और <code>target</code> वह प्रति रिक्ति प्रमाणित है जिसके लिए योजना बनानी है (0.2 से 5, डिफ़ॉल्ट 1)। प्रमाणन दर और पूर्वानुमानित रिक्तियाँ अपरिवर्तित रहती हैं; <code>order</code> <code>needed</code> भी हो सकता है।"
PAGE["The API is read-only and open: no key and no login. It serves the 2026 to 2030 forecasts, the early-warning alerts, the Demand Index, the capacity gap, the severity ranking and seat scenarios, with the same filters as the dashboard: state, district, sector and trade."] = "API केवल-पढ़ने योग्य और खुली है: न कुंजी, न लॉगिन। यह 2026 से 2030 के पूर्वानुमान, पूर्व-चेतावनियाँ, माँग सूचकांक, क्षमता अंतर, गंभीरता क्रम और सीट परिदृश्य देती है, डैशबोर्ड जैसे ही फ़िल्टर के साथ: राज्य, ज़िला, सेक्टर और ट्रेड।"

# the public pages updated for the severity ranking, seat scenarios, changing alerts, the API and the methodology document
PAGE["A Demand Index from 0 to 100, a capacity gap against training seats with seat scenarios, a severity ranking, and early warnings for the tightest and loosest tenth of districts."] = "0 से 100 तक का माँग सूचकांक, सीट परिदृश्यों के साथ प्रशिक्षण सीटों के सामने क्षमता अंतर, एक गंभीरता क्रम, और ज़िलों के सबसे तंग तथा सबसे ढीले दसवें हिस्से के लिए पूर्व चेतावनी।"
PAGE["A read-only API"] = "केवल-पढ़ने योग्य API"
PAGE["Alerts that begin or end"] = "चेतावनियाँ जो शुरू या खत्म होती हैं"
PAGE["Change the seats by a percentage and see the balance with the openings, and the seats needed to reach a target."] = "सीटों में प्रतिशत के अनुसार बदलाव करें और रिक्तियों के साथ संतुलन देखें, और लक्ष्य तक पहुँचने के लिए चाहिए सीटें भी।"
PAGE["Colour all 317 districts by sector, measure and months ahead, with the state borders drawn, and zoom into a state. The dashboard has a map page too."] = "सेक्टर, माप और कितने महीने आगे, के अनुसार सभी 317 ज़िलों को रंगें, राज्यों की सीमाएँ खिंची हुई हैं, और किसी राज्य में ज़ूम करें। डैशबोर्ड में एक मानचित्र पृष्ठ भी है।"
PAGE["Colours sort the 317 districts into five equal groups, so they show who is higher or lower, not by how much. Read the exact figure in the hover. The Demand Index is a position among peers from 0 to 100. Employed-worker forecasts are the most reliable and job-seeker forecasts the least, and the further ahead, the less certain. White lines mark the state borders. Boundaries are the Local Government Directory layer, distributed by bharatlas under CC0 or CC BY, simplified for orientation only."] = "रंग 317 ज़िलों को पाँच बराबर समूहों में बाँटते हैं, इसलिए वे बताते हैं कि कौन ऊपर या नीचे है, कितना, यह नहीं। सटीक आँकड़ा ज़िले पर जाकर पढ़ें। माँग सूचकांक अपने जैसे ज़िलों के बीच 0 से 100 तक की स्थिति है। नियोजित कामगारों के पूर्वानुमान सबसे भरोसेमंद और नौकरी चाहने वालों के सबसे कम हैं, और जितना आगे देखें, अनिश्चितता उतनी बढ़ती है। सफ़ेद रेखाएँ राज्यों की सीमाएँ दिखाती हैं। सीमाएँ स्थानीय सरकार निर्देशिका की परत हैं, जिसे bharatlas CC0 या CC BY के तहत वितरित करता है, और केवल दिशा-बोध के लिए सरल की गई हैं।"
PAGE["Demand Index, capacity gap, severity and early warnings"] = "माँग सूचकांक, क्षमता अंतर, गंभीरता और पूर्व चेतावनी"
PAGE["Every dashboard table downloads as CSV or JSON, and every export file carries a checksum. The method is written out in the project's methodology document."] = "डैशबोर्ड की हर तालिका CSV या JSON में डाउनलोड होती है, और हर निर्यात फ़ाइल के साथ चेकसम होता है। तरीका परियोजना के कार्यप्रणाली दस्तावेज़ में विस्तार से लिखा है।"
PAGE["For every series and month ahead: the forecast, two 90% ranges, a confidence label and an early-warning flag; the alerts that begin or end; the Demand Index; the capacity gap by year; the severity ranking and seat scenarios, which are computed from them on request; the rankings."] = "हर श्रृंखला और आगे के हर महीने के लिए: पूर्वानुमान, दो 90% दायरे, विश्वसनीयता लेबल और पूर्व-चेतावनी निशान; जो चेतावनियाँ शुरू या खत्म होती हैं; माँग सूचकांक; वर्ष के अनुसार क्षमता अंतर; गंभीरता क्रम और सीट परिदृश्य, जो इन्हीं से माँगने पर निकाले जाते हैं; रैंकिंग।"
PAGE["Multiply the seats by a percentage from a chosen year and see the ratio and the severity before and after, and the seats needed to reach a target. The certification rate and the forecast openings stay as they are, and no delay is modelled between sanctioning a seat and certifying a trainee."] = "किसी वर्ष से सीटों को एक प्रतिशत से गुणा करें और पहले और बाद का अनुपात और गंभीरता देखें, और लक्ष्य तक पहुँचने के लिए चाहिए सीटें। प्रमाणन दर और पूर्वानुमानित रिक्तियाँ जैसी हैं वैसी रहती हैं, और सीट स्वीकृत होने तथा प्रशिक्षु के प्रमाणित होने के बीच कोई देरी नहीं मानी गई है।"
PAGE["Score = the natural log of the trainees expected to be certified in a year divided by the average monthly openings. Below zero is undersupply and above zero oversupply; a ratio of 2 or more either way is severe, 1.5 high and 1.25 moderate. Trades, states, state and trade, districts, district and sector, and district and trade can be ranked for any year to 2030, within any filter."] = "अंक = एक वर्ष में प्रमाणित होने की अपेक्षा वाले प्रशिक्षुओं को औसत मासिक रिक्तियों से भाग देकर उसका प्राकृतिक लघुगणक। शून्य से कम का अर्थ कम आपूर्ति और शून्य से अधिक का अधिक आपूर्ति; दोनों ओर 2 या उससे अधिक का अनुपात गंभीर, 1.5 उच्च और 1.25 मध्यम है। ट्रेड, राज्य, राज्य और ट्रेड, ज़िले, ज़िला और सेक्टर, तथा ज़िला और ट्रेड को 2030 तक किसी भी वर्ष के लिए, किसी भी फ़िल्टर में, क्रमबद्ध किया जा सकता है।"
PAGE["Seat scenarios"] = "सीट परिदृश्य"
PAGE["Severity ranking"] = "गंभीरता क्रम"
PAGE["Six readings built on the forecasts, each defined in a few lines so that it can be checked. The full method, with a worked example, is written out in the project's methodology document, and every number is served by the <a class=\"ulink\" href=\"docs/api.html\">read-only API</a>."] = "पूर्वानुमानों पर बने छह पाठ, हर एक को कुछ पंक्तियों में परिभाषित किया गया है ताकि उसकी जाँच हो सके। पूरा तरीका, एक हल किए उदाहरण के साथ, परियोजना के कार्यप्रणाली दस्तावेज़ में लिखा है, और हर संख्या <a class=\"ulink\" href=\"docs/api.html\">केवल-पढ़ने योग्य API</a> से मिलती है।"
PAGE["The actual tightness of December 2025 is compared with the forecast at 12, 36 or 60 months, to list the series that enter or leave an alert tail and the first month they are in it. Alerts mostly persist: about one in eight of today's is out of its tail after 12 months, and about as many move in."] = "दिसंबर 2025 की वास्तविक तंगी की तुलना 12, 36 या 60 महीने के पूर्वानुमान से की जाती है, ताकि उन श्रृंखलाओं की सूची बने जो चेतावनी वाले छोर में प्रवेश करती हैं या उससे बाहर जाती हैं, और जिस पहले महीने वे उसमें होती हैं। चेतावनियाँ अधिकतर बनी रहती हैं: आज की लगभग आठ में से एक 12 महीने बाद अपने छोर से बाहर होती है, और लगभग उतनी ही अंदर आ जाती हैं।"
PAGE["The capacity gap assumes today's seats for every year to 2030 unless you test another number with a seat scenario, and reads best as a ranking of where capacity is stretched rather than a count of unfilled places."] = "क्षमता अंतर 2030 तक हर वर्ष के लिए आज की सीटें मानता है, जब तक आप सीट परिदृश्य से कोई और संख्या न आज़माएँ, और इसे खाली स्थानों की गिनती के बजाय इस क्रम के रूप में पढ़ना बेहतर है कि क्षमता कहाँ तनी हुई है।"
PAGE["The forecasts, alerts, Demand Index, capacity gap, severity ranking and seat scenarios as plain JSON, with the same filters as the dashboard."] = "पूर्वानुमान, चेतावनियाँ, माँग सूचकांक, क्षमता अंतर, गंभीरता क्रम और सीट परिदृश्य सादे JSON के रूप में, डैशबोर्ड जैसे ही फ़िल्टर के साथ।"
PAGE["The same numbers are served as JSON by the <a class=\"ulink\" href=\"docs/api.html\">read-only API</a>, and the method behind them is written out in the project's methodology document, which also lists what would change with real data."] = "यही संख्याएँ <a class=\"ulink\" href=\"docs/api.html\">केवल-पढ़ने योग्य API</a> से JSON के रूप में मिलती हैं, और इनके पीछे का तरीका परियोजना के कार्यप्रणाली दस्तावेज़ में लिखा है, जो यह भी बताता है कि वास्तविक डेटा आने पर क्या बदलेगा।"
PAGE["Trades, states, districts and district-trades in order of how far trained supply is from the openings, for any year to 2030."] = "ट्रेड, राज्य, ज़िले और ज़िला-ट्रेड इस क्रम में कि प्रशिक्षित आपूर्ति रिक्तियों से कितनी दूर है, 2030 तक किसी भी वर्ष के लिए।"
PAGE["Which districts will enter or leave the tightest or loosest tenth of their trade, 12, 36 or 60 months from now."] = "कौन-से ज़िले अपने ट्रेड के सबसे तंग या सबसे ढीले दसवें हिस्से में प्रवेश करेंगे या उससे बाहर जाएँगे, अब से 12, 36 या 60 महीने बाद।"

# the methodology page (docs/methodology.html) and the links to it
PAGE["Every dashboard table downloads as CSV or JSON, and every export file carries a checksum. The method is on the <a class=\"ulink\" href=\"docs/methodology.html\">Methodology</a> page."] = "डैशबोर्ड की हर तालिका CSV या JSON में डाउनलोड होती है, और हर निर्यात फ़ाइल के साथ चेकसम होता है। तरीका <a class=\"ulink\" href=\"docs/methodology.html\">कार्यप्रणाली</a> पृष्ठ पर लिखा है।"
PAGE["Methodology"] = "कार्यप्रणाली"
PAGE["Six readings built on the forecasts, each defined in a few lines so that it can be checked. The Demand Index is built step by step, with a worked example, on the <a class=\"ulink\" href=\"docs/methodology.html\">Methodology</a> page, and every number is served by the <a class=\"ulink\" href=\"docs/api.html\">read-only API</a>."] = "पूर्वानुमानों पर बने छह पाठ, हर एक को कुछ पंक्तियों में परिभाषित किया गया है ताकि उसकी जाँच हो सके। माँग सूचकांक कैसे बनता है, एक हल किए उदाहरण के साथ, यह <a class=\"ulink\" href=\"docs/methodology.html\">कार्यप्रणाली</a> पृष्ठ पर चरण-दर-चरण लिखा है, और हर संख्या <a class=\"ulink\" href=\"docs/api.html\">केवल-पढ़ने योग्य API</a> से मिलती है।"
PAGE["A number from 0 to 100 for a district and trade in a month. It compares openings per worker, from vacancies, job-portal postings and the National Career Service, with the other districts of the same trade, and moves over the years with the trade's national level. 50 is the median district at the 2018 to 2019 level."] = "किसी ज़िले और ट्रेड के लिए किसी महीने की 0 से 100 तक की संख्या। यह रिक्तियों, जॉब-पोर्टल पोस्टिंग और राष्ट्रीय कॅरियर सेवा से प्रति कामगार शुरुआती अवसरों की तुलना उसी ट्रेड के बाकी ज़िलों से करती है, और ट्रेड के राष्ट्रीय स्तर के साथ वर्षों में बदलती है। 50, 2018 से 2019 के स्तर पर बीच का ज़िला है।"
PAGE["Oversupply alerts 71%. One to twelve months ahead, on the test years. Flagging from today's tightness alone, with no forecast, gets 71% of shortage alerts right, so most of this is tightness persisting."] = "अधिक आपूर्ति की चेतावनियाँ 71%। परीक्षण वर्षों में, एक से बारह महीने आगे। आज की तंगी से ही, बिना किसी पूर्वानुमान के, चिह्नित करने पर 71% कमी की चेतावनियाँ सही निकलती हैं, इसलिए इसका अधिकांश हिस्सा इस बात से आता है कि तंगी बनी रहती है।"
PAGE["Limits stated plainly, so that the numbers are read as they deserve. The judgements behind them are on the <a class=\"ulink\" href=\"docs/methodology.html#real-data\">Methodology</a> page."] = "सीमाएँ साफ़ शब्दों में, ताकि संख्याओं को वैसे ही पढ़ा जाए जैसी वे हैं। इनके पीछे के निर्णय <a class=\"ulink\" href=\"docs/methodology.html#real-data\">कार्यप्रणाली</a> पृष्ठ पर हैं।"
PAGE["The same numbers are served as JSON by the <a class=\"ulink\" href=\"docs/api.html\">read-only API</a>, and the method behind them is on the <a class=\"ulink\" href=\"docs/methodology.html\">Methodology</a> page, which also lists what would change with real data."] = "यही संख्याएँ <a class=\"ulink\" href=\"docs/api.html\">केवल-पढ़ने योग्य API</a> से JSON के रूप में मिलती हैं, और इनके पीछे का तरीका <a class=\"ulink\" href=\"docs/methodology.html\">कार्यप्रणाली</a> पृष्ठ पर लिखा है, जो यह भी बताता है कि वास्तविक डेटा आने पर क्या बदलेगा।"
PAGE["How the Demand Index is built, how the doubt on each forecast is measured, and what would change with real data."] = "माँग सूचकांक कैसे बनता है, हर पूर्वानुमान पर संदेह कैसे मापा जाता है, और वास्तविक डेटा आने पर क्या बदलेगा।"
PAGE["This page holds only what the other pages do not. The data, the forecasting engine, the six readings and the test results are on <a class=\"ulink\" href=\"../about.html\">About</a>, where the data came from is on <a class=\"ulink\" href=\"../resources.html\">Resources</a>, and every number is served by the <a class=\"ulink\" href=\"../docs/api.html\">read-only API</a>."] = "इस पृष्ठ पर केवल वही है जो दूसरे पृष्ठों पर नहीं है। डेटा, पूर्वानुमान इंजन, छह पाठ और परीक्षण के नतीजे <a class=\"ulink\" href=\"../about.html\">परिचय</a> पर हैं, डेटा कहाँ से आया यह <a class=\"ulink\" href=\"../resources.html\">संसाधन</a> पर है, और हर संख्या <a class=\"ulink\" href=\"../docs/api.html\">केवल-पढ़ने योग्य API</a> से मिलती है।"
PAGE["Each step below can be checked against the dashboard. The full write-up, with the code behind every step, is the methodology document in the project's repository."] = "नीचे हर चरण की जाँच डैशबोर्ड से की जा सकती है। हर चरण के पीछे के कोड के साथ पूरा विवरण परियोजना के रिपॉज़िटरी में कार्यप्रणाली दस्तावेज़ है।"
PAGE["signals in the Demand Index"] = "माँग सूचकांक में संकेत"
PAGE["0 to 100"] = "0 से 100"
PAGE["the index scale"] = "सूचकांक का पैमाना"
PAGE["agreement of the forecast-month index with the full one, 2025"] = "2025 में पूर्वानुमान-महीनों वाले सूचकांक की पूरे सूचकांक से सहमति"
PAGE["The Demand Index, step by step"] = "माँग सूचकांक, चरण-दर-चरण"
PAGE["Several imperfect signals about hiring become one number for each district and trade. Only the signals that count openings are used."] = "रोज़गार के बारे में कई अधूरे संकेत मिलकर हर ज़िले और ट्रेड के लिए एक संख्या बनते हैं। केवल वही संकेत लिए जाते हैं जो रिक्तियों को गिनते हैं।"
PAGE["Signal"] = "संकेत"
PAGE["Available from"] = "कब से उपलब्ध"
PAGE["In the index?"] = "क्या सूचकांक में है?"
PAGE["January 2000"] = "जनवरी 2000"
PAGE["Yes. The reference signal, and the only one in forecast months."] = "हाँ। संदर्भ संकेत, और पूर्वानुमान-महीनों में एकमात्र।"
PAGE["Job-portal postings"] = "जॉब-पोर्टल पोस्टिंग"
PAGE["Yes, in history. A share of all openings, and a growing one as hiring moves online."] = "हाँ, इतिहास में। सभी रिक्तियों का एक हिस्सा, और भर्ती ऑनलाइन जाने के साथ बढ़ता हुआ।"
PAGE["National Career Service vacancies"] = "राष्ट्रीय कॅरियर सेवा की रिक्तियाँ"
PAGE["July 2015"] = "जुलाई 2015"
PAGE["Yes, from its launch. Before it starts, it adds nothing."] = "हाँ, शुरू होने से। शुरू होने से पहले यह कुछ नहीं जोड़ता।"
PAGE["Quarterly hiring survey"] = "तिमाही भर्ती सर्वेक्षण"
PAGE["January 2009"] = "जनवरी 2009"
PAGE["No. An index relative to its own series cannot be compared between districts. It is a model input."] = "नहीं। अपनी ही श्रृंखला के सापेक्ष सूचकांक की तुलना ज़िलों के बीच नहीं हो सकती। यह मॉडल का इनपुट है।"
PAGE["Labour-force survey estimate"] = "श्रम-बल सर्वेक्षण का अनुमान"
PAGE["July 2017"] = "जुलाई 2017"
PAGE["No. It measures employment, not demand. It is a model input."] = "नहीं। यह रोज़गार मापता है, माँग नहीं। यह मॉडल का इनपुट है।"
PAGE["No. It is supply, not demand. It is forecast as a target."] = "नहीं। यह आपूर्ति है, माँग नहीं। इसका पूर्वानुमान लक्ष्य के रूप में किया जाता है।"
PAGE["Openings per worker"] = "प्रति कामगार अवसर"
PAGE["For each signal, the logarithm of the signal plus 1, divided by employed workers. Dividing removes the size of the district, the logarithm turns ratios into differences, and the plus 1 keeps empty cells defined."] = "हर संकेत के लिए, संकेत में 1 जोड़कर नियोजित कामगारों से भाग देने का लघुगणक। भाग देने से ज़िले का आकार हट जाता है, लघुगणक अनुपातों को अंतर में बदल देता है, और 1 जोड़ने से खाली खाने भी परिभाषित रहते हैं।"
PAGE["Position among peers"] = "साथियों के बीच स्थिति"
PAGE["That figure is standardised against its peers, the districts of that trade in the same month, to an average of 0 and a spread of 1. This removes any national shift, such as the portals' growing coverage or the launch of the National Career Service."] = "उस संख्या को उसके साथियों, यानी उसी महीने उस ट्रेड के ज़िलों, के सामने मानकीकृत किया जाता है, औसत 0 और फैलाव 1 पर। इससे कोई भी राष्ट्रीय बदलाव हट जाता है, जैसे पोर्टलों का बढ़ता दायरा या राष्ट्रीय कॅरियर सेवा का शुरू होना।"
PAGE["Composite"] = "संयुक्त अंक"
PAGE["The average of the signals available, rescaled to a spread of 1 across the districts of the trade. A signal that has not started contributes nothing."] = "उपलब्ध संकेतों का औसत, जिसे ट्रेड के ज़िलों में 1 के फैलाव तक दोबारा पैमाने पर लाया जाता है। जो संकेत शुरू नहीं हुआ है वह कुछ नहीं जोड़ता।"
PAGE["National level"] = "राष्ट्रीय स्तर"
PAGE["Steps 2 and 3 are relative, so a trade whose demand rose everywhere would not move. A level term carries the trade's national openings per worker, measured from its 2018 to 2019 average in units of the district spread, so the index rises and falls over the years."] = "चरण 2 और 3 सापेक्ष हैं, इसलिए जिस ट्रेड की माँग हर जगह बढ़ी हो वह नहीं हिलेगा। एक स्तर-पद ट्रेड के राष्ट्रीय प्रति कामगार अवसर को उसके 2018 से 2019 के औसत से, ज़िलों के फैलाव की इकाइयों में, मापकर जोड़ता है, ताकि सूचकांक वर्षों में ऊपर-नीचे हो।"
PAGE["The index"] = "सूचकांक"
PAGE["100 times Φ of (composite plus level), where Φ is the normal distribution function. So 50 is the median district, 84 is one spread above it and 16 one below. It cannot leave 0 to 100."] = "100 गुणा Φ (संयुक्त अंक जमा स्तर), जहाँ Φ सामान्य वितरण फलन है। इसलिए 50 बीच का ज़िला है, 84 उससे एक फैलाव ऊपर और 16 एक फैलाव नीचे। यह 0 से 100 से बाहर नहीं जा सकता।"
PAGE["Forecast months and totals"] = "पूर्वानुमान के महीने और कुल"
PAGE["Forecast months use forecast vacancies and employed workers only, because the other signals measure the same openings and are not forecast. States, sectors, trades and India are averages of their series, weighted by employed workers."] = "पूर्वानुमान के महीनों में केवल पूर्वानुमानित रिक्तियाँ और नियोजित कामगार लिए जाते हैं, क्योंकि बाकी संकेत उन्हीं रिक्तियों को मापते हैं और उनका पूर्वानुमान नहीं होता। राज्य, सेक्टर, ट्रेड और भारत अपनी श्रृंखलाओं के औसत हैं, नियोजित कामगारों से भारित।"
PAGE["Worked example: house builders in Agra, December 2025"] = "हल किया उदाहरण: आगरा के मकान निर्माता, दिसंबर 2025"
PAGE["Quantity"] = "मात्रा"
PAGE["Value"] = "मान"
PAGE["Vacancies, portal postings, National Career Service vacancies"] = "रिक्तियाँ, पोर्टल पोस्टिंग, राष्ट्रीय कॅरियर सेवा की रिक्तियाँ"
PAGE["1,434, 247 and 449"] = "1,434, 247 और 449"
PAGE["Position among the 317 districts of the trade (step 2)"] = "ट्रेड के 317 ज़िलों के बीच स्थिति (चरण 2)"
PAGE["+0.46 for vacancies, +0.85 for portals, +0.68 for the National Career Service"] = "रिक्तियों के लिए +0.46, पोर्टलों के लिए +0.85, राष्ट्रीय कॅरियर सेवा के लिए +0.68"
PAGE["Average of the three, then the composite (step 3)"] = "तीनों का औसत, फिर संयुक्त अंक (चरण 3)"
PAGE["0.66, rescaled to 0.74"] = "0.66, जो 0.74 में दोबारा पैमाने पर आता है"
PAGE["National level (step 4)"] = "राष्ट्रीय स्तर (चरण 4)"
PAGE["The index (step 5)"] = "सूचकांक (चरण 5)"
PAGE["100 × Φ(0.74 + 0.03) = <strong>77.9</strong>, in the upper quarter of districts for this trade"] = "100 × Φ(0.74 + 0.03) = <strong>77.9</strong>, इस ट्रेड के ज़िलों में ऊपरी चौथाई में"
PAGE["What was checked"] = "क्या जाँचा गया"
PAGE["Forecast months track the full index"] = "पूर्वानुमान के महीने पूरे सूचकांक का साथ देते हैं"
PAGE["In every year from 2012 to 2025, the version that uses vacancies alone, as forecast months must, agrees with the three-signal index at 0.89 to 0.94 (0.93 in 2025), differing by 8 to 10 points on average."] = "2012 से 2025 के हर वर्ष में, केवल रिक्तियों वाला संस्करण, जैसा पूर्वानुमान के महीनों को करना पड़ता है, तीन-संकेत वाले सूचकांक से 0.89 से 0.94 पर सहमत है (2025 में 0.93), औसतन 8 से 10 अंक के अंतर के साथ।"
PAGE["Scale and bounds"] = "पैमाना और सीमाएँ"
PAGE["Every value lies between 0 and 100, and before the level term every trade-month has an average of 0 and a spread of 1, checked by tests on synthetic data."] = "हर मान 0 और 100 के बीच है, और स्तर-पद से पहले हर ट्रेड-महीने का औसत 0 और फैलाव 1 है, जिसे कृत्रिम डेटा पर परीक्षणों से जाँचा गया है।"
PAGE["Not checked"] = "नहीं जाँचा गया"
PAGE["Agreement with real hiring, because the data is simulated. The signals are weighted equally by choice, not estimated."] = "वास्तविक भर्ती से सहमति, क्योंकि डेटा सिम्युलेटेड है। संकेतों को बराबर भार चुनाव से दिया गया है, अनुमान से नहीं।"
PAGE["How the doubt is measured"] = "संदेह कैसे मापा जाता है"
PAGE["The ranges and the confidence labels are described on the About page. This is how they are set."] = "दायरे और विश्वसनीयता लेबल परिचय पृष्ठ पर बताए गए हैं। यहाँ वह है कि वे कैसे तय होते हैं।"
PAGE["A range from past errors"] = "पिछली त्रुटियों से बना दायरा"
PAGE["For a forecast some months ahead, the 90% range adds the 5th and 95th percentile of earlier errors on the log change, for the same measure at one or two months either side, widened until at least 400 errors from 8 forecast dates are pooled. Only years the model had not seen are used, so the range does not shrink when the fit to past data improves."] = "कुछ महीने आगे के पूर्वानुमान के लिए, 90% दायरा उसी माप की, एक या दो महीने इधर-उधर के, लघुगणक-परिवर्तन पर पहले की त्रुटियों के 5वें और 95वें प्रतिशतक को जोड़ता है, और तब तक चौड़ा किया जाता है जब तक 8 पूर्वानुमान-तिथियों की कम से कम 400 त्रुटियाँ इकट्ठी न हों। केवल वे वर्ष लिए जाते हैं जो मॉडल ने नहीं देखे थे, इसलिए पिछले डेटा से बेहतर मेल होने पर दायरा सिकुड़ता नहीं।"
PAGE["A range for each level"] = "हर स्तर के लिए दायरा"
PAGE["Neighbouring series tend to miss in the same direction at once, so the range of a state or of India is not the sum of the ranges of its series. It is set from the errors of that level itself, for district and sector, state and sector, state, sector, trade and India. Where no such errors exist, only the forecast is shown."] = "पड़ोसी श्रृंखलाएँ अक्सर एक साथ एक ही दिशा में चूकती हैं, इसलिए किसी राज्य या भारत का दायरा उसकी श्रृंखलाओं के दायरों का जोड़ नहीं है। यह उसी स्तर की अपनी त्रुटियों से बनता है: ज़िला और सेक्टर, राज्य और सेक्टर, राज्य, सेक्टर, ट्रेड और भारत। जहाँ ऐसी त्रुटियाँ नहीं हैं, केवल पूर्वानुमान दिखता है।"
PAGE["A label that must be earned"] = "कमाया जाने वाला लेबल"
PAGE["For each measure, trade and twelve-month band, the average miss (WAPE) of earlier forecasts decides the label: high up to 8%, medium up to 20%, low above, and one level lower for a small series. A label is useful only if later error rises from high to low. It does for employed workers and vacancies, not reliably for job seekers."] = "हर माप, ट्रेड और बारह महीने के खंड के लिए, पहले के पूर्वानुमानों की औसत चूक (WAPE) लेबल तय करती है: 8% तक उच्च, 20% तक मध्यम, उससे ऊपर निम्न, और छोटी श्रृंखला के लिए एक स्तर नीचे। लेबल तभी उपयोगी है जब बाद की त्रुटि उच्च से निम्न की ओर बढ़े। नियोजित कामगारों और रिक्तियों के लिए ऐसा होता है, नौकरी चाहने वालों के लिए भरोसेमंद रूप से नहीं।"
PAGE["Judgements, and what changes with real data"] = "निर्णय, और वास्तविक डेटा आने पर क्या बदलेगा"
PAGE["Some choices are conventions rather than results, and they are listed so that they can be challenged. The limits of the numbers are on the About page."] = "कुछ चुनाव नतीजे नहीं, परंपराएँ हैं, और उन्हें गिनाया गया है ताकि उन पर सवाल उठाया जा सके। संख्याओं की सीमाएँ परिचय पृष्ठ पर हैं।"
PAGE["Choice"] = "चुनाव"
PAGE["Equal weights"] = "बराबर भार"
PAGE["The signals in the Demand Index count equally, and 2018 to 2019 is the reference for its level."] = "माँग सूचकांक में संकेतों की गिनती बराबर है, और उसके स्तर का संदर्भ 2018 से 2019 है।"
PAGE["Thresholds"] = "तय सीमाएँ"
PAGE["The flag percentiles (90, 75, 25 and 10), the label limits (8% and 20%) and the severity ratios (1.25, 1.5 and 2) are conventions, fixed before the test years were opened, not tuned."] = "चेतावनी के प्रतिशतक (90, 75, 25 और 10), लेबल की सीमाएँ (8% और 20%) और गंभीरता के अनुपात (1.25, 1.5 और 2) परंपराएँ हैं, जो परीक्षण वर्ष खोलने से पहले तय की गईं, कसी नहीं गईं।"
PAGE["Leaving out the shock"] = "झटके को छोड़ना"
PAGE["The final fit leaves out the 2020 to 2023 shock and recovery, so it is not learned as an ordinary month. This is a judgement about a simulated shock. Its side effect is lumpier job-seeker growth where the horizon passes 24 months."] = "अंतिम फ़िट 2020 से 2023 के झटके और सुधार को छोड़ देता है, ताकि वह सामान्य महीने की तरह न सीखा जाए। यह एक सिम्युलेटेड झटके के बारे में निर्णय है। इसका साइड इफ़ेक्ट यह है कि जहाँ अवधि 24 महीने पार करती है वहाँ नौकरी चाहने वालों की वृद्धि ऊबड़-खाबड़ हो जाती है।"
PAGE["Flat seats"] = "स्थिर सीटें"
PAGE["Seats are held at the 2025 to 2026 level because no seat plans are forecast."] = "सीटें 2025 से 2026 के स्तर पर रखी गई हैं क्योंकि सीट योजनाओं का पूर्वानुमान नहीं किया जाता।"
PAGE["With real data, in this order"] = "वास्तविक डेटा के साथ, इसी क्रम में"
PAGE["Step"] = "चरण"
PAGE["What to do"] = "क्या करना है"
PAGE["Replace each simulated signal with its real extract: job portals, the National Career Service, the hiring survey, the labour-force survey and e-Shram, keeping the district and occupation codes."] = "हर सिम्युलेटेड संकेत को उसके वास्तविक निकास से बदलें: जॉब पोर्टल, राष्ट्रीय कॅरियर सेवा, भर्ती सर्वेक्षण, श्रम-बल सर्वेक्षण और ई-श्रम, ज़िला और व्यवसाय कोड वही रखते हुए।"
PAGE["Check that the signals' scales are still comparable after they are standardised within each trade."] = "जाँचें कि हर ट्रेड के भीतर मानकीकरण के बाद भी संकेतों के पैमाने तुलनीय हैं।"
PAGE["Test the Demand Index against realised hiring."] = "माँग सूचकांक को वास्तविक भर्ती के सामने परखें।"
PAGE["Refit the models and run the one-shot test again on a period held out."] = "मॉडल दोबारा फ़िट करें और रोके गए एक अवधि पर एक-बार का परीक्षण फिर चलाएँ।"
PAGE["Replace the flat seats with sanctioned seat plans."] = "स्थिर सीटों को स्वीकृत सीट योजनाओं से बदलें।"

# the pages after each idea was kept on one page only
PAGE["Eight pages for exploring every district and sector: overview, map, forecasts, Demand Index, capacity gap, severity ranking, early warnings and data."] = "आठ पृष्ठ, हर ज़िले और सेक्टर को खंगालने के लिए: अवलोकन, मानचित्र, पूर्वानुमान, माँग सूचकांक, क्षमता अंतर, गंभीरता क्रम, पूर्व चेतावनी और डेटा।"
PAGE["Ask the assistant"] = "सहायक से पूछें"
PAGE["The round button at the bottom right of every page answers questions about the forecasts and how to read them, in English."] = "हर पृष्ठ के नीचे दाईं ओर का गोल बटन पूर्वानुमानों और उन्हें पढ़ने के तरीके के बारे में सवालों के जवाब देता है, अंग्रेज़ी में।"
PAGE["Every dashboard table downloads as CSV or JSON, ready for a spreadsheet."] = "डैशबोर्ड की हर तालिका CSV या JSON में डाउनलोड होती है, स्प्रेडशीट में इस्तेमाल के लिए तैयार।"
PAGE["It forecasts employment, job vacancies and registered job seekers for every district and trade, five years ahead, with a range and a confidence label on every number, and sets the forecast openings against the training seats on offer, so that seats, camps and attention can go where they are needed."] = "यह हर ज़िले और ट्रेड के लिए रोज़गार, रिक्तियों और पंजीकृत नौकरी चाहने वालों का पाँच वर्ष आगे तक पूर्वानुमान देता है, हर संख्या पर एक दायरे और विश्वसनीयता लेबल के साथ, और पूर्वानुमानित रिक्तियों को उपलब्ध प्रशिक्षण सीटों के सामने रखता है, ताकि सीटें, शिविर और ध्यान वहाँ जा सकें जहाँ उनकी ज़रूरत है।"
PAGE["One model for each of the three measures, judged against simple forecasts on years it never saw. It is built to be believed only as far as it has earned, and every input uses only what was known at the forecast date."] = "तीनों मापों में से हर एक के लिए एक मॉडल, जिसे उन वर्षों पर सरल पूर्वानुमानों के सामने परखा गया जो उसने कभी नहीं देखे। इसे उतना ही भरोसेमंद माना जाना चाहिए जितना इसने कमाया है, और हर इनपुट केवल वही इस्तेमाल करता है जो पूर्वानुमान की तिथि पर ज्ञात था।"
PAGE["XGBoost histogram trees. Three measures, three random starts each: nine models in the final fit. Each forecasts the change in the log of the level, with the number of months ahead as an input, for every horizon from 1 to 60."] = "XGBoost हिस्टोग्राम पेड़। तीन माप, हर एक के तीन यादृच्छिक आरंभ: अंतिम फ़िट में नौ मॉडल। हर एक स्तर के लघुगणक में बदलाव का पूर्वानुमान लगाता है, कितने महीने आगे यह इनपुट के रूप में लेकर, 1 से 60 तक की हर अवधि के लिए।"
PAGE["82 inputs, chosen from 119 candidates by testing on the validation years: recent movement, level against the recent average, volatility, vacancy and seeker rates, training and wage ratios and the demand channels. Dropping the inputs that identify a single district or sector cut the validation error for employed workers from 10.9% to 4.5%, because they let the trees memorise the period instead of the series. A test cuts the data at the forecast month, rebuilds the inputs and checks they are unchanged."] = "119 उम्मीदवारों में से सत्यापन वर्षों पर परखकर चुने गए 82 इनपुट: हाल की गति, हाल के औसत के सामने स्तर, अस्थिरता, रिक्ति और नौकरी चाहने वालों की दरें, प्रशिक्षण और वेतन अनुपात और माँग के स्रोत। किसी एक ज़िले या सेक्टर की पहचान कराने वाले इनपुट हटाने से नियोजित कामगारों की सत्यापन त्रुटि 10.9% से 4.5% रह गई, क्योंकि वे पेड़ों को श्रृंखला के बजाय अवधि रटने देते थे। एक परीक्षण पूर्वानुमान के महीने पर डेटा काटता है, इनपुट दोबारा बनाता है और जाँचता है कि वे बदले नहीं हैं।"
PAGE["Every forecast gets two 90% ranges, set from past errors for the same horizon: a usual one from 2010 to 2019 and a wider one that also uses the shock years. How they are set is on the <a class=\"ulink\" href=\"docs/methodology.html#doubt\">Methodology</a> page."] = "हर पूर्वानुमान को दो 90% दायरे मिलते हैं, जो उसी अवधि की पिछली त्रुटियों से तय होते हैं: एक सामान्य, 2010 से 2019 से, और एक चौड़ा, जो झटके वाले वर्ष भी लेता है। वे कैसे तय होते हैं यह <a class=\"ulink\" href=\"docs/methodology.html#doubt\">कार्यप्रणाली</a> पृष्ठ पर है।"
PAGE["One row for each district, trade and month. The states, trades and columns are listed under Dataset details below."] = "हर ज़िले, ट्रेड और महीने के लिए एक पंक्ति। राज्य, ट्रेड और कॉलम नीचे डेटा विवरण में सूचीबद्ध हैं।"
PAGE["What the monthly panel covers: the states, the trades of each sector and the columns of every row."] = "मासिक पैनल क्या-क्या समेटता है: राज्य, हर सेक्टर के ट्रेड और हर पंक्ति के कॉलम।"
PAGE["This page holds only what the other pages do not. The forecasting engine, the six readings and the test results are on <a class=\"ulink\" href=\"../about.html\">About</a>, the data and where it came from are on <a class=\"ulink\" href=\"../resources.html\">Resources</a>, and every number is served by the <a class=\"ulink\" href=\"../docs/api.html\">read-only API</a>."] = "इस पृष्ठ पर केवल वही है जो दूसरे पृष्ठों पर नहीं है। पूर्वानुमान इंजन, छह पाठ और परीक्षण के नतीजे <a class=\"ulink\" href=\"../about.html\">परिचय</a> पर हैं, डेटा और वह कहाँ से आया यह <a class=\"ulink\" href=\"../resources.html\">संसाधन</a> पर है, और हर संख्या <a class=\"ulink\" href=\"../docs/api.html\">केवल-पढ़ने योग्य API</a> से मिलती है।"
PAGE["Neighbouring series tend to miss in the same direction at once, so the range of a state or of India is not the sum of the ranges of its series. It is set from the errors of that level itself, for district and sector, state and sector, state, sector, trade and India."] = "पड़ोसी श्रृंखलाएँ अक्सर एक साथ एक ही दिशा में चूकती हैं, इसलिए किसी राज्य या भारत का दायरा उसकी श्रृंखलाओं के दायरों का जोड़ नहीं है। यह उसी स्तर की अपनी त्रुटियों से बनता है: ज़िला और सेक्टर, राज्य और सेक्टर, राज्य, सेक्टर, ट्रेड और भारत।"
PAGE["The flag percentiles, the label limits and the severity ratios are conventions, fixed before the test years were opened, not tuned."] = "चेतावनी के प्रतिशतक, लेबल की सीमाएँ और गंभीरता के अनुपात परंपराएँ हैं, जो परीक्षण वर्ष खोलने से पहले तय की गईं, कसी नहीं गईं।"
PAGE["Leaving the 2020 to 2023 shock out of the final fit, as the About page describes, is a judgement about a simulated shock, not a tuned choice. Its side effect is lumpier job-seeker growth where the horizon passes 24 months."] = "2020 से 2023 के झटके को अंतिम फ़िट से बाहर रखना, जैसा परिचय पृष्ठ बताता है, एक सिम्युलेटेड झटके के बारे में निर्णय है, कसा हुआ चुनाव नहीं। इसका साइड इफ़ेक्ट यह है कि जहाँ अवधि 24 महीने पार करती है वहाँ नौकरी चाहने वालों की वृद्धि ऊबड़-खाबड़ हो जाती है।"
PAGE["Where no checked range exists, the field is null and a note says so. The limits of the forecasts themselves are on the <a class=\"ulink\" href=\"../about.html#limits\">About</a> page."] = "जहाँ कोई जाँचा हुआ दायरा नहीं है, वहाँ क्षेत्र खाली (null) होता है और एक टिप्पणी यही बताती है। पूर्वानुमानों की अपनी सीमाएँ <a class=\"ulink\" href=\"../about.html#limits\">परिचय</a> पृष्ठ पर हैं।"
PAGE["Colours sort the 317 districts into five equal groups, so they show who is higher or lower, not by how much. Read the exact figure in the hover. White lines mark the state borders, simplified for orientation only. Their source is listed on the <a class=\"ulink\" href=\"resources.html#datasets\">Resources</a> page, and the limits of the forecasts are on the <a class=\"ulink\" href=\"about.html#limits\">About</a> page."] = "रंग 317 ज़िलों को पाँच बराबर समूहों में बाँटते हैं, इसलिए वे बताते हैं कि कौन ऊपर या नीचे है, कितना, यह नहीं। सटीक आँकड़ा ज़िले पर जाकर पढ़ें। सफ़ेद रेखाएँ राज्यों की सीमाएँ दिखाती हैं, जो केवल दिशा-बोध के लिए सरल की गई हैं। उनका स्रोत <a class=\"ulink\" href=\"resources.html#datasets\">संसाधन</a> पृष्ठ पर दर्ज है, और पूर्वानुमानों की सीमाएँ <a class=\"ulink\" href=\"about.html#limits\">परिचय</a> पृष्ठ पर हैं।"
PAGE["Every response says that the data is <strong>simulated</strong> and not an official statistic."] = "हर उत्तर बताता है कि डेटा <strong>सिम्युलेटेड</strong> है और कोई आधिकारिक आँकड़ा नहीं है।"
