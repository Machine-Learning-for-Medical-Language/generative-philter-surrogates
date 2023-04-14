import abc
from collections import defaultdict
import csv
from enum import Enum, auto
import datetime
import os
import random
import re
from typing import Dict, List, Set, Tuple

class PersonFields(Enum):
    FIRST_NAME = auto()
    LAST_NAME = auto()
    MIDDLE_NAME = auto()
    STREET = auto()
    CITY = auto()
    STATE = auto()
    ZIPCODE = auto()

DOCTOR_REQ_FIELDS = frozenset([PersonFields.FIRST_NAME, PersonFields.LAST_NAME, PersonFields.MIDDLE_NAME])
PATIENT_FIELDS = frozenset([pf for pf in PersonFields])

class HospitalFields(Enum):
    NAME = auto()
    STREET = auto()
    CITY = auto()
    COUNTY = auto()
    STATE = auto()
    ZIPCODE = auto()

class NPI(Enum):
    last_name = 5
    first_name = 6
    middle_name = 7

class USPTO(Enum):
    # source: http://www.census.gov/genealogy/names/
    last_name = 1
    first_name = 2
    middle_name = 3
    address = 5
    city = 6
    state = 7
    zipcode = 9

class Facility(Enum):
    # source: https://data.medicare.gov/data/hospital-compare
    hospital = 1
    address = 2
    city = 3
    state = 4
    zipcode = 5
    county = 6
    phone = 7


def parse_csv(file_csv, column, delimiter=',', quotechar='"'):
    print("file_csv %s column %s" % (file_csv, column))
    res = list()

    if isinstance(column, Enum):
        column = column.value

    # NOTE: 'mac_roman'
    # https://stackoverflow.com/questions/21504319/python-3-csv-file-giving-unicodedecodeerror-utf-8-codec-cant-decode-byte-err
    with open(file_csv, 'r', encoding='mac_roman') as csvfile:
        csvreader = csv.reader(csvfile, delimiter=delimiter, quotechar=quotechar)
        for row in csvreader:
            res.append(row[column])
    return res


def flipcoin() -> bool:
    """
    :return: bool random 75/25 True/False
    """
    return random.choice([True, True, True, False])


def abbreviate(tokens: List[str]) -> str:
    """Abbreviate a name.
    :param tokens: The name tokens.
    :return: The abbreviation.
    """
    return ''.join([token[0].upper() for token in tokens])


def read_names(names_file) -> Dict[str, str]:
    names = dict()

    name_count = 0
    male_count = 0
    female_count = 0

    with open(names_file, 'r') as fh:
        fh.readline()  # skip the header

        for line in fh:
            tokens = line.split(',')

            gender = tokens[0]
            names[tokens[1].upper()] = gender

            if gender == 'F':
                female_count += 1
            else:
                male_count += 1

            name_count += 1

    print(f"Parsed {name_count} total names ({male_count} male, {female_count} female).")

    return names


def randomize(parsed_list: list):
    """
    Given a list, return a randomized list with None type filtered
    :param parsed_list:
    :return:
    """
    random.shuffle(parsed_list)
    return list(filter(None, parsed_list))


class LazyLoadCache(object):
    def __init__(self, csv_file: str):
        """Ctor.
        :param csv_file: The CSV file to cache.
        """
        self.__cache = dict()
        self.__file_name = csv_file

    def get(self, column, rand=False):
        _key = self.__key(column)

        if _key not in self.__cache.keys():
            parsed = parse_csv(self.__file_name, column)
            self.__cache[_key] = randomize(parsed) if rand else parsed

        return self.__cache.get(_key)

    def __key(self, column):
        return "%s[%s]" % (self.__file_name, column)


class __Surrogates(object):
    def __init__(self, file_name: str):
        """Ctor.
        :param file_name: The surrogate data file.
        """
        self.__cache = LazyLoadCache(file_name)
        self.__file_name = file_name

    def get(self, col: Enum):
        return self.__cache.get(col)


class _PersonSurrogates(__Surrogates):
    __metaclass__ = abc.ABCMeta

    def __init__(self, file_name):
        super(_PersonSurrogates, self).__init__(file_name)

    @abc.abstractmethod
    def last_name(self):
        pass

    @abc.abstractmethod
    def first_name(self):
        pass

    @abc.abstractmethod
    def middle_name(self):
        pass

    def address(self):
        pass

    def city(self):
        pass

    def state(self):
        pass

    def zipcode(self):
        pass


