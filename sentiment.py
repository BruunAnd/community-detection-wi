import re

import numpy as np
from loguru import logger
from collections import Counter

from sklearn.feature_extraction.text import CountVectorizer, TfidfTransformer
from sklearn.naive_bayes import MultinomialNB
from sklearn import metrics

import random

from sklearn.pipeline import Pipeline

from friendships import import_data


def _class_from_score(score):
    score_classes = {
        '1.0': 0,
        '2.0': 0,
        '3.0': None,
        '4.0': 1,
        '5.0': 1,
    }

    return score_classes[score]


def load_sentiment_data(file_name):
    x, y = [], []

    current_class = None

    with open(file_name, 'r') as file:
        for line in file.readlines():
            split = [x.strip() for x in line.split(':')]

            if split[0] == 'review/score':
                current_class = _class_from_score(split[1])
            elif split[0] == 'review/text' and current_class is not None:
                x.append(split[1])
                y.append(current_class)

                current_class = None

    return x, y


def shuffle_lists(*ls):
    zipped = list(zip(*ls))
    random.shuffle(zipped)
    return zip(*zipped)


def _undersample(x, y, random_state=0):
    random.seed = random_state

    x, y = shuffle_lists(x, y)

    # Get min class count
    counter = Counter(y)
    min_count = min(counter.values())

    # Undersample by taking min_count items from every class
    ret_x, ret_y = [], []
    for cls in counter.keys():
        cls_idx = set([idx for idx, val in enumerate(y) if val == cls][:min_count])

        ret_x.extend([val for idx, val in enumerate(x) if idx in cls_idx])
        ret_y.extend([cls] * min_count)

    return shuffle_lists(ret_x, ret_y)


def _preprocess(corpus):
    """ Remove HTML and perform negation. """
    punctuation = re.compile('[.:;!?]')
    negatives = {'don\'t', 'never', 'nothing', 'nowhere', 'noone', 'none', 'not', 'no', 'hasn\'t', 'hadn\'t', 'can\'t',
                 'couldn\'t', 'shouldn\'t', 'won\'t', 'wouldn\'t', 'don\'t', 'doesn\'t', 'didn\'t', 'isn\'t', 'aren\'t',
                 'ain\'t'}

    ret_corpus = []

    for text in corpus:
        text = text.lower().split()  # Remove HTML and split newlines
        new_text = []

        negate = False
        for word in text:
            new_text.append(word if not negate else f'neg_{word}')

            if word in negatives:
                negate = True
            elif punctuation.findall(word):
                negate = False

        ret_corpus.append(' '.join(new_text))

    return ret_corpus


def _train_model():
    classes = {0, 1}
    train_x, train_y = load_sentiment_data('SentimentTrainingData.txt')
    test_x, test_y = load_sentiment_data('SentimentTestingData.txt')
    logger.debug('Loaded training and testing data')

    # Undersample
    train_x, train_y = _undersample(train_x, train_y)
    test_x, test_y = _undersample(test_x, test_y)

    # Perform negation on the input sets
    train_x = _preprocess(train_x)
    test_x = _preprocess(test_x)

    # Some statistics on the data
    logger.debug(f'Training class distribution: {Counter(train_y)}')
    logger.debug(f'Testing class distribution: {Counter(test_y)}')

    # Construct classifier as a pipeline
    sent_classifier = Pipeline([
        ('vectorizer', CountVectorizer()),
        ('term-frequencyf', TfidfTransformer(use_idf=False)),
        ('classifier', MultinomialNB())
    ])
    sent_classifier.fit(train_x, train_y)
    logger.debug('Model fitted to data')

    # Evaluate
    predicted = sent_classifier.predict(test_x)
    logger.info(f'Accuracy: {np.mean(predicted == test_y) * 100}%')
    logger.info(metrics.classification_report(test_y, predicted))

    return sent_classifier


def get_sentiments(reviews):
    sentiments = {}

    model = _train_model()
    for friend, review in reviews.items():
        sentiments[friend] = model.predict([review])[0]

    return sentiments