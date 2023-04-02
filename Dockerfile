FROM python:3.9

WORKDIR /
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt
RUN python -m nltk.downloader punkt && python -m nltk.downloader stopwords

COPY . .

CMD [ "python", "./main.py", "import nltk; nltk.download('stopwords'); nltk.download('punkt')"]