class PatientSurrogates(_PersonSurrogates):
    def __init__(self):
        super(PatientSurrogates, self).__init__(USPTO_FILE)

    def last_name(self):
        return self.get(USPTO.last_name)

    def first_name(self):
        return self.get(USPTO.first_name)

    def middle_name(self):
        return self.get(USPTO.middle_name)

    def address(self):
        return self.get(USPTO.address)

    def city(self):
        return self.get(USPTO.city)

    def state(self):
        return self.get(USPTO.state)

    def zipcode(self):
        return self.get(USPTO.zipcode)


class DoctorSurrogates(_PersonSurrogates):
    def __init__(self):
        super(DoctorSurrogates, self).__init__(NPI_FILE)

    def first_name(self):
        return self.get(NPI.first_name)

    def last_name(self):
        return self.get(NPI.last_name)

    def middle_name(self):
        return self.get(NPI.middle_name)


class HospitalSurrogates(__Surrogates):
    def __init__(self):
        super(HospitalSurrogates, self).__init__(CMS_FILE)

    def name(self):
        return self.get(Facility.hospital)

    def address(self):
        return self.get(Facility.address)

    def city(self):
        return self.get(Facility.city)

    def county(self):
        return self.get(Facility.county)

    def state(self):
        return self.get(Facility.state)

    def zipcode(self):
        return self.get(Facility.zipcode)

    def phone_numeric(self):
        return self.get(Facility.phone)

    def date_start(self):
        return self.get(Facility.date_start)

    def date_stop(self):
        return self.get(Facility.date_stop)


#################################################################################

def get_random_person(surrogates: _PersonSurrogates,
                      req_fields: Set[PersonFields],
                      names: Dict[str, str] = None,
                      gender: str = None,
                      cache: Dict[str, List[Dict[PersonFields, str]]] = None) -> Dict[PersonFields, str]:
    """Randomly select from the population data.
    :param surrogates: The surrogate data to select from.
    :param req_fields: The set of fields that must have a valid value.
    :param names: Mapping of name to most likely gender.
    :param gender: The target gender.
    :param cache: Valid surrogates that were previously the wrong gender.
    :return: An individual's info.
    """
    if gender and len(cache[gender]):
        return cache[gender].pop()

    person = {}

    while True:
        index = random.randint(0, len(surrogates.first_name()))

        person[PersonFields.FIRST_NAME] = surrogates.first_name().pop(index).strip()
        person[PersonFields.LAST_NAME] = surrogates.last_name().pop(index).strip()
        person[PersonFields.MIDDLE_NAME] = surrogates.middle_name().pop(index).strip()
        person[PersonFields.STREET] = surrogates.address().pop(index).strip() if surrogates.address() else ''
        person[PersonFields.CITY] = surrogates.city().pop(index).strip() if surrogates.city() else ''
        person[PersonFields.STATE] = surrogates.state().pop(index).strip() if surrogates.state() else ''
        person[PersonFields.ZIPCODE] = surrogates.zipcode().pop(index).strip() if surrogates.zipcode() else ''

        for field in req_fields:
            if not person[field]:
                break
        else:  # we have a valid person
            if gender:
                surrogate_gender = names.get(person[PersonFields.FIRST_NAME].upper(),
                                             names.get(person[PersonFields.MIDDLE_NAME].upper()))
                if gender != surrogate_gender:
                    if surrogate_gender:
                        cache[surrogate_gender].append(person.copy())

                    continue

            return person


def get_random_hospital(surrogates: HospitalSurrogates) -> Dict[HospitalFields, str]:
    """Randomly select from the hospital data.
    :param surrogates: The surrogate data to select from.
    :return: An hosptial's info.
    """
    hospital = {}

    while True:
        index = random.randint(0, len(surrogates.name()))

        hospital[HospitalFields.NAME] = surrogates.name().pop(index).strip()
        hospital[HospitalFields.STREET] = surrogates.address().pop(index).strip()
        hospital[HospitalFields.CITY] = surrogates.city().pop(index).strip()
        hospital[HospitalFields.COUNTY] = surrogates.county().pop(index).strip()
        hospital[HospitalFields.STATE] = surrogates.state().pop(index).strip()
        hospital[HospitalFields.ZIPCODE] = surrogates.zipcode().pop(index).strip()

        for field in HospitalFields:
            if not hospital[field]:
                break
        else:
            return hospital


