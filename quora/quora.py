# coding=utf-8

from bs4 import BeautifulSoup
import re
import requests
import sys
import traceback

####################################################################
# Helpers
####################################################################
def try_cast_int(s):
    """ (str) -> int
    Look for digits in the given string and convert them to the required number.
    ('2 upvotes') -> 2
    ('2.2k upvotes') -> 2200
    """
    try:
        pattern = re.compile(r'([0-9]+(\.[0-9]+)*[ ]*[Kk])|([0-9]+)')
        raw_result = re.search(pattern, s).groups()
        if raw_result[2] != None:
            return int(raw_result[2])
        elif raw_result[1] == None:
            raw_result = re.search(r'([0-9]+)', raw_result[0])
            return int(raw_result.groups()[0]) * 1000
        else:
            raw_result = re.search(r'([0-9]+)\.([0-9]+)', raw_result[0]).groups()
            return int(raw_result[0]) * 1000 + int(raw_result[1]) * 100
    except:
        return s


def get_question_link(soup):
    """ (soup) -> str
    Returns the link at which the question can is present.
    """
    question_link = soup.find('a', attrs={'class': 'question_link'})
    return 'https://www.quora.com' + question_link.get('href')


def get_author(soup):
    """ (soup) -> str
    Returns the name of the author
    """
    author = soup.find('a', attrs={'class': 'user'}).contents[0]
    return author


def extract_username(username):
    """ (soup) -> str
    Returns the username of the author
    """
    if 'https://www.quora.com/' not in username['href']:
        return username['href'][1:]
    else:
        username = re.search("[a-zA-Z-\-]*\-+[a-zA-Z]*-?[0-9]*$", username['href'])
        if username is not None:
            return username.group(0)
        else:
            return None


def get_with_agent(url):
    """ Performs get method adding user agent information in header
    """
    user_agent = {
        'User-agent': ' Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:31.0) Gecko/20100101 Firefox/31.0',
    }
    return requests.get(url, headers=user_agent)


