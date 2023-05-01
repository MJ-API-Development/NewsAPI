# Financial News API

The Financial News API is a web service that provides access to the latest news articles related to a variety of 
financial instruments, including stocks, bonds, currencies, and commodities. 

The API collects news from a variety of sources and presents it in a standardized format that can be easily 
consumed by other applications.

## Features

The Financial News API offers the following features:

- Access to the latest news articles related to a variety of financial instruments.
- Support for a wide range of financial instruments, including stocks, bonds, currencies, and commodities.
- Integration with popular programming languages, including Python and JavaScript.
- Simple and intuitive API design, with comprehensive documentation and examples.

## Getting Started

To get started with the Financial News API, follow these steps:

1. Sign up for an API key on our website.
2. Read the documentation to learn how to use the API.
3. Integrate the API into your application using one of our SDKs or API clients.

## Usage

To use the Financial News API, send a GET request to the API endpoint with your API key and the 
ticker symbol of the financial instrument you are interested in. 

The API will return a list of news articles related to that instrument.

    https://gateway.eod-stock-api.site/api/v1/news/articles-by-ticker/{stock_code}


The response will be a JSON object containing a list of news articles in the following format:
```json
    {
        "title": "Apple stock rises on strong Q3 earnings report",
        "source": "CNBC",
        "url": "https://www.cnbc.com/2021/07/27/apple-aapl-earnings-q3-2021.html",
        "date": "2021-07-27T21:51:00.000Z",
        "body": "Apple reported strong earnings in the third quarter, driven by strong sales of the iPhone and Mac."
    }
```  


## Support

If you have any questions or issues, please contact us at [support@eod-stock-api.site](mailto:support@eod-stock-api.site) .

## License

This project is licensed under the MIT License. See the LICENSE file for details.

## Community

- [Slack Channel](https://join.slack.com/t/eod-stock-apisite/shared_invite/zt-1uelcf229-c_6QAgWFNyVfXKZr1hYYoQ)
- [StackOverflow](https://stackoverflowteams.com/c/eod-stock-market-api)
- [Quora](https://eodstockmarketapi.quora.com/)
