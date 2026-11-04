/* KaushalSetu dashboard (v4): dependency-free. Everything comes from data/core.js (India, sectors, trades, states, ranges, capacity gap, rankings), data/alerts.js and
   one shard per state (data/shards/<state>.json) that is fetched when a state or district is chosen.  Built by src/v4/build_dashboard.py; nothing is typed in here.
   The filters live in the URL hash, so every view can be bookmarked:  #/forecast?sector=Healthcare&trade=HLT-3221&state=Kerala&district=332 */
(function () {
  "use strict";
  var D = window.DASH4, A = window.DASH4_ALERTS, M = D.meta, root = document.documentElement, NS = "http://www.w3.org/2000/svg";
  var STATES = M.states, SECTORS = M.sectors, TRADES = M.trades, YEARS = M.years, HC = M.hist_core[2], HS = M.hist_shard[2];
  var LANG = root.dataset.lang === "hi" ? "hi" : "en";
  var HI = {
    "#": "क्र.",
    "(beyond 24 months) are learned from pre-2020 dynamics and are lumpier where the horizon crosses 24 months.": "(24 महीने से आगे) 2020 से पहले के रुझानों से सीखे गए हैं और जहाँ अवधि 24 महीने पार करती है वहाँ अधिक असमान दिखते हैं।",
    "0 to 100. Compares openings per worker (vacancies, job-portal postings, National Career Service) with other districts of the same trade, plus a national level term; 50 is the median district at the 2018-2019 level.": "0 से 100। प्रति कामगार रिक्तियों (रिक्तियाँ, जॉब-पोर्टल पोस्टिंग, राष्ट्रीय कॅरियर सेवा) की तुलना उसी ट्रेड के अन्य ज़िलों से करता है, साथ में एक राष्ट्रीय स्तर का घटक; 50 का अर्थ है 2018-2019 के स्तर पर मध्य ज़िला।",
    "0 to 100; 50 is a typical district in the trade at the 2018-2019 level": "0 से 100; 50 का अर्थ है 2018-2019 के स्तर पर ट्रेड का एक सामान्य ज़िला",
    "2020-23 shock and recovery": "2020-23 का झटका और सुधार",
    "A national level term lets the index move up and down over the years: 50 is the median district at the 2018-2019 demand level, 84 is one standard deviation above, 16 one below.": "एक राष्ट्रीय स्तर का घटक सूचकांक को वर्षों में ऊपर-नीचे होने देता है: 50 का अर्थ 2018-2019 की माँग पर मध्य ज़िला, 84 एक मानक विचलन ऊपर और 16 एक नीचे।",
    "Alert": "चेतावनी",
    "Alert accuracy in testing": "परीक्षण में चेतावनियों की सटीकता",
    "Alerts 12 months ahead for {0}": "{0} के लिए 12 महीने आगे की चेतावनियाँ",
    "Alerts are relative: the series is among the 10% of districts in its trade with the highest (shortage) or lowest (oversupply) forecast vacancies per seeker in that month.": "चेतावनियाँ सापेक्ष हैं: श्रृंखला अपने ट्रेड के उन 10% ज़िलों में है जिनमें उस महीने प्रति नौकरी चाहने वाले पूर्वानुमानित रिक्तियाँ सबसे अधिक (कमी) या सबसे कम (अधिशेष) हैं।",
    "Alerts page": "चेतावनी पृष्ठ",
    "All districts": "सभी ज़िले",
    "All sectors": "सभी सेक्टर",
    "All states": "सभी राज्य",
    "All trades": "सभी ट्रेड",
    "An alert is relative: the series lies in the top (shortage) or bottom (oversupply) 10% of districts in its trade in that month. In testing such alerts were right about seven times in ten at 1-12 months, against a base rate of one in ten. Seeker forecasts and long horizons are less reliable; the confidence columns show it.": "चेतावनी सापेक्ष है: श्रृंखला उस महीने अपने ट्रेड के शीर्ष (कमी) या निचले (अधिशेष) 10% ज़िलों में है। परीक्षण में 1-12 महीनों पर ऐसी चेतावनियाँ दस में लगभग सात बार सही थीं, जबकि आधार दर दस में एक है। नौकरी चाहने वालों के पूर्वानुमान और लंबी अवधि कम भरोसेमंद हैं; विश्वसनीयता के स्तंभ यह दिखाते हैं।",
    "Annual mean 2030, with 2026 for comparison. Choose a sector or state in the filters.": "2030 का वार्षिक औसत, तुलना के लिए 2026 के साथ। फ़िल्टर में सेक्टर या राज्य चुनें।",
    "Avg. openings": "औसत रिक्तियाँ",
    "Both": "दोनों",
    "Both are 90% ranges. The usual one is calibrated on 2010-2019; the wide one also on 2020-2025.": "दोनों 90% दायरे हैं। सामान्य दायरा 2010-2019 पर और विस्तृत दायरा 2020-2025 पर भी आधारित है।",
    "Built": "बनाया गया",
    "By year": "वर्ष के अनुसार",
    "CSV": "CSV",
    "CSV and JSON of the page you are on use the current filters. Series-level files for all 7,925 series are in the export folder.": "इस पृष्ठ की CSV और JSON फ़ाइलें वर्तमान फ़िल्टर के अनुसार बनती हैं। सभी 7,925 श्रृंखलाओं की फ़ाइलें export फ़ोल्डर में हैं।",
    "Capacity gap": "क्षमता अंतर",
    "Certified per opening": "प्रति रिक्ति प्रमाणित",
    "Change": "बदलाव",
    "Click a row to filter by state": "राज्य से फ़िल्टर करने के लिए पंक्ति पर क्लिक करें",
    "Click a trade to filter": "फ़िल्टर करने के लिए ट्रेड पर क्लिक करें",
    "Confidence": "विश्वसनीयता",
    "Confidence S": "विश्वसनीयता (नौकरी चाहने वाले)",
    "Confidence V": "विश्वसनीयता (रिक्तियाँ)",
    "Confidence of this forecast by horizon (12-month bands):": "इस पूर्वानुमान की विश्वसनीयता अवधि के अनुसार (12-महीने के खंड):",
    "Construction": "निर्माण कार्य",
    "Coverage of the dataset": "डेटासेट का दायरा",
    "Cr": "करोड़",
    "Dashboard": "डैशबोर्ड",
    "Data and notes": "डेटा और टिप्पणियाँ",
    "December": "दिसंबर",
    "December values": "दिसंबर के मान",
    "Definitions": "परिभाषाएँ",
    "Demand Index": "माँग सूचकांक",
    "Demand Index 2030": "माँग सूचकांक 2030",
    "Demand Index in 2030 (annual mean for trades, December for sectors); click a state to filter": "2030 में माँग सूचकांक (ट्रेड के लिए वार्षिक औसत, सेक्टर के लिए दिसंबर); फ़िल्टर करने के लिए राज्य पर क्लिक करें",
    "District": "ज़िला",
    "Districts forecast to be short of workers or in surplus": "वे ज़िले जहाँ कामगारों की कमी या अधिशेष का अनुमान है",
    "Districts with the highest index: {0}": "सबसे ऊँचे सूचकांक वाले ज़िले: {0}",
    "Districts with the lowest index: {0}": "सबसे नीचे के सूचकांक वाले ज़िले: {0}",
    "Downloaded {0}.csv ({1} rows)": "{0}.csv डाउनलोड हुई ({1} पंक्तियाँ)",
    "Downloaded {0}.json ({1} rows)": "{0}.json डाउनलोड हुई ({1} पंक्तियाँ)",
    "Downloads": "डाउनलोड",
    "Early warnings": "पूर्व चेतावनी",
    "Early-warning alert": "पूर्व-चेतावनी अलर्ट",
    "Early-warning summary": "पूर्व-चेतावनी सारांश",
    "Employed": "नियोजित",
    "Employed 2030": "नियोजित 2030",
    "Employed now": "अभी नियोजित",
    "Employed workers": "नियोजित कामगार",
    "Exit": "बाहर निकलें",
    "Expected certified": "अपेक्षित प्रमाणित",
    "Expected certified a year": "प्रति वर्ष अपेक्षित प्रमाणित",
    "Fewer trainees certified than openings": "रिक्तियों से कम प्रशिक्षु प्रमाणित",
    "Final models fitted on": "अंतिम मॉडल इस डेटा पर बने",
    "Five-year forecasts with 90% ranges": "90% दायरे सहित पाँच वर्ष के पूर्वानुमान",
    "For {0}, {1} months ahead": "{0} के लिए, {1} महीने आगे",
    "Forecast": "पूर्वानुमान",
    "Forecast from": "पूर्वानुमान का आधार माह",
    "Forecast months use the forecast vacancies only. In the past years this version tracks the three-channel index closely (correlation 0.89 to 0.94 in 2012-2025).": "पूर्वानुमान के महीनों में केवल पूर्वानुमानित रिक्तियाँ ली जाती हैं। बीते वर्षों में यह रूप तीन-स्रोत वाले सूचकांक के बहुत निकट रहता है (2012-2025 में सहसंबंध 0.89 से 0.94)।",
    "Forecast openings (average monthly vacancies) against seats and expected certified trainees": "पूर्वानुमानित रिक्तियाँ (औसत मासिक) सीटों और अपेक्षित प्रमाणित प्रशिक्षुओं के सामने",
    "Forecast openings against training seats": "पूर्वानुमानित रिक्तियाँ बनाम प्रशिक्षण सीटें",
    "Forecast openings against training seats sanctioned in 2025-26 (held flat) and the trainees expected to be certified (seats times the 2023-25 median certification rate). Status: seats fall short when the district's share of seats is less than 0.6 times its share of openings in the trade, exceed when more than 1.65 times.": "पूर्वानुमानित रिक्तियाँ बनाम 2025-26 में स्वीकृत प्रशिक्षण सीटें (स्थिर मानी गई) और अपेक्षित प्रमाणित प्रशिक्षु (सीटें × 2023-25 की माध्य प्रमाणन दर)। स्थिति: जब ट्रेड में ज़िले की सीटों का हिस्सा रिक्तियों के हिस्से के 0.6 गुना से कम हो तो सीटें कम पड़ती हैं, 1.65 गुना से अधिक हो तो सीटें अधिक हैं।",
    "Forecast page": "पूर्वानुमान पृष्ठ",
    "Forecasts are not certain.": "पूर्वानुमान निश्चित नहीं हैं।",
    "Healthcare": "स्वास्थ्य सेवा",
    "High": "उच्च",
    "High, Medium or Low from the typical error of earlier forecasts for the same trade and horizon band: up to 8%, up to 20%, above; one level lower for small series.": "उच्च, मध्यम या निम्न: उसी ट्रेड और अवधि-खंड के पिछले पूर्वानुमानों की सामान्य त्रुटि से, क्रमशः 8% तक, 20% तक, उससे अधिक; छोटी श्रृंखलाओं के लिए एक स्तर नीचे।",
    "Highest forecast vacancies per seeker in the trade": "ट्रेड में प्रति नौकरी चाहने वाले सबसे अधिक पूर्वानुमानित रिक्तियाँ",
    "History": "इतिहास",
    "History to {0} and forecast to {1}": "{0} तक का इतिहास और {1} तक का पूर्वानुमान",
    "How often the 90% ranges held": "90% दायरे कितनी बार सही रहे",
    "How strong hiring demand is, from 0 to 100": "भर्ती की माँग कितनी मज़बूत है, 0 से 100 तक",
    "IT-ITeS": "आईटी-आईटीईएस",
    "It behaves like official statistics but describes no real district.": "यह सरकारी आँकड़ों जैसा व्यवहार करता है, पर किसी वास्तविक ज़िले का वर्णन नहीं करता।",
    "It compares a district with the other districts of the same trade in the same month, using openings per worker from vacancies, job-portal postings and the National Career Service.": "यह एक ज़िले की तुलना उसी महीने उसी ट्रेड के अन्य ज़िलों से करता है, रिक्तियों, जॉब-पोर्टल पोस्टिंग और राष्ट्रीय कॅरियर सेवा से प्रति कामगार रिक्तियों के आधार पर।",
    "JSON": "JSON",
    "Job vacancies": "रिक्तियाँ",
    "L": "लाख",
    "Latest December against December 2030": "नवीनतम दिसंबर बनाम दिसंबर 2030",
    "Latest {0}, December {1}": "नवीनतम {0}, दिसंबर {1}",
    "Loading…": "लोड हो रहा है…",
    "Long horizons": "लंबी अवधि",
    "Low": "निम्न",
    "Lowest forecast vacancies per seeker in the trade": "ट्रेड में प्रति नौकरी चाहने वाले सबसे कम पूर्वानुमानित रिक्तियाँ",
    "Manufacturing": "विनिर्माण",
    "Measure": "माप",
    "Medium": "मध्यम",
    "Method, limits and downloads": "तरीका, सीमाएँ और डाउनलोड",
    "Month": "महीना",
    "More trainees certified than openings": "रिक्तियों से अधिक प्रशिक्षु प्रमाणित",
    "Name": "नाम",
    "No calibrated 90% range exists for this combination of filters, so only the point forecast is drawn. Choose a sector, state, state with sector, or a district with a sector or trade for a range.": "फ़िल्टर के इस संयोजन के लिए कोई जाँचा हुआ 90% दायरा नहीं है, इसलिए केवल बिंदु पूर्वानुमान दिखाया गया है। दायरे के लिए सेक्टर, राज्य, सेक्टर सहित राज्य, या सेक्टर/ट्रेड सहित ज़िला चुनें।",
    "Open": "खोलें",
    "By sector": "सेक्टर के अनुसार",
    "Click a row to choose a sector": "सेक्टर चुनने के लिए पंक्ति पर क्लिक करें",
    "Endpoint": "एंडपॉइंट",
    "Rows to return": "लौटाई जाने वाली पंक्तियाँ",
    "12, 36 and 60": "12, 36 और 60",
    "API": "API",
    "All years": "सभी वर्ष",
    "Build a request": "अनुरोध बनाएँ",
    "Choose an endpoint and its options. The filters above set the state, district, sector and trade.": "एक एंडपॉइंट और उसके विकल्प चुनें। ऊपर के फ़िल्टर राज्य, ज़िला, सेक्टर और ट्रेड तय करते हैं।",
    "Copied to the clipboard.": "क्लिपबोर्ड पर कॉपी हो गया।",
    "Copy": "कॉपी करें",
    "Current alerts": "मौजूदा चेतावनियाँ",
    "Detail": "विवरण",
    "District and trade series": "ज़िला और ट्रेड श्रृंखलाएँ",
    "Each December": "हर दिसंबर",
    "Entering a tail": "छोर में प्रवेश",
    "Every month": "हर महीना",
    "Every parameter, an example and the error codes are on the Forecast API page.": "हर पैरामीटर, एक उदाहरण और त्रुटि कोड पूर्वानुमान API पृष्ठ पर हैं।",
    "Every series": "हर श्रृंखला",
    "Filters: {0}": "फ़िल्टर: {0}",
    "Forecast API": "पूर्वानुमान API",
    "Largest gap either way": "दोनों ओर सबसे बड़ा अंतर",
    "Leaving a tail": "छोर से बाहर",
    "Level": "स्तर",
    "Months ahead": "कितने महीने आगे",
    "Most oversupplied first": "सबसे अधिक आपूर्ति पहले",
    "Most undersupplied first": "सबसे कम आपूर्ति पहले",
    "No key is needed; up to 60 requests a minute. Every response says that the data is simulated.": "किसी कुंजी की ज़रूरत नहीं; एक मिनट में 60 अनुरोध तक। हर उत्तर बताता है कि डेटा सिम्युलेटेड है।",
    "One total": "एक कुल",
    "Open in a new tab": "नए टैब में खोलें",
    "Press Run to fetch the request above.": "ऊपर का अनुरोध भेजने के लिए चलाएँ दबाएँ।",
    "Resolution": "विभाजन",
    "Response": "उत्तर",
    "Run": "चलाएँ",
    "Running…": "चल रहा है…",
    "Select the address above to copy it.": "कॉपी करने के लिए ऊपर का पता चुनें।",
    "Shortened to the first {0} characters; open the request for the whole response.": "पहले {0} अक्षरों तक छोटा किया गया; पूरा उत्तर देखने के लिए अनुरोध खोलें।",
    "The request could not be sent. Open the dashboard from a server that also serves the API.": "अनुरोध नहीं भेजा जा सका। डैशबोर्ड ऐसे सर्वर से खोलें जो API भी देता हो।",
    "This endpoint takes no filters.": "यह एंडपॉइंट कोई फ़िल्टर नहीं लेता।",
    "Type": "प्रकार",
    "Seat scenario": "सीट परिदृश्य",
    "Change the seats and see what it does to the balance with the openings. The certification rate and the forecast openings stay as they are.": "सीटें बदलकर देखें कि रिक्तियों के साथ संतुलन पर इसका क्या असर पड़ता है। प्रमाणन दर और पूर्वानुमानित रिक्तियाँ जैसी हैं वैसी रहती हैं।",
    "Change seats by (%)": "सीटों में बदलाव (%)",
    "From year": "किस वर्ष से",
    "Evaluate in": "किस वर्ष में आँकें",
    "Target certified per opening": "लक्ष्य: प्रति रिक्ति प्रमाणित",
    "Apply": "लागू करें",
    "Reset": "रीसेट",
    "{0}% from {1}": "{1} से {0}%",
    "No change": "कोई बदलाव नहीं",
    "All rows in {0}; below 1 is undersupply": "{0} में सभी पंक्तियाँ; 1 से कम का अर्थ कम आपूर्ति",
    "Undersupplied rows": "कम आपूर्ति वाली पंक्तियाँ",
    "Of {0} rows": "{0} पंक्तियों में से",
    "Seats to add for the target": "लक्ष्य के लिए जोड़ने योग्य सीटें",
    "Rows above the target could release {0}": "लक्ष्य से ऊपर की पंक्तियाँ {0} सीटें छोड़ सकती हैं",
    "Seats in scenario": "परिदृश्य में सीटें",
    "Certified per opening now → scenario": "प्रति रिक्ति प्रमाणित अभी → परिदृश्य",
    "Severity now → scenario": "गंभीरता अभी → परिदृश्य",
    "Seats for the target": "लक्ष्य के लिए सीटें",
    "Nothing to show for these filters.": "इन फ़िल्टर के लिए दिखाने को कुछ नहीं है।",
    "Download this scenario (CSV)": "यह परिदृश्य डाउनलोड करें (CSV)",
    "Trades of the chosen state": "चुने हुए राज्य के ट्रेड",
    "District and trade series of the chosen state": "चुने हुए राज्य की ज़िला और ट्रेड श्रृंखलाएँ",
    "{0}, ranked by the scenario's score, most undersupplied first.": "{0}, परिदृश्य के अंक के अनुसार क्रमबद्ध, सबसे कम आपूर्ति पहले।",
    "Seats for the target are the seats at which certified per opening reaches the target (openings of the year × target ÷ certification rate); the percentage is the change from today's seats. No delay is modelled between sanctioning a seat and a trainee being certified, and teaching capacity is not limited: read this as a planning ratio, not a forecast of placements.": "लक्ष्य के लिए सीटें वे सीटें हैं जिन पर प्रति रिक्ति प्रमाणित लक्ष्य तक पहुँचता है (वर्ष की रिक्तियाँ × लक्ष्य ÷ प्रमाणन दर); प्रतिशत आज की सीटों से बदलाव है। सीट स्वीकृत होने और प्रशिक्षु के प्रमाणित होने के बीच की देरी नहीं मानी गई है, और शिक्षण क्षमता सीमित नहीं है: इसे योजना अनुपात की तरह पढ़ें, नियुक्तियों के पूर्वानुमान की तरह नहीं।",
    "At the horizon": "आगे के महीने पर",
    "Entering an alert": "चेतावनी में प्रवेश",
    "Leaving an alert": "चेतावनी से बाहर",
    "View": "दृश्य",
    "Entering the shortage tail": "कमी वाले छोर में प्रवेश",
    "Entering the oversupply tail": "अधिशेष वाले छोर में प्रवेश",
    "Leaving the shortage tail": "कमी वाले छोर से बाहर",
    "Leaving the oversupply tail": "अधिशेष वाले छोर से बाहर",
    "Entering shortage alert": "कमी की चेतावनी में प्रवेश",
    "Leaving shortage alert": "कमी की चेतावनी से बाहर",
    "Entering oversupply alert": "अधिशेष चेतावनी में प्रवेश",
    "Leaving oversupply alert": "अधिशेष चेतावनी से बाहर",
    "Not in an alert tail now, in it {0} months ahead": "अभी चेतावनी वाले छोर में नहीं, {0} महीने आगे उसमें",
    "In an alert tail now, out of it {0} months ahead": "अभी चेतावनी वाले छोर में, {0} महीने आगे उससे बाहर",
    "{0} series change status": "{0} श्रृंखलाओं की स्थिति बदलती है",
    "For {0}, now (December 2025) against {1} months ahead": "{0} के लिए, अभी (दिसंबर 2025) बनाम {1} महीने आगे",
    "Percentile now → then": "प्रतिशतक अभी → तब",
    "Vacancies per 100 seekers now → then": "प्रति 100 नौकरी चाहने वाले रिक्तियाँ अभी → तब",
    "First month in the tail": "छोर में पहला महीना",
    "No changes for these filters.": "इन फ़िल्टर के लिए कोई बदलाव नहीं।",
    "Most alerts persist: of the {0} shortage and {1} oversupply alerts now, {2} and {3} are out of the tail {4} months ahead (and as many have moved in).": "अधिकतर चेतावनियाँ बनी रहती हैं: अभी की {0} कमी और {1} अधिशेष चेतावनियों में से {4} महीने आगे क्रमशः {2} और {3} छोर से बाहर हो जाती हैं (और लगभग उतनी ही अंदर आ जाती हैं)।",
    "Now means December 2025, from the actual vacancies and registered seekers, ranked among the districts of the trade like the forecasts. An alert tail is the top tenth (shortage) or the bottom tenth (oversupply). The forecast flags are relative: a series can leave a tail because others rose faster, not because it fell.": "'अभी' का अर्थ दिसंबर 2025 है, वास्तविक रिक्तियों और पंजीकृत नौकरी चाहने वालों से, पूर्वानुमानों की तरह ट्रेड के ज़िलों के बीच क्रमबद्ध। चेतावनी वाला छोर शीर्ष दसवाँ हिस्सा (कमी) या निचला दसवाँ हिस्सा (अधिशेष) है। पूर्वानुमान के निशान सापेक्ष हैं: कोई श्रृंखला इसलिए छोर छोड़ सकती है कि बाकी तेज़ी से बढ़े, इसलिए नहीं कि वह गिरी।",
    "Where trained supply and openings are furthest apart": "जहाँ प्रशिक्षित आपूर्ति और रिक्तियों में सबसे अधिक अंतर है",
    "Severity ranking": "गंभीरता क्रम",
    "Where trained supply is furthest from the openings, for the filters above. Undersupply: fewer people finish training in a year than there are openings. Oversupply: more.": "ऊपर के फ़िल्टर के लिए, जहाँ प्रशिक्षित आपूर्ति रिक्तियों से सबसे दूर है। कम आपूर्ति: एक वर्ष में रिक्तियों से कम लोग प्रशिक्षण पूरा करते हैं। अधिक आपूर्ति: अधिक लोग।",
    "State and trade": "राज्य और ट्रेड",
    "Districts": "ज़िले",
    "District and sector": "ज़िला और सेक्टर",
    "District and trade": "ज़िला और ट्रेड",
    "Undersupplied first": "कम आपूर्ति पहले",
    "Oversupplied first": "अधिक आपूर्ति पहले",
    "Largest gap first": "सबसे बड़ा अंतर पहले",
    "Rank": "क्रम",
    "Order": "क्रमबद्ध",
    "Rows": "पंक्तियाँ",
    "Choose a state or a district in the filters to rank the district and trade series.": "ज़िला और ट्रेड श्रृंखलाओं का क्रम देखने के लिए फ़िल्टर में राज्य या ज़िला चुनें।",
    "Nothing to rank for these filters. Clear the trade filter for district levels, and the district filter for trades.": "इन फ़िल्टर के लिए क्रम में रखने को कुछ नहीं है। ज़िला स्तर के लिए ट्रेड फ़िल्टर और ट्रेड के लिए ज़िला फ़िल्टर हटाएँ।",
    "Score": "अंक",
    "Severity": "गंभीरता",
    "Openings": "रिक्तियाँ",
    "Change since 2026": "2026 से बदलाव",
    "Place": "स्थान",
    "Showing {0} of {1}.": "{1} में से {0} दिखाई गई हैं।",
    "Top 25": "शीर्ष 25",
    "Top 100": "शीर्ष 100",
    "All": "सभी",
    "ln(expected certified per year ÷ average monthly openings of the year). Below 0 undersupply, above 0 oversupply. Severe: a ratio of 2 or more either way; high: 1.5; moderate: 1.25.": "ln(प्रति वर्ष अपेक्षित प्रमाणित ÷ उस वर्ष की औसत मासिक रिक्तियाँ)। 0 से कम पर कम आपूर्ति, 0 से अधिक पर अधिक आपूर्ति। गंभीर: दोनों ओर 2 या उससे अधिक का अनुपात; उच्च: 1.5; मध्यम: 1.25।",
    "Seats are held flat at the 2025-26 level, and openings are a monthly stock against an annual flow, so read this as a ranking, not a count of unfilled places.": "सीटें 2025-26 के स्तर पर स्थिर मानी गई हैं, और रिक्तियाँ मासिक स्टॉक हैं जबकि प्रमाणन वार्षिक प्रवाह, इसलिए इसे क्रम के रूप में पढ़ें, खाली स्थानों की गिनती के रूप में नहीं।",
    "Other rankings for all of India": "पूरे भारत के अन्य क्रम",
    "Balanced": "संतुलित",
    "Severe undersupply": "गंभीर कम आपूर्ति",
    "High undersupply": "उच्च कम आपूर्ति",
    "Moderate undersupply": "मध्यम कम आपूर्ति",
    "Severe oversupply": "गंभीर अधिक आपूर्ति",
    "High oversupply": "उच्च अधिक आपूर्ति",
    "Moderate oversupply": "मध्यम अधिक आपूर्ति",
    "Map": "मानचित्र",
    "Districts and states on the map": "मानचित्र पर ज़िले और राज्य",
    "Map of {0} districts coloured by {1}": "{0} ज़िलों का मानचित्र, {1} से रंगा हुआ",
    "{0} now, {1} in {2} months": "अभी {0}, {2} महीने में {1}",
    "Usual 90% range {0} to {1}": "सामान्य 90% दायरा {0} से {1}",
    "{0} months ahead": "{0} महीने आगे",
    "Dec 2025 and {0}": "दिसंबर 2025 और {0}",
    "Change in {0}, Dec 2025 to {1}": "दिसंबर 2025 से {1} तक {0} में बदलाव",
    "Demand Index in {0}": "{0} में माँग सूचकांक",
    "Five equal groups of districts; click a district to choose it.": "ज़िलों के पाँच बराबर समूह; किसी ज़िले को चुनने के लिए उस पर क्लिक करें।",
    "The map is by sector: the trade filter chooses its sector.": "मानचित्र सेक्टर के अनुसार है: ट्रेड फ़िल्टर उसका सेक्टर चुन लेता है।",
    "Show the whole region again": "पूरा क्षेत्र फिर दिखाएँ",
    "Open the Forecast page": "पूर्वानुमान पृष्ठ खोलें",
    "Open the Capacity gap": "क्षमता अंतर खोलें",
    "{0}: highest {1} ({2}), lowest {3} ({4}).": "{0}: सबसे ऊँचा {1} ({2}), सबसे नीचा {3} ({4})।",
    "Now": "अभी",
    "Highest districts": "सबसे ऊँचे ज़िले",
    "Lowest districts": "सबसे नीचे के ज़िले",
    "Where the alerts are": "चेतावनियाँ कहाँ हैं",
    "Districts with the most alerts {0} months ahead": "{0} महीने आगे सबसे अधिक चेतावनियों वाले ज़िले",
    "No alerts for these filters.": "इन फ़िल्टर के लिए कोई चेतावनी नहीं।",
    "An alert marks a district-trade in the top or bottom tenth of its trade for forecast vacancies per seeker.": "चेतावनी उस ज़िला-ट्रेड को चिह्नित करती है जो प्रति नौकरी चाहने वाले पूर्वानुमानित रिक्तियों में अपने ट्रेड के शीर्ष या निचले दसवें हिस्से में है।",
    "Click a row to choose a state": "राज्य चुनने के लिए पंक्ति पर क्लिक करें",
    "Press Enter to filter": "फ़िल्टर करने के लिए Enter दबाएँ",
    "Openings per seat": "प्रति सीट रिक्तियाँ",
    "Oversupply": "अधिशेष",
    "Oversupply alert": "अधिशेष चेतावनी",
    "Oversupply alerts": "अधिशेष चेतावनियाँ",
    "Overview": "सारांश",
    "Percentile": "प्रतिशतक",
    "Point forecast and the two 90% ranges": "बिंदु पूर्वानुमान और दोनों 90% दायरे",
    "Rankings": "रैंकिंग",
    "Rankings are computed once for all of India and do not follow the filters.": "रैंकिंग पूरे भारत के लिए एक बार निकाली जाती हैं और फ़िल्टर के अनुसार नहीं बदलतीं।",
    "Read this first": "पहले यह पढ़ें",
    "Registered job seekers": "पंजीकृत नौकरी चाहने वाले",
    "Reset filters": "फ़िल्टर हटाएँ",
    "Right": "सही",
    "Seats": "सीटें",
    "Seats are held flat because no seat plans are forecast. Openings are a monthly stock and seats an annual flow, so read the ratios as a ranking of where capacity is stretched, not as a count of unfilled places.": "सीटें स्थिर मानी गई हैं क्योंकि सीट योजनाओं का पूर्वानुमान नहीं होता। रिक्तियाँ मासिक स्टॉक हैं और सीटें वार्षिक प्रवाह, इसलिए अनुपात को इस क्रम के रूप में पढ़ें कि क्षमता कहाँ तनी हुई है, खाली स्थानों की गिनती के रूप में नहीं।",
    "Sector": "सेक्टर",
    "Seekers": "नौकरी चाहने वाले",
    "Seekers are the least reliable measure,": "नौकरी चाहने वाले सबसे कम भरोसेमंद माप हैं,",
    "Seekers change": "नौकरी चाहने वाले: बदलाव",
    "Series": "श्रृंखला",
    "Share of actual values inside the usual range in held-out years (a good range gives about 90%). The wide range includes 2020-25 in its calibration, so it cannot be tested on those years.": "परीक्षण वर्षों में वास्तविक मानों का कितना हिस्सा सामान्य दायरे के भीतर रहा (अच्छा दायरा लगभग 90% देता है)। विस्तृत दायरे में 2020-25 शामिल है, इसलिए उन वर्षों पर उसकी जाँच नहीं हो सकती।",
    "Share of alerts that were in the true top or bottom 10% (and how many times better than chance), 2015-19, 1-12 months ahead": "जो चेतावनियाँ वास्तव में शीर्ष या निचले 10% में थीं उनका हिस्सा (और संयोग से कितने गुना बेहतर), 2015-19, 1-12 महीने आगे",
    "Shortage": "कमी",
    "Shortage alert": "कमी की चेतावनी",
    "Shortage alerts": "कमी की चेतावनियाँ",
    "Showing the first {0} of {1}; the CSV has all of them.": "{1} में से पहली {0} दिखाई गई हैं; CSV में सभी हैं।",
    "Simulated data, not official statistics": "सिम्युलेटेड डेटा, आधिकारिक आँकड़े नहीं",
    "Skip to the page": "पृष्ठ पर जाएँ",
    "State": "राज्य",
    "States": "राज्य",
    "States by sector": "राज्य और सेक्टर",
    "States by trade": "राज्य और ट्रेड",
    "Textiles and Apparel": "वस्त्र एवं परिधान",
    "The 2020-23 shock was not foreseeable from earlier years; ranges calibrated on calm years are too narrow for totals, so wide ranges are drawn too.": "2020-23 का झटका पहले के वर्षों से अनुमान योग्य नहीं था; शांत वर्षों पर बने दायरे कुल योग के लिए बहुत संकरे हैं, इसलिए विस्तृत दायरे भी दिखाए गए हैं।",
    "The data is simulated.": "डेटा सिम्युलेटेड है।",
    "The series is in the top or bottom 10% of districts of its trade in forecast vacancies per seeker for that month. A watch is the next 15%.": "उस महीने प्रति नौकरी चाहने वाले पूर्वानुमानित रिक्तियों में श्रृंखला अपने ट्रेड के शीर्ष या निचले 10% ज़िलों में है। निगरानी अगले 15% के लिए है।",
    "The usual range was calibrated on 2010-2019, years without an unforeseen shock; the wide range also uses 2020-2025 and is the one to read for totals of many series, whose errors move together.": "सामान्य दायरा 2010-2019 पर बना है, जब कोई अप्रत्याशित झटका नहीं था; विस्तृत दायरा 2020-2025 भी लेता है और कई श्रृंखलाओं के कुल योग के लिए वही पढ़ना चाहिए, क्योंकि उनकी त्रुटियाँ साथ-साथ चलती हैं।",
    "This page could not be drawn": "यह पृष्ठ नहीं बन सका",
    "Totals for a state or India: the usual range held only {0} of the time for employed workers in 2015-19 and {1} in 2020-25, which is why the wide range is shown for totals. District-sector totals behave like single series ({2} in 2015-19).": "राज्य या भारत के कुल योग: नियोजित कामगारों के लिए सामान्य दायरा 2015-19 में केवल {0} और 2020-25 में {1} बार सही रहा, इसीलिए कुल योग के लिए विस्तृत दायरा दिखाया जाता है। ज़िला-सेक्टर कुल योग एकल श्रृंखला जैसे व्यवहार करते हैं (2015-19 में {2})।",
    "Trade": "ट्रेड",
    "Trades": "ट्रेड",
    "Trades, states and districts compared": "ट्रेड, राज्य और ज़िलों की तुलना",
    "Training seats": "प्रशिक्षण सीटें",
    "Usual 90% range": "सामान्य 90% दायरा",
    "Usual and wide range": "सामान्य और विस्तृत दायरा",
    "Usual range": "सामान्य दायरा",
    "Vacancies": "रिक्तियाँ",
    "Vacancies change": "रिक्तियाँ: बदलाव",
    "Vacancies per 100 seekers": "प्रति 100 नौकरी चाहने वाले रिक्तियाँ",
    "Value": "मान",
    "What the index means": "सूचकांक का अर्थ",
    "Where employment, vacancies and seekers are heading to 2030": "2030 तक रोज़गार, रिक्तियाँ और नौकरी चाहने वाले किस ओर",
    "Wide 90% range": "विस्तृत 90% दायरा",
    "Wide range": "विस्तृत दायरा",
    "Year": "वर्ष",
    "Year 2030. Below 1 certified per opening, fewer people finish training in a year than there are openings.": "वर्ष 2030। प्रति रिक्ति 1 से कम प्रमाणित होने का अर्थ है कि एक वर्ष में रिक्तियों से कम लोग प्रशिक्षण पूरा करते हैं।",
    "all sectors": "सभी सेक्टर",
    "and their confidence labels do not always fall as the horizon grows.": "और उनके विश्वसनीयता लेबल अवधि बढ़ने पर हमेशा नहीं घटते।",
    "by Dec {0}: {1}": "दिसंबर {0} तक: {1}",
    "charts show from": "चार्ट इससे दिखते हैं",
    "districts": "ज़िले",
    "districts from": "ज़िला स्तर इससे",
    "forecast": "पूर्वानुमान",
    "forecast for": "का पूर्वानुमान",
    "held flat at the 2025-26 level (assumption)": "2025-26 के स्तर पर स्थिर (मान्यता)",
    "in": "में",
    "in Dec {0}": "दिसंबर {0} में",
    "in {0}; {1} in {2}": "{0} में; {2} में {1}",
    "made from": "आधार",
    "months": "महीने",
    "seats times the 2023-25 certification rate": "सीटें × 2023-25 की प्रमाणन दर",
    "sectors": "सेक्टर",
    "series at 12 months": "12 महीने पर श्रृंखलाएँ",
    "states": "राज्य",
    "trades": "ट्रेड",
    "usual range": "सामान्य दायरा",
    "wide range": "विस्तृत दायरा",
    "without the 2020-23 shock and recovery pairs": "2020-23 के झटके और सुधार वाले जोड़ों के बिना",
    "{0} flagged series": "{0} चिह्नित श्रृंखलाएँ",
    "{0} months": "{0} महीने"
  };
  var t = function (s) { return LANG === "hi" && HI[s] ? HI[s] : s; };
  var HIN = window.DASH4_HI || {};                                            // Hindi names of the states, districts and trades (the public site's dictionary)
  /* In Hindi, names the page printed in English (a state, a district, a trade, "Kerala, Healthcare") are replaced in place after each draw. */
  function localise(node) {
    if (LANG !== "hi" || !node) return;
    var w = document.createTreeWalker(node, NodeFilter.SHOW_TEXT, null), n, list = [];
    while ((n = w.nextNode())) list.push(n);
    var one = function (p) { return HIN[p] || HI[p] || null; };
    list.forEach(function (x) {
      var raw = x.nodeValue, tt = raw.trim();
      if (!tt || /^[\d\s.,%+\-−]+$/.test(tt)) return;
      var h = one(tt);
      if (!h) { var parts = tt.split(", "), got = parts.map(function (p) { return one(p) || p; }); if (parts.length > 1 && parts.some(one)) h = got.join(", "); }
      if (h) x.nodeValue = raw.replace(tt, h);
    });
  }
  var tf = function (s) { var a = Array.prototype.slice.call(arguments, 1); return t(s).replace(/\{(\d)\}/g, function (_, i) { return a[+i]; }); };
  var PAGES = {
    overview: ["Overview", "Where employment, vacancies and seekers are heading to 2030"], map: ["Map", "Districts and states on the map"], forecast: ["Forecast", "Five-year forecasts with 90% ranges"], index: ["Demand Index", "How strong hiring demand is, from 0 to 100"],
    capacity: ["Capacity gap", "Forecast openings against training seats"], ranking: ["Rankings", "Where trained supply and openings are furthest apart"], warnings: ["Early warnings", "Districts forecast to be short of workers or in surplus"], data: ["Data and notes", "Method, limits and downloads"], api: ["API", "Fetch these numbers as JSON, with the filters above"]
  };
  var TR = {}, TIX = {}, DNAME = {}, DSTATE = {}, DLIST = [];
  TRADES.forEach(function (x, i) { TR[x.c] = x; TIX[x.c] = i; });
  D.meta.districts.forEach(function (d) { DNAME[d[0]] = d[1]; DSTATE[d[0]] = STATES[d[2]]; DLIST.push({ c: String(d[0]), n: d[1], s: STATES[d[2]] }); });
  DLIST.sort(function (a, b) { return a.n < b.n ? -1 : 1; });
  var $ = function (s, r) { return (r || document).querySelector(s); };
  var $$ = function (s, r) { return Array.prototype.slice.call((r || document).querySelectorAll(s)); };
  var esc = function (s) { return String(s).replace(/[&<>"]/g, function (c) { return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]; }); };
  var fmt = function (n, d) { return Number(n).toLocaleString("en-IN", { minimumFractionDigits: d || 0, maximumFractionDigits: d || 0 }); };
  var compact = function (n) { var a = Math.abs(n), s = n < 0 ? "−" : ""; return a >= 1e7 ? s + (a / 1e7).toFixed(2) + " " + t("Cr") : a >= 1e5 ? s + (a / 1e5).toFixed(2) + " " + t("L") : a >= 1e3 ? s + (a / 1e3).toFixed(1) + (LANG === "hi" ? " हज़ार" : "K") : s + Math.round(a); };
  var pct = function (n, d) { return (n > 0.0005 ? "+" : n < -0.0005 ? "−" : "") + Math.abs(n).toFixed(d == null ? 1 : d) + "%"; };
  var MON = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];
  var MONHI = ["जन॰", "फ़र॰", "मार्च", "अप्रैल", "मई", "जून", "जुलाई", "अग॰", "सित॰", "अक्टू॰", "नव॰", "दिस॰"];
  var ml = function (ym) { var p = ym.split("-"); return (LANG === "hi" ? MONHI : MON)[+p[1] - 1] + " " + p[0]; };
  var css = function (n) { return getComputedStyle(root).getPropertyValue(n).trim(); };
  var last = function (a) { return a[a.length - 1]; };
  var slug = function (s) { return String(s).toLowerCase().replace(/[^a-z0-9]+/g, "-").replace(/^-|-$/g, ""); };
  var sum = function (a) { return a.reduce(function (x, y) { return x + y; }, 0); };
  var dir = function (v) { return '<span class="delta ' + (v >= 0 ? "up" : "down") + '">' + pct(v) + "</span>"; };
  var growth = function (a, b) { return a ? (b / a - 1) * 100 : 0; };
  var NAMES = { E: "Employed workers", V: "Job vacancies", S: "Registered job seekers" };
  var COLORS = function () { return { E: css("--employed"), V: css("--demand"), S: css("--supply") }; };
  var CONF = { H: "High", M: "Medium", L: "Low" };
  function el(tag, attrs, parent) { var e = document.createElementNS(NS, tag); for (var k in attrs) e.setAttribute(k, attrs[k]); if (parent) parent.appendChild(e); return e; }
  function mAdd(ym, n) { var y = +ym.slice(0, 4), m = +ym.slice(5) - 1 + n; return (y + Math.floor(m / 12)) + "-" + ("0" + (m % 12 + 1)).slice(-2); }
  function monthsOf(start, n) { var o = []; for (var i = 0; i < n; i++) o.push(mAdd(start, i)); return o; }
  var decs = function (a) { return YEARS.map(function (_, y) { return a[12 * y + 11]; }); };

  /* ---------- tooltip ---------- */
  var tip = $("#tip");
  function showTip(html, x, y) { tip.innerHTML = html; tip.hidden = false; var w = tip.offsetWidth, h = tip.offsetHeight; tip.style.left = Math.min(Math.max(8, x + 14), window.innerWidth - w - 8) + "px"; tip.style.top = (y - h - 14 < 8 ? y + 18 : y - h - 14) + "px"; }
  function hideTip() { tip.hidden = true; }
  document.addEventListener("pointermove", function (e) { var q = e.target.closest ? e.target.closest("[data-tip]") : null; if (q) showTip(q.getAttribute("data-tip"), e.clientX, e.clientY); else if (!document.body.classList.contains("tip-chart")) hideTip(); });

  /* ---------- URL state: sector, trade, state, district ---------- */
  var cur = { page: "overview", p: {}, csv: null };
  function parse() {
    var h = location.hash.replace(/^#\/?/, ""), q = h.split("?"), page = PAGES[q[0]] ? q[0] : "overview", p = {};
    (q[1] || "").split("&").forEach(function (kv) { if (!kv) return; var a = kv.split("="); p[decodeURIComponent(a[0])] = decodeURIComponent((a[1] || "").replace(/\+/g, " ")); });
    if (p.trade && !TR[p.trade]) delete p.trade;
    if (p.trade) p.sector = TR[p.trade].s;
    if (p.sector && SECTORS.indexOf(p.sector) < 0) delete p.sector;
    if (p.trade && p.sector && TR[p.trade].s !== p.sector) delete p.trade;
    if (p.state && STATES.indexOf(p.state) < 0) delete p.state;
    if (p.district) { if (!DNAME[p.district]) delete p.district; else if (p.state && p.state !== DSTATE[p.district]) delete p.district; else p.state = DSTATE[p.district]; }
    return { page: page, p: p };
  }
  function url(page, patch) {
    var p = Object.assign({}, cur.p, patch), parts = [];
    if (patch && patch.trade) p.sector = TR[patch.trade].s;
    if (patch && patch.sector != null && !patch.trade && p.trade && TR[p.trade].s !== patch.sector) delete p.trade;
    if (patch && patch.district) p.state = DSTATE[patch.district];
    if (patch && patch.state != null && !patch.district && p.district && DSTATE[p.district] !== patch.state) delete p.district;
    Object.keys(p).forEach(function (k) { if (p[k] !== "" && p[k] != null) parts.push(encodeURIComponent(k) + "=" + encodeURIComponent(p[k])); });
    return "#/" + page + (parts.length ? "?" + parts.join("&") : "");
  }
  function go(patch, page) { location.hash = url(page || cur.page, patch); }
  var scopeText = function (p) { return [p.district ? DNAME[p.district] : p.state || t("All states"), p.trade ? TR[p.trade].n : p.sector ? t(p.sector) : t("all sectors")].join(", "); };

  /* ---------- the state shards ---------- */
  var shards = {};
  function shard(state) {
    if (!shards[state]) shards[state] = fetch("data/shards/" + slug(state) + ".json").then(function (r) { if (!r.ok) throw new Error("shard " + r.status); return r.json(); });
    return shards[state];
  }
  function rowsOf(sh, p) {
    var out = [];
    sh.ids.forEach(function (_, i) { var tr = TRADES[sh.t[i]]; if (p.district && String(sh.d[i]) !== String(p.district)) return; if (p.trade && tr.c !== p.trade) return; if (p.sector && tr.s !== p.sector) return; out.push(i); });
    return out;
  }
  function sumRows(sh, idx, block, k) { var n = sh[block][k][0].length, o = new Array(n).fill(0); idx.forEach(function (i) { var a = sh[block][k][i]; for (var m = 0; m < n; m++) o[m] += a[m]; }); return o; }
  function diRows(sh, idx) {
    var n = sh.DI[0].length, num = new Array(n).fill(0), den = new Array(n).fill(0), hs = sh.hist.E[0].length;
    idx.forEach(function (i) { var e = sh.hist.E[i].concat(sh.fc.E[i]), d = sh.DI[i]; for (var m = 0; m < n; m++) { num[m] += e[m] * d[m]; den[m] += e[m]; } });
    return num.map(function (v, m) { return den[m] ? Math.round(v / den[m] * 10) / 10 : 0; });
  }

  /* ---------- a scope: the numbers of the current filters ---------- */
  function fromGroup(G, level, sec) {
    return { nh: HC, start: M.hist_core[0], hist: { E: G.E.slice(0, HC), V: G.V.slice(0, HC), S: G.S.slice(0, HC) }, fc: { E: G.E.slice(HC), V: G.V.slice(HC), S: G.S.slice(HC) }, DI: G.DI, level: level, sec: sec };
  }
  function scopeOf(p) {
    var g = D.groups;
    if (!p.state && !p.district) return Promise.resolve(p.trade ? fromGroup(g.trade[p.trade], "trade", p.sector) : p.sector ? fromGroup(g.sector[p.sector], "sector", p.sector) : fromGroup(g.india[""], "india", null));
    if (p.state && !p.district && !p.trade) return Promise.resolve(p.sector ? fromGroup(g.state_sector[p.state + "|" + p.sector], "state_sector", p.sector) : fromGroup(g.state[p.state], "state", null));
    return shard(p.state).then(function (sh) {
      var idx = rowsOf(sh, p), level = null;
      if (p.district && p.trade) level = "series"; else if (p.district && p.sector) level = "district_sector";
      return { nh: HS, start: M.hist_shard[0], hist: { E: sumRows(sh, idx, "hist", "E"), V: sumRows(sh, idx, "hist", "V"), S: sumRows(sh, idx, "hist", "S") }, fc: { E: sumRows(sh, idx, "fc", "E"), V: sumRows(sh, idx, "fc", "V"), S: sumRows(sh, idx, "fc", "S") },
        DI: diRows(sh, idx), level: level, sec: p.sector, sh: sh, idx: idx };
    });
  }
  /* 90% ranges: the point forecast times exp(offset) from the calibration tables of core.js; the range always contains the point. null where no calibration exists for the combination. */
  function ranges(S, k) {
    if (!S.level) return null;
    var cal = S.level === "series" ? D.cal_series[k][k === "S" ? "all" : S.sec] : D.cal_levels[S.level][k], pt = S.fc[k];
    var f = function (nm, lo) { return pt.map(function (v, i) { var o = cal[nm][i]; o = lo ? Math.min(o, 0) : Math.max(o, 0); return Math.round(v * Math.exp(o)); }); };
    return { lo: f("lo", 1), hi: f("hi", 0), lo_w: f("lo_wide", 1), hi_w: f("hi_wide", 0) };
  }
  function breakdown(p) {
    var trs = TRADES.filter(function (x) { return (!p.sector || x.s === p.sector) && (!p.trade || x.c === p.trade); });
    if (!p.state && !p.district) return Promise.resolve(trs.map(function (x) { var G = D.groups.trade[x.c]; return { tr: x, E0: G.E[HC - 1], E5: G.E[HC + 59], V0: G.V[HC - 1], V5: G.V[HC + 59], S0: G.S[HC - 1], S5: G.S[HC + 59], DI5: G.DI[HC + 59], DI0: G.DI[HC - 1] }; }));
    return shard(p.state).then(function (sh) {
      return trs.map(function (x) {
        var idx = rowsOf(sh, Object.assign({}, p, { trade: x.c, sector: x.s })), E = sumRows(sh, idx, "hist", "E").concat(sumRows(sh, idx, "fc", "E")), V = sumRows(sh, idx, "hist", "V").concat(sumRows(sh, idx, "fc", "V")), S = sumRows(sh, idx, "hist", "S").concat(sumRows(sh, idx, "fc", "S")), d = diRows(sh, idx);
        return { tr: x, E0: E[HS - 1], E5: last(E), V0: V[HS - 1], V5: last(V), S0: S[HS - 1], S5: last(S), DI5: last(d), DI0: d[HS - 1], idx: idx };
      });
    });
  }

  /* ---------- line chart with two nested 90% ranges ---------- */
  function ticks(lo, hi, n) {
    if (hi - lo < 1e-9) hi = lo + 1;
    var span = hi - lo, step = Math.pow(10, Math.floor(Math.log10(span / n))), err = span / n / step;
    step *= err >= 7 ? 10 : err >= 3 ? 5 : err >= 1.5 ? 2 : 1;
    var a = Math.floor(lo / step) * step, b = Math.ceil(hi / step) * step, out = [];
    for (var v = a; v <= b + step / 2; v += step) out.push(+v.toFixed(10));
    return out;
  }
  function legend(items) { return '<div class="legend">' + items.map(function (l) { return '<span style="--c:' + l.color + '"><i class="' + (l.cls || "") + '"></i>' + esc(l.name) + "</span>"; }).join("") + "</div>"; }
  function lineChart(host, o) {
    host.innerHTML = "";
    var W = 780, HT = o.height || 290, m = { l: 64, r: 16, t: 16, b: 32 }, nT = o.T.length, nh = o.nh, lo = Infinity, hi = -Infinity;
    o.lines.forEach(function (l) {
      var all = l.hist.concat(l.fc || []).concat(l.band ? l.band.lo_w.concat(l.band.hi_w) : []);
      all.forEach(function (v) { if (v != null && isFinite(v)) { if (v < lo) lo = v; if (v > hi) hi = v; } });
    });
    (o.hlines || []).forEach(function (hl) { lo = Math.min(lo, hl.v); hi = Math.max(hi, hl.v); });
    var pad = (hi - lo) * 0.08 || Math.abs(hi) * 0.1 || 1, tk = ticks(o.zero ? Math.min(0, lo) : lo - pad, hi + pad, 5), s0 = tk[0], s1 = last(tk);
    var x = function (i) { return m.l + (i / (nT - 1)) * (W - m.l - m.r); }, y = function (v) { return m.t + (1 - (v - s0) / (s1 - s0)) * (HT - m.t - m.b); };
    var svg = el("svg", { viewBox: "0 0 " + W + " " + HT, role: "img", "aria-label": o.label || "chart" }, host);
    (o.regions || []).forEach(function (r) {
      var i0 = o.T.indexOf(r.from), i1 = o.T.indexOf(r.to); if (i0 < 0) i0 = 0; if (i1 < 0 || i1 < i0) return;
      el("rect", { x: x(i0), y: m.t, width: Math.max(2, x(i1) - x(i0)), height: HT - m.t - m.b, fill: css("--ink-2"), "fill-opacity": ".09" }, svg);
      el("text", { x: x(i0) + 4, y: m.t + 11, class: "axis-l" }, svg).textContent = r.label;
    });
    tk.forEach(function (v) { el("line", { x1: m.l, x2: W - m.r, y1: y(v), y2: y(v), stroke: css("--line"), "stroke-dasharray": v === 0 ? "none" : "3 5" }, svg); el("text", { x: m.l - 8, y: y(v) + 4, "text-anchor": "end" }, svg).textContent = (o.fmtAxis || compact)(v); });
    var lastYear = "";
    o.T.forEach(function (ym, i) { var yr = ym.slice(0, 4); if (ym.slice(5) === "01" && yr !== lastYear && (nT < 100 || +yr % 2 === 0 || i === 0)) { lastYear = yr; el("text", { x: x(i), y: HT - 10, "text-anchor": "middle" }, svg).textContent = yr; } });
    (o.hlines || []).forEach(function (hl) {
      el("line", { x1: m.l, x2: W - m.r, y1: y(hl.v), y2: y(hl.v), stroke: hl.color || css("--ink-2"), "stroke-dasharray": "5 4", "stroke-opacity": ".7" }, svg);
      if (hl.label) el("text", { x: m.l + 6, y: y(hl.v) - 4, class: "axis-l" }, svg).textContent = hl.label;
    });
    el("line", { x1: x(nh - 1), x2: x(nh - 1), y1: m.t, y2: HT - m.b, stroke: css("--ink-2"), "stroke-dasharray": "2 4" }, svg);
    el("text", { x: x(nh - 1) + 6, y: HT - m.b - 6, class: "axis-l" }, svg).textContent = t("forecast") + " →";
    o.lines.forEach(function (l) {
      var path = function (arr, from) { var d = "", st = false; arr.forEach(function (v, j) { if (v == null) return; d += (st ? "L" : "M") + x(from + j).toFixed(1) + " " + y(v).toFixed(1); st = true; }); return d; };
      if (l.band) {
        [["lo_w", "hi_w", ".11"], ["lo", "hi", ".22"]].forEach(function (b) {
          var up = l.band[b[1]].map(function (v, j) { return x(nh + j).toFixed(1) + "," + y(v).toFixed(1); }), dn = l.band[b[0]].map(function (v, j) { return x(nh + j).toFixed(1) + "," + y(v).toFixed(1); }).reverse();
          el("polygon", { points: x(nh - 1).toFixed(1) + "," + y(last(l.hist)).toFixed(1) + " " + up.join(" ") + " " + dn.join(" "), fill: l.color, "fill-opacity": b[2] }, svg);
        });
      }
      el("path", { d: path(l.hist, 0), fill: "none", stroke: l.color, "stroke-width": 2.4, "stroke-linejoin": "round", "stroke-linecap": "round" }, svg);
      if (l.fc) el("path", { d: path([last(l.hist)].concat(l.fc), nh - 1), fill: "none", stroke: l.color, "stroke-width": 2.4, "stroke-dasharray": "6 5", "stroke-linecap": "round" }, svg);
    });
    var hg = el("g", { style: "display:none", "pointer-events": "none" }, svg), hl = el("line", { y1: m.t, y2: HT - m.b, stroke: css("--ink"), "stroke-opacity": ".6" }, hg);
    var dots = o.lines.map(function (l) { return el("circle", { r: 4.5, fill: l.color, stroke: css("--surface"), "stroke-width": 2 }, hg); });
    var cap = el("rect", { x: m.l, y: m.t, width: W - m.l - m.r, height: HT - m.t - m.b, fill: "transparent", style: "cursor:crosshair" }, svg);
    function at(e) {
      var r = svg.getBoundingClientRect(), px = (e.clientX - r.left) / r.width * W, i = Math.max(0, Math.min(nT - 1, Math.round((px - m.l) / (W - m.l - m.r) * (nT - 1))));
      hg.style.display = ""; hl.setAttribute("x1", x(i)); hl.setAttribute("x2", x(i));
      var isF = i >= nh, html = "<b>" + ml(o.T[i]) + (isF ? " (" + t("forecast") + ")" : "") + "</b>";
      o.lines.forEach(function (l, j) {
        var v = isF ? (l.fc ? l.fc[i - nh] : null) : l.hist[i];
        if (v == null) { dots[j].style.display = "none"; return; }
        dots[j].style.display = ""; dots[j].setAttribute("cx", x(i)); dots[j].setAttribute("cy", y(v));
        var f = o.fmtTip || fmt;
        html += "<br>" + esc(l.name) + ": " + f(v);
        if (isF && l.band) html += "<br><small>" + t("Usual range") + " " + f(l.band.lo[i - nh]) + " – " + f(l.band.hi[i - nh]) + "<br>" + t("Wide range") + " " + f(l.band.lo_w[i - nh]) + " – " + f(l.band.hi_w[i - nh]) + "</small>";
      });
      document.body.classList.add("tip-chart"); showTip(html, e.clientX, e.clientY);
    }
    cap.addEventListener("pointermove", at); cap.addEventListener("pointerdown", at);
    cap.addEventListener("pointerleave", function () { hg.style.display = "none"; document.body.classList.remove("tip-chart"); hideTip(); });
  }
  function chartCard(title, sub, right, id) { return '<section class="card"><div class="card-h"><div><h2>' + title + "</h2>" + (sub ? "<p>" + sub + "</p>" : "") + "</div>" + (right || "") + '</div><div id="' + id + '-lg"></div><div class="chart" id="' + id + '"></div><p class="sr-only" id="' + id + '-sr"></p></section>'; }
  function draw(id, o, summary) {
    lineChart(document.getElementById(id), o);
    var band = o.lines.some(function (l) { return l.band; });
    document.getElementById(id + "-lg").innerHTML = legend(o.lines.map(function (l) { return { name: l.name, color: l.color }; }).concat(band ? [{ name: t("Usual 90% range"), color: o.lines[0].color, cls: "box" }, { name: t("Wide 90% range"), color: o.lines[0].color, cls: "box faint" }] : []));
    if (summary) document.getElementById(id + "-sr").textContent = summary;
  }
  var window_ = function (S) { return { T: monthsOf(S.start, S.nh + 60), nh: S.nh }; };
  var shock = function () { return [{ from: "2020-03", to: "2023-12", label: t("2020-23 shock and recovery") }]; };
  var rangeNote = function (S) { return S.level ? "" : '<p class="note">' + t("No calibrated 90% range exists for this combination of filters, so only the point forecast is drawn. Choose a sector, state, state with sector, or a district with a sector or trade for a range.") + "</p>"; };

  /* ---------- CSV and JSON ---------- */
  function toast(s) { var n = document.createElement("div"); n.className = "toast"; n.textContent = s; document.body.appendChild(n); setTimeout(function () { n.remove(); }, 2600); }
  function save(blob, name) { var a = document.createElement("a"); a.href = URL.createObjectURL(blob); a.download = name; document.body.appendChild(a); a.click(); setTimeout(function () { URL.revokeObjectURL(a.href); a.remove(); }, 500); }
  function downloadCsv(name, head, rows) {
    var q = function (v) { v = v == null ? "" : String(v); return /[",\n]/.test(v) ? '"' + v.replace(/"/g, '""') + '"' : v; };
    save(new Blob(["﻿" + [head].concat(rows).map(function (r) { return r.map(q).join(","); }).join("\r\n") + "\r\n"], { type: "text/csv;charset=utf-8" }), name + ".csv"); toast(tf("Downloaded {0}.csv ({1} rows)", name, fmt(rows.length)));
  }
  function downloadJson(name, head, rows) {
    var o = rows.map(function (r) { var x = {}; head.forEach(function (h, i) { x[h] = r[i]; }); return x; });
    save(new Blob([JSON.stringify({ source: "KaushalSetu dashboard, simulated data", forecast_origin: M.origin, rows: o }, null, 1)], { type: "application/json" }), name + ".json"); toast(tf("Downloaded {0}.json ({1} rows)", name, fmt(rows.length)));
  }
  var fname = function (page) { return "kaushalsetu_" + page + "_" + slug(cur.p.trade || cur.p.sector || "all-sectors") + "_" + slug(cur.p.district ? DNAME[cur.p.district] : cur.p.state || "all-states"); };

  /* ---------- small parts ---------- */
  var kpi = function (lbl, color, val, sub) { return '<div class="card kpi" style="--c:' + color + '"><div class="lbl"><i></i>' + lbl + '</div><span class="val">' + val + '</span><div class="sub">' + sub + "</div></div>"; };
  var confChip = function (c) { return '<span class="conf ' + ({ H: "high", M: "medium", L: "low" }[c] || "") + '">' + t(CONF[c] || c) + "</span>"; };
  var heat = function (v) { return 'style="background:color-mix(in srgb, var(--demand) ' + Math.round(Math.max(0, Math.min(100, v)) * 0.55) + '%, transparent)"'; };
  var scopeHead = function (p, right) { return '<div class="card-h"><div><h2 style="font-size:1.05rem">' + esc(scopeText(p)) + "</h2></div>" + (right || "") + "</div>"; };
  function segment(key, opts, value, label) { return '<div class="seg-row" role="group" aria-label="' + esc(t(label)) + '">' + opts.map(function (o) { return '<button type="button" data-k="' + key + '" data-v="' + o[0] + '" aria-pressed="' + (String(o[0]) === String(value)) + '">' + esc(o[1]) + "</button>"; }).join("") + "</div>"; }
  function bindSeg(view) { $$("[data-k]", view).forEach(function (b) { b.addEventListener("click", function () { var o = {}; o[b.dataset.k] = b.dataset.v; go(o); }); }); }
  function bindRows(view) { $$("tr.click", view).forEach(function (tr) { tr.addEventListener("click", function () { var o = {}; if (tr.dataset.trade) o.trade = tr.dataset.trade; if (tr.dataset.state) o.state = tr.dataset.state; if (tr.dataset.sector) o.sector = tr.dataset.sector; if (tr.dataset.district) o.district = tr.dataset.district; go(o); }); }); }
  var table = function (head, rows, cls) { return '<div class="tbl-wrap"><table class="tbl ' + (cls || "") + '"><thead><tr>' + head.map(function (h) { return '<th class="' + (h[1] || "") + '">' + esc(t(h[0])) + "</th>"; }).join("") + "</tr></thead><tbody>" + rows.join("") + "</tbody></table></div>"; };
  var render = {};
  var loadingErr = function (view, e) { view.innerHTML = '<div class="banner">' + esc(t("This page could not be drawn")) + ": " + esc(e.message) + "</div>"; if (window.console) console.error(e); };

  /* ---------- pages ---------- */
  render.overview = function (p, view) {
    return Promise.all([scopeOf(p), breakdown(p)]).then(function (r) {
      var S = r[0], rows = r[1], C = COLORS(), E0 = last(S.hist.E), V0 = last(S.hist.V), S0 = last(S.hist.S), E5 = last(S.fc.E), V5 = last(S.fc.V), S5 = last(S.fc.S), d0 = S.DI[S.nh - 1], d5 = last(S.DI);
      var w = window_(S), rE = ranges(S, "E"), rV = ranges(S, "V");
      var al = alertsFor(p, 0), nS = al.filter(function (a) { return a[0] === 0; }).length, nO = al.length - nS;
      var states = p.trade ? null : STATES.map(function (s) { var G = p.sector ? D.groups.state_sector[s + "|" + p.sector] : D.groups.state[s]; return { s: s, E0: G.E[HC - 1], E5: G.E[HC + 59], V5: G.V[HC + 59], V0: G.V[HC - 1], d5: G.DI[HC + 59] }; });
      view.innerHTML = scopeHead(p) + '<div class="grid g4">' +
        kpi(t(NAMES.E), C.E, compact(E0), dir(growth(E0, E5)) + " <span>" + tf("by Dec {0}: {1}", YEARS[4], compact(E5)) + "</span>") + kpi(t(NAMES.V), C.V, compact(V0), dir(growth(V0, V5)) + " <span>" + tf("by Dec {0}: {1}", YEARS[4], compact(V5)) + "</span>") +
        kpi(t(NAMES.S), C.S, compact(S0), dir(growth(S0, S5)) + " <span>" + tf("by Dec {0}: {1}", YEARS[4], compact(S5)) + "</span>") +
        kpi(t("Demand Index"), "var(--demand)", fmt(d0, 0), '<span class="pill ' + (d5 >= d0 ? "s1" : "c2") + '">' + fmt(d5, 0) + "</span> <span>" + tf("in Dec {0}", YEARS[4]) + "</span>") + "</div>" +
        '<div class="grid g2 mt">' + chartCard(t(NAMES.E), tf("Latest {0}, December {1}", compact(E0), M.hist_core[1].slice(0, 4)), "", "c-e") + chartCard(t(NAMES.V), tf("Latest {0}, December {1}", compact(V0), M.hist_core[1].slice(0, 4)), "", "c-v") + "</div>" + rangeNote(S) +
        '<div class="grid g2 mt">' + (states ? '<section class="card"><div class="card-h"><div><h2>' + t("States") + "</h2><p>" + t("Click a row to filter by state") + "</p></div></div>" + table([["State"], ["Employed now", "num"], ["Employed 2030", "num"], ["Change", "num"], ["Demand Index 2030", "num"]],
          states.map(function (x) { return '<tr class="click' + (p.state === x.s ? " on" : "") + '" data-state="' + esc(x.s) + '"><td>' + esc(x.s) + '</td><td class="num">' + compact(x.E0) + '</td><td class="num">' + compact(x.E5) + '</td><td class="num">' + dir(growth(x.E0, x.E5)) + '</td><td class="num" ' + heat(x.d5) + ">" + fmt(x.d5, 0) + "</td></tr>"; })) + "</section>" : "") +
        '<section class="card"><div class="card-h"><div><h2>' + t("Early-warning summary") + "</h2><p>" + tf("Alerts 12 months ahead for {0}", esc(scopeText(p))) + '</p></div><a class="chip-btn" href="' + url("warnings", {}) + '">' + t("Open") + '</a></div><div class="ew-tiles">' +
        '<a class="ew-tile a" href="' + url("warnings", { t: "0" }) + '"><span>' + t("Shortage alerts") + "</span><b>" + nS + "</b><span>" + t("series at 12 months") + '</span></a><a class="ew-tile a" href="' + url("warnings", { t: "1" }) + '"><span>' + t("Oversupply alerts") + "</span><b>" + nO + "</b><span>" + t("series at 12 months") + "</span></a></div>" +
        '<p class="note">' + t("Alerts are relative: the series is among the 10% of districts in its trade with the highest (shortage) or lowest (oversupply) forecast vacancies per seeker in that month.") + "</p></section></div>" +
        '<section class="card mt"><div class="card-h"><div><h2>' + t("Trades") + "</h2><p>" + t("Latest December against December 2030") + "</p></div></div>" + tradeTable(rows, p) + "</section>";
      draw("c-e", { T: w.T, nh: w.nh, label: t(NAMES.E), lines: [{ name: t(NAMES.E), color: C.E, hist: S.hist.E, fc: S.fc.E, band: rE }], regions: shock() }, summarise(NAMES.E, S, rE, "E"));
      draw("c-v", { T: w.T, nh: w.nh, label: t(NAMES.V), lines: [{ name: t(NAMES.V), color: C.V, hist: S.hist.V, fc: S.fc.V, band: rV }], regions: shock() }, summarise(NAMES.V, S, rV, "V"));
      bindRows(view);
      var head = ["trade_code", "trade", "sector", "employed_dec_2025", "employed_dec_2030", "vacancies_dec_2025", "vacancies_dec_2030", "seekers_dec_2025", "seekers_dec_2030", "demand_index_dec_2030"];
      cur.csv = { name: fname("overview"), head: head, rows: rows.map(function (x) { return [x.tr.c, x.tr.n, x.tr.s, x.E0, x.E5, x.V0, x.V5, x.S0, x.S5, x.DI5]; }) };
    });
  };
  function summarise(name, S, rg, k) {
    var s = t(name) + ": " + compact(last(S.hist[k])) + " " + t("in") + " " + ml(mAdd(S.start, S.nh - 1)) + ", " + compact(last(S.fc[k])) + " " + t("forecast for") + " " + ml(mAdd(S.start, S.nh + 59));
    return s + (rg ? " (" + t("usual range") + " " + compact(last(rg.lo)) + " – " + compact(last(rg.hi)) + ", " + t("wide range") + " " + compact(last(rg.lo_w)) + " – " + compact(last(rg.hi_w)) + ")" : "");
  }
  function tradeTable(rows, p) {
    return table([["Trade"], ["Employed now", "num"], ["Employed 2030", "num"], ["Change", "num"], ["Vacancies change", "num"], ["Seekers change", "num"], ["Demand Index 2030", "num"]], rows.map(function (x) {
      return '<tr class="click' + (p.trade === x.tr.c ? " on" : "") + '" data-trade="' + x.tr.c + '"><td>' + esc(x.tr.n) + " <small>" + x.tr.c + '</small></td><td class="num">' + compact(x.E0) + '</td><td class="num">' + compact(x.E5) + '</td><td class="num">' + dir(growth(x.E0, x.E5)) + '</td><td class="num">' + dir(growth(x.V0, x.V5)) + '</td><td class="num">' + dir(growth(x.S0, x.S5)) + '</td><td class="num" ' + heat(x.DI5) + ">" + fmt(x.DI5, 0) + "</td></tr>";
    }));
  }
  function alertsFor(p, hz) {
    return A.rows.filter(function (a) { var tr = TRADES[a[4]]; return a[1] === hz && (!p.state || STATES[a[2]] === p.state) && (!p.district || String(a[3]) === String(p.district)) && (!p.trade || tr.c === p.trade) && (!p.sector || tr.s === p.sector); });
  }

  render.forecast = function (p, view) {
    var k = ["E", "V", "S"].indexOf(p.k) >= 0 ? p.k : "E";
    return Promise.all([scopeOf(p), breakdown(p)]).then(function (r) {
      var S = r[0], rows = r[1], C = COLORS(), w = window_(S), rg = ranges(S, k), ye = decs(S.fc[k]), single = S.sh && p.district && p.trade ? S.idx[0] : -1;
      var yr = YEARS.map(function (y, i) { return '<tr><td>' + t("December") + " " + y + '</td><td class="num">' + fmt(ye[i]) + "</td>" + (rg ? '<td class="num">' + fmt(decs(rg.lo)[i]) + " – " + fmt(decs(rg.hi)[i]) + '</td><td class="num">' + fmt(decs(rg.lo_w)[i]) + " – " + fmt(decs(rg.hi_w)[i]) + "</td>" : "") + "</tr>"; });
      view.innerHTML = scopeHead(p, segment("k", [["E", t("Employed")], ["V", t("Vacancies")], ["S", t("Seekers")]], k, "Measure")) +
        chartCard(t(NAMES[k]), tf("History to {0} and forecast to {1}", ml(M.hist_core[1]), ml(M.fc[1])), "", "c-main") + rangeNote(S) +
        (single >= 0 ? '<p class="note">' + t("Confidence of this forecast by horizon (12-month bands):") + " " + M.bands.map(function (b, i) { return b + ": " + confChip(S.sh.conf[k][single][i]); }).join(" ") + "</p>" : "") +
        '<section class="card mt"><div class="card-h"><div><h2>' + t("December values") + "</h2><p>" + t("Point forecast and the two 90% ranges") + "</p></div></div>" + table([["Month"], ["Forecast", "num"]].concat(rg ? [["Usual range", "num"], ["Wide range", "num"]] : []), yr) + "</section>" +
        '<section class="card mt"><div class="card-h"><div><h2>' + t("Trades") + "</h2><p>" + t("Click a trade to filter") + "</p></div></div>" + tradeTable(rows, p) + "</section>" +
        '<p class="note">' + t("The usual range was calibrated on 2010-2019, years without an unforeseen shock; the wide range also uses 2020-2025 and is the one to read for totals of many series, whose errors move together.") + "</p>";
      draw("c-main", { T: w.T, nh: w.nh, label: t(NAMES[k]), lines: [{ name: t(NAMES[k]), color: C[k], hist: S.hist[k], fc: S.fc[k], band: rg }], regions: shock() }, summarise(NAMES[k], S, rg, k));
      bindSeg(view); bindRows(view);
      var T = w.T, head = ["month", "type", "value"].concat(rg ? ["usual_lo", "usual_hi", "wide_lo", "wide_hi"] : []);
      cur.csv = { name: fname("forecast_" + k), head: head, rows: T.map(function (m, i) { var f = i >= S.nh, j = i - S.nh; return [m, f ? "forecast" : "history", f ? S.fc[k][j] : S.hist[k][i]].concat(rg ? (f ? [rg.lo[j], rg.hi[j], rg.lo_w[j], rg.hi_w[j]] : ["", "", "", ""]) : []); }) };
    });
  };

  render.index = function (p, view) {
    var sec = p.sector || SECTORS[0];
    return Promise.all([scopeOf(p), breakdown(p)]).then(function (r) {
      var S = r[0], rows = r[1], w = window_(S), n = S.nh;
      var stateCols = p.sector ? TRADES.filter(function (x) { return x.s === p.sector; }).map(function (x) { return { k: x.c, n: x.n }; }) : SECTORS.map(function (s) { return { k: s, n: t(s) }; });
      var heatRows = STATES.map(function (s) {
        return '<tr class="click" data-state="' + esc(s) + '"><td>' + esc(s) + "</td>" + stateCols.map(function (c) { var v = p.sector ? D.di_state_trade[s + "|" + c.k][4] : D.groups.state_sector[s + "|" + c.k].DI[HC + 59]; return "<td class=\"num\" " + heat(v) + ">" + fmt(v, 0) + "</td>"; }).join("") + "</tr>";
      });
      var ds = DLIST.filter(function (d) { return !p.state || d.s === p.state; }).map(function (d) { return { d: d, v: D.di_district_sector[d.c + "|" + sec][4], v0: D.di_district_sector[d.c + "|" + sec][0] }; }).sort(function (a, b) { return b.v - a.v; });
      var top = ds.slice(0, 15), bottom = ds.slice(-5).reverse();
      var di2 = function (x, i) { return '<tr class="click" data-district="' + x.d.c + '" data-sector="' + esc(sec) + '"><td class="num">' + (i + 1) + "</td><td>" + esc(x.d.n) + "</td><td>" + esc(x.d.s) + '</td><td class="num" ' + heat(x.v) + ">" + fmt(x.v, 0) + '</td><td class="num">' + fmt(x.v0, 0) + "</td></tr>"; };
      view.innerHTML = scopeHead(p) + '<div class="grid g2">' + chartCard(t("Demand Index"), t("0 to 100; 50 is a typical district in the trade at the 2018-2019 level"), "", "c-di") +
        '<section class="card"><div class="card-h"><div><h2>' + t("What the index means") + '</h2></div></div><ul class="plain"><li>' + t("It compares a district with the other districts of the same trade in the same month, using openings per worker from vacancies, job-portal postings and the National Career Service.") + "</li><li>" + t("A national level term lets the index move up and down over the years: 50 is the median district at the 2018-2019 demand level, 84 is one standard deviation above, 16 one below.") + "</li><li>" + t("Forecast months use the forecast vacancies only. In the past years this version tracks the three-channel index closely (correlation 0.89 to 0.94 in 2012-2025).") + "</li></ul></section></div>" +
        '<section class="card mt"><div class="card-h"><div><h2>' + (p.sector ? t("States by trade") : t("States by sector")) + "</h2><p>" + t("Demand Index in 2030 (annual mean for trades, December for sectors); click a state to filter") + "</p></div></div>" + table([["State"]].concat(stateCols.map(function (c) { return [c.n, "num"]; })), heatRows) + "</section>" +
        '<div class="grid g2 mt"><section class="card"><div class="card-h"><div><h2>' + tf("Districts with the highest index: {0}", esc(t(sec))) + "</h2><p>" + t("Annual mean 2030, with 2026 for comparison. Choose a sector or state in the filters.") + "</p></div></div>" + table([["#", "num"], ["District"], ["State"], ["2030", "num"], ["2026", "num"]], top.map(di2)) + "</section>" +
        '<section class="card"><div class="card-h"><div><h2>' + tf("Districts with the lowest index: {0}", esc(t(sec))) + "</h2></div></div>" + table([["#", "num"], ["District"], ["State"], ["2030", "num"], ["2026", "num"]], bottom.map(function (x, i) { return di2(x, ds.length - 1 - i); })) + "</section></div>" +
        '<section class="card mt"><div class="card-h"><div><h2>' + t("Trades") + "</h2></div></div>" + tradeTable(rows, p) + "</section>";
      draw("c-di", { T: w.T, nh: n, label: t("Demand Index"), fmtAxis: function (v) { return fmt(v, 0); }, fmtTip: function (v) { return fmt(v, 1); }, lines: [{ name: t("Demand Index"), color: css("--demand"), hist: S.DI.slice(0, n), fc: S.DI.slice(n) }], hlines: [{ v: 50, label: "50", color: css("--ink-2") }], regions: shock() }, t("Demand Index") + ": " + fmt(S.DI[n - 1], 1) + " " + t("in") + " " + ml(mAdd(S.start, n - 1)) + ", " + fmt(last(S.DI), 1) + " " + t("forecast for") + " " + ml(M.fc[1]));
      bindRows(view);
      cur.csv = { name: fname("demand_index"), head: ["month", "type", "demand_index"], rows: w.T.map(function (m, i) { return [m, i >= n ? "forecast" : "history", S.DI[i]]; }) };
    });
  };

  /* ---------- capacity gap ---------- */
  function capTable(p, sh) {
    var C = D.capacity, pick = function (rows, f) { return rows.filter(f); };
    if (sh) {
      var idx = rowsOf(sh, p), o = YEARS.map(function (y, i) { var v = 0; idx.forEach(function (j) { v += sh.cap.vac[j][i]; }); return v; }), seats = 0, cert = 0;
      idx.forEach(function (j) { seats += sh.cap.seats[j]; cert += sh.cap.cert[j]; });
      return YEARS.map(function (y, i) { return { year: y, avg_vacancies: o[i], seats: seats, expected_certified: cert, openings_per_seat: seats ? o[i] / seats : 0, supply_per_opening: o[i] ? cert / o[i] : 0 }; });
    }
    var t_ = p.state ? (p.trade ? pick(C.state_trade, function (r) { return r.State_Name === p.state && r.Trade_Code === p.trade; }) : p.sector ? pick(C.state_sector, function (r) { return r.State_Name === p.state && r.Sector_Name === p.sector; }) : pick(C.state, function (r) { return r.State_Name === p.state; }))
      : p.trade ? pick(C.trade, function (r) { return r.Trade_Code === p.trade; }) : p.sector ? pick(C.sector, function (r) { return r.Sector_Name === p.sector; }) : C.india;
    return t_.slice().sort(function (a, b) { return a.year - b.year; });
  }
  render.capacity = function (p, view) {
    var needShard = !!(p.district), hold = needShard ? shard(p.state) : Promise.resolve(null);
    return Promise.all([hold, breakdownCap(p)]).then(function (r) {
      var sh = r[0], rows = capTable(p, sh), brk = r[1], C = COLORS(), y0 = rows[0], y4 = rows[4];
      var status = y4.supply_per_opening < 1 ? "Fewer trainees certified than openings" : "More trainees certified than openings";
      var yrs = rows.map(function (x) { return '<tr><td>' + x.year + '</td><td class="num">' + fmt(x.avg_vacancies) + '</td><td class="num">' + fmt(x.seats) + '</td><td class="num">' + fmt(x.expected_certified) + '</td><td class="num">' + fmt(x.openings_per_seat, 2) + '</td><td class="num">' + fmt(x.supply_per_opening, 2) + "</td></tr>"; });
      view.innerHTML = scopeHead(p) + '<div class="grid g4">' + kpi(t("Openings per seat"), "var(--demand)", fmt(y4.openings_per_seat, 2), "<span>" + tf("in {0}; {1} in {2}", YEARS[4], fmt(y0.openings_per_seat, 2), YEARS[0]) + "</span>") +
        kpi(t("Certified per opening"), "var(--supply)", fmt(y4.supply_per_opening, 2), '<span class="pill ' + (y4.supply_per_opening < 1 ? "c2" : "s1") + '">' + t(status) + "</span>") + kpi(t("Training seats"), "var(--employed)", compact(y4.seats), "<span>" + t("held flat at the 2025-26 level (assumption)") + "</span>") +
        kpi(t("Expected certified a year"), "var(--employed)", compact(y4.expected_certified), "<span>" + t("seats times the 2023-25 certification rate") + "</span>") + "</div>" +
        '<section class="card mt"><div class="card-h"><div><h2>' + t("By year") + "</h2><p>" + t("Forecast openings (average monthly vacancies) against seats and expected certified trainees") + "</p></div></div>" + table([["Year"], ["Avg. openings", "num"], ["Seats", "num"], ["Expected certified", "num"], ["Openings per seat", "num"], ["Certified per opening", "num"]], yrs) + "</section>" +
        '<section class="card mt"><div class="card-h"><div><h2>' + (brk.title) + "</h2><p>" + t("Year 2030. Below 1 certified per opening, fewer people finish training in a year than there are openings.") + "</p></div></div>" + table(brk.head, brk.rows) + "</section>" +
        '<p class="note">' + t("Seats are held flat because no seat plans are forecast. Openings are a monthly stock and seats an annual flow, so read the ratios as a ranking of where capacity is stretched, not as a count of unfilled places.") + "</p>";
      bindRows(view);
      cur.csv = { name: fname("capacity"), head: ["year", "avg_openings", "seats", "expected_certified", "openings_per_seat", "certified_per_opening"], rows: rows.map(function (x) { return [x.year, x.avg_vacancies, x.seats, x.expected_certified, x.openings_per_seat, x.supply_per_opening]; }) };
      return scenarioCard(p, view);
    });
  };
    /* ---------- the seat scenario: multiply the seats from a year on and see the ratio, the severity and the seats a target needs ----------
     certified(seats) = seats x the certification rate (unchanged); openings unchanged; seats needed for a target ratio T in year y = openings(y) x T / rate */
  var bandOf = function (sc) { var a = Math.abs(sc), b = M.severity_bands; for (var i = 0; i < b.length; i++) if (a >= b[i][1]) return b[i][0]; return "balanced"; };
  function scenarioCard(p, view) {
    var level = p.district ? "series" : p.state ? "state_trade" : "trade", yrs = [2026, 2027, 2028, 2029, 2030];
    var pct = Math.max(-90, Math.min(500, parseFloat(p.sc) || 0)), fy = yrs.indexOf(+p.sf) >= 0 ? +p.sf : 2026, y = yrs.indexOf(+p.sy) >= 0 ? +p.sy : 2030, tg = Math.max(0.2, Math.min(5, parseFloat(p.sr) || 1)), nShow = p.sn === "all" ? 1e9 : p.sn === "100" ? 100 : 25;
    return severityRows(p, level).then(function (raw) {
      var rows = [], k = 1 + pct / 100;
      raw.forEach(function (r) {
        var v = r.vac[y - 2026]; if (!(v > 0) || !(r.seats > 0)) return;
        var seatsS = y >= fy ? r.seats * k : r.seats, rate = r.cert / r.seats, base = Math.max(r.cert / v, 1e-3), scn = Math.max(r.cert * seatsS / r.seats / v, 1e-3), need = v * tg / rate;
        rows.push({ r: r, v: v, seats: r.seats, seatsS: seatsS, base: base, scn: scn, sb: Math.log(base), ss: Math.log(scn), need: need, dneed: need - r.seats, pneed: (need / r.seats - 1) * 100, bb: bandOf(Math.log(base)), bs: bandOf(Math.log(scn)) });
      });
      rows.sort(function (a, b) { return a.ss - b.ss || (a.r.name < b.r.name ? -1 : 1); });
      var sum = function (f) { return rows.reduce(function (a, r) { return a + f(r); }, 0); }, V = sum(function (r) { return r.v; });
      var tot = { seats: sum(function (r) { return r.seats; }), seatsS: sum(function (r) { return r.seatsS; }), base: sum(function (r) { return r.base * r.v; }) / V, scn: sum(function (r) { return r.scn * r.v; }) / V,
        underB: rows.filter(function (r) { return r.sb < 0; }).length, underS: rows.filter(function (r) { return r.ss < 0; }).length, add: sum(function (r) { return Math.max(r.dneed, 0); }), release: sum(function (r) { return Math.max(-r.dneed, 0); }) };
      var lbl = { trade: "Trades", state_trade: "Trades of the chosen state", series: "District and trade series of the chosen state" }[level];
      var yopts = function (cur, id) { return '<select id="' + id + '">' + yrs.map(function (x) { return '<option value="' + x + '"' + (x === cur ? " selected" : "") + ">" + x + "</option>"; }).join("") + "</select>"; };
      var pill = function (b, sc) { return '<span class="pill ' + (b === "balanced" ? "s2" : sc < 0 ? "alert" : "s4") + '">' + t(b === "balanced" ? "Balanced" : cap1(b) + " " + (sc < 0 ? "undersupply" : "oversupply")) + "</span>"; };
      var shown = rows.slice(0, nShow), sg = function (x) { return (x >= 0 ? "+" : "−") + fmt(Math.abs(x), 0); };
      var attrs = function (a) { return Object.keys(a).map(function (q) { return " data-" + q + '="' + esc(a[q]) + '"'; }).join(""); };
      var html = '<section class="card mt" id="scenario"><div class="card-h"><div><h2>' + t("Seat scenario") + "</h2><p>" + t("Change the seats and see what it does to the balance with the openings. The certification rate and the forecast openings stay as they are.") + "</p></div></div>" +
        '<div class="scn-form"><label><span>' + t("Change seats by (%)") + '</span><input type="number" id="sc-pct" min="-90" max="500" step="5" value="' + pct + '"></label><label><span>' + t("From year") + "</span>" + yopts(fy, "sc-from") + "</label><label><span>" + t("Evaluate in") + "</span>" + yopts(y, "sc-year") + '</label><label><span>' + t("Target certified per opening") +
        '</span><input type="number" id="sc-target" min="0.2" max="5" step="0.1" value="' + tg + '"></label><button class="chip-btn primary" id="sc-apply" type="button">' + t("Apply") + '</button><button class="chip-btn" id="sc-reset" type="button">' + t("Reset") + "</button></div>" +
        '<div class="grid g4">' + kpi(t("Seats"), "var(--employed)", compact(tot.seats) + " → " + compact(tot.seatsS), "<span>" + (pct ? tf("{0}% from {1}", (pct > 0 ? "+" : "−") + Math.abs(pct), fy) : t("No change")) + "</span>") +
        kpi(t("Certified per opening"), "var(--supply)", fmt(tot.base, 2) + " → " + fmt(tot.scn, 2), "<span>" + tf("All rows in {0}; below 1 is undersupply", y) + "</span>") + kpi(t("Undersupplied rows"), "var(--low)", tot.underB + " → " + tot.underS, "<span>" + tf("Of {0} rows", fmt(rows.length)) + "</span>") +
        kpi(t("Seats to add for the target"), "var(--demand)", compact(tot.add), "<span>" + tf("Rows above the target could release {0}", compact(tot.release)) + "</span>") + "</div>" +
        (shown.length ? table([["#", "num"], ["Name"], ["Place"], ["Seats", "num"], ["Seats in scenario", "num"], ["Certified per opening now → scenario", "num"], ["Severity now → scenario"], ["Seats for the target", "num"]], shown.map(function (r, i) {
          return '<tr class="click"' + attrs(r.r.at) + '><td class="num">' + (i + 1) + "</td><td>" + esc(r.r.name) + "</td><td>" + esc(r.r.place) + '</td><td class="num">' + compact(r.seats) + '</td><td class="num">' + compact(r.seatsS) + '</td><td class="num">' + fmt(r.base, 2) + " → " + fmt(r.scn, 2) + "</td><td>" + pill(r.bb, r.sb) + " → " + pill(r.bs, r.ss) + '</td><td class="num">' + compact(r.need) + " (" + sg(r.pneed) + "%)</td></tr>";
        })) : '<p class="note">' + t("Nothing to show for these filters.") + "</p>") + (rows.length > shown.length ? '<p class="note">' + tf("Showing {0} of {1}.", shown.length, fmt(rows.length)) + "</p>" : "") +
        segment("sn", [["25", t("Top 25")], ["100", t("Top 100")], ["all", t("All")]], p.sn === "all" ? "all" : p.sn === "100" ? "100" : "25", "Rows") + ' <button class="chip-btn" id="sc-csv" type="button">' + t("Download this scenario (CSV)") + "</button>" +
        '<p class="note">' + tf("{0}, ranked by the scenario's score, most undersupplied first.", t(lbl)) + " " + t("Seats for the target are the seats at which certified per opening reaches the target (openings of the year × target ÷ certification rate); the percentage is the change from today's seats. No delay is modelled between sanctioning a seat and a trainee being certified, and teaching capacity is not limited: read this as a planning ratio, not a forecast of placements.") + "</p></section>";
      var box = document.createElement("div"); box.innerHTML = html; view.appendChild(box);
      var apply = function () { go({ sc: String(parseFloat($("#sc-pct", box).value) || 0), sf: $("#sc-from", box).value, sy: $("#sc-year", box).value, sr: String(parseFloat($("#sc-target", box).value) || 1) }); };
      $("#sc-apply", box).addEventListener("click", apply);
      $$("#sc-pct, #sc-target", box).forEach(function (i) { i.addEventListener("keydown", function (e) { if (e.key === "Enter") apply(); }); });
      $("#sc-reset", box).addEventListener("click", function () { go({ sc: "", sf: "", sy: "", sr: "" }); });
      $("#sc-csv", box).addEventListener("click", function () {
        downloadCsv(fname("seat_scenario_" + y), ["rank", "name", "place", "level", "year", "seat_change_pct", "from_year", "target", "seats", "seats_in_scenario", "average_monthly_openings", "certified_per_opening", "certified_per_opening_in_scenario", "severity", "severity_in_scenario", "seats_needed_for_target", "seat_change_needed_pct"],
          rows.map(function (r, i) { return [i + 1, r.r.name, r.r.place, level, y, pct, fy, tg, r.seats, +r.seatsS.toFixed(1), +r.v.toFixed(1), +r.base.toFixed(3), +r.scn.toFixed(3), r.bb, r.bs, +r.need.toFixed(1), +r.pneed.toFixed(1)]; }));
      });
      bindSeg(box); bindRows(box);
    });
  }
  function breakdownCap(p) {
    var C = D.capacity, y = function (r) { return r.year === 2030; }, row = function (name, attrs, r) { return '<tr class="click" ' + attrs + "><td>" + esc(name) + '</td><td class="num">' + compact(r.avg_vacancies) + '</td><td class="num">' + compact(r.seats) + '</td><td class="num">' + fmt(r.openings_per_seat, 2) + '</td><td class="num" ' + heat(Math.max(0, 100 - r.supply_per_opening * 50)) + ">" + fmt(r.supply_per_opening, 2) + "</td></tr>"; };
    var head = [["Name"], ["Avg. openings", "num"], ["Seats", "num"], ["Openings per seat", "num"], ["Certified per opening", "num"]];
    if (!p.state && !p.district) {
      if (p.trade) return Promise.resolve({ title: t("States"), head: head, rows: C.state_trade.filter(function (r) { return r.Trade_Code === p.trade && y(r); }).map(function (r) { return row(r.State_Name, 'data-state="' + esc(r.State_Name) + '"', r); }) });
      return Promise.resolve({ title: t("Trades"), head: head, rows: C.trade.filter(function (r) { return y(r) && (!p.sector || TR[r.Trade_Code].s === p.sector); }).map(function (r) { return row(TR[r.Trade_Code].n, 'data-trade="' + r.Trade_Code + '"', r); }) });
    }
    if (!p.district) {
      return Promise.resolve({ title: t("Trades"), head: head, rows: C.state_trade.filter(function (r) { return r.State_Name === p.state && y(r) && (!p.sector || TR[r.Trade_Code].s === p.sector) && (!p.trade || r.Trade_Code === p.trade); }).map(function (r) { return row(TR[r.Trade_Code].n, 'data-trade="' + r.Trade_Code + '"', r); }) });
    }
    return shard(p.state).then(function (sh) {
      var idx = rowsOf(sh, p), rows = idx.map(function (j) { var v = sh.cap.vac[j][4], s = sh.cap.seats[j], c = sh.cap.cert[j]; return { j: j, r: { avg_vacancies: v, seats: s, openings_per_seat: s ? v / s : 0, supply_per_opening: v ? c / v : 0 } }; });
      return { title: t("Trades"), head: head, rows: rows.map(function (x) { var tr = TRADES[sh.t[x.j]]; return row(tr.n, 'data-trade="' + tr.c + '"', x.r); }) };
    });
  }

  /* ---------- the severity ranking: trades and places in order of how far trained supply is from the openings ----------
     score = ln(expected certified per year / average monthly openings of the year): below 0 undersupply, above 0 oversupply; bands from core.js (severity_bands) */
  var SEV_LEVELS = [["trade", "Trades"], ["state", "States"], ["state_trade", "State and trade"], ["district", "Districts"], ["district_sector", "District and sector"], ["series", "District and trade"]];
  function severityRows(p, level) {
    var C = D.capacity, raw = [], keepT = function (code) { return (!p.trade || code === p.trade) && (!p.sector || TR[code].s === p.sector); };
    var vac = function (rows) { return [2026, 2027, 2028, 2029, 2030].map(function (y) { return rows[y].avg_vacancies; }); };
    var by = function (tab, keyf) { var o = {}; tab.forEach(function (r) { var k = keyf(r); (o[k] = o[k] || { rows: {}, r: r }).rows[r.year] = r; }); return o; };
    if (level === "trade" && !p.state && !p.district) {
      var g = by(C.trade, function (r) { return r.Trade_Code; });
      Object.keys(g).forEach(function (c) { if (keepT(c)) raw.push({ name: TR[c].n, place: TR[c].s, at: { trade: c }, seats: g[c].rows[2026].seats, cert: g[c].rows[2026].expected_certified, vac: vac(g[c].rows) }); });
    } else if (level === "state" && !p.district && !p.sector && !p.trade) {
      var gs = by(C.state, function (r) { return r.State_Name; });
      Object.keys(gs).forEach(function (st) { if (!p.state || p.state === st) raw.push({ name: st, place: "", at: { state: st }, seats: gs[st].rows[2026].seats, cert: gs[st].rows[2026].expected_certified, vac: vac(gs[st].rows) }); });
    } else if (level === "state_trade" && !p.district) {
      var gt = by(C.state_trade, function (r) { return r.State_Name + "|" + r.Trade_Code; });
      Object.keys(gt).forEach(function (k) { var st = k.split("|")[0], c = k.split("|")[1]; if ((!p.state || p.state === st) && keepT(c)) raw.push({ name: TR[c].n, place: st, at: { state: st, trade: c }, seats: gt[k].rows[2026].seats, cert: gt[k].rows[2026].expected_certified, vac: vac(gt[k].rows) }); });
    } else if ((level === "district" || level === "district_sector") && !p.trade) {
      var agg = {};
      Object.keys(D.severity_district_sector).forEach(function (k) {
        var d = k.split("|")[0], sec = k.split("|")[1], v = D.severity_district_sector[k];
        if ((p.state && DSTATE[d] !== p.state) || (p.district && d !== p.district) || (p.sector && sec !== p.sector)) return;
        if (level === "district") { var a = agg[d] = agg[d] || { seats: 0, cert: 0, vac: [0, 0, 0, 0, 0] }; a.seats += v[0]; a.cert += v[1]; a.vac = a.vac.map(function (x, i) { return x + v[2 + i]; }); }
        else agg[k] = { seats: v[0], cert: v[1], vac: v.slice(2), sec: sec, d: d };
      });
      Object.keys(agg).forEach(function (k) { var d = level === "district" ? k : agg[k].d; raw.push({ name: DNAME[d], place: level === "district" ? DSTATE[d] : DSTATE[d] + " · " + agg[k].sec, at: level === "district" ? { district: d } : { district: d, sector: agg[k].sec }, seats: agg[k].seats, cert: agg[k].cert, vac: agg[k].vac }); });
    } else if (level === "series" && p.state) {
      return shard(p.state).then(function (sh) {
        var out = [];
        sh.ids.forEach(function (_, i) { var c = TRADES[sh.t[i]].c, d = String(sh.d[i]); if ((p.district && d !== p.district) || !keepT(c)) return; out.push({ name: DNAME[d], place: TR[c].n, at: { district: d, trade: c }, seats: sh.cap.seats[i], cert: sh.cap.cert[i], vac: sh.cap.vac[i] }); });
        return out;
      });
    }
    return Promise.resolve(raw);
  }
  function scoreRows(raw, y) {
    var bands = M.severity_bands, out = [];
    raw.forEach(function (r) {
      var v = r.vac[y - 2026]; if (!(v > 0) || !(r.vac[0] > 0)) return;
      var ratio = Math.max(r.cert / v, 1e-3), sc = Math.log(ratio), a = Math.abs(sc), band = "balanced";
      for (var i = 0; i < bands.length; i++) if (a >= bands[i][1]) { band = bands[i][0]; break; }
      out.push(Object.assign({}, r, { v: v, ratio: ratio, score: sc, band: band, dir: band === "balanced" ? "balanced" : sc < 0 ? "under" : "over", s26: Math.log(Math.max(r.cert / r.vac[0], 1e-3)) }));
    });
    return out;
  }

  render.ranking = function (p, view) {
    var level = SEV_LEVELS.some(function (l) { return l[0] === p.sl; }) ? p.sl : "trade", order = ["under", "over", "severity"].indexOf(p.so) >= 0 ? p.so : "under", y = [2026, 2027, 2028, 2029, 2030].indexOf(+p.sy) >= 0 ? +p.sy : 2030, nShow = p.sn === "all" ? 1e9 : p.sn === "100" ? 100 : 25;
    var by = {}; D.rankings.forEach(function (r) { (by[r.ranking] = by[r.ranking] || []).push(r); });
    var keyName = function (k) { return k.split(" | ").map(function (q) { return TR[q] ? TR[q].n + " (" + q + ")" : q; }).join(", "); };
    return severityRows(p, level).then(function (raw) {
      var rows = scoreRows(raw, y), key = { under: function (r) { return r.score; }, over: function (r) { return -r.score; }, severity: function (r) { return -Math.abs(r.score); } }[order];
      rows.sort(function (a, b) { return key(a) - key(b) || (a.name < b.name ? -1 : 1); }); rows.forEach(function (r, i) { r.rank = i + 1; });
      var need = level === "series" && !p.state, shown = rows.slice(0, nShow);
      var pill = function (r) { return '<span class="pill ' + (r.dir === "under" ? "alert" : r.dir === "over" ? "s4" : "s2") + '">' + t(r.dir === "balanced" ? "Balanced" : cap1(r.band) + " " + (r.dir === "under" ? "undersupply" : "oversupply")) + "</span>"; };
      var bar = function (r) { return '<span class="sev" aria-hidden="true"><i class="' + (r.dir === "over" ? "over" : "") + '" style="width:' + Math.min(100, Math.abs(r.score) / 2 * 100).toFixed(0) + '%"></i></span>'; };
      var attrs = function (a) { return Object.keys(a).map(function (k) { return " data-" + k + '="' + esc(a[k]) + '"'; }).join(""); };
      view.innerHTML = scopeHead(p, "") + '<section class="card"><div class="card-h"><div><h2>' + t("Severity ranking") + "</h2><p>" + t("Where trained supply is furthest from the openings, for the filters above. Undersupply: fewer people finish training in a year than there are openings. Oversupply: more.") + "</p></div></div>" +
        '<div class="seg-wrap">' + segment("sl", SEV_LEVELS.map(function (l) { return [l[0], t(l[1])]; }), level, "Rank") + segment("so", [["under", t("Undersupplied first")], ["over", t("Oversupplied first")], ["severity", t("Largest gap first")]], order, "Order") +
        segment("sy", [2026, 2027, 2028, 2029, 2030].map(function (x) { return [x, String(x)]; }), y, "Year") + "</div>" +
        (need ? '<p class="note">' + t("Choose a state or a district in the filters to rank the district and trade series.") + "</p>" : (shown.length ? table([["#", "num"], ["Name"], ["Place"], ["Certified per opening", "num"], ["Score"], ["Severity"], ["Openings", "num"], ["Seats", "num"], ["Change since 2026", "num"]], shown.map(function (r) {
          return '<tr class="click"' + attrs(r.at) + '><td class="num">' + r.rank + "</td><td>" + esc(r.name) + "</td><td>" + esc(r.place) + '</td><td class="num">' + fmt(r.ratio, 2) + '</td><td class="num">' + (r.score > 0 ? "+" : "−") + Math.abs(r.score).toFixed(2) + " " + bar(r) + "</td><td>" + pill(r) + '</td><td class="num">' + compact(r.v) + '</td><td class="num">' + compact(r.seats) + '</td><td class="num">' + ((r.score - r.s26) >= 0 ? "+" : "−") + Math.abs(r.score - r.s26).toFixed(2) + "</td></tr>"; })) : '<p class="note">' + t("Nothing to rank for these filters. Clear the trade filter for district levels, and the district filter for trades.") + "</p>")) +
        (rows.length > shown.length ? '<p class="note">' + tf("Showing {0} of {1}.", shown.length, fmt(rows.length)) + "</p>" : "") +
        segment("sn", [["25", t("Top 25")], ["100", t("Top 100")], ["all", t("All")]], p.sn === "all" ? "all" : p.sn === "100" ? "100" : "25", "Rows") +
        '<p class="note"><b>' + t("Score") + ":</b> " + t("ln(expected certified per year ÷ average monthly openings of the year). Below 0 undersupply, above 0 oversupply. Severe: a ratio of 2 or more either way; high: 1.5; moderate: 1.25.") + " " + t("Seats are held flat at the 2025-26 level, and openings are a monthly stock against an annual flow, so read this as a ranking, not a count of unfilled places.") + "</p></section>" +
        '<h2 class="sub-h">' + t("Other rankings for all of India") + '</h2><div class="grid g2">' + Object.keys(by).map(function (title) {
          return '<section class="card"><div class="card-h"><div><h2 style="font-size:.98rem">' + esc(title) + "</h2></div></div>" +
            table([["#", "num"], ["Name"], ["Value", "num"]], by[title].map(function (r) { return '<tr><td class="num">' + r.rank + "</td><td>" + esc(keyName(r.key)) + (r.detail ? "<br><small>" + esc(r.detail) + "</small>" : "") + '</td><td class="num">' + fmt(r.value, 2) + "</td></tr>"; })) + "</section>";
        }).join("") + "</div>";
      bindSeg(view); bindRows(view);
      cur.csv = { name: fname("severity_" + level + "_" + y), head: ["rank", "name", "place", "level", "year", "seats", "average_monthly_openings", "expected_certified", "certified_per_opening", "score", "severity", "direction", "score_2026"],
        rows: rows.map(function (r) { return [r.rank, r.name, r.place, level, y, r.seats, +r.v.toFixed(1), +r.cert.toFixed(1), +r.ratio.toFixed(3), +r.score.toFixed(3), r.band, r.dir === "under" ? "undersupply" : r.dir === "over" ? "oversupply" : "balanced", +r.s26.toFixed(3)]; }) };
    });
  };
  var cap1 = function (w) { return w.charAt(0).toUpperCase() + w.slice(1); };

  /* ---------- alerts that begin or end: the series that enter or leave an alert tail between now (December 2025, actual) and 12, 36 or 60 months ahead ---------- */
  var TRP = null;
  function loadTransitions() {
    if (!TRP) TRP = fetch("data/transitions.json").then(function (r) { if (!r.ok) throw new Error("transitions " + r.status); return r.json(); }).catch(function (e) { TRP = null; throw e; });
    return TRP;
  }
  function modeSeg(p) { return segment("c", [["", t("At the horizon")], ["enter", t("Entering an alert")], ["leave", t("Leaving an alert")]], p.c === "enter" || p.c === "leave" ? p.c : "", "View"); }
  function renderChanges(p, view) {
    var hzs = [12, 36, 60], hz = hzs.indexOf(+p.h) >= 0 ? hzs.indexOf(+p.h) : 0, ty = p.t === "0" || p.t === "1" ? +p.t : -1, mode = p.c;
    return loadTransitions().then(function (T) {
      var inScope = function (r) { var tr = TRADES[r[4]]; return r[1] === hz && (!p.state || STATES[r[2]] === p.state) && (!p.district || String(r[3]) === String(p.district)) && (!p.trade || tr.c === p.trade) && (!p.sector || tr.s === p.sector); };
      var base = T.rows.filter(inScope), n = function (type) { return base.filter(function (r) { return r[0] === type; }).length; };
      var rows = base.filter(function (r) { return (mode === "enter" ? r[0] % 2 === 0 : r[0] % 2 === 1) && (ty < 0 || (ty === 0 ? r[0] < 2 : r[0] >= 2)); });
      rows.sort(function (a, b) { return mode === "enter" ? (a[7] - b[7]) || (Math.abs(b[6] - 50) - Math.abs(a[6] - 50)) : Math.abs(b[5] - 50) - Math.abs(a[5] - 50); });
      var shown = rows.slice(0, 250), h = hzs[hz], kind = ["Entering shortage alert", "Leaving shortage alert", "Entering oversupply alert", "Leaving oversupply alert"];
      var kp = function (type, color, label) { return kpi(t(label), color, n(type), "<span>" + (type % 2 === 0 ? tf("Not in an alert tail now, in it {0} months ahead", h) : tf("In an alert tail now, out of it {0} months ahead", h)) + "</span>"); };
      var cs = T.counts, stay = function (name) { return cs[name + "|" + h]; };
      var cell = function (r) { return '<tr class="click" data-district="' + r[3] + '" data-trade="' + TRADES[r[4]].c + '"><td><span class="pill ' + (r[0] < 2 ? "alert" : "s4") + '">' + t(kind[r[0]]) + "</span></td><td>" + esc(DNAME[r[3]]) + "</td><td>" + esc(STATES[r[2]]) + "</td><td>" + esc(TRADES[r[4]].n) +
        '</td><td class="num">' + fmt(r[5], 0) + " → " + fmt(r[6], 0) + '</td><td class="num">' + (r[9] ? fmt(r[8] / r[9] * 100, 1) : "–") + " → " + (r[11] ? fmt(r[10] / r[11] * 100, 1) : "–") + '</td><td class="num">' + (r[7] ? ml(addM(M.fc[0], r[7] - 1)) : "–") + "</td></tr>"; };
      view.innerHTML = '<div class="grid g4">' + kp(0, "var(--demand)", "Entering the shortage tail") + kp(2, "var(--low)", "Entering the oversupply tail") + kp(1, "var(--employed)", "Leaving the shortage tail") + kp(3, "var(--supply)", "Leaving the oversupply tail") + "</div>" +
        '<section class="card mt"><div class="card-h"><div><h2>' + tf("{0} series change status", fmt(rows.length)) + "</h2><p>" + tf("For {0}, now (December 2025) against {1} months ahead", esc(scopeText(p)), h) + '</p></div><div style="display:flex;gap:8px;flex-wrap:wrap">' + modeSeg(p) +
        segment("h", [[12, tf("{0} months", 12)], [36, tf("{0} months", 36)], [60, tf("{0} months", 60)]], h, "Months ahead") + segment("t", [["", t("Both")], ["0", t("Shortage")], ["1", t("Oversupply")]], ty < 0 ? "" : ty, "Type") + "</div></div>" +
        (shown.length ? table([["Change"], ["District"], ["State"], ["Trade"], ["Percentile now → then", "num"], ["Vacancies per 100 seekers now → then", "num"], ["First month in the tail", "num"]], shown.map(cell)) : '<p class="note">' + t("No changes for these filters.") + "</p>") +
        (rows.length > shown.length ? '<p class="note">' + tf("Showing the first {0} of {1}; the CSV has all of them.", shown.length, fmt(rows.length)) + "</p>" : "") +
        '<p class="note">' + tf("Most alerts persist: of the {0} shortage and {1} oversupply alerts now, {2} and {3} are out of the tail {4} months ahead (and as many have moved in).", fmt(T.current.shortage), fmt(T.current.oversupply), fmt(stay("leave_shortage")), fmt(stay("leave_oversupply")), h) + " " +
        t("Now means December 2025, from the actual vacancies and registered seekers, ranked among the districts of the trade like the forecasts. An alert tail is the top tenth (shortage) or the bottom tenth (oversupply). The forecast flags are relative: a series can leave a tail because others rose faster, not because it fell.") + "</p></section>";
      bindSeg(view); bindRows(view);
      cur.csv = { name: fname("alert_changes_" + mode + "_" + h + "m"), head: ["change", "months_ahead", "state", "district_lgd", "district", "trade", "percentile_now", "percentile_then", "vacancies_now", "seekers_now", "vacancies_then", "seekers_then", "first_month_in_tail"],
        rows: rows.map(function (r) { return [kind[r[0]].toLowerCase(), h, STATES[r[2]], r[3], DNAME[r[3]], TRADES[r[4]].c, r[5], r[6], r[8], r[9], r[10], r[11], r[7] ? addM(M.fc[0], r[7] - 1) : ""]; }) };
    });
  }

  render.warnings = function (p, view) {
    if (p.c === "enter" || p.c === "leave") return renderChanges(p, view);
    var hzs = [12, 36, 60], hz = hzs.indexOf(+p.h) >= 0 ? hzs.indexOf(+p.h) : 0, ty = p.t === "0" || p.t === "1" ? +p.t : -1, all = alertsFor(p, hz), rows = all.filter(function (a) { return ty < 0 || a[0] === ty; });
    rows.sort(function (a, b) { return (a[0] - b[0]) || (a[0] === 0 ? b[5] - a[5] : a[5] - b[5]); });
    var shown = rows.slice(0, 250), nS = all.filter(function (a) { return a[0] === 0; }).length;
    view.innerHTML = '<div class="grid g4">' + kpi(t("Shortage alerts"), "var(--demand)", nS, "<span>" + t("Highest forecast vacancies per seeker in the trade") + "</span>") + kpi(t("Oversupply alerts"), "var(--low)", all.length - nS, "<span>" + t("Lowest forecast vacancies per seeker in the trade") + "</span>") + "</div>" +
      '<section class="card mt"><div class="card-h"><div><h2>' + tf("{0} flagged series", fmt(rows.length)) + "</h2><p>" + tf("For {0}, {1} months ahead", esc(scopeText(p)), hzs[hz]) + '</p></div><div style="display:flex;gap:8px;flex-wrap:wrap">' +
      modeSeg(p) + segment("h", [[12, tf("{0} months", 12)], [36, tf("{0} months", 36)], [60, tf("{0} months", 60)]], hzs[hz], "Months ahead") + segment("t", [["", t("Both")], ["0", t("Shortage")], ["1", t("Oversupply")]], ty < 0 ? "" : ty, "Type") + "</div></div>" +
      table([["Alert"], ["District"], ["State"], ["Trade"], ["Vacancies per 100 seekers", "num"], ["Percentile", "num"], ["Confidence V", "num"], ["Confidence S", "num"]], shown.map(function (a) {
        var tr = TRADES[a[4]], cov = a[7] ? a[6] / a[7] * 100 : 0;
        return '<tr class="click" data-district="' + a[3] + '" data-trade="' + tr.c + '"><td><span class="pill ' + (a[0] === 0 ? "alert" : "s4") + '">' + t(a[0] === 0 ? "Shortage alert" : "Oversupply alert") + "</span></td><td>" + esc(DNAME[a[3]]) + "</td><td>" + esc(STATES[a[2]]) + "</td><td>" + esc(tr.n) + '</td><td class="num">' + fmt(cov, 1) + '</td><td class="num">' + fmt(a[5], 0) + '</td><td class="num">' + confChip(a[8]) + '</td><td class="num">' + confChip(a[9]) + "</td></tr>";
      })) + (rows.length > shown.length ? '<p class="note">' + tf("Showing the first {0} of {1}; the CSV has all of them.", shown.length, fmt(rows.length)) + "</p>" : "") +
      '<p class="note">' + t("An alert is relative: the series lies in the top (shortage) or bottom (oversupply) 10% of districts in its trade in that month. In testing such alerts were right about seven times in ten at 1-12 months, against a base rate of one in ten. Seeker forecasts and long horizons are less reliable; the confidence columns show it.") + "</p></section>";
    bindSeg(view); bindRows(view);
    cur.csv = { name: fname("warnings_" + hzs[hz] + "m"), head: ["alert", "months_ahead", "state", "district_lgd", "district", "trade", "percentile", "vacancies", "seekers", "vacancies_per_100_seekers", "confidence_V", "confidence_S"], rows: rows.map(function (a) { var tr = TRADES[a[4]]; return [a[0] === 0 ? "shortage" : "oversupply", hzs[hz], STATES[a[2]], a[3], DNAME[a[3]], tr.c, a[5], a[6], a[7], a[7] ? +(a[6] / a[7] * 100).toFixed(2) : "", a[8], a[9]]; }) };
    return Promise.resolve();
  };

  render.data = function (p, view) {
    var cv = D.coverage, g = function (o, k) { return o[k] == null ? "–" : fmt(o[k] * 100, 0) + "%"; }, man = M.manifest, ap = cv.alert_precision_test;
    var pr = function (b, f) { var v = ap[b + "|" + f]; return v ? fmt(v[0] * 100, 0) + "% (" + v[1] + "×)" : "–"; };
    var row = function (a, b) { return '<tr><th scope="row">' + a + "</th><td>" + b + "</td></tr>"; };
    view.innerHTML = '<div class="grid g2"><section class="card"><div class="card-h"><div><h2>' + t("Coverage of the dataset") + '</h2></div></div><div class="tbl-wrap"><table class="tbl"><tbody>' + [
      [t("Series"), fmt(M.series) + " (" + STATES.length + " " + t("states") + ", " + DLIST.length + " " + t("districts") + ", " + SECTORS.length + " " + t("sectors") + ", " + TRADES.length + " " + t("trades") + ")"], [t("History"), "2000-01 – " + M.hist_core[1] + " (" + t("charts show from") + " " + M.hist_core[0] + ", " + t("districts from") + " " + M.hist_shard[0] + ")"],
      [t("Forecast"), ml(M.fc[0]) + " – " + ml(M.fc[1]) + " (60 " + t("months") + ", " + t("made from") + " " + ml(M.origin) + ")"], [t("Final models fitted on"), esc(String(man.deploy_fit.fit_targets_to)) + " (" + t("without the 2020-23 shock and recovery pairs") + ")"], [t("Built"), esc(man.generated_at_utc)]].map(function (r) { return row(r[0], r[1]); }).join("") + "</tbody></table></div></section>" +
      '<section class="card"><div class="card-h"><div><h2>' + t("Read this first") + '</h2></div></div><ul class="plain"><li><b>' + t("The data is simulated.") + "</b> " + t("It behaves like official statistics but describes no real district.") + "</li><li><b>" + t("Forecasts are not certain.") + "</b> " + t("The 2020-23 shock was not foreseeable from earlier years; ranges calibrated on calm years are too narrow for totals, so wide ranges are drawn too.") + "</li><li><b>" + t("Seekers are the least reliable measure,") + "</b> " + t("and their confidence labels do not always fall as the horizon grows.") + "</li><li><b>" + t("Long horizons") + "</b> " + t("(beyond 24 months) are learned from pre-2020 dynamics and are lumpier where the horizon crosses 24 months.") + "</li></ul></section></div>" +
      '<section class="card mt"><div class="card-h"><div><h2>' + t("How often the 90% ranges held") + "</h2><p>" + t("Share of actual values inside the usual range in held-out years (a good range gives about 90%). The wide range includes 2020-25 in its calibration, so it cannot be tested on those years.") + "</p></div></div>" + table([["Measure"], ["2015-19", "num"], ["2020-25", "num"]], ["E", "V", "S"].map(function (k) { return "<tr><td>" + t(NAMES[k]) + '</td><td class="num">' + g(cv.series, "test|" + k + "|validation") + '</td><td class="num">' + g(cv.series, "stress|" + k + "|validation+test") + "</td></tr>"; })) +
      '<p class="note">' + tf("Totals for a state or India: the usual range held only {0} of the time for employed workers in 2015-19 and {1} in 2020-25, which is why the wide range is shown for totals. District-sector totals behave like single series ({2} in 2015-19).", g(cv.aggregate, "forward|test|india|E"), g(cv.aggregate, "forward|stress|india|E"), g(cv.aggregate, "forward|test|district_sector|E")) + "</p></section>" +
      '<section class="card mt"><div class="card-h"><div><h2>' + t("Definitions") + '</h2></div></div><dl class="defs"><dt>' + t("Demand Index") + "</dt><dd>" + t("0 to 100. Compares openings per worker (vacancies, job-portal postings, National Career Service) with other districts of the same trade, plus a national level term; 50 is the median district at the 2018-2019 level.") + "</dd><dt>" + t("Capacity gap") + "</dt><dd>" + t("Forecast openings against training seats sanctioned in 2025-26 (held flat) and the trainees expected to be certified (seats times the 2023-25 median certification rate). Status: seats fall short when the district's share of seats is less than 0.6 times its share of openings in the trade, exceed when more than 1.65 times.") + "</dd><dt>" + t("Early-warning alert") + "</dt><dd>" + t("The series is in the top or bottom 10% of districts of its trade in forecast vacancies per seeker for that month. A watch is the next 15%.") + "</dd><dt>" + t("Usual and wide range") + "</dt><dd>" + t("Both are 90% ranges. The usual one is calibrated on 2010-2019; the wide one also on 2020-2025.") + "</dd><dt>" + t("Confidence") + "</dt><dd>" + t("High, Medium or Low from the typical error of earlier forecasts for the same trade and horizon band: up to 8%, up to 20%, above; one level lower for small series.") + "</dd></dl></section>" +
      '<section class="card mt"><div class="card-h"><div><h2>' + t("Alert accuracy in testing") + "</h2><p>" + t("Share of alerts that were in the true top or bottom 10% (and how many times better than chance), 2015-19, 1-12 months ahead") + "</p></div></div>" + table([["Alert"], ["Right", "num"]], [["Shortage alert"], ["Oversupply alert"]].map(function (f) { return "<tr><td>" + t(f[0]) + '</td><td class="num">' + pr("1-12", f[0]) + "</td></tr>"; })) + "</section>" +
      '<section class="card mt"><div class="card-h"><div><h2>' + t("Downloads") + "</h2><p>" + t("CSV and JSON of the page you are on use the current filters. Series-level files for all 7,925 series are in the export folder.") + '</p></div></div><div class="dl-row"><a class="chip-btn primary" style="margin-left:0" href="' + url("forecast", {}) + '">' + t("Forecast page") + '</a> <a class="chip-btn primary" style="margin-left:0" href="' + url("warnings", {}) + '">' + t("Alerts page") + "</a></div></section>";
    cur.csv = { name: "kaushalsetu_coverage", head: ["key", "coverage"], rows: Object.keys(cv.series).map(function (k) { return ["series|" + k, cv.series[k]]; }).concat(Object.keys(cv.aggregate).map(function (k) { return ["aggregate|" + k, cv.aggregate[k]]; })) };
    return Promise.resolve();
  };

  /* ---------- the API page: build a request from the current filters, run it and read the JSON ----------
     The parameters of every endpoint are documented on the public Forecast API page; this page is the tool, not a second copy of the documentation. */
  var API_YEARS = [["2026", "2026"], ["2027", "2027"], ["2028", "2028"], ["2029", "2029"], ["2030", "2030"]];
  var API_LEVELS = [["trade", "Trades"], ["state", "States"], ["state_trade", "State and trade"], ["district", "Districts"], ["district_sector", "District and sector"], ["series", "District and trade series"]];
  var API_EPS = {
    forecast: { limit: "series", opts: [
      { k: "measure", l: "Measure", d: "all", o: [["all", "All"], ["E", "Employed workers"], ["V", "Job vacancies"], ["S", "Registered job seekers"]] },
      { k: "horizon", l: "Months ahead", d: "12,36,60", o: [["12,36,60", "12, 36 and 60"], ["12", "12"], ["36", "36"], ["60", "60"], ["all", "Every month"]] },
      { k: "detail", l: "Detail", d: "aggregate", o: [["aggregate", "One total"], ["series", "Every series"]] }] },
    flags: { limit: true, opts: [
      { k: "horizon", l: "Months ahead", d: "12", o: [["12", "12"], ["36", "36"], ["60", "60"]] },
      { k: "type", l: "Type", d: "all", o: [["all", "Both"], ["shortage", "Shortage"], ["oversupply", "Oversupply"]] },
      { k: "change", l: "Change", d: "", o: [["", "Current alerts"], ["entering", "Entering a tail"], ["leaving", "Leaving a tail"]] }] },
    "demand-index": { opts: [{ k: "resolution", l: "Resolution", d: "annual", o: [["annual", "Each December"], ["monthly", "Every month"]] }] },
    "capacity-gap": { opts: [{ k: "year", l: "Year", d: "", o: [["", "All years"]].concat(API_YEARS) }] },
    severity: { limit: true, opts: [
      { k: "level", l: "Level", d: "trade", o: API_LEVELS },
      { k: "order", l: "Order", d: "under", o: [["under", "Most undersupplied first"], ["over", "Most oversupplied first"], ["severity", "Largest gap either way"]] },
      { k: "year", l: "Year", d: "2030", o: API_YEARS }] },
    scenario: { limit: true, opts: [
      { k: "level", l: "Level", d: "trade", o: API_LEVELS },
      { k: "year", l: "Year", d: "2030", o: API_YEARS },
      { k: "seat_change", l: "Change seats by (%)", d: "20", always: true, n: [-90, 500, 5] },
      { k: "from_year", l: "From year", d: "2026", always: true, o: API_YEARS },
      { k: "target", l: "Target certified per opening", d: "1", always: true, n: [0.2, 5, 0.1] }] },
    meta: { opts: [] }
  };
  var APIST = { v: {} };
  render.api = function (p, view) {
    var ep = API_EPS[p.e] ? p.e : "forecast", cfg = API_EPS[ep];
    if (cfg.opts.length && cfg.opts[0].k === "level") cfg.opts[0].d = p.district ? "series" : p.state ? "state_trade" : "trade";      // the levels that exist for the chosen filters
    var  vals = APIST.v[ep] = APIST.v[ep] || {}, MAX = 12000;
    var scope = ep === "meta" ? [] : ["state", "district", "sector", "trade"].filter(function (k) { return p[k]; }).map(function (k) { return [k, p[k]]; });
    var get = function (o) { return vals[o.k] != null ? vals[o.k] : o.d; };
    var wantsLimit = function () { return cfg.limit === true || (cfg.limit === "series" && get(cfg.opts[2]) === "series"); };
    var query = function () {
      var q = scope.slice();
      cfg.opts.forEach(function (o) { var v = get(o); if (o.always || String(v) !== String(o.d)) q.push([o.k, v]); });
      if (wantsLimit()) q.push(["limit", vals.limit != null ? vals.limit : 5]);
      return q;
    };
    var rel = function () { var q = query(); return "../api/" + ep + (q.length ? "?" + q.map(function (kv) { return kv[0] + "=" + encodeURIComponent(kv[1]).replace(/%2C/g, ","); }).join("&") : ""); };
    var abs = function () { try { return new URL(rel(), location.href).href; } catch (e) { return rel(); } };
    var field = function (id, label, ctl) { return '<label for="' + id + '"><span>' + t(label) + "</span>" + ctl + "</label>"; };
    var ctls = cfg.opts.map(function (o) {
      var id = "api-o-" + o.k, v = get(o);
      if (o.n) return field(id, o.l, '<input type="number" id="' + id + '" data-k="' + o.k + '" min="' + o.n[0] + '" max="' + o.n[1] + '" step="' + o.n[2] + '" value="' + esc(v) + '">');
      return field(id, o.l, '<select id="' + id + '" data-k="' + o.k + '">' + o.o.map(function (x) { return '<option value="' + esc(x[0]) + '"' + (String(x[0]) === String(v) ? " selected" : "") + ">" + esc(t(x[1])) + "</option>"; }).join("") + "</select>");
    }).join("") + (wantsLimit() ? field("api-o-limit", "Rows to return", '<input type="number" id="api-o-limit" data-k="limit" min="1" max="200" step="1" value="' + esc(vals.limit != null ? vals.limit : 5) + '">') : "");
    var epSel = field("api-ep", "Endpoint", '<select id="api-ep" translate="no">' + Object.keys(API_EPS).map(function (k) { return '<option value="' + k + '"' + (k === ep ? " selected" : "") + ">/api/" + k + "</option>"; }).join("") + "</select>");
    view.innerHTML = '<section class="card"><div class="card-h"><div><h2>' + t("Build a request") + "</h2><p>" + t("Choose an endpoint and its options. The filters above set the state, district, sector and trade.") + '</p></div></div>' +
      '<div class="scn-form">' + epSel + ctls + "</div>" +
      '<p class="note api-scope">' + (ep === "meta" ? t("This endpoint takes no filters.") : tf("Filters: {0}", esc(scopeText(p)))) + "</p>" +
      '<div class="api-bar"><code class="api-url" id="api-url" translate="no"></code><button class="chip-btn" id="api-copy" type="button">' + t("Copy") + '</button><a class="chip-btn" id="api-open" target="_blank" rel="noopener">' + t("Open in a new tab") + '</a><button class="chip-btn primary" id="api-run" type="button">' + t("Run") + "</button></div></section>" +
      '<section class="card mt"><div class="card-h"><div><h2>' + t("Response") + '</h2><p id="api-status" role="status" aria-live="polite"></p></div></div><pre class="api-out" id="api-out" tabindex="0" translate="no" aria-label="' + esc(t("Response")) + '"></pre></section>' +
      '<p class="note">' + t("Every parameter, an example and the error codes are on the Forecast API page.") + ' <a class="ulink" href="../docs/api.html">' + t("Forecast API") + "</a> · " + t("No key is needed; up to 60 requests a minute. Every response says that the data is simulated.") + "</p>";
    var status = $("#api-status", view), out = $("#api-out", view);
    var refresh = function () {
      $("#api-url", view).textContent = abs(); $("#api-open", view).href = rel();
      cur.csv = { name: fname("api_request"), head: ["endpoint", "request"], rows: [["/api/" + ep, abs()]] };
    };
    var stale = function () { status.textContent = t("Press Run to fetch the request above."); out.textContent = ""; };
    var run = function () {
      var t0 = performance.now();
      status.textContent = t("Running…"); out.textContent = "";
      fetch(rel(), { headers: { Accept: "application/json" } }).then(function (r) { return r.text().then(function (txt) { return { r: r, txt: txt }; }); }).then(function (x) {
        var ms = Math.round(performance.now() - t0), shown = x.txt, js = null;
        try { js = JSON.parse(x.txt); shown = JSON.stringify(js, null, 2); } catch (e) { /* not JSON: show it as it came */ }
        out.textContent = shown.length > MAX ? shown.slice(0, MAX) + "\n…" : shown;
        status.textContent = x.r.status + " · " + ms + " ms · " + fmt(x.txt.length / 1024, 1) + " KB" + (x.r.ok ? "" : " · " + ((js && js.message) || "")) + (shown.length > MAX ? " · " + tf("Shortened to the first {0} characters; open the request for the whole response.", fmt(MAX)) : "");
      }).catch(function () { status.textContent = t("The request could not be sent. Open the dashboard from a server that also serves the API."); });
    };
    $("#api-ep", view).addEventListener("change", function (e) { go({ e: e.target.value }); });
    $$("[data-k]", view).forEach(function (c) { c.addEventListener("change", function () { vals[c.dataset.k] = c.value; if (cfg.limit === "series" && c.dataset.k === "detail") { render.api(p, view); return; } refresh(); stale(); }); });
    $("#api-run", view).addEventListener("click", run);
    $("#api-copy", view).addEventListener("click", function () {
      var done = function () { status.textContent = t("Copied to the clipboard."); }, text = abs();
      if (navigator.clipboard && navigator.clipboard.writeText) navigator.clipboard.writeText(text).then(done, function () { status.textContent = t("Select the address above to copy it."); });
      else status.textContent = t("Select the address above to copy it.");
    });
    refresh(); run();
    return Promise.resolve();
  };

  /* ---------- the map page: 317 districts coloured by a measure, with the states, the districts and the alerts beside it ---------- */
  var MAPP = null, MTI = { E: 0, V: 1, S: 2 };
  function loadMap() {
    if (window.MAP_DATA) return Promise.resolve(window.MAP_DATA);
    if (!MAPP) MAPP = new Promise(function (res, rej) {
      var s = document.createElement("script"); s.src = document.body.getAttribute("data-map");
      s.onload = function () { res(window.MAP_DATA); }; s.onerror = function () { MAPP = null; rej(new Error("map data")); };
      document.head.appendChild(s);
    });
    return MAPP;
  }
  /* one measure over a set of districts and sectors: totals now and at the horizon, the change, the usual 90% range (one sector only) and the Demand Index (employed-weighted) */
  function mapVal(M, codes, k, h, sis) {
    var j = M.horizons.indexOf(h), fi = 1 + j, now = 0, fc = 0, lo = 0, hi = 0, wn = 0, wf = 0, dn = 0, df = 0;
    codes.forEach(function (c) {
      var v = M.values[c];
      sis.forEach(function (si) {
        if (k === "D") { var e = v[si][0], d = v[si][3]; wn += e[0]; wf += e[fi]; dn += e[0] * d[0]; df += e[fi] * d[fi]; return; }
        var a = v[si][MTI[k]]; now += a[0]; fc += a[fi]; lo += a[4 + 2 * j]; hi += a[5 + 2 * j];
      });
    });
    if (k === "D") return { now: dn / wn, fc: df / wf, val: df / wf, lo: null, hi: null };
    var one = sis.length === 1 && codes.length === 1;
    return { now: now, fc: fc, val: (fc / now - 1) * 100, lo: one ? lo : null, hi: one ? hi : null };
  }
  var mapFill = function (k, c) { return "color-mix(in srgb, " + (k === "E" ? "var(--employed)" : k === "S" ? "var(--supply)" : "var(--demand)") + " " + [26, 44, 62, 82, 100][c] + "%, var(--surface))"; };
  var mapFmt = function (k, v) { return k === "D" ? fmt(v, 1) : pct(v, 1); };
  var mapName = function (k) { return k === "D" ? t("Demand Index") : t(NAMES[k]); };

  function drawMap(box, M, rows, k, p, shown) {
    box.innerHTML = "";
    var svg = el("svg", { role: "img", "aria-label": tf("Map of {0} districts coloured by {1}", rows.length, mapName(k)) }, box);
    el("path", { d: M.backdrop, class: "mbackdrop" }, svg);
    var g = el("g", {}, svg), byCode = {};
    rows.forEach(function (r) {
      var d = r.d, q = el("path", { d: d.d, class: "mdist" + (p.state && p.state !== d.s ? " dim" : ""), style: "fill:" + mapFill(k, r.cls), "data-code": d.c }, g);
      q.setAttribute("data-tip", "<b>" + esc(LANG === "hi" && HIN[d.n] ? HIN[d.n] : d.n) + "</b> · " + esc(LANG === "hi" && HIN[d.s] ? HIN[d.s] : d.s) + "<br>" + esc(mapName(k)) + ": <b>" + mapFmt(k, r.val) + "</b><br>" + (k === "D" ? tf("{0} now, {1} in {2} months", fmt(r.now, 1), fmt(r.fc, 1), shown.h) : tf("{0} now, {1} in {2} months", fmt(Math.round(r.now)), fmt(Math.round(r.fc)), shown.h)) +
        (r.lo != null ? "<br>" + tf("Usual 90% range {0} to {1}", fmt(Math.round(r.lo)), fmt(Math.round(r.hi))) : ""));
      q.addEventListener("click", function () { go({ district: p.district === d.c ? "" : d.c }); });
      byCode[d.c] = q;
    });
    if (M.borders) el("path", { d: M.borders, class: "mborder" }, svg);
    if (p.district && byCode[p.district]) el("path", { d: byCode[p.district].getAttribute("d"), class: "mhl" }, svg);
    var labels = [];
    M.states.forEach(function (s) {
      var ds = M.districts.filter(function (d) { return d.s === s; }); if (!ds.length || (p.state && p.state !== s)) return;
      var tx = el("text", { class: "mstate" }, svg); tx.textContent = LANG === "hi" && HIN[s] ? HIN[s] : s;
      labels.push({ n: tx, x: ds.reduce(function (a, d) { return a + (d.bb[0] + d.bb[2]) / 2; }, 0) / ds.length, y: ds.reduce(function (a, d) { return a + (d.bb[1] + d.bb[3]) / 2; }, 0) / ds.length });
    });
    var vb = M.viewBox.slice();
    if (p.state) {
      var x0 = 1e9, y0 = 1e9, x1 = -1e9, y1 = -1e9;
      M.districts.filter(function (d) { return d.s === p.state; }).forEach(function (d) { x0 = Math.min(x0, d.bb[0]); y0 = Math.min(y0, d.bb[1]); x1 = Math.max(x1, d.bb[2]); y1 = Math.max(y1, d.bb[3]); });
      var pad = Math.max(x1 - x0, y1 - y0) * 0.12; vb = [x0 - pad, y0 - pad, x1 - x0 + 2 * pad, y1 - y0 + 2 * pad];
    }
    var r = box.clientWidth > 0 && box.clientHeight > 0 ? box.clientWidth / box.clientHeight : 1, cx = vb[0] + vb[2] / 2, cy = vb[1] + vb[3] / 2, w = vb[2], hh = vb[3];
    if (w / hh < r) w = hh * r; else hh = w / r;
    svg.setAttribute("viewBox", [cx - w / 2, cy - hh / 2, w, hh].map(function (n) { return n.toFixed(1); }).join(" "));
    var kx = Math.min(box.clientWidth / w, box.clientHeight / hh) || 1;
    labels.forEach(function (l) { l.n.setAttribute("x", l.x.toFixed(1)); l.n.setAttribute("y", l.y.toFixed(1)); l.n.setAttribute("font-size", (11 / kx).toFixed(1)); l.n.setAttribute("stroke-width", (3 / kx).toFixed(1)); });
  }

  render.map = function (p, view) {
    return loadMap().then(function (M) {
      var k = ["E", "V", "S", "D"].indexOf(p.k) >= 0 ? p.k : "V", h = [12, 36, 60].indexOf(+p.h) >= 0 ? +p.h : 12;
      var sis = p.sector ? [M.sectors.indexOf(p.sector)] : M.sectors.map(function (_, i) { return i; });
      var rows = M.districts.map(function (d) { var r = mapVal(M, [d.c], k, h, sis); r.d = d; return r; });
      var ord = rows.slice().sort(function (a, b) { return a.val - b.val; });
      ord.forEach(function (r, i) { r.cls = Math.min(4, Math.floor(i * 5 / ord.length)); });
      var scoped = rows.filter(function (r) { return (!p.state || r.d.s === p.state); }), codes = scoped.map(function (r) { return r.d.c; });
      var sel = p.district ? rows.filter(function (r) { return r.d.c === p.district; })[0] : null;
      var months = tf("{0} months ahead", h), tgt = ml(addM(M.origin, h));
      var spans = [0, 1, 2, 3, 4].map(function (c) { var vs = ord.filter(function (r) { return r.cls === c; }).map(function (r) { return r.val; }); return [Math.min.apply(null, vs), Math.max.apply(null, vs)]; });
      var legend = '<div class="ctx-legend">' + spans.map(function (s, c) { return '<span style="--c:' + mapFill(k, c) + '"><i></i>' + mapFmt(k, s[0]) + " → " + mapFmt(k, s[1]) + "</span>"; }).join("") + "</div>";
      var chips = [["", t("All states")]].concat(M.states.map(function (s) { return [s, s]; }));
      var four = ["E", "V", "S", "D"].map(function (kk) { var v = mapVal(M, sel ? [sel.d.c] : codes, kk, h, sis); return { k: kk, v: v }; });
      var sumCard = '<section class="card"><div class="card-h"><div><h2>' + esc(sel ? sel.d.n + ", " + sel.d.s : (p.state || t("All states"))) + "</h2><p>" + esc(p.sector ? t(p.sector) : t("all sectors")) + " · " + esc(tf("Dec 2025 and {0}", tgt)) + "</p></div>" + (sel ? '<button class="chip-btn" type="button" data-clear="1">' + t("Show the whole region again") + "</button>" : "") + "</div>" +
        table([["Measure"], ["Now", "num"], [tgt, "num"], ["Change", "num"]].concat(four[0].v.lo != null ? [["Usual 90% range", "num"]] : []), four.map(function (x) {
          return "<tr><td>" + esc(mapName(x.k)) + '</td><td class="num">' + (x.k === "D" ? fmt(x.v.now, 1) : compact(x.v.now)) + '</td><td class="num">' + (x.k === "D" ? fmt(x.v.fc, 1) : compact(x.v.fc)) + '</td><td class="num">' + (x.k === "D" ? fmt(x.v.fc - x.v.now, 1) : dir(x.v.val)) + "</td>" + (four[0].v.lo != null ? '<td class="num">' + (x.v.lo != null ? compact(x.v.lo) + " – " + compact(x.v.hi) : "–") + "</td>" : "") + "</tr>";
        })) + (sel ? '<p class="note"><a class="chip-btn" href="' + url("forecast", { district: sel.d.c }) + '">' + t("Open the Forecast page") + '</a> <a class="chip-btn" href="' + url("capacity", { district: sel.d.c }) + '">' + t("Open the Capacity gap") + "</a></p>" : "") + "</section>";
      var secCard = '<section class="card mt"><div class="card-h"><div><h2>' + t("By sector") + "</h2><p>" + t("Click a row to choose a sector") + "</p></div></div>" + table([["Sector"], [k === "D" ? "Demand Index" : "Change", "num"], ["Now", "num"], [tgt, "num"]], M.sectors.map(function (sn, i) {
        var v = mapVal(M, sel ? [sel.d.c] : codes, k, h, [i]);
        return '<tr class="click' + (p.sector === sn ? " on" : "") + '" data-sector="' + esc(sn) + '"><td>' + esc(t(sn)) + '</td><td class="num" ' + (k === "D" ? heat(v.val) : "") + ">" + mapFmt(k, v.val) + '</td><td class="num">' + (k === "D" ? fmt(v.now, 1) : compact(v.now)) + '</td><td class="num">' + (k === "D" ? fmt(v.fc, 1) : compact(v.fc)) + "</td></tr>";
      })) + "</section>";
      var srt = scoped.slice().sort(function (a, b) { return b.val - a.val; });
      var line = function (r, i) { return '<tr class="click" data-district="' + r.d.c + '"><td class="num">' + (i + 1) + "</td><td>" + esc(r.d.n) + "</td><td>" + esc(r.d.s) + '</td><td class="num" ' + (k === "D" ? heat(r.val) : "") + ">" + mapFmt(k, r.val) + '</td><td class="num">' + (k === "D" ? fmt(r.now, 1) : compact(r.now)) + "</td></tr>"; };
      var head = [["#", "num"], ["District"], ["State"], [k === "D" ? "Demand Index" : "Change", "num"], ["Now", "num"]];
      var states = M.states.map(function (s) { var cs = M.districts.filter(function (d) { return d.s === s; }).map(function (d) { return d.c; }); return { s: s, v: mapVal(M, cs, k, h, sis) }; }).sort(function (a, b) { return b.v.val - a.v.val; });
      var hz = [12, 36, 60].indexOf(h), A_ = alertsScope(p, hz), cnt = {};
      A_.forEach(function (a) { var c = cnt[a[3]] = cnt[a[3]] || { s: 0, o: 0, st: STATES[a[2]] }; if (a[0] === 0) c.s++; else c.o++; });
      var alertRows = Object.keys(cnt).map(function (c) { return { c: c, n: DNAME[c], st: cnt[c].st, s: cnt[c].s, o: cnt[c].o }; }).sort(function (a, b) { return (b.s + b.o) - (a.s + a.o) || (a.n < b.n ? -1 : 1); }).slice(0, 10);
      view.innerHTML = scopeHead({ state: p.state, district: p.district, sector: p.sector, trade: p.trade }, segment("k", [["V", t("Vacancies")], ["E", t("Employed")], ["S", t("Seekers")], ["D", t("Demand Index")]], k, "Measure") + segment("h", [[12, tf("{0} months", 12)], [36, tf("{0} months", 36)], [60, tf("{0} months", 60)]], h, "Months ahead")) +
        (p.trade ? '<p class="note">' + t("The map is by sector: the trade filter chooses its sector.") + "</p>" : "") +
        '<div class="grid g-map"><section class="card"><div class="card-h"><div><h2>' + esc(mapName(k)) + "</h2><p>" + esc(k === "D" ? tf("Demand Index in {0}", tgt) : tf("Change in {0}, Dec 2025 to {1}", mapName(k).toLowerCase(), tgt)) + ". " + t("Five equal groups of districts; click a district to choose it.") + "</p></div></div>" +
        '<div class="mapbox" id="mapbox"><div class="m-chips" role="group" aria-label="' + esc(t("State")) + '">' + chips.map(function (c) { return '<button type="button" data-st="' + esc(c[0]) + '" aria-pressed="' + ((p.state || "") === c[0]) + '">' + esc(c[1]) + "</button>"; }).join("") + '</div><div id="mapsvg"></div></div>' + legend +
        '<p class="sr-only" id="map-sr"></p></section><div>' + sumCard + secCard + "</div></div>" +
        '<div class="grid g2 mt"><section class="card"><div class="card-h"><div><h2>' + t("Highest districts") + "</h2><p>" + esc(p.state || t("All states")) + ", " + esc(months) + "</p></div></div>" + table(head, srt.slice(0, 10).map(line)) + "</section>" +
        '<section class="card"><div class="card-h"><div><h2>' + t("Lowest districts") + "</h2><p>" + esc(p.state || t("All states")) + ", " + esc(months) + "</p></div></div>" + table(head, srt.slice(-10).reverse().map(function (r, i) { return line(r, srt.length - 1 - i); })) + "</section></div>" +
        '<div class="grid g2 mt"><section class="card"><div class="card-h"><div><h2>' + t("States") + "</h2><p>" + t("Click a row to choose a state") + "</p></div></div>" + table([["State"], [k === "D" ? "Demand Index" : "Change", "num"], ["Now", "num"], [tgt, "num"]], states.map(function (x) {
          return '<tr class="click' + (p.state === x.s ? " on" : "") + '" data-state="' + esc(x.s) + '"><td>' + esc(x.s) + '</td><td class="num" ' + (k === "D" ? heat(x.v.val) : "") + ">" + mapFmt(k, x.v.val) + '</td><td class="num">' + (k === "D" ? fmt(x.v.now, 1) : compact(x.v.now)) + '</td><td class="num">' + (k === "D" ? fmt(x.v.fc, 1) : compact(x.v.fc)) + "</td></tr>"; })) + "</section>" +
        '<section class="card"><div class="card-h"><div><h2>' + t("Where the alerts are") + "</h2><p>" + esc(tf("Districts with the most alerts {0} months ahead", [12, 36, 60][hz])) + '</p></div><a class="chip-btn" href="' + url("warnings", { h: [12, 36, 60][hz] }) + '">' + t("Open") + "</a></div>" +
        (alertRows.length ? table([["District"], ["State"], ["Shortage", "num"], ["Oversupply", "num"]], alertRows.map(function (r) { return '<tr class="click" data-district="' + r.c + '"><td>' + esc(r.n) + "</td><td>" + esc(r.st) + '</td><td class="num">' + r.s + '</td><td class="num">' + r.o + "</td></tr>"; })) : '<p class="note">' + t("No alerts for these filters.") + "</p>") +
        '<p class="note">' + t("An alert marks a district-trade in the top or bottom tenth of its trade for forecast vacancies per seeker.") + "</p></section></div>";
      var box = $("#mapsvg", view); box.style.cssText = "position:absolute;inset:0";
      drawMap(box, M, rows, k, p, { h: h });
      $("#map-sr", view).textContent = tf("{0}: highest {1} ({2}), lowest {3} ({4}).", mapName(k), srt[0].d.n, mapFmt(k, srt[0].val), srt[srt.length - 1].d.n, mapFmt(k, srt[srt.length - 1].val));
      $$("[data-st]", view).forEach(function (b) { b.addEventListener("click", function () { go({ state: b.dataset.st, district: "" }); }); });
      var clr = $("[data-clear]", view); if (clr) clr.addEventListener("click", function () { go({ district: "" }); });
      bindSeg(view); bindRows(view);
      cur.csv = { name: fname("map_" + k + "_" + h), head: ["district_lgd", "district", "state", "sector", "measure", "months_ahead", "now", "forecast", "change_pct"], rows: scoped.map(function (r) { return [r.d.c, r.d.n, r.d.s, p.sector || "all", k, h, +r.now.toFixed(2), +r.fc.toFixed(2), k === "D" ? "" : +r.val.toFixed(2)]; }) };
    });
  };
  function alertsScope(p, hz) {
    return window.DASH4_ALERTS.rows.filter(function (a) { var tr = TRADES[a[4]]; return a[1] === hz && (!p.state || STATES[a[2]] === p.state) && (!p.trade || tr.c === p.trade) && (!p.sector || tr.s === p.sector) && (!p.district || String(a[3]) === String(p.district)); });
  }
  var addM = function (ym, n) { var q = ym.split("-"), i = (+q[0]) * 12 + (+q[1] - 1) + n; return Math.floor(i / 12) + "-" + ("0" + ((i % 12) + 1)).slice(-2); };

  /* ---------- frame: filters, sidebar, router ---------- */
  function renderFilters(p) {
    var fs = $("#f-sector"), ft = $("#f-trade"), fa = $("#f-state"), fd = $("#f-district");
    fs.innerHTML = '<option value="">' + t("All sectors") + "</option>" + SECTORS.map(function (s) { return '<option value="' + esc(s) + '">' + esc(t(s)) + "</option>"; }).join(""); fs.value = p.sector || "";
    ft.innerHTML = '<option value="">' + t("All trades") + "</option>" + TRADES.filter(function (x) { return !p.sector || x.s === p.sector; }).map(function (x) { return '<option value="' + x.c + '">' + esc(x.n) + (p.sector ? "" : " (" + x.c + ")") + "</option>"; }).join(""); ft.value = p.trade || "";
    fa.innerHTML = '<option value="">' + t("All states") + "</option>" + STATES.map(function (s) { return '<option value="' + esc(s) + '">' + esc(s) + "</option>"; }).join(""); fa.value = p.state || "";
    fd.innerHTML = '<option value="">' + t("All districts") + "</option>" + DLIST.filter(function (d) { return !p.state || d.s === p.state; }).map(function (d) { return '<option value="' + d.c + '">' + esc(d.n) + (p.state ? "" : " (" + d.s + ")") + "</option>"; }).join(""); fd.value = p.district || "";
  }
  function applyStatic() { $$("[data-t]").forEach(function (e) { e.textContent = t(e.dataset.t); }); $("#lang-label").textContent = LANG === "hi" ? "EN" : "हिं"; $("#tb-origin").textContent = t("Forecast from") + " " + ml(M.origin); $("#foot-origin").textContent = ml(M.origin); }
  /* the rows that filter when clicked are reachable and operable from the keyboard: Tab to a row, Enter or Space to choose it */
  function keyboardRows(node) {
    $$("tr.click", node).forEach(function (tr) {
      tr.tabIndex = 0; tr.setAttribute("title", t("Press Enter to filter"));
      tr.addEventListener("keydown", function (e) { if (e.key === "Enter" || e.key === " ") { e.preventDefault(); tr.click(); } });
    });
  }
  var token = 0;
  function route() {
    var r = parse(), my = ++token; cur.page = r.page; cur.p = r.p; cur.csv = null;
    var meta = PAGES[r.page]; $("#page-title").textContent = t(meta[0]); $("#page-sub").textContent = t(meta[1]); document.title = t(meta[0]) + " | KaushalSetu";
    $$("#nav a").forEach(function (a) { a.setAttribute("aria-current", a.dataset.page === r.page ? "page" : "false"); a.href = url(a.dataset.page, {}); });
    renderFilters(r.p); localise($("#filters"));
    var view = $("#view"); hideTip(); view.innerHTML = '<p class="loading">' + t("Loading…") + "</p>";
    Promise.resolve().then(function () { return render[r.page](r.p, view); }).then(function () { if (my === token) { keyboardRows(view); localise(view); $("#main").scrollTop = 0; } }).catch(function (e) { if (my === token) loadingErr(view, e); });
    document.body.classList.remove("sb-open"); $("#scrim").hidden = true;
  }
  function init() {
    applyStatic();
    ["sector", "trade", "state", "district"].forEach(function (k) { $("#f-" + k).addEventListener("change", function (e) { var o = {}; o[k] = e.target.value; if (k === "state") o.district = ""; if (k === "sector") o.trade = ""; go(o); }); });
    $("#f-reset").addEventListener("click", function () { go({ sector: "", trade: "", state: "", district: "" }); });
    $("#f-csv").addEventListener("click", function () { if (cur.csv) downloadCsv(cur.csv.name, cur.csv.head, cur.csv.rows); });
    $("#f-json").addEventListener("click", function () { if (cur.csv) downloadJson(cur.csv.name, cur.csv.head, cur.csv.rows); });
    var tog = $("#sb-toggle"), small = function () { return window.matchMedia("(max-width: 900px)").matches; };
    tog.addEventListener("click", function () {
      if (small()) { var o = document.body.classList.toggle("sb-open"); $("#scrim").hidden = !o; tog.setAttribute("aria-expanded", o); return; }
      var c = root.classList.toggle("sb-collapsed"); tog.setAttribute("aria-expanded", !c);
      try { var d = JSON.parse(localStorage.getItem("lmis-dash") || "{}"); d.collapsed = c; localStorage.setItem("lmis-dash", JSON.stringify(d)); } catch (e) { /* the choice lasts for this visit */ }
    });
    $("#scrim").addEventListener("click", function () { document.body.classList.remove("sb-open"); $("#scrim").hidden = true; });
    $("#theme-toggle").addEventListener("click", function () {
      var th = root.dataset.theme === "dark" ? "light" : "dark"; root.dataset.theme = th;
      try { var s = JSON.parse(localStorage.getItem("lmis-display") || "{}"); s.theme = th; localStorage.setItem("lmis-display", JSON.stringify(s)); } catch (e) { /* ignore */ }
      route();
    });
    $("#lang-toggle").addEventListener("click", function () {
      LANG = LANG === "hi" ? "en" : "hi"; root.dataset.lang = LANG; root.lang = LANG;
      try { var s = JSON.parse(localStorage.getItem("lmis-display") || "{}"); s.lang = LANG; localStorage.setItem("lmis-display", JSON.stringify(s)); } catch (e) { /* ignore */ }
      applyStatic(); route();
    });
    window.addEventListener("hashchange", route);
    route();
  }
  init();
})();
