"""Texts for spike S-8.

Written by Kiro and not checked by native speakers: they test rendering and OCR, not translation
quality. The "message" block is the same short message in each script. The "stress" block
collects clusters that come out visibly wrong when shaping fails: conjuncts, reph, two-part
vowel signs, chillu letters, Arabic joining and ligatures, and non-Latin digits.
"""
from __future__ import annotations

from dataclasses import dataclass

BLOCK_KEYS = ("title", "message", "stress")

# English source page. "Zqxwv" marks every source block, so a leftover is easy to detect.
SOURCE = {
    "title": "Meeting update Zqxwvone",
    "message": (
        "Hey, quick update: the meeting has moved to tomorrow at 10 AM because the client is "
        "travelling. Please bring the updated report and the budget sheet. If you can't make it, "
        "tell me by tonight so I can reschedule. Thanks, and don't worry, everything will be fine. "
        "Zqxwvtwo"
    ),
    "stress": (
        "This paragraph is replaced with letter combinations that come out wrong when shaping "
        "fails. Zqxwvthree"
    ),
}


@dataclass(frozen=True)
class Target:
    key: str
    label: str
    lang: str  # BCP 47 language for the HTML lang attribute and HarfBuzz
    font: str  # file name in assets/fonts
    ocr_lang: str  # Tesseract language code
    title: str
    message: str
    stress: str
    rtl: bool = False
    line_height: float = 1.45

    def text(self, block: str) -> str:
        return {"title": self.title, "message": self.message, "stress": self.stress}[block]


