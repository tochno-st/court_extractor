import os
import pandas as pd

class MunicipalityExtractor:
    """
    Based on the curated dictionary of territorial jurisdiction for each district court, determine 
    the region and municipality in which the court operates.

    The extractor accounts for:
    - Courts serving multiple municipalities
    - Large municipalities having several district courts

    Returns:
        For each court code, returns a tuple of (region, municipality, oktmo)
    """

    def __init__(self, use_name: bool = False, dict_path: str = None):
        self.use_name = use_name
        self.court_identifier = 'court_name' if self.use_name else 'court_code'
        
        if dict_path is None:
            # Default path relative to the project root
            dict_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'data', 'interim', 'mun_court_dict_v20250424.csv')
            
        if not os.path.exists(dict_path):
            raise FileNotFoundError(f"Dictionary file not found at: {dict_path}")
            
        self.court_dict = pd.read_csv(dict_path,
                            sep=';', 
                            names=['municipality', 'region', 'oktmo', 'court_name', 'court_code', 'comment'],
                            dtype='string')
        
    def get_municipality(self, court_id: str) -> tuple:
        
        match = self.court_dict[self.court_dict[self.court_identifier] == court_id]
        
        if len(match) == 0:
            print("Check if is court code is correct")
            return None, None, None
            
        row = match.iloc[0]
        return row['region'], row['municipality'], row['oktmo']

    def process_dataframe(self, df: pd.DataFrame, code_column: str) -> pd.DataFrame:
        df[['region', 'municipality', 'oktmo']] = df[code_column].apply(
            lambda x: pd.Series(self.get_municipality(x))
        )
        return df

if __name__ == '__main__':
    extractor = MunicipalityExtractor()
    print(extractor.get_municipality("61RS0006"))
