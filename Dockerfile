FROM python:3.9

WORKDIR /
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt
RUN apt-get update && apt-get install -y curl

COPY . .

CMD [ "python", "./main.py", "import nltk; nltk.download('stopwords'); nltk.download('punkt')"]