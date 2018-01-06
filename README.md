## pointslut

A simple code base to run [Imgur](https://imgur.com/) bots.

### Requirements

- Python 3
- [Requests](http://docs.python-requests.org/en/master/)

### Installation

Clone this repository and install the required packages.

```
git clone https://github.com/Zeroji/pointslut.git
cd pointslut/
pip install -r requirements
```

### Tokens

In order to create a session, authentication tokens must be supplied directly
or as a file name. The following file formats are accepted for sessions:

- Raw text file: contains only the token, possibly prefixed with `Client-ID` or
  `Bearer` depending on its type. Extra spaces or newlines will be stripped.
  > Note: this type of token cannot be refreshed by `refresh.py`!
  > If you need to refresh your tokens, please use another file format.
- JSON format: tokens are represented as dictionaries, with the following data:
  Key            |Required|Description
  ---------------|--------|-----------
  `token`        |required|Authentication token, without prefix
  `refresh`      |refresh¹|Refresh token
  `client_id`    |refresh¹|Client ID (of your application)
  `client_secret`|refresh¹|Client secret (of your application)
  `token_type`   |optional|Token type, either `Client-ID` or `Bearer`

  > [1] Keys marked with "refresh" are only required if you need to use `refresh.py`

  Your JSON file should contain either one single token, or a list or
  dictionary containing only tokens. Tokens can have additional custom data.

### Refreshing tokens

If your tokens are stored in a JSON structure, you can call `refresh.py` to
refresh them. You can refresh several files at once.

```
python refresh.py token_1.json token_2.json
```
