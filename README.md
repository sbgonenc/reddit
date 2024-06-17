## Reddit Content Search

This project is an application that allows users to search for Reddit posts, threads and comments based on a keyword. The application will display the title, author, and number of comments for each post. Outputs a json file with the search results.

## Installation

To install the application, clone the repository and navigate to the project directory:

```bash
git clone https://github.com/sbgonenc/reddit.git 
```

within the virtual environment, run the following command to install the required packages:

```bash
pip install -r requirements.txt
```

configure the ```config.toml``` file with your Reddit API credentials. You can look intp and copy `config_template.toml` file. 
Program looks for the `config.toml` file in the same directory as the main.py file. Also, `--config_file_path` argument can be used to specify the path of the config file.

You can obtain your credentials by following the instructions [here](https://www.reddit.com/prefs/apps).


## Usage

To run the application, run the following command:

### Basic usage:
```bash
python main.py
```
This automatically searches popular subreddits and outputs the contents to a json file within the project path.

To search for a specific keyword, use the `--search_query` argument:

```bash
python main.py --search_query "keyword"
```

that searches subreddits and threads that contain the keyword in their title.

To search for a specific subreddit(s), use the `--subreddit` argument:

```bash
python main.py --subreddit "subreddit_name1" "subreddit_name2" "subreddit_name3"
```

You can also specify an output path with `--output_file` argument:

```bash
python main.py --output_file "output.json"
```

### Example usages

```bash
python main.py --subreddit askreddit  --output_file ask_reddit.json  --max_thread 1000 --include_nsfw --min_comment_score 100
```
Code above searches posts in `askreddit` subreddit, saves the results to `ask_reddit.json` file, includes nsfw posts, and only includes comments with a minimum comment score of 100.

```bash
python main.py --search_query programming  --output_file programming.json --max_thread 10 --min_comment_score 10 --fuzzy_search
```
Command above searches `programming` keyword in popular subreddits, saves the results to `programming.json` file, only includes threads with a minimum comment score of 10, and uses fuzzy search to find the keyword in the titles.


## Output file format

The output file is a json file that contains the following fields:

```json
{
    "subreddit_name": {
    "title": "subreddit_name",
        "description": "subreddit_description",
        "display_name": "subreddit_display_name",
        "url": "subreddit_url",
        "contents": [
            {
                "title": "thread_title",
                "author": "thread_author",
                "num_comments": "number_of_comments",
                "comments": [
                    {
                        "author": "comment_author",
                        "body": "comment_body",
                        "score": "comment_score"
                    }
                ]
            }
        ]
    }
}
```

## Contact
If you have any questions or suggestions, please feel free to add issues or contact me!