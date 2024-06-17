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
                 thread_limit=20, include_nsfw:bool=False, config_file_path:str=None
                 ):
        self.config_file_path = CONFIG_FILE_PATH if config_file_path is None else config_file_path
        self.thread_limit = thread_limit
        self.include_nsfw = include_nsfw

        ### Comment related parameters
        self.max_comment_length = max_comment_length
        self.min_comment_length = min_comment_length
        self.min_comment_score = min_comment_score

        ### Parameters to be used
        self.reddit = None
        self.contents = {}

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

        ## Get query related subreddits if search query is provided
        ## default is to have popular subreddits
        if (search_query is None and subreddits is None) or get_popular:
            print("Getting the popular subreddits.")
            subs = self.get_popular_subreddits()

        elif search_query is not None:
            if fuzzy_search:
                print(f"Getting {search_query} related subreddits.")
                subs = self.search_subreddits(search_query)
            else:
                print(f"Getting {search_query} subreddit(s).")
                subs = self.search_subreddits_by_name(search_query, exact=exact_search)
        elif subreddits is not None:
            for subred in subreddits:
                self.process(search_query=subred, exact_search=True, get_popular=False)
            return 0

        else:
            raise Exception("Invalid arguments provided. Please provide either search_query or subreddits.")

        ## Get threads from subreddits
        self.update_content_subreddits(subs)

        ##get threads and comments
        self.update_content_threads_comments()

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
        if isinstance(subreddits, str):
            return self.reddit.subreddit(subreddits)
        return self.reddit.subreddit("+".join(subreddits))

    def get_subreddit_threads(self, subreddits:List[AnyStr])->Iterator[Any]:## subreddit object of the subreddits
        return self.get_subreddits(subreddits).hot(limit=self.thread_limit)

    def get_popular_subreddits(self):
        return self.reddit.subreddits.popular()

    def update_content_subreddits(self, subreddits:List[Subreddit]):
        """
        Populates self.contents with subreddits
        :param subreddits:
        :return:
        """
        for sub in subreddits:
            r_url = sub.url.split("/")[2]
            self.contents.update({r_url: {
                "title": sub.title,
                "description": sub.description,
                "display_name": sub.display_name,
                "url": r_url,
                "contents": []
            }})

    def update_content_threads_comments(self):
        """
        Updates self.contents with threads and comments
        :return:
        """
        ##get display names for the subreddits
        subreddit_names = [sub["display_name"] for sub in self.contents.values()]
        threads_comments = self.get_subreddit_threads(subreddit_names)
        for thread in threads_comments:
            comments = self.get_comments(thread.id)
            if not comments: continue
            r_url = comments[0]["url"].split("/")[2]
            self.contents[r_url]["contents"].append({
                "thread_id": thread.id,
                "title": thread.title,
                "comments": comments,
                "is_nsfw": thread.over_18,
                "upvotes": thread.score,
                "thread_url": thread.url,
                "upvote_ratio": thread.upvote_ratio,
            })

    def get_comments(self, post_id, sort_by="top",
                     max_comment_length=2000, min_comment_length=100,
                     min_comment_score=10):
        """
        Get comments from a post / thread, filters the comments and returns them
        :param post_id: post id to be submitted
        :param sort_by: after getting the comments, sort them by top, new, controversial, etc.
        :param max_comment_length:
        :param min_comment_length:
        :return: a dict of comments --> {text: str, id: str, url: str, author: str, upvotes: int}
        """
        submission = self.reddit.submission(post_id)
        if submission.over_18 and not self.include_nsfw: return {}
        submission.comment_sort = sort_by

        comments = []
        for top_level_comment in submission.comments.list():
            if isinstance(top_level_comment, MoreComments): continue
            filters = [ ## If any of the filters are true, skip the comment
                top_level_comment.body in ["[removed]", "[deleted]"],
                top_level_comment.stickied,
                len(top_level_comment.body) < min_comment_length,
                len(top_level_comment.body) > max_comment_length,
                top_level_comment.author is None,
                top_level_comment.score < min_comment_score
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