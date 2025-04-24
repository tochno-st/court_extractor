import re
import os
import google.generativeai as genai
import json

import pandas as pd
import spacy
import yaml
from gender import GenderExtractor

# Load the spaCy model for lemmatization
spacy_model = "ru_core_news_sm"
nlp = spacy.load(spacy_model)


class PunishmentExtractor:
    def __init__(self, yaml_path=None, spacy_model="ru_core_news_sm", api_key=None):
        """Initialize with YAML configuration and spaCy model."""
        self.nlp = spacy.load(spacy_model)
        if yaml_path is None:
            # Get the directory where this module is located
            module_dir = os.path.dirname(os.path.abspath(__file__))
            yaml_path = os.path.join(module_dir, "punishments.yaml")
        with open(yaml_path, "r", encoding="utf-8") as file:
            self.config = yaml.safe_load(file)
            self.punishments_data = self.config["punishments"]
            self.pattern = self.config.get("decision_pattern")
            self.sensitive_pattern = self.config.get("sensitive_pattern")

        if not api_key:
            raise ValueError("No API key provided. Please provide an API key.")
        else:
            genai.configure(api_key=api_key)
            self.model = genai.GenerativeModel("gemini-2.0-flash-001")

    # Step 1: Extract the resolutive part.
    def extract_resolutive_part(self, text):
        """
        Extract the resolutive part of the sentence based on sensitive phrases and the regex pattern.
        """
        if isinstance(text, str):
            if re.search(self.sensitive_pattern, text, re.IGNORECASE):
                print("Text was not published")
                return None
            if len(text) < 500:
                print("Something went wrong. Text is too short.")
                return None
            match = re.search(f"{self.pattern}.*", text, re.DOTALL | re.IGNORECASE)
            if match:
                return match.group(0)
        return None

    # Step 2: Lemmatize text.
    def lemmatize_text(self, text):
        """Lemmatizes text using spaCy."""
        if isinstance(text, str):
            doc = self.nlp(text)
            return " ".join([token.lemma_ for token in doc])
        return ""

    # Step 3: Remove extra spaces.
    def remove_double_spaces(self, text):
        """Replaces multiple spaces with a single space."""
        return re.sub(r"\s+", " ", text).strip()
    
    @staticmethod
    def extract_json_from_code_block(text):
        # Find the start marker
        start_marker = "```json"
        end_marker = "```"
        
        start_index = text.find(start_marker)
        if start_index == -1:
            return None
        
        # Move past the start marker
        start_index += len(start_marker)
        
        # Find the end marker
        end_index = text.find(end_marker, start_index)
        if end_index == -1:
            return None
        
        # Extract the JSON string
        json_string = text[start_index:end_index].strip()
        return json_string

    # Step 4: Find punishments.
    def find_punishment(self, input_string):

        gender_extractor = GenderExtractor(russian_names_db=False)
        names_accused = gender_extractor.extract_names(input_string, canonical=True)
        
        prompt = f"""
        Analyze the following text and extract the final punishments for each person mentioned:

        Text: {input_string}

        Requirements:
        1. For each unique person in the text:
           - Extract their final/aggregated punishments
           - If multiple punishments of the same type exist, only return the final aggregated punishment
           - If different types of punishments exist, return all of them
           - Verify all names against {names_accused.keys()}
           - Use nominative case for names

        2. Return format:
           {{
               "Person Name": {{
                   "1": {{
                       "punishment": "<form only from {self.punishments_data.keys()}>",
                       "type": "<type from {self.punishments_data} type field>",
                       "severity": {{
                           "years": <number>,
                           "months": <number>,
                           "rubles": <number>,
                           "days": <number>,
                           "hours": <number>
                       }}
                   }},
                   "2": {{
                       // Additional punishment if different type but also from {self.punishments_data.keys()}
                   }}
               }}
           }}

        3. Severity rules:
           - Use years and months for imprisonment
           - Use rubles for fines
           - Use days/hours for other time-based punishments
           - Default to 0 for unspecified months
           - Apply transformations from punishments_data if needed
           - Only include final severity values

        4. Return None if no punishment information found

        Return the result as a JSON object.
        """

        response = self.model.generate_content(prompt)

        if response and hasattr(response, "text") and response.text:
                return input_string, json.loads(self.extract_json_from_code_block(response.text).replace('\n', ' ').replace('    ', ' ').replace('  ', ' '))
        else:
                return input_string, None
        
    def find_punishemtns(self, input_string):
        resolutive_part = self.extract_resolutive_part(input_string)
        if resolutive_part is None:
            return None
        removed_double_spaces = self.remove_double_spaces(resolutive_part)
        return self.find_punishment(removed_double_spaces)

    def process_dataframe(self, df, text_column="result_text"):
        df["punishments"] = df.apply(lambda row: self.find_punishemtns(row[text_column]), axis=1)
        return df


if __name__ == '__main__':
# Example Usage:
    punishment_extractor = PunishmentExtractor()
    
    input_string = """Шестакова Александра Владимировича признать виновным в совершении преступлений, предусмотренных п. «з» ч.2 ст.111, п. 
    «а» ч.3 ст.158 Уголовного кодекса Российской Федерации и назначить ему наказание: - по п. «з» ч.2 ст.111УК РФ – в виде лишения свободы на 
    срок три года; - по п. «а» ч.3 ст.158 УК РФ – в виде лишения свободы на срок два года. На основании ч.3 ст. 69 Уголовного кодекса Российской 
    Федерации по совокупности преступлений путем частичного сложения наказаний окончательно назначить Шестакову Александру Владимировичу наказание 
    в виде лишения свободы на срок четыре года. В соответствии со ст. 70 Уголовного кодекса Российской Федерации, по совокупности приговоров, 
    к наказанию, назначенному по настоящему приговору, частично присоединить неотбытую часть наказания по приговору от 18.05.2021 Уватского районного 
    суда Тюменской области и окончательно назначить Шестакову Александру Владимировичу наказание в виде лишения свободы на срок 4 (четыре) года 6 (шесть)
    месяцев, с отбыванием в исправительной колонии общего режима. Меру пресечения в виде подписки о невыезде и надлежащем поведении Шестакову 
    Александру Владимировичу изменить на меру пресечения в виде заключения под стражу, взять его под стражу немедленно в зале суда. 
    Срок наказания Шестакову Александру Владимировичу исчислять со дня вступления настоящего приговора в законную силу. В соответствии с п. "б" ч. 
    3.1 ст. 72 Уголовного кодекса Российской Федерации время содержания под стражей Шестакову Александру Владимировичу с 18 мая 2023 года до дня 
    вступления настоящего приговора в законную силу зачесть в срок лишения свободы из расчета один день содержания под стражей за полтора дня отбывания 
    наказания в исправительной колонии общего режима."""

    # Process a subset for testing.
    initial_string, res = punishment_extractor.find_punishemtns(input_string)
    print(res)