def make_surrogate_dates(date_tags: List[Dict[str, str]]) -> Dict[str, str]:
    """Process the date tags and map them to realistic values.
    :param date_tags: The I2B2 date tags.
    :return: Mapping of I2B2 date to surrogate date.
    """
    min_year = 2000
    max_year = datetime.date.today().year
    all_dates = dict()
    for tag in date_tags:
        i2b2_date = tag['text']
        parsed = parse_date_and_format(i2b2_date)

        if parsed is None:
            if i2b2_date.isnumeric():
                parsed = (datetime.date(year=int(i2b2_date), month=1, day=1), '%Y')
            else:
                continue

        # don't worry about dates where default year was used
        if parsed[0].year == 1900:
            continue

        all_dates[i2b2_date] = parsed

    if len(all_dates) == 0:
        return {}

    max_obs_date = max(set([d for d, _ in all_dates.values()]))
    max_obs_year = max_obs_date.year
    if max_obs_date > datetime.date.today():
        max_obs_year += 1

    date_map = dict()
    for i2b2_date, parsed in all_dates.items():
        parsed_date, date_format = parsed
        parsed_year = parsed_date.year
        if max_obs_year - parsed_year >= 100:
            parsed_year += 100

        new_date = parsed_date.replace(year=max(max_year - max_obs_year + parsed_year, min_year))

        date_map[i2b2_date] = new_date.strftime(date_format)

    return date_map


def tokenize_name(name):
    return re.findall(r"[\w\.\-]+", name)


def guess_patient_gender(record_text: str, patient_tags: List[Dict[str, str]], names: Dict[str, str]):
    """Use context clues to guess the patient's sex.
    :param record_text: The body of the medical record.
    :param patient_tags: The PATIENT tags.
    :param names: Mapping of name to most likely gender.
    :return: The best guess at gender if possible; otherwise None.s
    """
    if len(patient_tags):
        patient_names = set(name.upper() for tag in patient_tags for name in tokenize_name(tag['text']))
        for pat_name in patient_names:
            if pat_name in names:
                return names[pat_name]

        for tag in patient_tags:
            tag_start = int(tag['start'])
            preceding = record_text[(tag_start - 5):tag_start]

            if 'Ms' in preceding or 'Mrs' in preceding:
                return 'F'

            if 'Mr' in preceding:
                return 'M'

    return 'M' if random.choice([True, False]) else 'F'


def num_tokens(text: str) -> int:
    return len(text.split())


def phi_hospital_name(i2b2_text: str, hospital_name: str) -> str:
    if num_tokens(i2b2_text) == 1 and i2b2_text.isupper():
        return abbreviate(hospital_name.title().split())

    return hospital_name.title()


def format_name(i2b2_name: str, surrogate_name: str) -> str:
    """Handle formatting of first/middle name fields.
    :param i2b2_name: The I2B2 name field.
    :param surrogate_name: The surrogate name to format.
    :return: The formatted surrogate name.
    """
    if len(i2b2_name) == 1:
        return surrogate_name[0]

    if len(i2b2_name) == 2 and i2b2_name[1] == '.':
        return surrogate_name[0] + '.'

    return surrogate_name


