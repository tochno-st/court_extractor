from natasha import Segmenter, Doc, NamesExtractor, MorphVocab, PER, NewsMorphTagger, NewsSyntaxParser, NewsEmbedding, NewsNERTagger
from russiannames.parser import NamesParser
import pymorphy2
from pytrovich.detector import PetrovichGenderDetector
from collections import defaultdict
import difflib
import re

class GenderExtractor:
    def __init__(self, russian_names_db = False):
        self.segmenter = Segmenter()
        self.names_extractor = NamesExtractor(morph=MorphVocab())
        self.morph_analyzer = pymorphy2.MorphAnalyzer()
        self.russian_names_db = NamesParser()
        self.emb = NewsEmbedding()
        self.syntax_parser = NewsSyntaxParser(self.emb)
        self.ner_tagger = NewsNERTagger(self.emb)
        self.morph_vocab = MorphVocab()
        self.morph_tagger = NewsMorphTagger(self.emb)
        self.russian_names_db = russian_names_db

    @staticmethod
    def get_full_name(info):
        return ' '.join([info.get('last', ''), info.get('first', ''), info.get('middle', '')]).strip()

    @staticmethod
    def get_initials_from_full(info):
        return ''.join([c[0] + '.' for c in [info.get('first', ''), info.get('middle', '')] if c])

    def match_by_initials(self, name1, name2):
        return (
            name1.get('last') == name2.get('last') and
            self.get_initials_from_full(name1) == self.get_initials_from_full(name2)
        )

    def extract_canonical(self, names_dict):
        canonical_map = {}  # full name → component dict
        reverse_map = defaultdict(list)  # full name → [original name variants]

        for raw_name, components in names_dict.items():
            full = self.get_full_name(components)
            matched = None

            for canon_name, canon_comp in canonical_map.items():
                # 1. Exact full name match
                if full == canon_name:
                    matched = canon_name
                    break
                # 2. Initials-based match
                elif self.match_by_initials(canon_comp, components):
                    matched = canon_name
                    break
                # 3. Fuzzy full name match
                elif difflib.SequenceMatcher(None, self.get_full_name(canon_comp), full).ratio() > 0.88:
                    matched = canon_name
                    break

            if matched:
                reverse_map[matched].append(raw_name)
            else:
                canonical_map[full] = components
                reverse_map[full].append(raw_name)

        return reverse_map

    def extract_names(self, text, canonical=False):
        """Extract names from the input text using Natasha."""

        doc_pr = Doc(text)
        doc_pr.segment(self.segmenter)

        doc_pr.tag_morph(self.morph_tagger)
        doc_pr.parse_syntax(self.syntax_parser)
        doc_pr.tag_ner(self.ner_tagger)
        
        for span in doc_pr.spans:
            if span.type == PER:
                span.normalize(self.morph_vocab)
                span.extract_fact(self.names_extractor)

        if canonical:
            return self.extract_canonical({_.normal: _.fact.as_dict for _ in doc_pr.spans if _.fact})
        else:
            return {_.normal: _.fact.as_dict for _ in doc_pr.spans if _.fact}
    
    def detect_gender_with_pytrovich(self, f_name, l_name, m_name):
        """Detect gender using pytrovich library."""

        detector = PetrovichGenderDetector()
        try:
            result = detector.detect(firstname=f_name, lastname=l_name, middlename=m_name)
            return result.name[:1]
        except StopIteration as e:
            return "U"  
    
    def detect_gender_with_russiannames(self, person_name):
        """Detect gender using russiannames."""

        name_info = self.russian_names_db.parse(person_name)
        if name_info:
            if "gender" in name_info.keys():
                 return name_info["gender"].upper()
            else:
                return "U"
        else:
            return "U"

    def extract_genders(self, text):
        """Extract names and detect genders for each person in the text."""
        names = self.extract_names(text)
        genders = []

        for name, details in names.items():

            last_name = details["last"] if "last" in details.keys() else ""
            first_name = details["first"] if "first" in details.keys() else ""
            middle_name = details["middle"] if "middle" in details.keys() else ""

            merged_name = " ".join(word for word in [last_name, first_name, middle_name] if word)    

            if self.russian_names_db:
                gender_rn = self.detect_gender_with_russiannames(merged_name)
            else:
                gender_rn = "U"
            gender_ph = self.detect_gender_with_pytrovich(first_name, last_name, middle_name)

            if gender_ph == gender_rn:
                if gender_ph != "U":
                    genders.append((merged_name, gender_ph))
                else:
                    genders.append((merged_name, "U"))
            elif gender_ph == "U":
                genders.append((merged_name, gender_rn))
            elif (gender_rn == "U") or (gender_rn == "-"):
                genders.append((merged_name, gender_ph))
            else:
                genders.append((merged_name, "C"))
            
        return genders
    
if __name__ == "__main__":
    text = "Волостных Владислав Витальевич - ст.291 ч.3; ст.222 ч.1; ст.290 ч.5 п.в; ст.290 ч.5 п.в; ст.290 ч.5 п.в УК РФ"
    extractor = GenderExtractor(russian_names_db=False)
    result = extractor.extract_genders(text)
    print(result)