TARGETS: tuple[Target, ...] = (
    Target(
        key="latin",
        label="Latin (Roman-script hybrids)",
        lang="en",
        font="NotoSans-Regular.ttf",
        ocr_lang="eng",
        title="Meeting update",
        message=(
            "Hey, quick update: meeting kal subah 10 baje shift ho gayi hai kyunki client travel "
            "kar raha hai. Please updated report aur budget sheet le aana. Agar tum nahi aa sakte "
            "toh aaj raat tak bata dena taaki main reschedule kar sakun. Thanks, aur tension mat "
            "lo, sab theek ho jayega."
        ),
        stress="Café, déjà vu, señor, garçon, naïve, São Paulo, Kraków, Ærø – 10:00, 50 %",
    ),
    Target(
        key="deva",
        label="Devanagari (Hindi, Hinglish)",
        lang="hi",
        font="NotoSansDevanagari-Regular.ttf",
        ocr_lang="hin",
        title="मीटिंग अपडेट",
        message=(
            "नमस्ते, एक छोटी सी जानकारी: मीटिंग कल सुबह 10 बजे कर दी गई है क्योंकि क्लाइंट यात्रा "
            "कर रहे हैं। कृपया अपडेट की गई रिपोर्ट और बजट शीट लेकर आइए। अगर आप नहीं आ सकते तो आज "
            "रात तक बता दीजिए ताकि मैं समय बदल सकूँ। धन्यवाद, और चिंता मत कीजिए, सब ठीक हो जाएगा।"
        ),
        stress="क्षत्रिय ज्ञान श्रीमान् द्वार अर्क कृष्ण हृदय त्र्यंबक प्रश्न स्त्री बुद्ध ब्रह्म क़िला ज़रूर ॐ",
    ),
    Target(
        key="beng",
        label="Bengali (Banglish)",
        lang="bn",
        font="NotoSansBengali-Regular.ttf",
        ocr_lang="ben",
        title="মিটিং আপডেট",
        message=(
            "হাই, একটা ছোট আপডেট: ক্লায়েন্ট ভ্রমণে আছেন বলে মিটিংটা কাল সকাল ১০টায় সরানো হয়েছে। "
            "দয়া করে আপডেট করা রিপোর্ট আর বাজেট শিট নিয়ে আসবেন। আসতে না পারলে আজ রাতের মধ্যে "
            "জানাবেন, যাতে আমি সময়টা বদলাতে পারি। ধন্যবাদ, চিন্তা করবেন না, সব ঠিক হয়ে যাবে।"
        ),
        stress="ক্ষমা জ্ঞান শ্রী দ্বার কর্ম কৃষ্ণ রূপ স্ত্রী শক্তি চন্দ্র ময়ূর বড় ৎ",
    ),
    Target(
        key="mlym",
        label="Malayalam (Manglish)",
        lang="ml",
        font="NotoSansMalayalam-Regular.ttf",
        ocr_lang="mal",
        title="മീറ്റിംഗ് അപ്ഡേറ്റ്",
        message=(
            "ഹായ്, ഒരു ചെറിയ അപ്ഡേറ്റ്: ക്ലയന്റ് യാത്രയിലായതിനാൽ മീറ്റിംഗ് നാളെ രാവിലെ 10 "
            "മണിയിലേക്ക് മാറ്റി. ദയവായി പുതുക്കിയ റിപ്പോർട്ടും ബജറ്റ് ഷീറ്റും കൊണ്ടുവരിക. വരാൻ "
            "കഴിയില്ലെങ്കിൽ ഇന്ന് രാത്രിക്ക് മുമ്പ് പറയുക, ഞാൻ സമയം മാറ്റാം. നന്ദി, വിഷമിക്കേണ്ട, "
            "എല്ലാം ശരിയാകും."
        ),
        stress="ക്ഷമ ജ്ഞാനം ശ്രീ കർമ്മം എന്റെ അവൻ അവർ കാൽ അവൾ കൺ സ്ത്രീ ബന്ധം അക്ക കണ്ടു വാങ്ങൾ",
    ),
    Target(
        key="taml",
        label="Tamil (not a launch Style)",
        lang="ta",
        font="NotoSansTamil-Regular.ttf",
        ocr_lang="tam",
        title="கூட்டம் பற்றிய தகவல்",
        message=(
            "வணக்கம், ஒரு சிறிய தகவல்: வாடிக்கையாளர் பயணத்தில் இருப்பதால் கூட்டம் நாளை காலை 10 "
            "மணிக்கு மாற்றப்பட்டுள்ளது. தயவுசெய்து புதுப்பிக்கப்பட்ட அறிக்கையையும் பட்ஜெட் தாளையும் "
            "கொண்டு வாருங்கள். உங்களால் வர முடியாவிட்டால் இன்று இரவுக்குள் சொல்லுங்கள், நான் "
            "நேரத்தை மாற்றுகிறேன். நன்றி, கவலைப்பட வேண்டாம், எல்லாம் சரியாகிவிடும்."
        ),
        stress="க்ஷேமம் ஸ்ரீ கொண்டு கோவில் கௌரவம் விஞ்ஞானம் வெற்றி பாட்டு ஶ்ரீ",
    ),
    Target(
        key="telu",
        label="Telugu (not a launch Style)",
        lang="te",
        font="NotoSansTelugu-Regular.ttf",
        ocr_lang="tel",
        title="సమావేశం సమాచారం",
        message=(
            "నమస్తే, ఒక చిన్న సమాచారం: క్లయింట్ ప్రయాణంలో ఉన్నందున సమావేశం రేపు ఉదయం 10 గంటలకు "
            "మార్చబడింది. దయచేసి నవీకరించిన నివేదిక మరియు బడ్జెట్ షీట్ తీసుకురండి. మీరు రాలేకపోతే "
            "ఈ రాత్రిలోగా చెప్పండి, నేను సమయం మారుస్తాను. ధన్యవాదాలు, చింతించకండి, అంతా సరిపోతుంది."
        ),
        stress="క్షమ జ్ఞానం శ్రీ స్త్రీ కర్మ ద్వారం ప్రశ్న శక్తి ఆత్మ",
    ),
    Target(
        key="urdu",
        label="Urdu, Nastaliq (Roman Urdu)",
        lang="ur",
        font="NotoNastaliqUrdu-Regular.ttf",
        ocr_lang="urd",
        title="میٹنگ کی اطلاع",
        message=(
            "ہیلو، ایک مختصر اطلاع: میٹنگ کل صبح 10 بجے کر دی گئی ہے کیونکہ کلائنٹ سفر میں ہیں۔ "
            "براہ کرم اپ ڈیٹ شدہ رپورٹ اور بجٹ شیٹ ساتھ لائیں۔ اگر آپ نہیں آ سکتے تو آج رات تک بتا "
            "دیں تاکہ میں وقت تبدیل کر سکوں۔ شکریہ، اور فکر نہ کریں، سب ٹھیک ہو جائے گا۔"
        ),
        stress="یہ تحریر نستعلیق خط میں ہے۔ پاکستان، لاہور، کراچی، ۱۲۳۴۵، ’’اردو‘‘",
        rtl=True,
        line_height=2.2,
    ),
    Target(
        key="arab",
        label="Arabic, Naskh (Arabizi's Arabic counterpart)",
        lang="ar",
        font="NotoNaskhArabic-Regular.ttf",
        ocr_lang="ara",
        title="تحديث الاجتماع",
        message=(
            "مرحبًا، تحديث سريع: تم تأجيل الاجتماع إلى الغد الساعة 10 صباحًا لأن العميل مسافر. "
            "من فضلك أحضر التقرير المحدّث وورقة الميزانية. إذا لم تتمكن من الحضور، أخبرني قبل "
            "الليلة حتى أغيّر الموعد. شكرًا، ولا تقلق، كل شيء سيكون على ما يرام."
        ),
        stress="لا إله إلا الله، السلام عليكم، مستشفى، ١٢٣٤٥، «عربي»",
        rtl=True,
        line_height=1.8,
    ),
)