def phi_person_text(i2b2_text: str, person_info: Dict[PersonFields, str], prefix: str, preceding: str) \
        -> Tuple[str, List[Tuple[str, str]]]:
    """Format name text.
     :param i2b2_text: The name text from the I2B2 record.
     :param person_info: The person data to format.
     :param prefix: The patient/doctor prefix for labeling name fields.
     :param preceding: The raw text preceding the name PHI.
     :return: The formatted name replacement text, and individual name labels and values.
     """
    # strip suffixes
    if i2b2_text.endswith(', Jr.') or i2b2_text.endswith(', III'):
        i2b2_text = i2b2_text[:-5]

    name_tokens = tokenize_name(i2b2_text)
    num_name_tokens = len(name_tokens)

    first_name = person_info[PersonFields.FIRST_NAME]
    last_name = person_info[PersonFields.LAST_NAME]
    middle_name = person_info[PersonFields.MIDDLE_NAME]

    first_label = f"{prefix}_first"
    middle_label = f"{prefix}_middle"
    last_label = f"{prefix}_last"
    initials_label = f"{prefix}_initials"

    if ',' in i2b2_text:  # McMurry, Andrew
        # check for multi-token last name
        last_tokens = tokenize_name(i2b2_text.split(',')[0])
        if len(last_tokens) > 1:
            num_name_tokens -= len(last_tokens) - 1

        first_name = format_name(name_tokens[1], first_name)
        person_text = f"{last_name}, {first_name}"  # McMurry, Andrew
        fields = [(last_label, last_name), ('COMMA', ','), (first_label, first_name)]

        if num_name_tokens >= 3:
            middle_name = format_name(name_tokens[2], middle_name)

            person_text = f"{person_text} {middle_name}"  # McMurry, Andrew John
            fields.append((middle_label, middle_name))
    else:
        first_name = format_name(name_tokens[0], first_name)
        if num_name_tokens >= 3:  # Andrew John McMurry
            middle_name = format_name(name_tokens[1], middle_name)
            person_text = f"{first_name} {middle_name} {last_name}"
            fields = [(first_label, first_name), (middle_label, middle_name), (last_label, last_name)]
        elif num_name_tokens == 2:  # Andrew McMurry
            person_text = f"{first_name} {last_name}"
            fields = [(first_label, first_name), (last_label, last_name)]
        else:
            if i2b2_text.isupper():  # AM, AJM
                if len(i2b2_text) == 2:
                    person_text = abbreviate([first_name, last_name])
                else:
                    person_text = abbreviate([first_name, middle_name, last_name])

                fields = [(initials_label, person_text)]
            else:  # Andrew or McMurry
                flip = flipcoin()  # bias to last name for doctors and first name for patients
                if prefix == 'dr':
                    if 'Dr' in preceding or ' DR ' in preceding or 'Nurse' in preceding or ' dr ' in preceding or \
                            ' dr.' in preceding or 'PCP' in preceding or 'Ms' in preceding or flip:
                        person_text = last_name
                        fields = [(last_label, last_name)]
                    else:
                        person_text = first_name
                        fields = [(first_label, first_name)]
                else:
                    if 'Mr' in preceding or 'Ms' in preceding or not flip:
                        person_text = last_name
                        fields = [(last_label, last_name)]
                    else:
                        person_text = first_name
                        fields = [(first_label, first_name)]

    return person_text, fields


def get_random_digits(n: int) -> List[int]:
    """Get N random integers between 0 and 9 (inclusive).
    @param n: The number of integers to generate.
    @return: List of N integers.
    """
    return [random.choice(range(10)) for _ in range(n)]


def get_hospital_name_or_abbr(hospital_name: str) -> str:
    """Get the hospital name either in full or abbreviated.
    @param hospital_name: The original hospital name.
    @return: The formatted name.
    """
    return abbreviate(hospital_name.split()) if flipcoin() else hospital_name


