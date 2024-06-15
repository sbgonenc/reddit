from settings import CONFIG_FILE_PATH
import re
from praw.models import MoreComments


class Reddit:
    def __init__(self, thread_limit=1, include_nsfw:bool=False, subreddits=None):
        self.config_file_path = CONFIG_FILE_PATH
        self.thread_limit = thread_limit
        self.include_nsfw = include_nsfw

        self.reddit = None
        self.subreddits = subreddits
        self.contents = {}

    def process_popular(self):
        ## Authenticate if not already authenticated
        if not self.reddit:
            self.authenticate()

        ## Get popular subreddits
        self.subreddits = self.get_popular_subreddits(),

        ## Get threads from popular subreddits
        subnames= []
        for sub in self.subreddits:
            self.contents["subreddit"] = {sub.title: {
                "title": sub.title,
                #"description": sub.description,
                "display_name": sub.display_name,
                "contents" : []
            }}
            subnames.append(sub.display_name)

        ##get threads and comments
        for thread in self.get_subreddit_threads(subnames):
            self.contents["subreddit"][thread.title]["contents"].append({
                "title": thread.title,
                "comments": self.get_comments(thread.id)
            })


    def search_subreddits(self, query:str):
        """
        Search for subreddits' title and description by query
        :param query:
        :param exact:
        :return:
        """
        return self.reddit.subreddits.search(query=query)

    def search_subreddits_by_name(self, query:str, exact:bool=False):
        return self.reddit.subreddits.search_by_name(query, exact=exact, include_nsfw=self.include_nsfw)

    def get_subreddit_threads(self, subreddits:list):
        subreddit = self.reddit.subreddit("+".join(subreddits))
        thread_objs = subreddit.hot(limit=self.thread_limit)
        return thread_objs

    def get_popular_subreddits(self):
        return self.reddit.subreddits.popular()

    @staticmethod
    def get_post_id(reddit_obj):
        """"
        This function takes a reddit object and returns the post id
        """
        return reddit_obj.id
        #return re.sub(r"[^\w\s-]", "", reddit_obj["thread_id"])

    def get_comments(self, post_id, sort_by="top", max_comment_length=2000, min_comment_length=10):
        submission = self.reddit.submission(post_id)
        submission.comment_sort = sort_by
        comment_list = submission.comments.list()

        comments = []

        for top_level_comment in comment_list:
            if isinstance(top_level_comment, MoreComments): continue
            filters = [ ## If any of the filters are true, skip the comment
                top_level_comment.body in ["[removed]", "[deleted]"],
                top_level_comment.stickied,
                len(top_level_comment.body) < min_comment_length,
                len(top_level_comment.body) > max_comment_length,
                top_level_comment.author is None,
                 ]
            if any(filters): continue
            sanitised_text = self.sanitise_text(top_level_comment.body)
            if sanitised_text is None or sanitised_text.isspace(): continue
            comments.append({
                "body": sanitised_text,
                "id": top_level_comment.id,
                "url": top_level_comment.permalink,
                "author": top_level_comment.author.name
            })

        return comments

    def authenticate(self):
        from authentication import authenticate_reddit, get_reddit_config
        config = get_reddit_config(self.config_file_path)
        self.reddit = authenticate_reddit(config)

    @staticmethod
    def sanitise_text(text:str, no_urls:bool=True, no_special_chars:bool=True):
        r"""Sanitizes the text for tts.
                What gets removed:
             - following characters`^_~@!&;#:-%“”‘"%*/{}[]()\|<>?=+`
             - any http or https links

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

        # remove extra whitespace
        return " ".join(text.split())


rdt = Reddit()
rdt.authenticate()
subreddits = []
for sub in rdt.get_popular_subreddits():
    #print(sub.title, sub.display_name)
    subreddits.append(sub.display_name)

threads = rdt.get_subreddit_threads(subreddits)
for thread in threads:
    print("Thread Title:\t" + thread.title)
    print("Thread URL:\t" + thread.url)
    print("Thread ID:\t" + thread.id)
    print("Thread Upvotes:\t" + str(thread.score))
    print("Thread Upvote Ratio:\t" + str(thread.upvote_ratio))
    print("Thread Comments:\t" + str(thread.num_comments))
    print("Thread NSFW:\t" + str(thread.over_18))
    print("Thread Self Text:\t" + thread.selftext)
    print("Thread Author:\t" + thread.author.name)


    #print(rdt.get_comments(thread.id))