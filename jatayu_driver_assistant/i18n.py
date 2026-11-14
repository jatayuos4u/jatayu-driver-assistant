TRANSLATIONS = {
'en': {
 'diag_intro':'Read-only findings based on observed driver bindings. These are not confirmed faults.', 'diag_empty':'Scan hardware to see diagnostic findings.', 'next_step':'Suggested next step', 'workspace':'WORKSPACE', 'side_info':'Read-only hardware diagnostics. Your system remains unchanged.', 'hero_badge':'●  HARDWARE INSIGHTS', 'hero_title':'Know your hardware.\nStay in control.', 'hero_desc':'Discover devices, review kernel drivers, and export a detailed report — safely.', 'recent_devices':'Detected hardware', 'view_all':'View all devices', 'devices_desc':'Explore detected hardware and inspect available driver information.', 'app':'Jatayu Driver Assistant', 'subtitle':'Understand your hardware', 'overview':'Overview', 'devices':'Devices', 'recommendations': 'Recommendations',
        'diagnostics':'Diagnostics', 'about':'About',
 'scan':'Scan hardware', 'export':'Export report', 'search':'Search devices…', 'all':'All', 'detected':'Devices detected',
 'drivers':'Drivers bound', 'review':'Needs review', 'unbound':'Unbound PCI', 'unknown':'Not determined', 'unbound_status':'No PCI driver bound', 'unknown_status':'Binding unknown', 'notice':'Basic Edition: read-only hardware information. No drivers will be installed or changed.',
 'category':'Category', 'device':'Device', 'driver':'Driver', 'status':'Status', 'details':'Device details',
 'language':'Language', 'ready':'Ready', 'scanning':'Scanning hardware…', 'saved':'Report saved',
 'no_devices':'No matching devices', 'about_text':'Version 0.1.3 Alpha. Read-only Linux hardware discovery for Debian 13 and KDE Plasma 6.',
 'disclaimer':'An unbound PCI device does not necessarily need a driver. USB and class devices may bind at other levels. Device functionality has not been fully tested.',
 'error':'Could not save report', 'choose':'Save hardware report', 'bound':'Driver loaded', 'detected_status':'Detected',
 'connected':'Connected', 'needs_review':'Needs review', 'none':'Not reported', 'total':'Total', 'binding_note':'Driver binding is not a hardware health test. This alpha does not install or repair drivers.',
},
'hi': {
 'diag_intro':'ड्राइवर की स्थिति पर आधारित जाँच। ये पुष्टि की गई खराबियाँ नहीं हैं।', 'diag_empty':'जाँच देखने के लिए हार्डवेयर स्कैन करें।', 'next_step':'अगला सुझाव', 'recommendations': 'सुझाव',
        'diagnostics':'जाँच',
 'workspace':'कार्यस्थल', 'side_info':'केवल हार्डवेयर की जानकारी। सिस्टम में कोई बदलाव नहीं होगा।', 'hero_badge':'●  हार्डवेयर जानकारी', 'hero_title':'अपने हार्डवेयर को जानें।', 'hero_desc':'उपकरण देखें, ड्राइवर की जानकारी पाएँ और सुरक्षित रिपोर्ट सहेजें।', 'recent_devices':'पहचाने गए उपकरण', 'view_all':'सभी उपकरण देखें', 'devices_desc':'हार्डवेयर और ड्राइवर की उपलब्ध जानकारी देखें।', 'app':'जटायु ड्राइवर असिस्टेंट', 'subtitle':'अपने हार्डवेयर को समझें', 'overview':'अवलोकन', 'devices':'उपकरण', 'diagnostics':'जाँच', 'about':'परिचय',
 'scan':'हार्डवेयर जाँचें', 'export':'रिपोर्ट सहेजें', 'search':'उपकरण खोजें…', 'all':'सभी', 'detected':'मिले हुए उपकरण',
 'drivers':'सक्रिय ड्राइवर', 'review':'जाँच आवश्यक', 'unbound':'PCI ड्राइवर नहीं जुड़ा', 'unknown':'स्थिति स्पष्ट नहीं', 'unbound_status':'PCI ड्राइवर नहीं जुड़ा', 'unknown_status':'ड्राइवर की स्थिति अज्ञात', 'notice':'बेसिक संस्करण: केवल हार्डवेयर की जानकारी। कोई ड्राइवर इंस्टॉल या बदला नहीं जाएगा।',
 'category':'श्रेणी', 'device':'उपकरण', 'driver':'ड्राइवर', 'status':'स्थिति', 'details':'उपकरण की जानकारी',
 'language':'भाषा', 'ready':'तैयार', 'scanning':'हार्डवेयर जाँच जारी है…', 'saved':'रिपोर्ट सहेजी गई',
 'no_devices':'कोई मेल खाता उपकरण नहीं', 'about_text':'संस्करण 0.1.3 अल्फ़ा। Debian 13 और KDE Plasma 6 के लिए केवल-पढ़ने वाला हार्डवेयर निरीक्षण।',
 'disclaimer':'PCI ड्राइवर न जुड़ना हमेशा खराबी नहीं है। USB उपकरणों के ड्राइवर अलग स्तर पर हो सकते हैं। उपकरण की पूरी कार्यक्षमता की जाँच नहीं हुई है।',
 'error':'रिपोर्ट सहेजी नहीं जा सकी', 'choose':'हार्डवेयर रिपोर्ट सहेजें', 'bound':'ड्राइवर लोड है', 'detected_status':'मिला',
 'connected':'कनेक्ट है', 'needs_review':'जाँच आवश्यक', 'none':'जानकारी उपलब्ध नहीं', 'total':'कुल', 'binding_note':'ड्राइवर जुड़ा होना हार्डवेयर के सही काम करने का प्रमाण नहीं है। यह संस्करण ड्राइवर इंस्टॉल या ठीक नहीं करता।',
}}

def tr(language, key):
    return TRANSLATIONS.get(language, TRANSLATIONS['en']).get(key, key)