class MimicSurrogateInjector:
    __PATIENTS = PatientSurrogates()
    __PHI_PATTERN = re.compile(r'\[\*{2}.+?\*{2}\]')
    __SHORT_DATE_PATTERN = re.compile(r'\d{1,2}-\d{1,2}$')
    __DOCTORS = DoctorSurrogates()
    __HOSPITALS = HospitalSurrogates()

    def __init__(self):
        self.substitution_map = dict()
        self._patient_surrogates = dict()
        self._doctor_cache = defaultdict(list)
        self._hospitals = dict()
        self._patient_id = 0
        self.__last_doc = None
        self.__last_doc_name_field = None

        self.__get_valid_surrogates()

        # file located in s3://biomed-raw-data/resources
        self._names_by_gender = read_names(os.path.join(os.path.dirname(__file__),
                                                        'us-likelihood-of-gender-by-name-in-2014.csv'))

        self._CCUs = ('CCU', 'CSRU', 'MICU', 'SICU', 'TSICU')
        self._COUNTRIES = ('Mexico', 'Canada')
        self._OLD_AGES = tuple(str(age) for age in range(90, 106))
        self._UNIVERSITIES = ('Boston University', 'Boston College', 'Harvard', 'MIT', 'Northeastern', 'Tufts')
        self._HOLIDAYS = ('Chrismas', 'New Years', 'Memorial Day', '4th of July', 'Labor Day', 'Thanksgiving')
        self._WARDS = ('AMU', 'AEC', 'Coronary Care', 'HDU', 'ICU', 'Geriatrics')
        self._COMPANIES = ('Barnes Group', 'Headwaters Inc.', 'Knowles Corporation',
                           'Zoetis Inc.', 'Ventas Inc.', 'PartnerRe Ltd.')
        self._STATES = ('Alabama', 'AL', 'Alaska', 'AK', 'Arizona', 'AZ', 'Arkansas', 'AR', 'California', 'CA',
                        'Colorado', 'CO', 'Connecticut', 'CT', 'Delaware', 'DE', 'Florida', 'FL', 'Georgia', 'GA',
                        'Hawaii', 'HI', 'Idaho', 'ID', 'Illinois', 'IL', 'Indiana', 'IN', 'Iowa', 'IA', 'Kansas',
                        'KS', 'Kentucky', 'KY', 'Louisiana', 'LA', 'Maine', 'ME', 'Maryland', 'MD', 'Massachusetts',
                        'MA', 'Michigan', 'MI', 'Minnesota', 'MN', 'Mississippi', 'MS', 'Missouri', 'MO', 'Montana',
                        'MT', 'Nebraska', 'NE', 'Nevada', 'NV', 'New Hampshire', 'NH', 'New Jersey', 'NJ',
                        'New Mexico', 'NM', 'New York', 'NY', 'North Carolina', 'NC', 'North Dakota', 'ND', 'Ohio',
                        'OH', 'Oklahoma', 'OK', 'Oregon', 'OR', 'Pennsylvania', 'PA', 'Rhode Island', 'RI',
                        'South Carolina', 'SC', 'South Dakota', 'SD', 'Tennessee', 'TN', 'Texas', 'TX', 'Utah', 'UT',
                        'Vermont', 'VT', 'Virginia', 'VA', 'Washington', 'WA', 'West Virginia', 'WV', 'Wisconsin',
                        'WI', 'Wyoming', 'WY')
        self._DOMAINS = (
            'medal.com', 'gmail.com', 'yahoo.com', 'hotmail.com', 'protonmail.com', 'bwh.org', 'harvard.edu')
        self._ETHNICITIES = ('african american', 'caucasian', 'hispanic')

    def inject(self, record_txt: str) -> str:
        self.substitution_map.clear()

        substitutions = dict()

        pat_keys = list(self._patient_surrogates)

        patient = self._patient_surrogates[random.choice(pat_keys)]
        while True:
            phi_match = self.__PHI_PATTERN.search(record_txt)
            if not phi_match:
                break

            phi_text = phi_match[0]
            if phi_text not in substitutions:
                substitutions[phi_text] = self.__get_phi_sub(phi_match, self._patient_id, patient)

            substitution = substitutions[phi_text]
            sub_text = ' '.join(substitution)

            self.substitution_map[(phi_match.start(), phi_match.end())] = sub_text

            record_txt = record_txt.replace(phi_text, sub_text, 1)

        self._patient_id += 1

        return record_txt

    def __get_valid_surrogates(self):
        """Pre-filter surrogates that are missing required information."""
        for i in range(len(self.__PATIENTS.first_name())):
            person = dict()
            person[PersonFields.FIRST_NAME] = self.__PATIENTS.first_name()[i].strip()
            person[PersonFields.LAST_NAME] = self.__PATIENTS.last_name()[i].strip()
            person[PersonFields.MIDDLE_NAME] = self.__PATIENTS.middle_name()[i].strip()
            person[PersonFields.STREET] = self.__PATIENTS.address()[i].strip()
            person[PersonFields.CITY] = self.__PATIENTS.city()[i].strip()
            person[PersonFields.STATE] = self.__PATIENTS.state()[i].strip()
            person[PersonFields.ZIPCODE] = self.__PATIENTS.zipcode()[i].strip()

            for field in PATIENT_FIELDS:
                if not person[field]:
                    break
            else:
                self._patient_surrogates[i] = person

        operations_logger.info(f'Kept {len(self._patient_surrogates)} patient surrogates with required information.')

    def __get_phi_sub(self, match, subject_id: int, patient) -> Tuple:
        """Get the substitution for a PHI text blob.
        @param match: The PHI match.
        @param subject_id: The patient id.
        @return: The text to substitute, demographics type, and PHI type.
        """
        phi_text = match[0].replace('[**', '').replace('**]', '')

        if phi_text.startswith('Country'):
            return random.choice(self._COUNTRIES),

        if phi_text.startswith('Age over 90'):
            return random.choice(self._OLD_AGES),

        if phi_text.startswith('University'):
            return random.choice(self._UNIVERSITIES),

        if phi_text.startswith('Holiday'):
            return random.choice(self._HOLIDAYS),

        if phi_text.startswith('Wardname') or phi_text.startswith('Hospital Ward Name'):
            return random.choice(self._WARDS),

        if phi_text.startswith('Location') or phi_text.startswith('Numeric Identifier'):
            return f'Room {random.choice(range(1, 501))}',

        if phi_text.startswith('Company'):
            return random.choice(self._COMPANIES),

        if phi_text.startswith('Known lastname'):
            return patient[PersonFields.LAST_NAME],

        if phi_text.startswith('State'):
            return random.choice(self._STATES),

        if phi_text.startswith('Hospital Unit Name'):
            return random.choice(self._CCUs),

        if phi_text.startswith('Hospital'):
            if subject_id not in self._hospitals:
                self._hospitals[subject_id] = get_random_hospital(self.__HOSPITALS)

            return get_hospital_name_or_abbr(self._hospitals[subject_id][HospitalFields.NAME].title()),

        if phi_text.startswith('Telephone'):
            area = str(random.choice(range(2, 10))) + ''.join(str(i) for i in get_random_digits(2))
            prefix = ''.join(str(i) for i in get_random_digits(3))
            line = ''.join(str(i) for i in get_random_digits(4))

            return f'{area}-{prefix}-{line}',

        if phi_text.startswith('Dictator') or phi_text.startswith('CC Contact') or phi_text.startswith('Attending'):
            if phi_text not in self._doctor_cache:
                self._doctor_cache[phi_text].append(get_random_person(self.__DOCTORS, DOCTOR_REQ_FIELDS))

            person = self._doctor_cache[phi_text][0]

            return person[PersonFields.FIRST_NAME], person[PersonFields.LAST_NAME]

        if phi_text.startswith('E-mail'):
            domain = random.choice(self._DOMAINS)

            if flipcoin():
                first_name = patient[PersonFields.FIRST_NAME]
                middle_init = patient[PersonFields.MIDDLE_NAME][0]
                last_name = patient[PersonFields.LAST_NAME]

                if flipcoin():
                    if flipcoin():
                        return f'{first_name[0]}{last_name}@{domain}',

                    return f'{first_name[0]}{middle_init}{last_name}@{domain}',

                return f'{first_name}.{last_name}@{domain}',

            doctor = self.__get_doctor(subject_id)

            return f'{doctor[PersonFields.FIRST_NAME]}.{doctor[PersonFields.LAST_NAME]}@{domain}',

        if phi_text.startswith('Doctor'):
            if 'First' in phi_text:
                return self.__get_dr_name(PersonFields.FIRST_NAME, subject_id),

            return self.__get_dr_name(PersonFields.LAST_NAME, subject_id),

        if phi_text.startswith('Last Name') or phi_text.startswith('lastname'):
            return self.__get_dr_name(PersonFields.LAST_NAME, subject_id),

        if 'First Name' in phi_text or phi_text.startswith('firstname'):
            return self.__get_dr_name(PersonFields.FIRST_NAME, subject_id),

        if phi_text.startswith('Initial'):
            person = self.__get_doctor(subject_id)

            if phi_text.startswith('Initial '):
                return f'{person[PersonFields.FIRST_NAME][0]}.',

            return f'{person[PersonFields.FIRST_NAME][0]}.{person[PersonFields.MIDDLE_NAME][0]}.',

        if phi_text.startswith('Name'):
            person = self.__get_doctor(subject_id)

            if phi_text.startswith('Name Initial') or phi_text.startswith('Name (NI)'):
                return f'{person[PersonFields.FIRST_NAME][0]}.', person[PersonFields.LAST_NAME],

            return person[PersonFields.FIRST_NAME], person[PersonFields.LAST_NAME]

        if 'Address' in phi_text:
            if phi_text.startswith('Street Address'):
                if subject_id not in self._hospitals:
                    self._hospitals[subject_id] = get_random_hospital(self.__HOSPITALS)

                hospital = self._hospitals[subject_id]

                return (hospital[HospitalFields.STREET], hospital[HospitalFields.CITY], hospital[HospitalFields.STATE],
                        hospital[HospitalFields.ZIPCODE])

        if 'Number' in phi_text:
            return ''.join(str(i) for i in get_random_digits(10)),

        if 'Ethnicity' in phi_text:
            return random.choice(self._ETHNICITIES),

        date_sub = self.__get_date_sub(phi_text)
        if date_sub:
            return date_sub,

        return phi_text,

    def __get_date_sub(self, phi_text: str) -> str:
        """Try to process a PHI field as a date.
        @param phi_text: The PHI field to process.
        @return: The text to substitute, if the PHI is a date.
        """
        date_formats = ['%Y-%m-%d', '%m/%Y', '%Y', '%B %Y', ', %Y']
        YEARS = [str(y) for y in range(2000, 2013)]
        MONTHS = [f'0{m}'[-2:] for m in range(1, 13)]
        MONTH_NAMES = ['January', 'February', 'March', 'April', 'May', 'June', 'July', 'August', 'September',
                       'October', 'November', 'December']
        DAYS = [f'0{m}'[-2:] for m in range(1, 28)]

        if phi_text.lower().startswith('date range'):
            r_year = random.choice(YEARS)
            rindex = random.choice(range(1, len(MONTHS)))

            return f'{MONTHS[random.choice(range(rindex))]}/{r_year} - {MONTHS[rindex]}/{r_year}'

        if phi_text.startswith('Year'):
            if phi_text.startswith('Year (4 digits)'):
                return random.choice(YEARS)

            if phi_text.startswith('Year/Month/Day'):
                return f'{random.choice(YEARS)}/{random.choice(MONTHS)}/{random.choice(DAYS)}'

            if phi_text.startswith('Year (2 digits)'):
                return random.choice(YEARS[-2:])

            if phi_text.startswith('Year/Month'):
                return f'{random.choice(YEARS)}/{random.choice(MONTHS)}'

        if phi_text == 'Day Month':
            return f'{random.choice(DAYS)} {random.choice(MONTH_NAMES)}'

        if phi_text.startswith('Month'):
            if phi_text.startswith('Month (only) '):
                return f'{random.choice(MONTH_NAMES)}'

            if phi_text.startswith('Month/Day/Year '):
                return f'{random.choice(MONTHS)}/{random.choice(DAYS)}/{random.choice(YEARS)}'

            if phi_text.startswith('Month/Day '):
                return f'{random.choice(MONTHS)}/{random.choice(DAYS)}'

            if phi_text.startswith('Month/Year '):
                return f'{random.choice(MONTHS)}/{random.choice(YEARS)}'

            if phi_text.startswith('Month Day '):
                return f'{random.choice(MONTH_NAMES)} {random.choice(DAYS)}'

            if phi_text.startswith('Month Year '):
                return f'{random.choice(MONTH_NAMES)} {random.choice(YEARS)}'

        if self.__SHORT_DATE_PATTERN.match(phi_text):
            return phi_text

        for df in date_formats:
            try:
                phi_date = datetime.datetime.strptime(phi_text, df)

                if phi_date.month == 2 and phi_date.day == 29:
                    phi_date = phi_date.replace(day=28)

                return phi_date.strftime(df)
            except:
                pass

    def __get_dr_name(self, name_field: PersonFields, subject_id: int) -> str:
        """Get a formatted doctor name.
        @param name_field: The name part to retrieve.
        @param subject_id: The patient id.
        @return: The doctor name.
        """
        if not self.__last_doc or not self.__last_doc_name_field or self.__last_doc_name_field == name_field:
            self.__last_doc = self.__get_doctor(subject_id)

        if self.__last_doc_name_field:
            self.__last_doc_name_field = None
        else:
            self.__last_doc_name_field = name_field

        return self.__last_doc[name_field]

    def __get_doctor(self, subject_id: int) -> Dict[PersonFields, str]:
        """Get a doctor for a patient record.
        @param subject_id: The patient id.
        """
        n_docs = 5
        if subject_id not in self._doctor_cache:
            self._doctor_cache[subject_id].append(get_random_person(self.__DOCTORS, DOCTOR_REQ_FIELDS))
        elif len(self._doctor_cache[subject_id]) != n_docs:
            for _ in range(n_docs - 1):
                self._doctor_cache[subject_id].append(get_random_person(self.__DOCTORS, DOCTOR_REQ_FIELDS))

        return random.choice(self._doctor_cache[subject_id])
