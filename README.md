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

### Complex grammar

You can write rules to generate text out of many randomized elements.
A JSON file containing a dictionary of text elements can be used to get them,
following certain rules. Keys are the name you use to get the value.

#### Randomized string evaluation

Strings can contain the following pattern:
```json
"{Hello|Hi}, user!"
```
When evaluated, one of the two possibilities will be chosed at random. You can
use as many possibilites as you'd like, and you can nest them. Example:
```json
"{Hello|Hi|Good {morning|afternoon}}, {dear |}user"
```
In this example, `{dear |}` will evaluate to nothing, half the time.

> This pattern can be used in all the following expressions.

#### Randomly occuring strings

You can make something appear only every so often. To achieve that, replace the
string with a dictionary, containing a key `"o"` defining the rarity of the string.
For example, `"o": 3` will make the string appear one third of the time. The string
itself should be stored under the key `"s"`.
```json
{
    "o": 5,
    "s": "There is one chance in {five|5} that you will see this!"
}
```

#### Weighted randomized strings

That's if you want to have very different strings, and have them display more often
than others. For example, allowing less formal greetings with lowered odds. This is
achieved through a list of dictionaries (order doesn't matter), which have one key
`"w"` being the weight of the string, and `"s"` containing the string.
```json
[
    {"w": 5, "s": "Hello"},
    {"w": 2, "s": "Hi"},
    {"w": 1, "s": "Yo"}
]
```
In this example, the total weight of the pool is 5+2+1=8. That means `"Hello"` has
a 5/8 chance to appear, while `"Yo"` has only 1/8.

#### Referencing other values

By using `{key}` inside your strings, you can reference other values. This is
useful in complex cases, or when you need multiple reference to a single text.

*Full file example*
```json
{
    "main": "{greeting}, {user}{suffix}",
    "greeting": [
        {"w": 5, "s": "Hello"},
        {"w": 1, "s": "Hi"}
    ],
    "user": "{Zeroji|unknown}",
    "suffix": {"o": 3, "s": "!"}
}
```
This will return `"Hello, Zeroji!"` with odds of `(5/6) * (1/2) * (1/3)`.

#### Referencing with a parameter

That's the last and most complex call. By using `{key(some text)}`, you can make
a reference to a piece of text (called by `key`) that contains a reference to
`{x}`. This will be replaced by whatever you send it, here `'some text'`.

*Full file example*
```json
{
    "main": "{give(a gift)}",
    "give": [
        {"w": 2, "give me {x}"},
        {"w": 1, "give {x} to me"}
    ]
}
```
This will evaluate to either `'give me a gift'` or `'give a gift to me'`. Of
course, you can also use references and all between the parentheses.
