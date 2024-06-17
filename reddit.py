import prawcore.exceptions
from settings import CONFIG_FILE_PATH
import re
from praw.models import MoreComments, Subreddit, ListingGenerator
from typing import Iterator, Any, AnyStr, Union, Dict, List


class RedditContent:
    """
    Authenticates to Reddit,
    Search for subreddits, get threads and comments.

    """
    def __init__(self,
                 max_comment_length=2000, min_comment_length=100, min_comment_score=10,
                 thread_limit=20, include_nsfw:bool=False, config_file_path:str=None,
                 sub_limit=100
                 ):

        """

        :param max_comment_length:
        :param min_comment_length:
        :param min_comment_score:
        :param thread_limit:
        :param include_nsfw:
        :param config_file_path:
        :param sub_limit:
        """
        self.config_file_path = CONFIG_FILE_PATH if config_file_path is None else config_file_path
        self.thread_limit = thread_limit
        self.sub_limit = sub_limit
        self.include_nsfw = include_nsfw

        ### Comment related parameters
        self.max_comment_length = max_comment_length
        self.min_comment_length = min_comment_length
        self.min_comment_score = min_comment_score

        ### Parameters to be used
        self.reddit = None
        self.subs:List[Subreddit]=None
        self.contents = {}
        self.controlled=False

    def process(self,
                get_popular:bool=True,
                search_query:str=None,
                exact_search:bool=False,
                fuzzy_search:bool=False,
                subreddits:List[AnyStr]=None
                ):
        ## Authenticate if not already authenticated
        if not self.reddit:
            self.authenticate()

        ## Run process pipeline
        if subreddits:
            from time import sleep
            for sub in subreddits:
                sleep(2)
                try:
                    self.pipe(query=sub, fuzzy=False, exact=True)
                except prawcore.exceptions.Forbidden as e:
                    print(f"Could not get the {sub} subreddit due to:\n{e}")
                    continue
        elif search_query:
            self.pipe(query=search_query, fuzzy=fuzzy_search, exact=exact_search)
        else:## default value -> gets popular subreddits
            self.pipe(query=None, fuzzy=False, exact=False)

        if not self.controlled:
            ##control the contents
            self.control_contents()

    def pipe(self, query, fuzzy, exact):
        self.get_subs(
            query=query,
            exact=exact,
            fuzzy=fuzzy
        )

        ## Get threads from subreddits
        self.update_content_subreddits()

        ##get threads and comments
        self.update_content_threads_comments()

    def get_subs(self,query:AnyStr, exact:bool=False, fuzzy:bool=False):
        """
        Calls the methods for popular or query related subreddits
        :param query:
        :param exact:
        :param fuzzy:
        :return:
        """
        ## Get query related subreddits if search query is provided
        ## default is to have popular subreddits

        if query is None:
            print("Getting the popular subreddits.")
            self.subs = self.get_popular_subreddits()
            return self.subs

        if fuzzy:
            print(f"Getting {query} related subreddits.")
            self.subs = self.search_subreddits(query)
            return self.subs

        print(f"Getting {query} subreddit.")
        self.subs = self.search_subreddits_by_name(query, exact=exact)
        return self.subs

    def search_subreddits(self, query:str):
        """
        Search for subreddits title and description by query
        :param query:
        :return:
        """
        return self.reddit.subreddits.search(query=query)

    def search_subreddits_by_name(self, query:str, exact:bool=False):
        return self.reddit.subreddits.search_by_name(query, exact=exact, include_nsfw=self.include_nsfw)

    def get_subreddits(self, subreddits:list|str)->Subreddit:
        ## https://praw.readthedocs.io/en/stable/code_overview/models/subreddit.html#praw.models.Subreddit
        if isinstance(subreddits, str):
            return self.reddit.subreddit(subreddits)
        return self.reddit.subreddit("+".join(subreddits))

    def get_subreddit_threads(self, subreddits:List[AnyStr])->Iterator[Any]:## subreddit object of the subreddits
        return self.get_subreddits(subreddits).hot(limit=self.thread_limit)

    def get_popular_subreddits(self):
        return self.reddit.subreddits.popular(limit=self.sub_limit)

    def update_content_subreddits(self):
        """
        Populates self.contents with subreddits
        :param subreddits:
        :return:
        """
        for sub in self.subs:
            r_url = sub.url.split("/")[2]
            self.contents.update({r_url: {
                "title": sub.title,
                "description": sub.description,
                "display_name": sub.display_name,
                "url": r_url,
                "contents": []
            }})

    def update_content_threads_comments(self, subreddit_names:List[str]=None):
        """
        Updates self.contents with threads and comments
        :return:
        """
        ##get display names for the subreddits
        subreddit_names = [sub["display_name"] for sub in self.contents.values()] if subreddit_names is None else subreddit_names
        threads_comments = self.get_subreddit_threads(subreddit_names)
        for thread in threads_comments:
            comments = self.get_comments(thread.id)
            if not comments: continue
            r_url = comments[0]["url"].split("/")[2]
            self.contents[r_url]["contents"].append({
                "thread_id": thread.id,
                "title": thread.title,
                "num_comments": thread.num_comments,
                "comments": comments,
                "is_nsfw": thread.over_18,
                "upvotes": thread.score,
                "thread_url": thread.url,
                "upvote_ratio": thread.upvote_ratio,
            })

    def get_comments(self, post_id, sort_by="top"):
        """
        Get comments from a post / thread, filters the comments and returns them
        :param post_id: post id to be submitted
        :param sort_by: after getting the comments, sort them by top, new, controversial, etc.
        :return: a dict of comments --> {text: str, id: str, url: str, author: str, upvotes: int}
        """
        submission = self.reddit.submission(post_id)
        if submission.over_18 and not self.include_nsfw: return {}
        submission.comment_sort = sort_by

        comments = []
        for top_level_comment in submission.comments.list():
            if isinstance(top_level_comment, MoreComments): continue ## TODO: include all comments in the comment tree
            filters = [ ## If any of the filters are true, skip the comment
                top_level_comment.body in ["[removed]", "[deleted]"],
                top_level_comment.stickied,
                len(top_level_comment.body) < self.min_comment_length,
                len(top_level_comment.body) > self.max_comment_length,
                top_level_comment.author is None,
                top_level_comment.score < self.min_comment_score
                 ]
            if any(filters): continue
            sanitised_text = self.sanitise_text(top_level_comment.body)
            if sanitised_text is None or sanitised_text.isspace(): continue
            comments.append({
                "text": sanitised_text,
                "id": top_level_comment.id,
                "url": top_level_comment.permalink,
                "author": top_level_comment.author.name,
                "upvotes": top_level_comment.score,
            })

        return comments

    def authenticate(self):
        from authentication import authenticate_reddit, get_reddit_config
        config = get_reddit_config(self.config_file_path)
        self.reddit = authenticate_reddit(config)

    def control_contents(self):
        """
        When querying multiple subreddits, sometimes some contents returned empty.
        Controls the contents of the self.contents
        :return:
        """
        subs_with_no_contents = [
            subreddit_content["display_name"] for subreddit_url, subreddit_content in self.contents.items()
            if not subreddit_content["contents"]
        ]

        self.controlled = True

        ##print(no_contents) ##Debug purposes
        if subs_with_no_contents:
            self.update_content_threads_comments(
                subreddit_names=subs_with_no_contents
            )

    @staticmethod
    def sanitise_text(text:str, no_urls:bool=True, no_special_chars:bool=True, no_emojis:bool=True)->str:
        r"""Sanitizes the text for tts.
                What gets removed:
             - following characters`^_~@!&;#:-%“”‘"%*/{}[]()\|<>?=+`
             - any http or https links
             - emojis

            Args:
                text (str): Text to be sanitized

            Returns:
                str: Sanitized text
            """
        # remove any urls from the text
        if no_urls:
            regex_urls = r"((http|https)\:\/\/)?[a-zA-Z0-9\.\/\?\:@\-_=#]+\.([a-zA-Z]){2,6}([a-zA-Z0-9\.\&\/\?\:@\-_=#])*"
            text = re.sub(regex_urls, " ", text)

        # note: not removing apostrophes
        if no_special_chars:
            regex_expr = r"\s['|’]|['|’]\s|[\^_~@!&;#:\-%—“”‘\"%\*/{}\[\]\(\)\\|<>=+]"
            result = re.sub(regex_expr, " ", text)
            text = result.replace("+", "plus").replace("&", "and")

        if no_emojis:
            emoj = re.compile("["
                              u"\U0001F600-\U0001F64F"  # emoticons
                              u"\U0001F300-\U0001F5FF"  # symbols & pictographs
                              u"\U0001F680-\U0001F6FF"  # transport & map symbols
                              u"\U0001F1E0-\U0001F1FF"  # flags (iOS)
                              u"\U00002500-\U00002BEF"  # chinese char
                              u"\U00002702-\U000027B0"
                              u"\U000024C2-\U0001F251"
                              u"\U0001f926-\U0001f937"
                              u"\U00010000-\U0010ffff"
                              u"\u2640-\u2642"
                              u"\u2600-\u2B55"
                              u"\u200d"
                              u"\u23cf"
                              u"\u23e9"
                              u"\u231a"
                              u"\ufe0f"  # dingbats
                              u"\u3030"
                              "]+", re.UNICODE)
            text = re.sub(emoj, '', text)

        # utf-8 decode translate unicode characters
        text = str(text)
        # remove extra whitespace
        return " ".join(text.split())

    def write_contents(self, out_file_path:str):
        import json
        with open(out_file_path, "w") as f:
            json.dump(self.contents, f, indent=4)