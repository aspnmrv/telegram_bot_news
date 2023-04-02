import pymorphy2
import re
import nltk
import string

from string import punctuation
from nltk.corpus import stopwords
from nltk.tokenize import word_tokenize
from db import get_user_keywords_db


async def prepare_data(messages):
    """"""
    stop = stopwords.words("russian")
    stop = stop + ["в", "который", "под", "по", "на", "при", "о", "к", "также", "это", "такой", "кроме",
                   "ру", "свой", "лента", "каждый", "другой", "свой", "быть", "являться",
                   "во", "над", "изза", "их", "но", "из", "со", 'около', 'кто-то', 'очень', 'видимо', 'ко', 'лентару',
                   'риа', 'новости', "другой", "который", "такой", "свои", "сам", "тот", "этот", "однако",
                                        "например", "это", "один", "являться"]
    punkt = [p for p in punctuation] + ["`", "``", "''", "'", "»", "«", "\\", "-", "–", "+", "=", "*", "&", "%",
                                        "в", "который", "под", "по", "на", "при", "о", "к", "который", "также", "это",
                                        "такой", "кроме",
                                        "ру", "свой", "лента", "каждый", '—', 'который']
    rus_lemmatizer = pymorphy2.MorphAnalyzer(lang="ru")
    clean_html_tags = re.compile("<.*?>")
    result = list()

    def remove_emoji(text):
        """"""
        emoji_pattern = re.compile("["
                                   u"\U0001F600-\U0001F64F"  # emoticons
                                   u"\U0001F300-\U0001F5FF"  # symbols & pictographs
                                   u"\U0001F680-\U0001F6FF"  # transport & map symbols
                                   u"\U0001F1E0-\U0001F1FF"  # flags (iOS)
                                   u"\U00002702-\U000027B0"
                                   u"\U000024C2-\U0001F251"
                                   "]+", flags=re.UNICODE)
        return emoji_pattern.sub(r'', text)

    def clean_text(text):
        """"""
        text = str(text).lower()
        text = re.sub('\[.*?\]', '', text)
        text = re.sub('https?://\S+|www\.\S+', '', text)
        text = re.sub('<.*?>+', '', text)
        text = re.sub('[%s]' % re.escape(string.punctuation), '', text)
        text = re.sub('\n', '', text)
        text = re.sub('\w*\d\w*', '', text)
        return text

    def clean_html(raw_html):
        """"""
        cleantext = re.sub(clean_html_tags, '', raw_html)
        return cleantext

    def tokenize(sent):
        sent = word_tokenize(sent)
        return [word for word in sent if word not in stop and word not in punkt]

    def lemmatize(sent):
        return " ".join([rus_lemmatizer.normal_forms(word)[0] for word in sent])

    def preprocess_sent(sent):
        try:
            return lemmatize(tokenize(remove_emoji(clean_html(clean_text(str(sent))))))
        except:
            return ''

    for message in messages:
        result.append(preprocess_sent(message))

    return result


async def get_pred_labels(preds):
    """"""
    labels = list()
    for pred in preds[0]:
        labels.append(pred[0].split("__label__")[1])
    return labels


async def check_keywords(user_id: int, text: str):
    """"""
    user_keywords = await get_user_keywords_db(user_id)

    if any(word in text for word in user_keywords):
        return True
    else:
        return False
