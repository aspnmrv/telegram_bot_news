import sys
import os

sys.path.append(os.path.dirname(__file__))
sys.path.insert(1, os.path.realpath(os.path.pardir))

import pymorphy2
import re
import nltk
import string

from string import punctuation
from nltk.corpus import stopwords
from nltk.tokenize import word_tokenize
from app.db.db import get_user_keywords_db
from collections import OrderedDict
from app.globals import ADDITIONAL_STOP_WORDS_RU, ADDITIONAL_PUNCT_VALUES


async def prepare_data(messages: list) -> list:
    """"""
    stop_words = stopwords.words("russian")
    stop_words = stop_words + ADDITIONAL_STOP_WORDS_RU

    punkt = [p for p in punctuation] + ADDITIONAL_PUNCT_VALUES

    rus_lemmatizer = pymorphy2.MorphAnalyzer(lang="ru")
    clean_html_tags = re.compile("<.*?>")
    result = list()

    def remove_emoji(text: str) -> str:
        """Removes emoji from text"""

        emoji_pattern = re.compile("["
                                   u"\U0001F600-\U0001F64F"  # emoticons
                                   u"\U0001F300-\U0001F5FF"  # symbols & pictographs
                                   u"\U0001F680-\U0001F6FF"  # transport & map symbols
                                   u"\U0001F1E0-\U0001F1FF"  # flags (iOS)
                                   u"\U00002702-\U000027B0"
                                   u"\U000024C2-\U0001F251"
                                   "]+", flags=re.UNICODE)

        return emoji_pattern.sub(r'', text)

    def clean_text(text: str) -> str:
        """Removes html tags from text"""

        text = str(text).lower()
        text = re.sub('\[.*?\]', '', text)
        text = re.sub('https?://\S+|www\.\S+', '', text)
        text = re.sub('<.*?>+', '', text)
        text = re.sub('[%s]' % re.escape(string.punctuation), '', text)
        text = re.sub('\n', '', text)
        text = re.sub('\w*\d\w*', '', text)
        return text

    def clean_html(raw_html: str) -> str:
        """Removes html tags from text"""

        cleantext = re.sub(clean_html_tags, '', raw_html)
        return cleantext

    def tokenize(sent: str) -> list:
        """Text tokenization"""

        sent = word_tokenize(sent)

        return [word for word in sent if word not in stop_words and word not in punkt]

    def lemmatize(sent: list) -> str:
        """Text Lemmatization"""

        return " ".join([rus_lemmatizer.normal_forms(word)[0] for word in sent])

    def preprocess_sent(sent: str) -> str:
        """Cleaning, tokenization and lemmatization of text and casting"""

        try:
            return lemmatize(tokenize(remove_emoji(clean_html(clean_text(str(sent))))))
        except:
            return ""

    for message in messages:
        result.append(preprocess_sent(message))

    return result


async def get_pred_labels(preds: list) -> list:
    """Returns the model's predicted values in the correct format"""

    labels = list()

    for pred in preds:
        labels.append(pred[0].split("__label__")[1])

    return labels


async def check_keywords(user_id: int, text: str) -> bool:
    """Checks for the presence of keywords selected by the user in the text"""

    user_keywords = await get_user_keywords_db(user_id)

    if any(word.lower() in text for word in user_keywords):
        return True
    else:
        return False


async def remove_duplicate_text(text: str) -> str:
    """Removing chunks of the same text"""

    return "\n".join(list(OrderedDict.fromkeys(text.split("."))))
