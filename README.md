[![License: CC BY-NC-SA 4.0](https://img.shields.io/badge/License-CC_BY—NC—SA_4.0-lightgrey.svg)](https://creativecommons.org/licenses/by-nc-sa/4.0/)

# Court Data Extractor

A Python library for extracting structured data from Russian court decisions, including punishments, territorial jurisdiction, gender information, and criminal code articles.

## Modules

✅ **Punishment Extractor**: Extracting structured data from court decision texts regarding punishments and their corresponding severity, taking into account that punishment may be applied both to specific charges and in aggregate.

✅ **Municipality Extractor**: Based on a curated dictionary of territorial jurisdiction for each district court, determine the region and municipality in which the court operates. Account for the fact that some courts serve multiple municipalities, and large municipalities may have several district courts.

✅ **Gender Extractor**: Extract the gender of the judge and the defendant from their full name and the text of the court decision.

✅ **Articles Extractor**: Extract articles, parts and subparts of the Criminal Code (Ugolovnyi Kodeks) and the Code of Administrative Offenses (Kodeks ob Administrativnykh Pravonarusheniyakh) from the string representing all articles under which charges are filed.

🔜 **LLM Pipeline**: Providing researchers with examples and templates for using Large Language Models (LLMs) to extract structured information from court decision texts, including customizable entity extraction patterns and best practices for prompt engineering.

## Project structure

``` bash
court_extractor
├── README.md                    # Project documentation
├── requirements.txt             # Python dependencies
├── AUTHORS                      # Contributors list
│
├── src                          # Source code directory
│   ├── articles.py              # Articles Extractor source code
│   ├── districts.py             # Municipality Extractor source code
│   ├── gender.py                # Gender Extractor source code
│   ├── punishments.py           # Punishment Extractor source code
│   └── punishments.yaml         # Punishment configuration file
│
├── data                         # Data directory
│   ├── raw                      # Original datasets examples
│   └── interim                  # Dictionaries used for library
│
└── notebooks                    # Jupyter notebooks
    └── court_extractor_demo.ipynb  # Demo notebook
```

## How to use

### Punishment Extractor

The ```punishments``` module enables to extract structured data about punishments from court decision texts. The module uses **Gemini 2.0 Flash** model to analyze text and extract punishments for each person mentioned in the text.

To use the module, you need to initialize ```PunishmentExtractor``` class. By default, it will use the punishments configuration from [punishments.yaml](src/punishments.yaml). You can also specify your own YAML file path. You should also provide your api key for [Gemini (Google Cloud AI Studio)](https://console.cloud.google.com/apis/) to use the module. New users can get started with up to $300 in free credits now.

``` Python
from src.punishments import PunishmentExtractor

extractor = PunishmentExtractor(api_key='<your key is here>')

input_string = """Шестакова Александра Владимировича признать виновным в совершении преступлений, предусмотренных п. «з» ч.2 ст.111, п. «а» ч.3 ст.158 Уголовного кодекса Российской Федерации и назначить ему наказание: - по п. «з» ч.2 ст.111УК РФ – в виде лишения свободы на срок три года; - по п. «а» ч.3 ст.158 УК РФ – в виде лишения свободы на срок два года. На основании ч.3 ст. 69 Уголовного кодекса Российской Федерации по совокупности преступлений путем частичного сложения наказаний окончательно назначить Шестакову Александру Владимировичу наказание в виде лишения свободы на срок четыре года. В соответствии со ст. 70 Уголовного кодекса Российской Федерации, по совокупности приговоров, к наказанию, назначенному по настоящему приговору, частично присоединить неотбытую часть наказания по приговору от 18.05.2021 Уватского районного суда Тюменской области и окончательно назначить Шестакову Александру Владимировичу наказание в виде лишения свободы на срок 4 (четыре) года 6 (шесть) месяцев, с отбыванием в исправительной колонии общего режима. Меру пресечения в виде подписки о невыезде и надлежащем поведении Шестакову Александру Владимировичу изменить на меру пресечения в виде заключения под стражу, взять его под стражу немедленно в зале суда. Срок наказания Шестакову Александру Владимировичу исчислять со дня вступления настоящего приговора в законную силу. В соответствии с п. "б" ч. 3.1 ст. 72 Уголовного кодекса Российской Федерации время содержания под стражей Шестакову Александру Владимировичу с 18 мая 2023 года до дня вступления настоящего приговора в законную силу зачесть в срок лишения свободы из расчета один день содержания под стражей за полтора дня отбывания наказания в исправительной колонии общего режима."""

initial_string, res = punishment_extractor.find_punishemtns(df.at[9, "text_decision"])
print(res)
#{'Шестаков Александр Владимирович': {'1': {'punishment': 'лишение свободы на определенный срок', 'type': 'колония общего режима', 'severity': {'years': # 4, 'months': 6, 'rubles': 0, 'days': 0, 'hours': 0}}}}
```

### Municipality Extractor

All courts in Russia have their own special code that can be found in this library's dictionary ([mun_court_dict_v20250424.csv](data/interim/mun_court_dict_v20250424.csv), column ```court_code```) or on [the State Services NSI website](https://esnsi.gosuslugi.ru/classifiers?p=1) (search *Судебные органы*). 

The ```districts``` module enables you to receive the region, municipality and oktmo code (as of March 2025) for a given court code:

- Use ```get_municipality``` to receive data for the given court code
- Use ```process dataframe``` to process dataframe with court codes saved in the specified column

``` Python
from src.districts import MunicipalityExtractor

extractor = MunicipalityExtractor()

extractor.get_municipality("61RS0006")
# ('Ростовская', 'Городской округ Город Ростов-на-Дону', '60701000')

data = extractor.process_dataframe(data, "court_code")
# will add columns 'region', 'municipality', 'oktmo' to the given dataframe
```

The module **requires valid court codes to function properly**. We intentionally omitted the ability to search districts by court 
names since many courts in Russia share identical names. However, you can implement such functionality yourself using the provided 
court dictionary ([mun_court_dict_v20250212.csv](data/interim/mun_court_dict_v20250424.csv)) if needed.

To determine the territorial jurisdiction of each district court, we used several data sources. First, the API at [территориальная-подсудность.рф](https://xn----7sbarabva2auedgdkhac2adbeqt1tna3e.xn--p1ai/), second, the territorial jurisdiction module on court websites, and third, information from open sources. Some courts are abolished over time, so the information needs to be updated regularly.

### Gender Extractor

The ```gender``` module enables to extract data about defendants and determine their gender. To improve accuracy, the module utilizes two libraries: ```russiannames``` and ```pytrovich```.

To use ```russiannames``` library you need to install MongoDB instance. Instruction is available in [the library repository](https://github.com/datacoon/russiannames). By default parameter ```russian_names_db``` of ```GenderExtractor``` is set to ```False```. To use ```russiannames``` set ```russian_names_db``` to ```True```.

You can apply ```extract_genders``` method to any string to retrive people names and their corresponding genders.

``` Python
from src.gender import GenderExtractor

extractor = GenderExtractor(russian_names_db = False)

extractor.extract_genders("Волостных Владислав Витальевич - ст.291 ч.3; ст.222 ч.1; ст.290 ч.5 п.в; ст.290 ч.5 п.в; ст.290 ч.5 п.в УК РФ")
#[('Волостных Владислав Витальевич', 'M')]
```

There are several possible answers:

- **M**: male
- **F**: female
- **U**: undefined (when neither of the two methods could determine the gender)
- **C**: contradiction (when two methods returned different results)

### Articles Extractor

The ```articles``` module extracts structured information about legal articles, their parts, and subparts from strings containing charges. It supports both Criminal Code (УК) and Code of Administrative Offenses (КоАП) articles.

``` Python
from src.articles import ArticlesExtractor

extractor = ArticlesExtractor(remove_duplicates=True)

# Process single string
result = extractor.process_string("Губаев Борис Магомедович - ст.159 ч.2 УК РФ")

# Process DataFrame with parallel execution
results = extractor.process_dataframe(df, 'text_column', parallel=True, n_workers=4)
```

The output is a list of dictionaries, where each dictionary represents a person and contains:
- ```person```: Person identifier (e.g., "Person 1")
- ```articles```: List of dictionaries with article information:
  - ```article```: Article number (e.g., "159")
  - ```part```: Part number (e.g., "2")
  - ```subpart```: List of subpart letters (e.g., ["а", "б"])
- ```code_type```: Type of legal code ("CRIMINAL", "ADMIN", "MATERIAL", or "UNKNOWN")

Example output:
```python
[
    {
        'person': 'Person 1',
        'articles': [
            {
                'article': '159',
                'part': '2',
                'subpart': None
            }
        ],
        'code_type': 'CRIMINAL'
    }
]
```

The module supports:
- Multiple articles per person (separated by semicolons)
- Article ranges (using hyphens)
- Parallel processing for large datasets
- Optional duplicate removal
- Both Criminal Code (УК) and Administrative Code (КоАП) articles

## Contributors

[Adam Torosyan](https://github.com/adamtorosyan), Vitovt Kopytok (vitovt.kopytok@gmail.com)

## License

<a rel="license" href="https://creativecommons.org/licenses/by-nc-sa/4.0/"><img alt="Creative Commons License" style="border-width:0" src="https://i.creativecommons.org/l/by-nc-sa/4.0/88x31.png" /></a><br />
Creative Commons License Attribution-NonCommercial-ShareAlike 4.0 International (CC BY-NC-SA 4.0).

Copyright © the respective contributors, as shown by the `AUTHORS` file.
