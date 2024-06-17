
def run_reddit_content(args):
    from reddit import RedditContent
    ## Initiate RedditContent class
    reddit_content = RedditContent(
        thread_limit=args.max_thread,
        include_nsfw=args.include_nsfw,
        config_file_path=args.config_file_path,
        max_comment_length=args.max_comment_length,
        min_comment_length=args.min_comment_length,
        min_comment_score=args.min_comment_score,
    )
    ## authenticates, api calls, gets content
    reddit_content.process(
        subreddits=args.subreddit,
        search_query=args.search_query,
        get_popular=args.popular,
        fuzzy_search=args.fuzzy_search
    )
    ## write content to file
    reddit_content.write_contents(args.output_file)
    print(f"Hurray! Content has been written to {args.output_file}")


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Gets Reddit Content from trending threads and comments.")

    parser.add_argument("--subreddit", type=str, nargs="+", default=[], required=False, help="Subreddit(s) to get content from")
    parser.add_argument("--max_thread", type=int, required=False, default=20, help="Maximum number of threads in a subreddit to get content from")
    parser.add_argument("--search_query", type=str, required=False, help="Search query to get content from")
    parser.add_argument("--output_file", type=str, required=False, default="reddit_contents.json",help="Output json file to write content to")
    parser.add_argument("--popular", action="store_true", help="Get content from popular subreddits. Without any other arguments, this is the default")
    parser.add_argument("--config_file_path", type=str, required=False, default=None, help="Path to the config file")
    parser.add_argument("--include_nsfw", action="store_true", help="Include NSFW comments or threads in the output")
    parser.add_argument("--min_comment_score", type=int, required=False, default=10, help="Minimum score for a comment to be included")
    parser.add_argument("--max_comment_length", type=int, required=False, default=2000, help="Maximum length of a comment to be included")
    parser.add_argument("--min_comment_length", type=int, required=False, default=100, help="Minimum length of a comment to be included")
    parser.add_argument("--fuzzy_search", action="store_true", required=False, help="Make your search query fuzzy, extending to descriptions and titles of subreddits")

    args = parser.parse_args()
    run_reddit_content(args)