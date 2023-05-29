from bs4 import BeautifulSoup


def parse_motley_article(html):
    soup = BeautifulSoup(html, 'html.parser')

    # Extract article title
    title_element = soup.find('h2', class_='font-light')
    title = title_element.text if title_element else ''

    # Extract company name and ticker symbol
    company_element = soup.find('div', class_='company-card-vue-component')
    if company_element:
        company_name = company_element.find('div', class_='font-medium').text.strip()
        ticker_symbol = company_element.find('a', class_='text-gray-1100').text.strip()
    else:
        company_name = ''
        ticker_symbol = ''

    # Extract stock price information
    price_element = soup.find('div', class_='w-5/6 h-full py-10')
    if price_element:
        today_change = price_element.find('div', class_='text-green-900').text.strip()
        current_price = price_element.find('div', class_='text-gray-1100').text.strip()
    else:
        today_change = ''
        current_price = ''

    # Extract article content
    content_elements = soup.find_all('p')
    content = ' '.join(element.text.strip() for element in content_elements)

    # Construct the parsed data dictionary
    parsed_data = {
        'title': title,
        'company_name': company_name,
        'ticker_symbol': ticker_symbol,
        'today_change': today_change,
        'current_price': current_price,
        'content': content
    }

    return parsed_data
