import re
from concurrent.futures import ThreadPoolExecutor
import pandas as pd

class ArticlesExtractor:
    """
    Extract articles, parts and subparts from legal codes:
    
    - Criminal Code (Ugolovnyi Kodeks)
    - Code of Administrative Offenses (Kodeks ob Administrativnykh Pravonarusheniyakh)
    
    Takes a string containing articles under which charges are filed and extracts structured
    information about the specific articles, parts and subparts referenced.
    """
    
    def __init__(self, remove_duplicates=True):
        """Initialize the extractor without input string"""
        self.input_string = None
        self.person_blocks = None
        self.remove_duplicates = remove_duplicates

    def process_string(self, input_string):
        """Process a single input string"""
        self.input_string = input_string
        self.person_blocks = self._divide_into_person_blocks()
        return self.extract_info()

    def process_dataframe(self, df, column_name, parallel=True, n_workers=4):
        """
        Process multiple strings from a DataFrame column
        """
        if parallel:
            with ThreadPoolExecutor(max_workers=n_workers) as executor:
                results = list(executor.map(self.process_string, df[column_name]))
        else:
            results = df[column_name].apply(self.process_string).tolist()
        return results

    def _divide_into_person_blocks(self):
        """
        Divides the input string into blocks for each person.
        """
        return re.split(r';\s*(?=[А-Я])', self.input_string)

    def _extract_article_info(self, article_text):
        """
        Extracts article, part, and subpart information from a single article text.
        """
        article_pattern = re.compile(r'ст\.\s*(\d+\.?\d*)')  # Matches article (e.g., 30 or 228.1)
        part_pattern = re.compile(r'ч\.\s*(\d+)')  # Matches part (e.g., ч.1)
        subpart_pattern = re.compile(r'п(?:п|\.)\.?\s*([а-я,]+)')  # Matches subparts (e.g., пп. е,ж,з or п.в)

        article_match = article_pattern.search(article_text)
        part_match = part_pattern.search(article_text)
        subpart_match = subpart_pattern.search(article_text)

        article = article_match.group(1) if article_match else None
        part = part_match.group(1) if part_match else None
        subpart = subpart_match.group(1) if subpart_match else None

        if subpart:
            subpart = re.sub(r'\s+', '', subpart)  # Remove spaces
            subpart = subpart.lower()  # Convert to lowercase
            subpart = subpart.split(',')  # Split into list

        return article, part, subpart

    def _split_articles(self, person_block):
        """
        Splits a person block into individual articles, handling commas, semicolons, and article ranges.
        """
        articles = re.split(r'[;,]\s*(?=ст\.)', person_block)
        expanded_articles = []
        for article in articles:
            if '-' in article:  # Handle article ranges
                range_parts = article.split('-')
                for part in range_parts:
                    expanded_articles.append(part.strip())
            else:
                expanded_articles.append(article.strip())

        return expanded_articles

    def _extract_articles_for_person(self, person_block):
        """
        Extracts article information and code type for a single person block.
        """

        court_types = {"CRIMINAL": ["УК", "Уголовного", "уголовного"],
                       "ADMIN": ["КОАП", "об административных правонарушениях", "КоАП"],
                       "MATERIAL": ["УПК"]}

        articles = self._split_articles(person_block)

        code_type_pattern = re.compile(r'(' + '|'.join([item for sublist in court_types.values() for item in sublist]) + ')')
        code_type_match = code_type_pattern.search(person_block)
        code_type = None
        if code_type_match:
            code_type = code_type_match.group(1)
            for key, values in court_types.items():
                if code_type in values:
                    code_type = key
                    break
            else:
                code_type = 'UNKNOWN'

        articles_list = []
        for article_text in articles:
            article, part, subpart = self._extract_article_info(article_text)
            if article:  # Only add if article is found
                articles_list.append({
                    'article': article,
                    'part': part,
                    'subpart': subpart
                })

        return articles_list, code_type

    def _remove_duplicate_articles(self, articles_list):
        """
        Removes duplicate article dictionaries from the list.
        """
        unique_articles = []
        seen = set()
        for article in articles_list:
            article_tuple = (
                ('article', article['article']),
                ('part', article['part']),
                ('subpart', tuple(article['subpart']) if article['subpart'] else None)
            )
            if article_tuple not in seen:
                seen.add(article_tuple)
                unique_articles.append(article)
        return unique_articles

    def extract_info(self):
        """
        Extracts legal information for all persons in the input string.

        Args:
            remove_duplicates (bool): If True, removes duplicate article dictionaries for each person.
        """
        result = []
        for index, person_block in enumerate(self.person_blocks, start=1):
            articles_list, code_type = self._extract_articles_for_person(person_block)

            if self.remove_duplicates:
                articles_list = self._remove_duplicate_articles(articles_list)

            person_dict = {
                'person': f'Person {index}',
                'articles': articles_list,
                'code_type': code_type
            }

            result.append(person_dict)

        return result
    

if __name__ == '__main__':
    # Example 1: Single string processing
    test_string = "Губаев Борис Магомедович - ст.159 ч.2 УК РФ"
    extractor = ArticlesExtractor(remove_duplicates=True)
    result = extractor.process_string(test_string)
    print("Single string processing result:")
    print(result)

    # Example 2: DataFrame processing with parallel execution
    import pandas as pd
    
    # Create sample DataFrame
    data = {
        'text_column': [
            "Губаев Борис Магомедович - ст.159 ч.2 УК РФ",
            "ст. 20.1 КоАП; ст. 19.3 ч.1 КоАП",
            "ст. 105 ч.1 п.а УК; ст. 111 ч.2 УК"
        ]
    }
    df = pd.DataFrame(data)
    
    results = extractor.process_dataframe(df, 'text_column', parallel=True, n_workers=2)
    print("\nDataFrame processing results:")
    for i, result in enumerate(results):
        print(f"\nRow {i+1}:")
        print(result)