####################################################################
# API
####################################################################
class Quora:
    """
    The class that contains functions required to fetch details of questions and answers.
    """

    @staticmethod
    def get_one_answer(question, author=None):
        """ (str [, str]) -> dict
        Fetches one answer and it's details.
        """
        if author is None:  # For short URL's
            if re.match('https', question):  # question like https://qr.ae/znrZ3
                soup = BeautifulSoup(requests.get(question).text)
            else:  # question like znrZ3
                soup = BeautifulSoup(requests.get('https://qr.ae/' + question).text)
        else:
            soup = BeautifulSoup(requests.get('https://www.quora.com/' + question + '/answer/' + author).text)
        return Quora.scrape_one_answer(soup)

    @staticmethod
    def scrape_one_answer(soup):
        """ (soup) -> dict
        Scrapes the soup object to get details of an answer.
        """
        # print 'scrape_one_answer::'
        try:

            answer = soup.find('div', attrs={'class': 'inline_editor_content'}).text
            question_link = get_question_link(soup)
            author = get_author(soup)
            views = soup.find('div', attrs={'class': 'AnswerHeader ContentHeader'}).text
            try:
                want_answers = soup.find('span', attrs={'class': 'count'}).string
            except:
                want_answers = 0
            try:
                upvote_count = soup.find('a', attrs={'class': 'AnswerUpvotesStatsRow StatsRow'}).text
                if upvote_count is None:
                    upvote_count = 0
            except:
                upvote_count = 0

            try:
                comment_count = soup.find('a', attrs={'class': 'view_comments'})
                # print 'comment_count:', comment_count
                # Only the comments directly on the answer are considered. Comments on comments are ignored.
            except Exception as e:
                print str(e)
                comment_count = 0

            answer_stats = map(try_cast_int, [views, want_answers, upvote_count, comment_count])

            answer_dict = {'views': answer_stats[0],
                           'want_answers': answer_stats[1],
                           'upvote_count': answer_stats[2],
                           'comment_count': answer_stats[3],
                           'answer': answer,
                           'question_link': question_link,
                           'author': author
                           }
            return answer_dict
        except Exception as e:
            # print str(e)
            traceback.print_exc(file=sys.stdout)
            return {}

    @staticmethod
    def get_latest_answers(question):
        """ (str) -> list
        Takes the title of one question and returns the latest answers to that question.
        """
        soup = BeautifulSoup(requests.get('https://www.quora.com/' + question + '/log').text)
        authors = Quora.scrape_latest_answers(soup)
        return [Quora.get_one_answer(question, author) for author in authors]

    @staticmethod
    def scrape_latest_answers(soup):
        """ (soup) -> list
        Returns a list with usernames of those who have recently answered the question.
        """
        try:
            authors = []
            clean_logs = []
            raw_logs = soup.find_all('div', attrs={'class': 'feed_item_activity'})

            for entry in raw_logs:
                if 'Answer added by' in entry.next:
                    username = entry.find('a', attrs={'class': 'user'})
                    if username is not None:
                        username = extract_username(username)
                        if username not in authors:
                            authors.append(username)
            # print authors
            return authors
        except Exception as e:
            print str(e)
            return []

    @staticmethod
    def get_question_stats(question):
        """ (soup) -> dict
        Returns details about the question.
        """
        soup = BeautifulSoup(requests.get('https://www.quora.com/' + question).text)
        return Quora.scrape_question_stats(soup)

    @staticmethod
    def scrape_question_stats(soup):
        """ (soup) -> dict
        Scrapes the soup object to get details of a question.
        """

        try:
            raw_topics = soup.find('div', attrs={'class': 'question_page_topic_section QuestionTopicsSidebar'}
                                   ).find_all('span', attrs={'class': 'TopicNameSpan TopicName'})
            topics = []
            for topic in raw_topics:
                topics.append(topic.string)

            # want_answers = soup.find('span', attrs={'class' : 'count'}).string
            want_answers = 0
            try:
                answer_count = soup.find('div', attrs={'class': 'answer_count'}).next.split()[0]
            except:
                answer_count = 0
            question_text = soup.find('div', attrs={'class': 'QuestionArea'}).find('h1').contents[1].text
            question_details = soup.find('div', attrs={'class': 'question_details_text'})
            answer_wiki = soup.find('div', attrs={'class': 'AnswerWikiArea'}).find('div')
            # related_questions = [str(question.contents[1]) for question in
            #                      soup.find_all('span', attrs={'class': 'question_text'})]
            related_questions = []
            for question in soup.find_all('span', attrs={'class': 'question_text'}):
                try:
                    question_text = str(question.contents[1])
                    related_questions.append(question_text)
                except:
                    print 'Skipping question: ', question.contents[0]
            last_asked = soup.find('div', attrs={'class': 'QuestionLastAskedTime'}).text

            question_dict = {'want_answers': try_cast_int(want_answers),
                             'answer_count': try_cast_int(answer_count),
                             'question_text': question_text,
                             'topics': topics,
                             'question_details': str(question_details),
                             'answer_wiki': str(answer_wiki),
                             'related_questions': related_questions,
                             'last_asked': last_asked.replace('Last asked: ', '')
                             }
            return question_dict
        except Exception as e:
            traceback.print_exc(file=sys.stdout)
            return {}

    @staticmethod
    def get_snippets_by_query(query):
        """Obtains snippets returned by the search

        :param query: Query for quora search e.g. 'isis'
        :type query: str.
        :returns:  list<str> - the list of snippets found for particular query.
        """
        url = 'https://www.quora.com/search?q=%s' % query

        soup = BeautifulSoup(get_with_agent(url).text)

        # Getting text snippets from 'search_result_snippet' span
        search_result_snippets = [snippet.text for snippet in soup.find_all(
            'span',
            attrs={'class': 'search_result_snippet'}
        )]

        return search_result_snippets

    ### Legacy API
    @staticmethod
    def get_user_stats(u):
        """ (str) -> dict
        Depreciated. Use the User class.
        """
        from user import User
        return User.get_user_stats(u)

    @staticmethod
    def get_user_activity(u):
        """ (str) -> dict
        Depreciated. Use the User class.
        """
        from user import User
        return User.get_user_activity(u)

    @staticmethod
    def get_activity(u):
        """ (str) -> dict
        Depreciated. Use the User class.
        """
        from user import User
        return User.get_activity(u)
